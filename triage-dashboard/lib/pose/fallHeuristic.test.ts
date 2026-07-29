import { describe, expect, it } from "vitest";
import {
  DEFAULT_CONFIG,
  FallStateMachine,
  measureFrame,
  type FallEvent,
  type FrameMeasurement,
  type LandmarkPoint,
} from "./fallHeuristic";

// ---------------------------------------------------------------------------
// Landmark fixtures — 33-point MediaPipe pose arrays, normalized coords
// (x right, y DOWN). Only the torso indices matter to the measurement;
// everything else is parked near the torso so motion math stays sane.
// ---------------------------------------------------------------------------

const L_SHOULDER = 11;
const R_SHOULDER = 12;
const L_HIP = 23;
const R_HIP = 24;

function poseArray(
  shoulderMid: [number, number],
  hipMid: [number, number],
  visibility = 0.95,
): LandmarkPoint[] {
  const pts: LandmarkPoint[] = Array.from({ length: 33 }, () => ({
    x: (shoulderMid[0] + hipMid[0]) / 2,
    y: (shoulderMid[1] + hipMid[1]) / 2,
    visibility,
  }));
  const half = 0.08;
  pts[L_SHOULDER] = { x: shoulderMid[0] - half, y: shoulderMid[1], visibility };
  pts[R_SHOULDER] = { x: shoulderMid[0] + half, y: shoulderMid[1], visibility };
  pts[L_HIP] = { x: hipMid[0] - half, y: hipMid[1], visibility };
  pts[R_HIP] = { x: hipMid[0] + half, y: hipMid[1], visibility };
  return pts;
}

/** Standing person: shoulders well above hips. */
const upright = () => poseArray([0.5, 0.3], [0.5, 0.55]);
/** Person flat on the ground: torso runs sideways at equal height. */
const lying = () => poseArray([0.3, 0.75], [0.62, 0.77]);

// ---------------------------------------------------------------------------
// measureFrame
// ---------------------------------------------------------------------------

