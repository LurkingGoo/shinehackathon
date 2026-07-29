/**
 * Camera fall heuristic — the pure logic behind /watch (feature-spec §1b).
 *
 * MediaPipe supplies 33 normalized pose landmarks per frame; this module turns
 * them into a posture classification and runs the fall state machine:
 *
 *   upright ──(goes horizontal within fallWindowMs)──▶ fall candidate
 *   candidate ──(continuous stillness for stillMs)──▶ FIRE {stillnessS, confidence}
 *   fired ──(cooldownMs)──▶ back to monitoring
 *
 * A slow transition (deliberately lying down) never arms the candidate.
 * Confidence is this heuristic's OWN honest estimate (0.55–0.85 band from
 * transition speed) — never the calibrated accelerometer detector's number.
 *
 * Deliberately DOM-free and MediaPipe-free so it is unit-testable
 * (fallHeuristic.test.ts) with synthetic landmark sequences.
 */

export interface LandmarkPoint {
  x: number;
  y: number; // normalized image coords: y grows DOWNWARD
  visibility?: number;
}

export type Posture = "upright" | "horizontal" | "transitional" | "no-person";

export interface FrameMeasurement {
  posture: Posture;
  /** Torso lean vs vertical, degrees: 0 = standing, 90 = flat. Null when no person. */
  torsoAngleDeg: number | null;
  /** Mean normalized landmark displacement vs the previous frame; null without one. */
  motion: number | null;
  /** Mean torso-landmark visibility, 0..1. */
  visibility: number;
}

export interface FallEvent {
  kind: "fall";
  stillnessS: number;
  confidence: number;
  note: string;
}

/**
 * Long-lie escalation (ADR 0012): fired ONCE per fall when the person is
 * still on the ground `escalateAfterMs` after the fall event. Any upright
 * frame (they got up) or lost tracking cancels it.
 */
export interface StillDownEvent {
  kind: "still-down";
  stillDownS: number;
}

export type WatchEvent = FallEvent | StillDownEvent;

export interface FallHeuristicConfig {
  uprightMaxDeg: number;
  horizontalMinDeg: number;
  minVisibility: number;
  /** Max ms between last upright frame and hitting horizontal to count as a fall. */
  fallWindowMs: number;
  /** Continuous stillness required on the ground before firing. */
  stillMs: number;
  /** Motion below this (normalized units/frame) counts as still. */
  stillEps: number;
  cooldownMs: number;
  confidenceBase: number;
  confidenceSpeedGain: number;
  confidenceMax: number;
  /** Post-fire: still on the ground this long after the alert → escalate. */
  escalateAfterMs: number;
}

export const DEFAULT_CONFIG: FallHeuristicConfig = {
  uprightMaxDeg: 35,
  // A webcam mounted above the screen sees a real drop at a foreshortened
  // angle — 60deg missed drops that settled in the 45-55deg "transitional"
  // band and never armed the candidate. Lowered so those still count.
  horizontalMinDeg: 48,
  // Loosened alongside horizontalMinDeg: a person low/prone on the floor
  // is more likely to be partially out of frame or occluded.
  minVisibility: 0.4,
  // Widened 1800 → 3000 → 3500: a person MIMICKING a fall protects
  // themselves (knee first, hand down) and reaches the floor in ~2-2.5s;
  // rehearsal falls padded with extra caution stretch to ~3-3.5s (2026-07-29).
  // A deliberate lie-down still takes longer; a near-window descent honestly
  // earns the lowest confidence via confidenceSpeedGain.
  fallWindowMs: 3500,
  stillMs: 3000,
  stillEps: 0.012,
  cooldownMs: 10_000,
  confidenceBase: 0.55,
  confidenceSpeedGain: 0.3,
  confidenceMax: 0.85,
  // 45s (tune): long enough to mean "not getting up", short enough to demo.
  // Must exceed cooldownMs — the tracker survives the cooldown transition.
  escalateAfterMs: 45_000,
};

// MediaPipe pose landmark indices.
const L_SHOULDER = 11;
const R_SHOULDER = 12;
const L_HIP = 23;
const R_HIP = 24;
const TORSO = [L_SHOULDER, R_SHOULDER, L_HIP, R_HIP];

function mid(a: LandmarkPoint, b: LandmarkPoint): [number, number] {
  return [(a.x + b.x) / 2, (a.y + b.y) / 2];
}

export function measureFrame(
  landmarks: LandmarkPoint[] | undefined,
  prev?: LandmarkPoint[],
  config: FallHeuristicConfig = DEFAULT_CONFIG,
): FrameMeasurement {
  if (!landmarks || landmarks.length <= Math.max(...TORSO)) {
    return { posture: "no-person", torsoAngleDeg: null, motion: null, visibility: 0 };
  }

  const visibility =
    TORSO.reduce((s, i) => s + (landmarks[i].visibility ?? 1), 0) / TORSO.length;
  if (visibility < config.minVisibility) {
    return { posture: "no-person", torsoAngleDeg: null, motion: null, visibility };
  }

  const [sx, sy] = mid(landmarks[L_SHOULDER], landmarks[R_SHOULDER]);
  const [hx, hy] = mid(landmarks[L_HIP], landmarks[R_HIP]);
  // Vector hips → shoulders; for a standing person it points UP (negative dy).
  const dx = Math.abs(sx - hx);
  const dyUp = hy - sy; // positive when shoulders are above hips
  const torsoAngleDeg = (Math.atan2(dx, Math.max(dyUp, 0)) * 180) / Math.PI;

  let motion: number | null = null;
  if (prev && prev.length === landmarks.length) {
    let sum = 0;
    for (let i = 0; i < landmarks.length; i++) {
      sum += Math.hypot(landmarks[i].x - prev[i].x, landmarks[i].y - prev[i].y);
    }
    motion = sum / landmarks.length;
  }

  const posture: Posture =
    torsoAngleDeg < config.uprightMaxDeg
      ? "upright"
      : torsoAngleDeg > config.horizontalMinDeg
        ? "horizontal"
        : "transitional";

  return { posture, torsoAngleDeg, motion, visibility };
}

