"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { ReplayFactsPayload } from "@/lib/types";
import { dataClient } from "@/lib/data/client";
import { decodeFrames, type RingFrame } from "@/lib/pose/replayBuffer";
import { findPhases, type ReplayPhases } from "@/lib/pose/replayFacts";
import {
  advancePlayhead,
  frameIndexAt,
  phaseBandSegments,
} from "@/lib/pose/replayMath";
import { REPLAY_BONES } from "@/lib/pose/skeleton";
import styles from "./dashboard.module.css";

/**
 * "How the fall happened" — the camera incident's native drilldown panel
 * (ADR 0017 phase 3), the counterpart of TraceChart's accelerometer
 * waveform. Renders the uploaded stick-figure trace with a scrubber, ¼×
 * slow-mo and descent/ground phase bands in TraceChart's color language.
 * Coordinates only — this panel proves the privacy claim by construction.
 * Renders nothing while calm, for accelerometer incidents, or before the
 * upload lands (the endpoint 404s).
 */

const W = 320;
const H = 180;

function factsCaption(facts: ReplayFactsPayload | null | undefined): string {
  if (!facts) return "Replayed joint positions · no pixels were recorded";
  const bits: string[] = [];
  if (facts.direction && facts.direction !== "unknown")
    bits.push(
      facts.direction === "toward-camera"
        ? "fell toward the camera"
        : `fell ${facts.direction === "left" ? "leftward" : "rightward"}`,
    );
  if (facts.descentDurationMs)
    bits.push(`${(facts.descentDurationMs / 1000).toFixed(1)}s descent`);
  if (facts.protectiveArm === false) bits.push("no arm protection");
  if (facts.protectiveArm === true) bits.push("arms broke the fall");
  return bits.length
    ? `${bits.join(" · ")} · joint positions only, no pixels`
    : "Replayed joint positions · no pixels were recorded";
}