describe("measureFrame", () => {
  it("classifies a standing person as upright with a small torso angle", () => {
    const m = measureFrame(upright());
    expect(m.posture).toBe("upright");
    expect(m.torsoAngleDeg).not.toBeNull();
    expect(m.torsoAngleDeg!).toBeLessThan(DEFAULT_CONFIG.uprightMaxDeg);
  });

  it("classifies a person on the ground as horizontal", () => {
    const m = measureFrame(lying());
    expect(m.posture).toBe("horizontal");
    expect(m.torsoAngleDeg!).toBeGreaterThan(DEFAULT_CONFIG.horizontalMinDeg);
  });

  it("reports no-person when landmarks are missing or barely visible", () => {
    expect(measureFrame(undefined).posture).toBe("no-person");
    expect(measureFrame([]).posture).toBe("no-person");
    expect(measureFrame(poseArray([0.5, 0.3], [0.5, 0.55], 0.1)).posture).toBe(
      "no-person",
    );
  });

  it("pins the 48° horizontal boundary: 46° is transitional, 50° is horizontal", () => {
    // angle = atan2(dx, dyUp); hip (0.5, 0.6), shoulders 0.1 above.
    const at = (deg: number) =>
      poseArray([0.5 + Math.tan((deg * Math.PI) / 180) * 0.1, 0.5], [0.5, 0.6]);
    const below = measureFrame(at(46));
    expect(below.torsoAngleDeg!).toBeCloseTo(46, 0);
    expect(below.posture).toBe("transitional"); // dead band — never arms
    const above = measureFrame(at(50));
    expect(above.torsoAngleDeg!).toBeCloseTo(50, 0);
    expect(above.posture).toBe("horizontal");
  });

  it("computes motion as displacement against the previous frame", () => {
    const still = measureFrame(upright(), upright());
    expect(still.motion).not.toBeNull();
    expect(still.motion!).toBeLessThan(1e-6);

    const moved = measureFrame(poseArray([0.55, 0.3], [0.55, 0.55]), upright());
    expect(moved.motion!).toBeGreaterThan(0.02);
  });

  it("leaves motion null without a previous frame", () => {
    expect(measureFrame(upright()).motion).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// FallStateMachine — driven with synthetic measurements
// ---------------------------------------------------------------------------

const M = (
  posture: FrameMeasurement["posture"],
  motion: number | null = 0,
): FrameMeasurement => ({
  posture,
  torsoAngleDeg: posture === "upright" ? 10 : posture === "horizontal" ? 80 : 50,
  motion,
  visibility: posture === "no-person" ? 0 : 0.95,
});

/** Feed one measurement per 100 ms from t0; returns any event fired. */
function drive(
  sm: FallStateMachine,
  t0: number,
  frames: Array<FrameMeasurement>,
) {
  const events = [];
  let t = t0;
  for (const f of frames) {
    const ev = sm.update(f, t);
    if (ev) events.push({ ev, t });
    t += 100;
  }
  return { events, tEnd: t };
}

function fastFallFrames() {
  return [
    ...Array.from({ length: 5 }, () => M("upright")),
    ...Array.from({ length: 3 }, () => M("transitional", 0.08)),
    // hits the floor 800 ms after last upright, then dead still for 3.2 s
    ...Array.from({ length: 33 }, () => M("horizontal", 0.001)),
  ];
}

describe("FallStateMachine", () => {
  it("fires exactly one event on a fast fall followed by stillness", () => {
    const sm = new FallStateMachine();
    const { events } = drive(sm, 1_000, fastFallFrames());
    expect(events).toHaveLength(1);
    const { stillnessS, confidence } = events[0].ev as FallEvent;
    expect(stillnessS).toBeGreaterThanOrEqual(3.0);
    expect(stillnessS).toBeLessThan(4.0);
    expect(confidence).toBeGreaterThanOrEqual(0.55);
    expect(confidence).toBeLessThanOrEqual(0.85);
    expect(sm.state).toBe("cooldown");
  });

  it("fires on a mimicked self-protecting fall (~2.5 s down), at lower confidence", () => {
    const sm = new FallStateMachine();
    const frames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      // 2.5 s controlled descent — inside the widened 3 s window
      ...Array.from({ length: 25 }, () => M("transitional", 0.03)),
      ...Array.from({ length: 35 }, () => M("horizontal", 0.001)),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(1);
    const { confidence } = events[0].ev as FallEvent;
    expect(confidence).toBeGreaterThanOrEqual(0.55);
    expect(confidence).toBeLessThan(0.65); // slow descent honestly scores low
  });

  it("fires on a demo-pace descent (~3.3 s), just inside the 3.5 s window", () => {
    // Widened 3000 → 3500 (2026-07-29): rehearsal falls padded with caution
    // land in 3–3.5 s and were rejected by the 3 s window.
    const sm = new FallStateMachine();
    const frames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      ...Array.from({ length: 32 }, () => M("transitional", 0.02)),
      ...Array.from({ length: 35 }, () => M("horizontal", 0.001)),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(1);
    const { confidence } = events[0].ev as FallEvent;
    expect(confidence).toBeGreaterThanOrEqual(0.55);
    expect(confidence).toBeLessThan(0.6); // near-window descent scores lowest
  });

  it("never fires on a slow, deliberate lie-down", () => {
    const sm = new FallStateMachine();
    const frames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      // 4 s of slow transition — far beyond the fall window
      ...Array.from({ length: 40 }, () => M("transitional", 0.004)),
      ...Array.from({ length: 60 }, () => M("horizontal", 0.001)),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(0);
  });

  it("does not fire while the person on the ground keeps moving", () => {
    const sm = new FallStateMachine();
    const frames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      ...Array.from({ length: 60 }, () => M("horizontal", 0.05)),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(0);
  });

  it("aborts the candidate when the person gets up before stillness completes", () => {
    const sm = new FallStateMachine();
    const frames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      ...Array.from({ length: 15 }, () => M("horizontal", 0.001)), // 1.5 s still
      ...Array.from({ length: 30 }, () => M("upright")),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(0);
    expect(sm.state).toBe("monitoring");
  });

  it("respects cooldown, then can fire again", () => {
    const sm = new FallStateMachine();
    const first = drive(sm, 1_000, fastFallFrames());
    expect(first.events).toHaveLength(1);

    // Immediately fall again inside the cooldown: suppressed.
    const second = drive(sm, first.tEnd, [
      ...Array.from({ length: 5 }, () => M("upright")),
      ...Array.from({ length: 40 }, () => M("horizontal", 0.001)),
    ]);
    expect(second.events).toHaveLength(0);

    // Past the cooldown a new fall fires normally.
    const t3 = first.tEnd + DEFAULT_CONFIG.cooldownMs + 1_000;
    const third = drive(sm, t3, fastFallFrames());
    expect(third.events).toHaveLength(1);
  });

  it("a faster drop earns higher confidence than a slower one", () => {
    const fast = new FallStateMachine();
    const fastEv = drive(fast, 0, fastFallFrames()).events[0].ev as FallEvent;

    const slow = new FallStateMachine();
    const slowFrames = [
      ...Array.from({ length: 5 }, () => M("upright")),
      // 1.6 s transition — still inside the window, but slow
      ...Array.from({ length: 16 }, () => M("transitional", 0.08)),
      ...Array.from({ length: 40 }, () => M("horizontal", 0.001)),
    ];
    const slowEv = drive(slow, 0, slowFrames).events[0].ev as FallEvent;

    expect(fastEv.confidence).toBeGreaterThan(slowEv.confidence);
  });

  it("escalates ONCE when the person is still down escalateAfterMs after the fall", () => {
    // Short escalation window so the test drives seconds, not 45 s of frames.
    const sm = new FallStateMachine({ escalateAfterMs: 5_000 });
    const frames = [
      ...fastFallFrames(), // fires the fall ~4.1 s in
      // stays on the ground well past the 5 s escalation window
      ...Array.from({ length: 80 }, () => M("horizontal", 0.001)),
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(2);
    expect(events[0].ev.kind).toBe("fall");
    expect(events[1].ev.kind).toBe("still-down");
    const still = events[1].ev as { kind: string; stillDownS: number };
    expect(still.stillDownS).toBeGreaterThanOrEqual(5.0);
    expect(still.stillDownS).toBeLessThan(6.0);
  });

  it("never escalates when the person gets up after the alert", () => {
    const sm = new FallStateMachine({ escalateAfterMs: 5_000 });
    const frames = [
      ...fastFallFrames(),
      ...Array.from({ length: 20 }, () => M("horizontal", 0.001)), // 2 s down
      ...Array.from({ length: 100 }, () => M("upright")), // recovered
    ];
    const { events } = drive(sm, 1_000, frames);
    expect(events).toHaveLength(1);
    expect(events[0].ev.kind).toBe("fall");
  });

  it("stillness progress is exposed for the UI countdown", () => {
    const sm = new FallStateMachine();
    drive(sm, 1_000, [
      ...Array.from({ length: 5 }, () => M("upright")),
      ...Array.from({ length: 10 }, () => M("horizontal", 0.001)), // 1.0 s still
    ]);
    expect(sm.state).toBe("fallen-still");
    expect(sm.stillnessMs).toBeGreaterThanOrEqual(800);
    expect(sm.stillnessMs).toBeLessThanOrEqual(1_200);
  });
});
