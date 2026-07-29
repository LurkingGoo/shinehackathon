"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AlertStatus, CaseloadEntry } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import {
  FallStateMachine,
  measureFrame,
  type LandmarkPoint,
  type Posture,
  type WatchState,
} from "@/lib/pose/fallHeuristic";
import type { PoseEngine } from "@/lib/pose/engine";
import type { FaceEngine } from "@/lib/face/engine";
import {
  DEFAULT_MATCH_CONFIG,
  IdentityTracker,
  bestMatch,
  type EnrolledPerson,
} from "@/lib/face/matcher";
import { addEmbedding, loadGallery, removePerson } from "@/lib/face/gallery";
import styles from "./watch.module.css";

/**
 * /watch — the camera acute source (feature-spec §1b). MediaPipe pose runs
 * entirely in this browser; the unit-tested state machine (upright →
 * horizontal within 3 s → still 3 s) decides, and a detection POSTs
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
  // Identity selector (ADR 0011, phase 1): which caseload resident a detection
  // is reported as. "" = generic default. Phase 4's face binding will set this
  // automatically; until then it is the manual (and demo-insurance) path.
  const [residents, setResidents] = useState<CaseloadEntry[]>([]);
  const [residentId, setResidentId] = useState<string>("");
  const residentIdRef = useRef(residentId);
  residentIdRef.current = residentId;

  // Face identity (ADR 0011, phases 3+4): on-device gallery + sticky binding.
  const [gallery, setGallery] = useState<EnrolledPerson[]>([]);
  const galleryRef = useRef<EnrolledPerson[]>([]);
  galleryRef.current = gallery;
  const [faceStatus, setFaceStatus] = useState<"off" | "loading" | "on" | "error">("off");
  const [boundId, setBoundId] = useState<string | null>(null);
  const boundIdRef = useRef(boundId);
  boundIdRef.current = boundId;
  const [enrollTarget, setEnrollTarget] = useState<string>("");
  const [enrollBusy, setEnrollBusy] = useState(false);
  const faceEngineRef = useRef<FaceEngine | null>(null);
  const trackerRef = useRef(new IdentityTracker());
  const faceBusyRef = useRef(false);
  const lastFaceTickRef = useRef(0);
  const postureRef = useRef<Posture>("no-person");

  useEffect(() => {
    setGallery(loadGallery());
  }, []);

  // People & locations (ADR 0013): key in a location for a roster resident,
  // or register a new person by name. Synced through the caseload refetch.
  const [locTarget, setLocTarget] = useState<string>("new");
  const [newName, setNewName] = useState("");
  const [zoneInput, setZoneInput] = useState("");
  const [blockInput, setBlockInput] = useState("");
  const [unitNoInput, setUnitNoInput] = useState("");
  const [coords, setCoords] = useState<{ lat: number; lon: number } | null>(null);
  const [locBusy, setLocBusy] = useState(false);

  const refreshResidents = useCallback(
    () =>
      dataClient
        .getRankedCaseload()
        .then((c) => setResidents(c.entries))
        .catch(() => undefined),
    [],
  );

  useEffect(() => {
    dataClient.getAlertStatus().then(setAlerts).catch(() => setAlerts(null));
    void refreshResidents();
  }, [refreshResidents]);

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
        // Identity precedence (ADR 0011): face binding first, manual selector
        // second, generic default last. Read via refs so detections fired
        // from the camera loop see current values. Always fail-open.
        const rid = boundIdRef.current || residentIdRef.current || undefined;
        await dataClient.reportCameraFall(
          payload || rid ? { ...payload, residentId: rid } : undefined,
        );
        const asWho = rid
          ? ` as ${
              residents.find((r) => r.id === rid)?.name ??
              galleryRef.current.find((p) => p.residentId === rid)?.label ??
              rid
            }`
          : "";
        pushLog(
          payload
            ? `Fall detected${asWho} — sent to the dashboard (confidence ${Math.round(
                (payload.confidence ?? 0) * 100,
              )}%)`
            : `Test detection${asWho} sent to the dashboard`,
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
    [pushLog, residents],
  );

  // Long-lie escalation (ADR 0012): the state machine saw no recovery
  // escalateAfterMs after the fall — fire the STILL DOWN message through the
  // same identity resolution. Fail-open like everything else on this path.
  const escalate = useCallback(
    async (stillDownS: number) => {
      const rid = boundIdRef.current || residentIdRef.current || undefined;
      try {
        await dataClient.reportStillDown({ stillDownS, residentId: rid });
        pushLog(
          `Still down ${stillDownS.toFixed(0)}s after the alert — escalation sent`,
        );
      } catch {
        pushLog("Escalation could not reach the scoring service");
      }
    },
    [pushLog],
  );

  // "Use my location": browser geolocation, no reverse geocoding (the demo
  // runs offline) — the backend renders raw coordinates as `GPS lat, lon`
  // unless a block/unit is also keyed in.
  const captureLocation = useCallback(() => {
    if (!navigator.geolocation) {
      pushLog("Location service unavailable in this browser");
      return;
    }
    navigator.geolocation.getCurrentPosition(
      (p) => {
        setCoords({ lat: p.coords.latitude, lon: p.coords.longitude });
        pushLog("Current location captured from the browser");
      },
      () => pushLog("Location permission denied — key in the address instead"),
    );
  }, [pushLog]);

  const saveLocation = useCallback(async () => {
    const loc = {
      zone: zoneInput.trim() || undefined,
      block: blockInput.trim() || undefined,
      unitNumber: unitNoInput.trim() || undefined,
      lat: coords?.lat,
      lon: coords?.lon,
    };
    setLocBusy(true);
    try {
      if (locTarget === "new") {
        const name = newName.trim();
        if (!name) {
          pushLog("Give the new person a name first");
          return;
        }
        // Deliberately does NOT change the "Report as" selector: auto-binding
        // detections to whoever was last registered silently misattributed
        // strangers' falls. Pick them in "Report as" or enroll their face.
        const entry = await dataClient.registerResident({ name, ...loc });
        setNewName("");
        pushLog(
          `${entry.name} registered — ${entry.unit}${entry.zone ? ` · ${entry.zone}` : ""}`,
        );
      } else {
        await dataClient.setResidentLocation(locTarget, loc);
        const who = residents.find((r) => r.id === locTarget)?.name ?? locTarget;
        pushLog(
          loc.zone || loc.block || loc.unitNumber || coords
            ? `Location saved for ${who}`
            : `No location keyed in — ${who} keeps the default`,
        );
      }
      setCoords(null);
      await refreshResidents();
    } catch {
      pushLog("Could not reach the scoring service — location NOT saved");
    } finally {
      setLocBusy(false);
    }
  }, [
    locTarget, newName, zoneInput, blockInput, unitNoInput, coords,
    residents, pushLog, refreshResidents,
  ]);

  const stop = useCallback(() => {
    cancelAnimationFrame(rafRef.current);
    engineRef.current?.close();
    engineRef.current = null;
    faceEngineRef.current = null;
    trackerRef.current.reset();
    setBoundId(null);
    setFaceStatus("off");
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

      // Face identity loads alongside, NON-FATAL (ADR 0011 fail-open): if it
      // errors, fall detection continues and incidents stay generic/manual.
      setFaceStatus("loading");
      import("@/lib/face/engine")
        .then((m) => m.createFaceEngine())
        .then((fe) => {
          faceEngineRef.current = fe;
          trackerRef.current.reset();
          setFaceStatus("on");
          pushLog(`Face identity ready (models: ${fe.source})`);
        })
        .catch((err) => {
          console.error("[watch] face engine failed:", err);
          setFaceStatus("error");
          pushLog("Face identity unavailable — incidents stay generic/manual");
        });

      const loop = () => {
        const v = videoRef.current;
        const eng = engineRef.current;
        if (!v || !eng) return;
        const now = performance.now();
        if (v.readyState >= 2) {
          const landmarks = eng.detect(v, now);
          const m = measureFrame(landmarks, prevLandmarksRef.current);
          prevLandmarksRef.current = landmarks;
          postureRef.current = m.posture;
          const event = smRef.current.update(m, now);
          drawOverlay(landmarks);
          if (event) {
            if (event.kind === "still-down") void escalate(event.stillDownS);
            else void report(event);
          }
          // Identity tick (ADR 0011): low cadence, ONLY while upright — the
          // binding is what carries the name through the fall, so nothing is
          // ever recognized mid-fall. Decay is handled by the tracker.
          const fe = faceEngineRef.current;
          if (
            fe &&
            galleryRef.current.length > 0 &&
            !faceBusyRef.current &&
            now - lastFaceTickRef.current > 700 &&
            m.posture === "upright"
          ) {
            lastFaceTickRef.current = now;
            faceBusyRef.current = true;
            fe.embed(v)
              .then((desc) => {
                // faceSeen distinguishes "nobody's face in view" (binding
                // holds through a fall) from "a face we can't match" (a few
                // of those unbind — likely a different person).
                const match = desc ? bestMatch(desc, galleryRef.current) : null;
                if (match) console.log(`[face] match ${match.residentId} d=${match.distance.toFixed(3)}`);
                else if (desc) console.log("[face] face seen, no match");
                const b = trackerRef.current.update(
                  match,
                  performance.now(),
                  desc !== null,
                );
                setBoundId(b?.residentId ?? null);
              })
              .catch(() => undefined)
              .finally(() => {
                faceBusyRef.current = false;
              });
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
  }, [drawOverlay, escalate, pushLog, report, stop]);

  useEffect(() => stop, [stop]);

  // Enrollment (phase 3): capture the current frame's descriptor for the
  // chosen resident. Embeddings go to localStorage only — never uploaded.
  const captureAngle = useCallback(async () => {
    const fe = faceEngineRef.current;
    const v = videoRef.current;
    if (!fe || !v || !enrollTarget) return;
    setEnrollBusy(true);
    try {
      const desc = await fe.embed(v);
      if (!desc) {
        pushLog("No face found — face the camera up close, then capture");
        return;
      }
      const label = residents.find((r) => r.id === enrollTarget)?.name ?? enrollTarget;
      setGallery(addEmbedding(enrollTarget, label, desc));
      pushLog(`Captured face angle for ${label}`);
    } finally {
      setEnrollBusy(false);
    }
  }, [enrollTarget, residents, pushLog]);

  const removeEnrolled = useCallback((rid: string) => {
    setGallery(removePerson(rid));
    trackerRef.current.reset();
    setBoundId(null);
  }, []);

  const boundName = boundId
    ? residents.find((r) => r.id === boundId)?.name ??
      gallery.find((p) => p.residentId === boundId)?.label ??
      boundId
    : null;

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
            Pose estimation runs in this browser — upright, then horizontal within three
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
              {engineStatus === "running" && gallery.length > 0 && (
                <span
                  className={`${styles.chip} ${boundName ? styles.chipOk : styles.chipIdle}`}
                >
                  {boundName ? `Identified: ${boundName}` : "Identity: unknown"}
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
                <b>Down fast.</b> Horizontal within 3&nbsp;s of last standing —
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
            <label className={styles.selLabel}>
              Report as
              <select
                className={styles.residentSelect}
                value={residentId}
                onChange={(e) => setResidentId(e.target.value)}
              >
                <option value="">Default resident (Tan Ah Moi)</option>
                {residents.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
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

          <section className={styles.card}>
            <h2 className={styles.cardTitle}>People &amp; locations</h2>
            <p className={styles.testNote}>
              Key in where a resident is, or register a new person by name.
              Syncs to the dashboard and the Telegram alert. Nothing keyed in
              means the default location (Living room) stands.
            </p>
            <label className={styles.selLabel}>
              Who
              <select
                className={styles.residentSelect}
                value={locTarget}
                onChange={(e) => setLocTarget(e.target.value)}
              >
                <option value="new">➕ Register a new person…</option>
                {residents.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
            {locTarget === "new" && (
              <label className={styles.selLabel}>
                Name
                <input
                  className={styles.textInput}
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  placeholder="e.g. your own name"
                />
              </label>
            )}
            <label className={styles.selLabel}>
              Zone (in-flat area)
              <input
                className={styles.textInput}
                list="zone-suggestions"
                value={zoneInput}
                onChange={(e) => setZoneInput(e.target.value)}
                placeholder="Living room (default)"
              />
              <datalist id="zone-suggestions">
                <option value="Living room" />
                <option value="Bedroom" />
                <option value="Kitchen" />
                <option value="Bathroom" />
              </datalist>
            </label>
            <div className={styles.fieldRow}>
              <label className={styles.selLabel}>
                Block (optional)
                <input
                  className={styles.textInput}
                  value={blockInput}
                  onChange={(e) => setBlockInput(e.target.value)}
                  placeholder="112"
                />
              </label>
              <label className={styles.selLabel}>
                Unit no. (optional)
                <input
                  className={styles.textInput}
                  value={unitNoInput}
                  onChange={(e) => setUnitNoInput(e.target.value)}
                  placeholder="05-214"
                />
              </label>
            </div>
            <button
              className={`${styles.btn} ${styles.btnGhost} ${styles.btnTest}`}
              onClick={captureLocation}
              disabled={locBusy}
            >
              {coords
                ? `📍 GPS ${coords.lat.toFixed(4)}, ${coords.lon.toFixed(4)}`
                : "📍 Use my current location"}
            </button>
            <button
              className={`${styles.btn} ${styles.btnTest}`}
              onClick={() => void saveLocation()}
              disabled={locBusy || (locTarget === "new" && !newName.trim())}
            >
              {locBusy
                ? "Saving…"
                : locTarget === "new"
                  ? "Register person"
                  : "Save location"}
            </button>
          </section>

          <section className={styles.card}>
            <h2 className={styles.cardTitle}>Face enrollment (on-device)</h2>
            <p className={styles.testNote}>
              Enroll front, left, and right angles per person. Embeddings stay in
              this browser&apos;s storage — no face image is kept, nothing is
              uploaded. An identified person makes their fall a named alert;
              anyone unenrolled still fires the generic alert.
            </p>
            <label className={styles.selLabel}>
              Enroll as
              <select
                className={styles.residentSelect}
                value={enrollTarget}
                onChange={(e) => setEnrollTarget(e.target.value)}
              >
                <option value="">Choose a resident…</option>
                {residents.map((r) => (
                  <option key={r.id} value={r.id}>
                    {r.name}
                  </option>
                ))}
              </select>
            </label>
            <button
              className={`${styles.btn} ${styles.btnTest}`}
              onClick={() => void captureAngle()}
              disabled={
                enrollBusy || !enrollTarget || faceStatus !== "on" || engineStatus !== "running"
              }
            >
              {faceStatus === "on"
                ? enrollBusy
                  ? "Capturing…"
                  : "Capture this angle"
                : engineStatus !== "running"
                  ? "Start the camera to enroll"
                  : faceStatus === "loading"
                    ? "Face models loading…"
                    : "Face identity unavailable"}
            </button>
            {gallery.length > 0 && (
              <ul className={styles.logList} style={{ marginTop: 12 }}>
                {gallery.map((p) => (
                  <li key={p.residentId} className={styles.logItem}>
                    <span className={styles.logAt}>{p.embeddings.length} angle{p.embeddings.length === 1 ? "" : "s"}</span>
                    {p.label}
                    {p.embeddings.length < DEFAULT_MATCH_CONFIG.minAngles && (
                      <em> — capture another angle to activate matching</em>
                    )}
                    <button
                      className={styles.removeBtn}
                      onClick={() => removeEnrolled(p.residentId)}
                      aria-label={`Forget ${p.label}`}
                    >
                      forget
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </section>

          <section className={`${styles.card} ${styles.honesty}`}>
            <h2 className={styles.cardTitle}>Honest labelling</h2>
            <p className={styles.honestyText}>
              This is a pose <b>heuristic</b>, not the calibrated accelerometer
              detector — its incidents carry the sensor label{" "}
              <b>Camera&nbsp;(pose)</b> and its own confidence estimate, never the
              96.2% figure. Video never leaves this browser
              {assetSource ? ` (model assets: ${assetSource})` : ""}; only the
              detection event and the matched resident id are sent. Face
              embeddings from enrollment stay in this browser&apos;s storage.
            </p>
          </section>
        </aside>
      </div>
    </div>
  );
}
