import { describe, expect, it } from "vitest";
import type { LandmarkPoint } from "./fallHeuristic";
import {
  QUANT_SCALE,
  REPLAY_WINDOW_MS,
  ReplayRing,
  buildReplayUpload,
  decodeFrames,
  encodeFrames,
} from "./replayBuffer";
import { BONES, REPLAY_BONES, REPLAY_LANDMARKS } from "./skeleton";

function fullPose(x = 0.5, y = 0.5, vis = 0.9): LandmarkPoint[] {
  return Array.from({ length: 33 }, () => ({ x, y, visibility: vis }));
}

describe("skeleton subset", () => {
  it("covers every bone endpoint and remaps bijectively", () => {
    const set = new Set(REPLAY_LANDMARKS);
    for (const [a, b] of BONES) {
      expect(set.has(a)).toBe(true);
      expect(set.has(b)).toBe(true);
    }
    expect(REPLAY_BONES).toHaveLength(BONES.length);
    for (const [a, b] of REPLAY_BONES) {
      expect(a).toBeGreaterThanOrEqual(0);
      expect(b).toBeLessThan(REPLAY_LANDMARKS.length);
    }
  });
});

describe("ReplayRing", () => {
  it("downsamples a 60 Hz feed to ~10 fps", () => {
    const ring = new ReplayRing();
    for (let t = 0; t < 5000; t += 16) ring.push(fullPose(), t);
    const n = ring.freeze(5000).length;
    expect(n).toBeGreaterThanOrEqual(45);
    expect(n).toBeLessThanOrEqual(55);
  });

  it("holds only the last 15 s", () => {
    const ring = new ReplayRing();
    for (let t = 0; t < 30_000; t += 100) ring.push(fullPose(), t);
    const frames = ring.freeze(30_000);
    expect(frames[0].tMs).toBeGreaterThanOrEqual(30_000 - REPLAY_WINDOW_MS);
  });

  it("records gaps as null frames — no person is data", () => {
    const ring = new ReplayRing();
    ring.push(fullPose(), 0);
    ring.push(undefined, 100);
    ring.push(fullPose(), 200);
    const frames = ring.freeze(200);
    expect(frames.map((f) => f.pts === null)).toEqual([false, true, false]);
  });

  it("freeze is a deep copy, immune to later pushes and mutation", () => {
    const ring = new ReplayRing();
    ring.push(fullPose(0.3), 0);
    const snap = ring.freeze(0);
    ring.push(fullPose(0.9), 200);
    expect(snap).toHaveLength(1);
    snap[0].pts![0].x = 999;
    expect(ring.freeze(200)[0].pts![0].x).toBe(0.3);
  });

  it("survives a fall fired seconds after camera start", () => {
    const ring = new ReplayRing();
    for (let t = 0; t < 3000; t += 100) ring.push(fullPose(), t);
    expect(ring.freeze(3000).length).toBeGreaterThan(20);
  });
});

describe("wire codec", () => {
  it("round-trips within quantization error and rebases time", () => {
    const ring = new ReplayRing();
    ring.push(fullPose(0.123456, 0.654321, 0.77), 5000);
    ring.push(undefined, 5100);
    const rows = encodeFrames(ring.freeze(5100));
    expect(rows[0][0]).toBe(0); // rebased
    expect(rows[1]).toHaveLength(1); // null frame
    const back = decodeFrames(rows);
    expect(back[0].pts![0].x).toBeCloseTo(0.123456, 2);
    expect(back[0].pts![0].y).toBeCloseTo(0.654321, 2);
    expect(back[0].pts![0].visibility).toBeCloseTo(0.77, 1);
    expect(back[1].pts).toBeNull();
  });

  it("a full 15 s window stays under the 64 KB keepalive budget", () => {
    const ring = new ReplayRing();
    for (let t = 0; t < 16_000; t += 16) ring.push(fullPose(0.987654, 0.123456), t);
    const payload = buildReplayUpload(ring.freeze(16_000), "cv-1");
    expect(payload.frames.length).toBeLessThanOrEqual(200); // backend cap
    expect(JSON.stringify(payload).length).toBeLessThan(64_000);
  });

  it("encodes rows the backend contract accepts (≤99 ints, quantScale set)", () => {
    const ring = new ReplayRing();
    ring.push(fullPose(), 0);
    const payload = buildReplayUpload(ring.freeze(0), "cv-9");
    expect(payload.quantScale).toBe(QUANT_SCALE);
    expect(payload.frames[0]).toHaveLength(1 + REPLAY_LANDMARKS.length * 3); // 40
    expect(payload.frames[0].every((n) => Number.isInteger(n))).toBe(true);
  });
});
