/**
 * Replay facts (ADR 0017, phase 2) — pure functions over the frozen ring
 * buffer, computed at freeze time on the watch page and shipped inside the
 * upload. The server folds them into the deterministic rationale + feature
 * rows; the dashboard never recomputes, so the "why" stays single-sourced.
 *
 * Torso math mirrors fallHeuristic.measureFrame exactly, re-indexed onto the
 * 13-point replay subset. Direction is SCREEN coordinates: "left" means the
 * viewer's left (the /watch video is not mirrored).
 */

import type { RingFrame } from "./replayBuffer";

export interface ReplayFactsData {
  descentDurationMs: number | null;
  direction: "left" | "right" | "toward-camera" | "unknown";
  protectiveArm: boolean | null;
  postImpactMovement: "none" | "slight" | "moving" | "unknown";
  /** Peak downward torso velocity during descent, normalized frame-heights/s. */
  impactSpeed: number | null;
  /** Severity band derived from impactSpeed — a triage cue, not a diagnosis. */
  impactSeverity: "gentle" | "moderate" | "hard" | null;
}

export interface ReplayPhases {
  descentStartMs: number | null;
  impactMs: number | null;
}

// Subset indices (REPLAY_LANDMARKS order: nose, shoulders, elbows, wrists,
// hips, knees, ankles).
const SHO_L = 1, SHO_R = 2, WRI_L = 5, WRI_R = 6, HIP_L = 7, HIP_R = 8;
const TORSO = [SHO_L, SHO_R, HIP_L, HIP_R];

/** Thresholds; posture ones are the fallHeuristic defaults, the rest are
 * starting points to tune on rehearsal footage (like fallWindowMs was). */
export const FACTS_CONFIG = {
  uprightMaxDeg: 35,
  horizontalMinDeg: 48,
  minVisibility: 0.4,
  /** Torso-midpoint x drift (normalized) that counts as a sideways fall. */
  driftThreshold: 0.08,
  /** Apparent torso-size growth that counts as falling toward the camera. */
  towardCameraGrowth: 1.25,
  wristVisibility: 0.5,
  /** Mean displacement per 100 ms below this = still (fallHeuristic's eps). */
  stillEps: 0.012,
  slightEps: 0.03,
  /** Facts need at least this many valid frames per phase, else "unknown". */
  minValidFrames: 3,
  /** protectiveArm=true needs the wrist below the hip line in at least this
   * many descent frames — one frame is landmark noise, not a reach. */
  protectiveMinFrames: 2,
  /** Impact severity bands over peak descent velocity (frame-heights/s). */
  moderateMinSpeed: 0.5,
  hardMinSpeed: 1.0,
};

type Posture = "upright" | "transitional" | "horizontal" | null;

function torsoMid(pts: { x: number; y: number }[]): [number, number] {
  const sx = (pts[SHO_L].x + pts[SHO_R].x) / 2;
  const sy = (pts[SHO_L].y + pts[SHO_R].y) / 2;
  const hx = (pts[HIP_L].x + pts[HIP_R].x) / 2;
  const hy = (pts[HIP_L].y + pts[HIP_R].y) / 2;
  return [(sx + hx) / 2, (sy + hy) / 2];
}

function torsoSize(pts: { x: number; y: number }[]): number {
  const sx = (pts[SHO_L].x + pts[SHO_R].x) / 2;
  const sy = (pts[SHO_L].y + pts[SHO_R].y) / 2;
  const hx = (pts[HIP_L].x + pts[HIP_R].x) / 2;
  const hy = (pts[HIP_L].y + pts[HIP_R].y) / 2;
  return Math.hypot(sx - hx, sy - hy);
}

/** measureFrame's classification, subset-indexed. Null = not classifiable. */
export function postureOf(frame: RingFrame, cfg = FACTS_CONFIG): Posture {
  const pts = frame.pts;
  if (!pts || pts.length <= Math.max(...TORSO)) return null;
  const vis = TORSO.reduce((s, i) => s + (pts[i].visibility ?? 1), 0) / TORSO.length;
  if (vis < cfg.minVisibility) return null;
  const sx = (pts[SHO_L].x + pts[SHO_R].x) / 2;
  const sy = (pts[SHO_L].y + pts[SHO_R].y) / 2;
  const hx = (pts[HIP_L].x + pts[HIP_R].x) / 2;
  const hy = (pts[HIP_L].y + pts[HIP_R].y) / 2;
  const dx = Math.abs(sx - hx);
  const dyUp = hy - sy;
  const angle = (Math.atan2(dx, Math.max(dyUp, 0)) * 180) / Math.PI;
  if (angle < cfg.uprightMaxDeg) return "upright";
  if (angle > cfg.horizontalMinDeg) return "horizontal";
  return "transitional";
}

/** The descent window: last upright frame before the FINAL contiguous
 * horizontal run (trailing nulls tolerated — the person on the ground is
 * often half-tracked). Either leg absent → null, honestly. */
export function findPhases(frames: RingFrame[], cfg = FACTS_CONFIG): ReplayPhases {
  const postures = frames.map((f) => postureOf(f, cfg));
  let end = postures.length - 1;
  while (end >= 0 && postures[end] === null) end--;
  let impactIdx = -1;
  for (let i = end; i >= 0 && postures[i] === "horizontal"; i--) impactIdx = i;
  if (impactIdx < 0) return { descentStartMs: null, impactMs: null };
  let startIdx = -1;
  for (let i = impactIdx - 1; i >= 0; i--) {
    if (postures[i] === "upright") {
      startIdx = i;
      break;
    }
  }
  return {
    descentStartMs: startIdx >= 0 ? frames[startIdx].tMs : null,
    impactMs: frames[impactIdx].tMs,
  };
}