export function ReplayPlayer() {
  const [frames, setFrames] = useState<RingFrame[] | null>(null);
  const [facts, setFacts] = useState<ReplayFactsPayload | null>(null);
  const [phases, setPhases] = useState<ReplayPhases>({
    descentStartMs: null,
    impactMs: null,
  });
  const [playing, setPlaying] = useState(false);
  const [slow, setSlow] = useState(false);
  const [tDisplay, setTDisplay] = useState(0);
  const tRef = useRef(0);
  const rateRef = useRef(1);
  rateRef.current = slow ? 0.25 : 1;
  const canvasRef = useRef<HTMLCanvasElement>(null);

  useEffect(() => {
    let alive = true;
    dataClient
      .getIncidentReplay()
      .then((r) => {
        if (!alive || !r) return;
        const decoded = decodeFrames(r.frames, r.quantScale);
        setFrames(decoded);
        setFacts((r.facts as ReplayFactsPayload | null) ?? null);
        setPhases(findPhases(decoded));
      })
      .catch(() => {}); // a missing replay must never break the drilldown
    return () => {
      alive = false;
    };
  }, []);

  const durationMs = frames?.length ? frames[frames.length - 1].tMs : 0;

  const draw = useCallback(
    (tMs: number) => {
      const canvas = canvasRef.current;
      if (!canvas || !frames) return;
      const dpr = window.devicePixelRatio || 1;
      if (canvas.width !== W * dpr) {
        canvas.width = W * dpr;
        canvas.height = H * dpr;
      }
      const ctx = canvas.getContext("2d");
      if (!ctx) return;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const idx = frameIndexAt(frames, tMs);
      const pts = idx >= 0 ? frames[idx].pts : null;
      if (!pts) {
        ctx.fillStyle = "rgba(138, 124, 109, 0.7)"; // --muted
        ctx.font = "12px sans-serif";
        ctx.textAlign = "center";
        ctx.fillText("person not tracked", W / 2, H / 2);
        return;
      }
      const alphaOf = (i: number) =>
        (pts[i]?.visibility ?? 0) < 0.5 ? 0.25 : 1;
      ctx.strokeStyle = "rgba(192, 57, 43, 0.9)"; // --red: acute language
      ctx.fillStyle = "rgba(192, 57, 43, 0.95)";
      ctx.lineWidth = 2.5;
      for (const [a, b] of REPLAY_BONES) {
        const pa = pts[a];
        const pb = pts[b];
        if (!pa || !pb) continue;
        ctx.globalAlpha = Math.min(alphaOf(a), alphaOf(b));
        ctx.beginPath();
        ctx.moveTo(pa.x * W, pa.y * H);
        ctx.lineTo(pb.x * W, pb.y * H);
        ctx.stroke();
      }
      for (let i = 0; i < pts.length; i++) {
        ctx.globalAlpha = alphaOf(i);
        ctx.beginPath();
        ctx.arc(pts[i].x * W, pts[i].y * H, i === 0 ? 4 : 2.8, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.globalAlpha = 1;
    },
    [frames],
  );

  // Playback loop: playhead in a ref, canvas drawn imperatively, scrubber
  // state synced at ~10 Hz (the WatchPanel throttling pattern).
  useEffect(() => {
    if (!playing || !frames) return;
    let raf = 0;
    let last = performance.now();
    let lastPush = 0;
    const loop = (now: number) => {
      const { tMs, ended } = advancePlayhead(
        tRef.current,
        now - last,
        rateRef.current,
        durationMs,
      );
      last = now;
      tRef.current = tMs;
      draw(tMs);
      if (now - lastPush > 100) {
        lastPush = now;
        setTDisplay(tMs);
      }
      if (ended) {
        setPlaying(false);
        setTDisplay(tMs);
        return;
      }
      raf = requestAnimationFrame(loop);
    };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, [playing, frames, durationMs, draw]);

  // First frame once loaded.
  useEffect(() => {
    if (frames) draw(0);
  }, [frames, draw]);

  if (!frames || frames.length < 2) return null;

  const scrub = (t: number) => {
    setPlaying(false);
    tRef.current = t;
    setTDisplay(t);
    draw(t);
  };

  const play = () => {
    if (tRef.current >= durationMs) {
      tRef.current = 0;
      setTDisplay(0);
    }
    setPlaying(true);
  };

  const segs = phaseBandSegments(phases, durationMs);

  return (
    <>
      <h4 className={styles.sec}>How the fall happened</h4>
      <div className={styles.trace}>
        <canvas
          ref={canvasRef}
          className={styles.replayCanvas}
          role="img"
          aria-label={`Skeleton replay of the fall: ${factsCaption(facts)}`}
        />
        <div className={styles.replayControls}>
          <button
            className={styles.replayBtn}
            onClick={() => (playing ? setPlaying(false) : play())}
            aria-pressed={playing}
          >
            {playing ? "⏸ Pause" : "▶ Play"}
          </button>
          <button
            className={styles.replayBtn}
            onClick={() => setSlow((s) => !s)}
            aria-pressed={slow}
          >
            ¼× {slow ? "on" : "off"}
          </button>
          <span className={styles.replayTime}>
            {(tDisplay / 1000).toFixed(1)}s / {(durationMs / 1000).toFixed(1)}s
          </span>
        </div>
        <div className={styles.replayScrubWrap}>
          <div className={styles.replayBands} aria-hidden>
            {segs.map((s) => (
              <i
                key={s.kind}
                className={
                  s.kind === "descent" ? styles.bandDescent : styles.bandGround
                }
                style={{ left: `${s.leftPct}%`, width: `${s.widthPct}%` }}
              />
            ))}
          </div>
          <input
            type="range"
            className={styles.replayScrub}
            min={0}
            max={durationMs}
            step={50}
            value={Math.round(tDisplay)}
            onChange={(e) => scrub(Number(e.target.value))}
            aria-label="Replay position"
            aria-valuetext={`${(tDisplay / 1000).toFixed(1)} seconds`}
          />
        </div>
        <div className={styles.traceCaption}>{factsCaption(facts)}</div>
      </div>
    </>
  );
}