export type WatchState =
  | "idle" // no person in frame
  | "monitoring" // person tracked, nothing alarming
  | "fallen-still" // fall candidate on the ground, stillness clock running
  | "cooldown"; // just fired; suppressing repeats

export class FallStateMachine {
  private cfg: FallHeuristicConfig;
  private _state: WatchState = "idle";
  private lastUprightTs: number | null = null;
  private inHorizontal = false;
  private candidate = false;
  private transitionMs = 0;
  private stillStartTs: number | null = null;
  private lastTs = 0;
  private cooldownUntil = 0;
  // Post-fire long-lie tracker (ADR 0012) — independent of the main state so
  // it survives the cooldown → monitoring transition (escalateAfterMs > cooldownMs).
  private firedAt: number | null = null;
  private escalated = false;

  constructor(config?: Partial<FallHeuristicConfig>) {
    this.cfg = { ...DEFAULT_CONFIG, ...config };
  }

  get state(): WatchState {
    return this._state;
  }

  /** Milliseconds of continuous stillness accumulated on the ground (UI countdown). */
  get stillnessMs(): number {
    return this.stillStartTs === null ? 0 : this.lastTs - this.stillStartTs;
  }

  update(m: FrameMeasurement, timestampMs: number): WatchEvent | null {
    this.lastTs = timestampMs;

    // Post-fire long-lie check (ADR 0012), before any state handling: getting
    // up (or losing the person) cancels; still down at the deadline escalates
    // ONCE. Movement on the ground does not cancel — down is down.
    if (this.firedAt !== null && !this.escalated) {
      if (m.posture === "upright" || m.posture === "no-person") {
        this.firedAt = null; // recovered, or nobody to escalate for
      } else if (timestampMs - this.firedAt >= this.cfg.escalateAfterMs) {
        this.escalated = true;
        return {
          kind: "still-down",
          stillDownS: Math.round((timestampMs - this.firedAt) / 100) / 10,
        };
      }
    }

    if (this._state === "cooldown") {
      if (timestampMs < this.cooldownUntil) return null;
      this._state = "monitoring";
      this.resetGroundTracking();
      this.lastUprightTs = null;
    }

    if (m.posture === "no-person") {
      this._state = "idle";
      this.resetGroundTracking();
      this.lastUprightTs = null;
      return null;
    }

    if (m.posture === "upright") {
      this.lastUprightTs = timestampMs;
      this._state = "monitoring";
      this.resetGroundTracking();
      return null;
    }

    if (m.posture === "transitional") {
      this._state = "monitoring";
      this.resetGroundTracking();
      return null;
    }

    // horizontal
    if (!this.inHorizontal) {
      this.inHorizontal = true;
      this.transitionMs =
        this.lastUprightTs === null ? Infinity : timestampMs - this.lastUprightTs;
      this.candidate = this.transitionMs <= this.cfg.fallWindowMs;
      this.stillStartTs = null;
    }

    if (!this.candidate) {
      this._state = "monitoring"; // deliberate lying down — never alarms
      return null;
    }

    const isStill = m.motion !== null && m.motion < this.cfg.stillEps;
    if (!isStill) {
      this.stillStartTs = null;
      this._state = "monitoring";
      return null;
    }

    this.stillStartTs ??= timestampMs;
    this._state = "fallen-still";
    const stillnessMs = timestampMs - this.stillStartTs;
    if (stillnessMs < this.cfg.stillMs) return null;

    // FIRE — one event, then cooldown.
    const speed = Math.max(0, 1 - this.transitionMs / this.cfg.fallWindowMs);
    const confidence = Math.min(
      this.cfg.confidenceMax,
      this.cfg.confidenceBase + this.cfg.confidenceSpeedGain * speed,
    );
    const stillnessS = Math.round((stillnessMs / 1000) * 10) / 10;
    const event: FallEvent = {
      kind: "fall",
      stillnessS,
      confidence: Math.round(confidence * 100) / 100,
      note: `pose heuristic: upright → horizontal in ${Math.round(this.transitionMs)} ms, still ${stillnessS}s`,
    };
    this._state = "cooldown";
    this.cooldownUntil = timestampMs + this.cfg.cooldownMs;
    this.firedAt = timestampMs;
    this.escalated = false;
    this.resetGroundTracking();
    return event;
  }

  private resetGroundTracking() {
    this.inHorizontal = false;
    this.candidate = false;
    this.stillStartTs = null;
  }
}
