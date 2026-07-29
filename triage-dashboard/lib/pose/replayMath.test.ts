import { describe, expect, it } from "vitest";
import type { RingFrame } from "./replayBuffer";
import { advancePlayhead, frameIndexAt, phaseBandSegments } from "./replayMath";

const frames: RingFrame[] = [0, 100, 200, 300].map((t) => ({
  tMs: t,
  pts: t === 200 ? null : [{ x: 0.5, y: 0.5, visibility: 0.9 }],
}));

describe("frameIndexAt", () => {
  it("exact hit, between frames, before first, after last", () => {
    expect(frameIndexAt(frames, 100)).toBe(1);
    expect(frameIndexAt(frames, 150)).toBe(1); // holds the earlier frame
    expect(frameIndexAt(frames, -10)).toBe(-1);
    expect(frameIndexAt(frames, 999)).toBe(3);
  });

  it("a null frame governs its own interval (gap stays a gap)", () => {
    expect(frames[frameIndexAt(frames, 250)].pts).toBeNull();
  });
});

describe("advancePlayhead", () => {
  it("advances, scales by rate, clamps and ends at duration", () => {
    expect(advancePlayhead(0, 100, 1, 300)).toEqual({ tMs: 100, ended: false });
    expect(advancePlayhead(0, 100, 0.25, 300).tMs).toBeCloseTo(25);
    expect(advancePlayhead(250, 100, 1, 300)).toEqual({ tMs: 300, ended: true });
  });
});

describe("phaseBandSegments", () => {
  it("full phases yield descent + ground segments in order", () => {
    const segs = phaseBandSegments({ descentStartMs: 100, impactMs: 200 }, 400);
    expect(segs).toHaveLength(2);
    expect(segs[0]).toMatchObject({ kind: "descent", leftPct: 25, widthPct: 25 });
    expect(segs[1].kind).toBe("ground");
    expect(segs[1].leftPct + segs[1].widthPct).toBeLessThanOrEqual(100);
  });

  it("missing descent leg omits its band; missing impact omits everything", () => {
    expect(
      phaseBandSegments({ descentStartMs: null, impactMs: 200 }, 400).map((s) => s.kind),
    ).toEqual(["ground"]);
    expect(phaseBandSegments({ descentStartMs: null, impactMs: null }, 400)).toEqual([]);
  });

  it("zero duration yields nothing", () => {
    expect(phaseBandSegments({ descentStartMs: 0, impactMs: 0 }, 0)).toEqual([]);
  });
});
