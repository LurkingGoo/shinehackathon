/**
 * Skeleton replay ring buffer (ADR 0017). Runs inside the /watch camera
 * loop: keeps the last REPLAY_WINDOW_MS of pose landmarks (the 13-joint
 * replay subset) downsampled to ~10 fps. Frozen synchronously when a fall
 * fires; the frozen copy is quantized and uploaded AFTER the alert POST —
 * the alert path never waits on this. Gaps are recorded as null frames:
 * "no person tracked" is data the player and facts both need.
 */

import type { LandmarkPoint } from "./fallHeuristic";
import { REPLAY_LANDMARKS } from "./skeleton";
import type { ReplayUploadPayload } from "@/lib/types";

export const REPLAY_WINDOW_MS = 15_000;
/** 95 not 100: a 60 Hz rAF cadence lands at ~10.2 fps instead of aliasing low. */
export const REPLAY_MIN_GAP_MS = 95;
export const REPLAY_FPS = 10;
export const QUANT_SCALE = 1000;

export interface RingFrame {
  tMs: number;
  /** The 13 replay-subset points, or null when nobody was tracked. */
  pts: LandmarkPoint[] | null;
}

export class ReplayRing {
  private frames: RingFrame[] = [];
  private lastKeptTs = -Infinity;

  push(landmarks: LandmarkPoint[] | undefined, tMs: number): void {
    if (tMs - this.lastKeptTs < REPLAY_MIN_GAP_MS) return;
    this.lastKeptTs = tMs;
    this.frames.push({
      tMs,
      pts: landmarks
        ? REPLAY_LANDMARKS.map((i) => ({ ...(landmarks[i] ?? { x: 0, y: 0, visibility: 0 }) }))
        : null,
    });
    const cutoff = tMs - REPLAY_WINDOW_MS;
    while (this.frames.length && this.frames[0].tMs < cutoff) this.frames.shift();
  }

  /** Deep-copied window ending at nowMs — immune to later pushes. The ring
   * keeps recording (a post-cooldown second fall gets a fresh window). */
  freeze(nowMs: number): RingFrame[] {
    const cutoff = nowMs - REPLAY_WINDOW_MS;
    return this.frames
      .filter((f) => f.tMs >= cutoff)
      .map((f) => ({
        tMs: f.tMs,
        pts: f.pts ? f.pts.map((p) => ({ ...p })) : null,
      }));
  }

  reset(): void {
    this.frames = [];
    this.lastKeptTs = -Infinity;
  }
}

/* ------------------------------ wire codec -------------------------------- */
// Row shape (documented on both sides of the seam): [tMs, then per joint
// x*QUANT_SCALE, y*QUANT_SCALE, visibility*100] as integers; a 1-length row
// is a null frame. Timestamps rebased to the window start.

export function encodeFrames(frames: RingFrame[]): number[][] {
  if (frames.length === 0) return [];
  const t0 = frames[0].tMs;
  return frames.map((f) => {
    const row: number[] = [Math.round(f.tMs - t0)];
    if (f.pts)
      for (const p of f.pts)
        row.push(
          Math.round(p.x * QUANT_SCALE),
          Math.round(p.y * QUANT_SCALE),
          Math.round((p.visibility ?? 0) * 100),
        );
    return row;
  });
}

export function decodeFrames(rows: number[][], quantScale = QUANT_SCALE): RingFrame[] {
  return rows.map((row) => {
    if (row.length <= 1) return { tMs: row[0] ?? 0, pts: null };
    const pts: LandmarkPoint[] = [];
    for (let i = 1; i + 3 <= row.length; i += 3)
      pts.push({
        x: row[i] / quantScale,
        y: row[i + 1] / quantScale,
        visibility: row[i + 2] / 100,
      });
    return { tMs: row[0], pts };
  });
}

export function buildReplayUpload(
  frames: RingFrame[],
  incidentId: string,
): ReplayUploadPayload {
  return {
    incidentId,
    fps: REPLAY_FPS,
    quantScale: QUANT_SCALE,
    frames: encodeFrames(frames),
  };
}
