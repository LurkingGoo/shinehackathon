/**
 * Pure player helpers for the skeleton replay (ADR 0017 phase 3) — kept out
 * of the component so playback logic is unit-testable without a DOM.
 */

import type { RingFrame } from "./replayBuffer";
import type { ReplayPhases } from "./replayFacts";

/** Index of the frame governing time tMs (last frame with tMs <= t).
 * -1 before the first frame. A null frame governs its own interval — a gap
 * draws as a gap, never as a held ghost. */
export function frameIndexAt(frames: RingFrame[], tMs: number): number {
  let lo = 0;
  let hi = frames.length - 1;
  let ans = -1;
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    if (frames[mid].tMs <= tMs) {
      ans = mid;
      lo = mid + 1;
    } else {
      hi = mid - 1;
    }
  }
  return ans;
}

export function advancePlayhead(
  tMs: number,
  dtMs: number,
  rate: number,
  durationMs: number,
): { tMs: number; ended: boolean } {
  const next = tMs + dtMs * rate;
  if (next >= durationMs) return { tMs: durationMs, ended: true };
  return { tMs: next, ended: false };
}

export interface PhaseSegment {
  kind: "descent" | "ground";
  leftPct: number;
  widthPct: number;
}

/** Scrubber underlay segments (percent geometry). Absent phases are simply
 * omitted — no fake precision when the fall was not captured. */
export function phaseBandSegments(
  phases: ReplayPhases,
  durationMs: number,
): PhaseSegment[] {
  if (durationMs <= 0) return [];
  const pct = (t: number) => Math.max(0, Math.min(100, (t / durationMs) * 100));
  const out: PhaseSegment[] = [];
  if (phases.descentStartMs !== null && phases.impactMs !== null)
    out.push({
      kind: "descent",
      leftPct: pct(phases.descentStartMs),
      widthPct: Math.max(1, pct(phases.impactMs) - pct(phases.descentStartMs)),
    });
  if (phases.impactMs !== null)
    out.push({
      kind: "ground",
      leftPct: pct(phases.impactMs),
      widthPct: Math.max(1, 100 - pct(phases.impactMs)),
    });
  return out;
}
