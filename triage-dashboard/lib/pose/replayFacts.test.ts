import { describe, expect, it } from "vitest";
import type { LandmarkPoint } from "./fallHeuristic";
import { measureFrame } from "./fallHeuristic";
import type { RingFrame } from "./replayBuffer";
import {
  computeReplayFacts,
  findPhases,
  postureOf,
} from "./replayFacts";
import { REPLAY_LANDMARKS } from "./skeleton";

/* ---------------- synthetic 13-point pose builders ------------------------ */
// Subset order: nose, LSho, RSho, LElb, RElb, LWri, RWri, LHip, RHip, knees, ankles.

function base(vis = 0.9): LandmarkPoint[] {
  return Array.from({ length: 13 }, () => ({ x: 0.5, y: 0.5, visibility: vis }));
}

/** Upright at horizontal center cx: shoulders above hips. */
function standing(cx: number, opts: { wristY?: number; wristVis?: number } = {}): LandmarkPoint[] {
  const p = base();
  p[1] = { x: cx, y: 0.3, visibility: 0.9 };
  p[2] = { x: cx, y: 0.3, visibility: 0.9 };
  p[7] = { x: cx, y: 0.6, visibility: 0.9 };
  p[8] = { x: cx, y: 0.6, visibility: 0.9 };
  p[5] = { x: cx, y: opts.wristY ?? 0.45, visibility: opts.wristVis ?? 0.9 };
  p[6] = { x: cx, y: opts.wristY ?? 0.45, visibility: opts.wristVis ?? 0.9 };
  return p;
}

/** Mid-descent (~45° torso — transitional band). */
function midFall(cx: number, opts: { wristY?: number; wristVis?: number } = {}): LandmarkPoint[] {
  const p = base();
  p[1] = { x: cx + 0.15, y: 0.45, visibility: 0.9 };
  p[2] = { x: cx + 0.15, y: 0.45, visibility: 0.9 };
  p[7] = { x: cx, y: 0.6, visibility: 0.9 };
  p[8] = { x: cx, y: 0.6, visibility: 0.9 };
  p[5] = { x: cx, y: opts.wristY ?? 0.4, visibility: opts.wristVis ?? 0.9 };
  p[6] = { x: cx, y: opts.wristY ?? 0.4, visibility: opts.wristVis ?? 0.9 };
  return p;
}

/** On the ground, torso mid at cx; halfSpan controls apparent size. Jitter
 * is a DETERMINISTIC per-frame translation (alternating sign) — Math.random
 * here made the crawling test a coin flip. */
let jitterTick = 0;
function lying(cx: number, halfSpan = 0.2, jitter = 0): LandmarkPoint[] {
  const o = jitter ? (jitterTick++ % 2 ? 1 : -1) * (jitter / 2) : 0;
  const p = base();
  p[1] = { x: cx + halfSpan + o, y: 0.8 + o, visibility: 0.9 };
  p[2] = { x: cx + halfSpan + o, y: 0.8 + o, visibility: 0.9 };
  p[7] = { x: cx - halfSpan + o, y: 0.8 + o, visibility: 0.9 };
  p[8] = { x: cx - halfSpan + o, y: 0.8 + o, visibility: 0.9 };
  return p;
}

function seq(...groups: Array<[number, () => LandmarkPoint[] | null]>): RingFrame[] {
  const frames: RingFrame[] = [];
  let t = 0;
  for (const [count, make] of groups)
    for (let i = 0; i < count; i++) {
      const pts = make();
      frames.push({ tMs: t, pts });
      t += 100;
    }
  return frames;
}

/* -------------------------------- tests ----------------------------------- */

describe("postureOf mirrors measureFrame", () => {
  it("agrees with measureFrame on padded 33-point arrays", () => {
    for (const pose of [standing(0.4), midFall(0.4), lying(0.5)]) {
      const padded: LandmarkPoint[] = Array.from({ length: 33 }, () => ({
        x: 0.5, y: 0.5, visibility: 0.9,
      }));
      REPLAY_LANDMARKS.forEach((mp, i) => (padded[mp] = pose[i]));
      const subset = postureOf({ tMs: 0, pts: pose });
      const full = measureFrame(padded).posture;
      expect(subset).toBe(full === "no-person" ? null : full);
    }
  });
});

describe("findPhases", () => {
  it("finds descent start and impact around the final ground run", () => {
    const frames = seq([5, () => standing(0.4)], [3, () => midFall(0.4)], [10, () => lying(0.6)]);
    const p = findPhases(frames);
    expect(p.descentStartMs).toBe(400); // last upright frame
    expect(p.impactMs).toBe(800); // first horizontal frame
  });

  it("tolerates trailing null frames (half-tracked on the ground)", () => {
    const frames = seq([5, () => standing(0.4)], [8, () => lying(0.6)], [3, () => null]);
    expect(findPhases(frames).impactMs).toBe(500);
  });

  it("returns nulls when the fall was not captured", () => {
    const p = findPhases(seq([10, () => standing(0.4)]));
    expect(p).toEqual({ descentStartMs: null, impactMs: null });
  });
});