function frameAt(frames: RingFrame[], tMs: number): RingFrame | undefined {
  return frames.find((f) => f.tMs === tMs);
}

function fallDirection(
  frames: RingFrame[],
  phases: ReplayPhases,
  cfg = FACTS_CONFIG,
): ReplayFactsData["direction"] {
  if (phases.descentStartMs === null || phases.impactMs === null) return "unknown";
  const a = frameAt(frames, phases.descentStartMs);
  const b = frameAt(frames, phases.impactMs);
  if (!a?.pts || !b?.pts) return "unknown";
  const dx = torsoMid(b.pts)[0] - torsoMid(a.pts)[0];
  if (Math.abs(dx) >= cfg.driftThreshold) return dx < 0 ? "left" : "right";
  const sizeA = torsoSize(a.pts);
  if (sizeA > 0 && torsoSize(b.pts) / sizeA >= cfg.towardCameraGrowth)
    return "toward-camera";
  return "unknown";
}

/** A wrist visibly dropping below the hip line during the descent = the
 * protective response clinicians look for; its absence hints at syncope.
 * Wrists never visible enough → null (we do not guess). */
function protectiveArm(
  frames: RingFrame[],
  phases: ReplayPhases,
  cfg = FACTS_CONFIG,
): boolean | null {
  if (phases.descentStartMs === null || phases.impactMs === null) return null;
  let sawVisibleWrist = false;
  let reachFrames = 0;
  for (const f of frames) {
    // exclusive of impact: the protective response happens DURING descent
    if (f.tMs < phases.descentStartMs || f.tMs >= phases.impactMs || !f.pts) continue;
    const hipY = (f.pts[HIP_L].y + f.pts[HIP_R].y) / 2;
    let reachedThisFrame = false;
    for (const w of [WRI_L, WRI_R]) {
      const wrist = f.pts[w];
      if ((wrist.visibility ?? 0) < cfg.wristVisibility) continue;
      sawVisibleWrist = true;
      if (wrist.y > hipY) reachedThisFrame = true; // y grows downward
    }
    if (reachedThisFrame && ++reachFrames >= cfg.protectiveMinFrames) return true;
  }
  return sawVisibleWrist ? false : null;
}

/** Peak downward torso-midpoint velocity across the descent window
 * (frame-heights per second). Null when the window or its frames are
 * missing — like every fact, absence is reported, never guessed. */
function impactSpeed(
  frames: RingFrame[],
  phases: ReplayPhases,
): number | null {
  if (phases.descentStartMs === null || phases.impactMs === null) return null;
  const window = frames.filter(
    (f) =>
      f.tMs >= phases.descentStartMs! && f.tMs <= phases.impactMs! && f.pts &&
      f.pts.length > Math.max(...TORSO),
  );
  let peak: number | null = null;
  for (let i = 1; i < window.length; i++) {
    const dt = window[i].tMs - window[i - 1].tMs;
    if (dt <= 0) continue;
    const dy = torsoMid(window[i].pts!)[1] - torsoMid(window[i - 1].pts!)[1];
    const v = (dy / dt) * 1000; // per second; positive = downward
    if (v > (peak ?? -Infinity)) peak = v;
  }
  return peak === null ? null : Math.round(peak * 100) / 100;
}

function severityOf(
  speed: number | null,
  cfg = FACTS_CONFIG,
): ReplayFactsData["impactSeverity"] {
  if (speed === null || speed <= 0) return null;
  if (speed >= cfg.hardMinSpeed) return "hard";
  if (speed >= cfg.moderateMinSpeed) return "moderate";
  return "gentle";
}

function postImpactMovement(
  frames: RingFrame[],
  phases: ReplayPhases,
  cfg = FACTS_CONFIG,
): ReplayFactsData["postImpactMovement"] {
  if (phases.impactMs === null) return "unknown";
  const ground = frames.filter((f) => f.tMs >= phases.impactMs! && f.pts);
  if (ground.length < cfg.minValidFrames) return "unknown";
  let sum = 0;
  let pairs = 0;
  for (let i = 1; i < ground.length; i++) {
    const a = ground[i - 1].pts!;
    const b = ground[i].pts!;
    const dt = ground[i].tMs - ground[i - 1].tMs;
    if (dt <= 0) continue;
    let d = 0;
    const n = Math.min(a.length, b.length);
    for (let j = 0; j < n; j++) d += Math.hypot(b[j].x - a[j].x, b[j].y - a[j].y);
    sum += (d / n) * (100 / dt); // normalize to per-100ms, like the loop cadence
    pairs++;
  }
  if (pairs < cfg.minValidFrames - 1) return "unknown";
  const mean = sum / pairs;
  if (mean <= cfg.stillEps) return "none";
  if (mean <= cfg.slightEps) return "slight";
  return "moving";
}

export function computeReplayFacts(
  frames: RingFrame[],
  cfg = FACTS_CONFIG,
): ReplayFactsData {
  const phases = findPhases(frames, cfg);
  const speed = impactSpeed(frames, phases);
  return {
    descentDurationMs:
      phases.descentStartMs !== null && phases.impactMs !== null
        ? phases.impactMs - phases.descentStartMs
        : null,
    direction: fallDirection(frames, phases, cfg),
    protectiveArm: protectiveArm(frames, phases, cfg),
    postImpactMovement: postImpactMovement(frames, phases, cfg),
    impactSpeed: speed,
    impactSeverity: severityOf(speed, cfg),
  };
}
