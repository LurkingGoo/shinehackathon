"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AlertStatus } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import {
  FallStateMachine,
  measureFrame,
  type LandmarkPoint,
  type Posture,
  type WatchState,
} from "@/lib/pose/fallHeuristic";
import type { PoseEngine } from "@/lib/pose/engine";
import styles from "./watch.module.css";

/**
 * /watch — the camera acute source (feature-spec §1b). MediaPipe pose runs
 * entirely in this browser; the unit-tested state machine (upright →
 * horizontal within 1.8 s → still 3 s) decides, and a detection POSTs
 * through the data seam to fire the SAME incident path as an accelerometer
 * fall: caseload preemption, SSE re-rank, Telegram alert.
 */

const STILL_TARGET_MS = 3000;

// Minimal skeleton: torso box + limbs, MediaPipe pose indices.
const BONES: Array<[number, number]> = [
  [11, 12], [11, 23], [12, 24], [23, 24], // torso
  [11, 13], [13, 15], [12, 14], [14, 16], // arms
  [23, 25], [25, 27], [24, 26], [26, 28], // legs
];

type EngineStatus = "off" | "loading" | "running" | "error";

interface LogEntry {
  at: string;
  text: string;
}

export function WatchPanel() {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const engineRef = useRef<PoseEngine | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const rafRef = useRef<number>(0);
  const prevLandmarksRef = useRef<LandmarkPoint[] | undefined>(undefined);
  const smRef = useRef(new FallStateMachine());
  const lastUiPushRef = useRef(0);

  const [engineStatus, setEngineStatus] = useState<EngineStatus>("off");
  const [assetSource, setAssetSource] = useState<"local" | "cdn" | null>(null);
  const [posture, setPosture] = useState<Posture>("no-person");
  const [watchState, setWatchState] = useState<WatchState>("idle");
  const [stillnessMs, setStillnessMs] = useState(0);
  const [log, setLog] = useState<LogEntry[]>([]);
  const [sending, setSending] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [alerts, setAlerts] = useState<AlertStatus | null>(null);

  useEffect(() => {
    dataClient.getAlertStatus().then(setAlerts).catch(() => setAlerts(null));
  }, []);

  const pushLog = useCallback((text: string) => {
    const at = new Date().toLocaleTimeString([], {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
    setLog((l) => [{ at, text }, ...l].slice(0, 8));
  }, []);

  const report = useCallback(
    async (payload?: { stillnessS?: number; confidence?: number; note?: string }) => {
      setSending(true);
      try {
        await dataClient.reportCameraFall(payload);
        pushLog(
          payload
            ? `Fall detected — sent to the dashboard (confidence ${Math.round(
                (payload.confidence ?? 0) * 100,
              )}%)`
            : "Test detection sent to the dashboard",
        );
        // The Telegram dispatch resolves on a backend thread a beat later —
        // fetch its actual outcome so the alert leg is never silent.
        setTimeout(async () => {
          try {
            const status = await dataClient.getAlertStatus();
            setAlerts(status);
            const outcome = status.lastDispatch?.outcome;
            pushLog(
              outcome === "sent"
                ? "Telegram alert delivered"
                : outcome === "failed"
                  ? "Telegram alert FAILED to send"
                  : "Telegram not configured — no caregiver ping sent",
            );
          } catch {
            /* status endpoint unreachable — leave the log as-is */
          }
        }, 1500);
      } catch {
        pushLog("Could not reach the scoring service — detection NOT sent");
      } finally {
        setSending(false);
      }
    },
    [pushLog],
  );

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    engineRef.current?.close();
    engineRef.current = null;
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null;
    prevLandmarksRef.current = undefined;
    smRef.current = new FallStateMachine();
    if (videoRef.current) videoRef.current.srcObject = null;
    const canvas = canvasRef.current;
    canvas?.getContext("2d")?.clearRect(0, 0, canvas.width, canvas.height);
    setEngineStatus("off");
    setPosture("no-person");
    setWatchState("idle");
    setStillnessMs(0);
  }, []);

  const drawOverlay = useCallback((landmarks: LandmarkPoint[] | undefined) => {
    const canvas = canvasRef.current;
    const video = videoRef.current;
    if (!canvas || !video) return;
    if (canvas.width !== video.videoWidth) canvas.width = video.videoWidth;
    if (canvas.height !== video.videoHeight) canvas.height = video.videoHeight;
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    if (!landmarks) return;
    ctx.strokeStyle = "rgba(198, 93, 59, 0.85)"; // --brand
    ctx.fillStyle = "rgba(198, 93, 59, 0.9)";
    ctx.lineWidth = 3;
    for (const [a, b] of BONES) {
      const pa = landmarks[a];
      const pb = landmarks[b];
      if (!pa || !pb) continue;
      ctx.beginPath();
      ctx.moveTo(pa.x * canvas.width, pa.y * canvas.height);
      ctx.lineTo(pb.x * canvas.width, pb.y * canvas.height);
      ctx.stroke();
    }
    for (const p of landmarks) {
      ctx.beginPath();
      ctx.arc(p.x * canvas.width, p.y * canvas.height, 3.5, 0, Math.PI * 2);
      ctx.fill();
    }
  }, []);

  const start = useCallback(async () => {
    setErrorMsg(null);
    setEngineStatus("loading");
    try {
      const [{ createPoseEngine }, stream] = await Promise.all([
        import("@/lib/pose/engine"),
        navigator.mediaDevices.getUserMedia({
          video: { width: 960, height: 540, facingMode: "user" },
          audio: false,
        }),
      ]);
      const video = videoRef.current;
      if (!video) throw new Error("video element missing");
      video.srcObject = stream;
      streamRef.current = stream;
      await video.play();

      const engine = await createPoseEngine();
      engineRef.current = engine;
      setAssetSource(engine.source);
      smRef.current = new FallStateMachine();
      setEngineStatus("running");
      pushLog(`Camera watching (pose model: ${engine.source})`);

      const loop = () => {
        const v = videoRef.current;
        const eng = engineRef.current;
        if (!v || !eng) return;
        const now = performance.now();
        if (v.readyState >= 2) {
          const landmarks = eng.detect(v, now);
          const m = measureFrame(landmarks, prevLandmarksRef.current);
          prevLandmarksRef.current = landmarks;
          const event = smRef.current.update(m, now);
          drawOverlay(landmarks);
          if (event) {
            void report(event);
          }
          if (now - lastUiPushRef.current > 150) {
            lastUiPushRef.current = now;
            setPosture(m.posture);
            setWatchState(smRef.current.state);
            setStillnessMs(smRef.current.stillnessMs);
          }
        }
        rafRef.current = requestAnimationFrame(loop);
      };
      rafRef.current = requestAnimationFrame(loop);
    } catch (err) {
      console.error("[watch] engine start failed:", err);
      stop();
      setEngineStatus("error");
      setErrorMsg(
        err instanceof DOMException && err.name === "NotAllowedError"
          ? "Camera permission was denied. Allow camera access and try again."
          : "Could not start the camera engine. Check the connection (the pose model loads from a CDN on first run) and try again.",
      );
    }
  }, [drawOverlay, pushLog, report, stop]);

  useEffect(() => stop, [stop]);

  const stateChip = (() => {
    if (engineStatus !== "running")
      return { cls: styles.chipIdle, label: engineStatus === "loading" ? "Loading…" : "Camera off" };
    if (watchState === "fallen-still")
      return { cls: styles.chipAlarm, label: "ON THE GROUND — confirming stillness" };
    if (watchState === "cooldown") return { cls: styles.chipCooldown, label: "Alert sent · cooldown" };
    if (posture === "no-person") return { cls: styles.chipIdle, label: "No person in view" };
    if (posture === "horizontal") return { cls: styles.chipWatch, label: "Lying down (no alarm)" };
    return { cls: styles.chipOk, label: posture === "upright" ? "Upright · monitoring" : "Moving · monitoring" };
  })();

  const stillPct = Math.min(100, (stillnessMs / STILL_TARGET_MS) * 100);

  return (
    <div className={styles.app}>
      <header className={styles.top}>
        <div>
          <h1 className={styles.brandTitle}>A camera that knows a fall from a lie-down</h1>
          <p className={styles.brandSub}>
            Pose estimation runs in this browser — upright, then horizontal within two
            seconds, then three seconds of stillness. Only then does it alarm.
          </p>
        </div>
        <a className={styles.backLink} href="/">
          Open the triage dashboard &rarr;
        </a>
      </header>

      <div className={styles.grid}>
        <section className={styles.stage} aria-label="Live camera with pose overlay">
          <div className={styles.videoWrap}>
            {/* eslint-disable-next-line jsx-a11y/media-has-caption */}
            <video ref={videoRef} className={styles.video} playsInline muted />
            <canvas ref={canvasRef} className={styles.overlay} />
            {engineStatus !== "running" && (
              <div className={styles.videoPlaceholder}>
                {engineStatus === "loading"
                  ? "Starting camera + pose model…"
                  : "Camera is off. Everything stays on this device — no video is uploaded."}
              </div>
            )}
          </div>
          <div className={styles.stageBar}>
            <div className={styles.chipRow}>
              <span className={`${styles.chip} ${stateChip.cls}`}>{stateChip.label}</span>
              {alerts && (
                <span
                  className={`${styles.chip} ${
                    alerts.telegram.configured ? styles.chipOk : styles.chipIdle
                  }`}
                >
                  {alerts.telegram.configured
                    ? "Telegram: connected"
                    : "Telegram: not configured"}
                </span>
              )}
            </div>
            {engineStatus === "running" ? (
              <button className={`${styles.btn} ${styles.btnGhost}`} onClick={stop}>
                Stop camera
              </button>
            ) : (
              <button
                className={styles.btn}
                onClick={start}
                disabled={engineStatus === "loading"}
              >
                {engineStatus === "loading" ? "Starting…" : "Start camera"}
              </button>
            )}
          </div>
          {watchState === "fallen-still" && (
            <div className={styles.stillMeter} role="status" aria-label="Stillness countdown">
              <div className={styles.stillTrack}>
                <div className={styles.stillFill} style={{ width: `${stillPct}%` }} />
              </div>
              <span className={styles.stillLabel}>
                still {(stillnessMs / 1000).toFixed(1)} s / 3.0 s
              </span>
            </div>
          )}
          {errorMsg && (
            <div className={styles.errorNote} role="alert">
              {errorMsg}
            </div>
          )}
        </section>

        <aside className={styles.side}>
          <section className={styles.card}>
            <h2 className={styles.cardTitle}>How it decides</h2>
            <ol className={styles.stepList}>
              <li className={posture === "upright" ? styles.stepActive : undefined}>
                <b>Upright.</b> A person is tracked standing or walking.
              </li>
              <li className={watchState === "fallen-still" ? styles.stepActive : undefined}>
                <b>Down fast.</b> Horizontal within 1.8&nbsp;s of last standing —
                slower means they lay down on purpose, and nothing alarms.
              </li>
              <li className={watchState === "fallen-still" ? styles.stepActive : undefined}>
                <b>Still.</b> Three seconds without movement on the ground fires the
                alert into the caseload, over SSE, and to Telegram.
              </li>
            </ol>
          </section>

          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Recent detections</h2>
            {log.length === 0 ? (
              <p className={styles.emptyLog}>Nothing yet — the log fills as events fire.</p>
            ) : (
              <ul className={styles.logList}>
                {log.map((e, i) => (
                  <li key={`${e.at}-${i}`} className={styles.logItem}>
                    <span className={styles.logAt}>{e.at}</span>
                    {e.text}
                  </li>
                ))}
              </ul>
            )}
            <button
              className={`${styles.btn} ${styles.btnGhost} ${styles.btnTest}`}
              onClick={() => void report()}
              disabled={sending}
            >
              Send test detection
            </button>
            <p className={styles.testNote}>
              Demo insurance: fires the same camera-incident endpoint with default
              values when nobody can physically fall.
            </p>
          </section>

          <section className={`${styles.card} ${styles.honesty}`}>
            <h2 className={styles.cardTitle}>Honest labelling</h2>
            <p className={styles.honestyText}>
              This is a pose <b>heuristic</b>, not the calibrated accelerometer
              detector — its incidents carry the sensor label{" "}
              <b>Camera&nbsp;(pose)</b> and its own confidence estimate, never the
              96.2% figure. Video never leaves this browser
              {assetSource ? ` (model assets: ${assetSource})` : ""}; only the
              detection event is sent.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