describe("computeReplayFacts", () => {
  it("scores a clean rightward fall", () => {
    const frames = seq([5, () => standing(0.4)], [3, () => midFall(0.4)], [10, () => lying(0.6)]);
    const f = computeReplayFacts(frames);
    expect(f.descentDurationMs).toBe(400);
    expect(f.direction).toBe("right");
    expect(f.postImpactMovement).toBe("none");
  });

  it("scores a leftward fall", () => {
    const frames = seq([5, () => standing(0.6)], [3, () => midFall(0.6)], [10, () => lying(0.4)]);
    expect(computeReplayFacts(frames).direction).toBe("left");
  });

  it("detects toward-camera from torso growth without drift", () => {
    const frames = seq([5, () => standing(0.5)], [3, () => midFall(0.5)], [10, () => lying(0.5, 0.35)]);
    expect(computeReplayFacts(frames).direction).toBe("toward-camera");
  });

  it("protective arm: wrist below hips during descent → true", () => {
    const frames = seq(
      [5, () => standing(0.4)],
      [3, () => midFall(0.4, { wristY: 0.75 })],
      [10, () => lying(0.6)],
    );
    expect(computeReplayFacts(frames).protectiveArm).toBe(true);
  });

  it("protective arm: visible wrists that never drop → false", () => {
    const frames = seq(
      [5, () => standing(0.4, { wristY: 0.2 })],
      [3, () => midFall(0.4, { wristY: 0.2 })],
      [10, () => lying(0.6)],
    );
    expect(computeReplayFacts(frames).protectiveArm).toBe(false);
  });

  it("protective arm: wrists never visible → null, not a guess", () => {
    const frames = seq(
      [5, () => standing(0.4, { wristVis: 0.1 })],
      [3, () => midFall(0.4, { wristVis: 0.1 })],
      [10, () => lying(0.6)],
    );
    expect(computeReplayFacts(frames).protectiveArm).toBeNull();
  });

  it("post-impact crawling reads as moving", () => {
    const frames = seq([5, () => standing(0.4)], [3, () => midFall(0.4)], [10, () => lying(0.6, 0.2, 0.2)]);
    expect(computeReplayFacts(frames).postImpactMovement).toBe("moving");
  });

  it("degrades to unknown/null on an all-null buffer", () => {
    const f = computeReplayFacts(seq([10, () => null]));
    expect(f).toEqual({
      descentDurationMs: null,
      direction: "unknown",
      protectiveArm: null,
      postImpactMovement: "unknown",
      impactSpeed: null,
      impactSeverity: null,
    });
  });

  it("protective arm: a single noisy reach frame is NOT a protective response", () => {
    let dropped = 0;
    const frames = seq(
      [5, () => standing(0.4, { wristY: 0.2 })],
      // exactly one descent frame with the wrist below the hips
      [3, () => midFall(0.4, { wristY: dropped++ === 0 ? 0.75 : 0.2 })],
      [10, () => lying(0.6)],
    );
    expect(computeReplayFacts(frames).protectiveArm).toBe(false);
  });

  it("impact severity: a fast synthetic drop reads as hard, with a speed", () => {
    const f = computeReplayFacts(
      seq([5, () => standing(0.4)], [3, () => midFall(0.4)], [10, () => lying(0.6)]),
    );
    expect(f.impactSpeed).toBeGreaterThan(1.0);
    expect(f.impactSeverity).toBe("hard");
  });

  it("impact severity: a slow eased descent reads below hard", () => {
    // interpolate torso-mid from standing to lying over 2.4 s — ~0.15 u/s
    const steps = 24;
    let i = 0;
    const glide = (): LandmarkPoint[] => {
      const t = Math.min(1, i++ / steps);
      const p = base();
      const shoY = 0.3 + t * 0.5;
      const hipY = 0.6 + t * 0.2;
      p[1] = { x: 0.4 + t * 0.2, y: shoY, visibility: 0.9 };
      p[2] = { x: 0.4 + t * 0.2, y: shoY, visibility: 0.9 };
      p[7] = { x: 0.4, y: hipY, visibility: 0.9 };
      p[8] = { x: 0.4, y: hipY, visibility: 0.9 };
      return p;
    };
    const f = computeReplayFacts(seq([3, () => standing(0.4)], [steps, glide], [8, () => lying(0.6)]));
    expect(f.impactSeverity === "hard").toBe(false);
    if (f.impactSpeed !== null) expect(f.impactSpeed).toBeLessThan(1.0);
  });

  it("impact severity: null when the fall was not captured", () => {
    const f = computeReplayFacts(seq([10, () => standing(0.4)]));
    expect(f.impactSpeed).toBeNull();
    expect(f.impactSeverity).toBeNull();
  });

  it("is deterministic for identical frames", () => {
    const make = () => seq([5, () => standing(0.4)], [3, () => midFall(0.4)], [10, () => lying(0.6)]);
    expect(computeReplayFacts(make())).toEqual(computeReplayFacts(make()));
  });
});
