import { describe, expect, it } from "vitest";
import {
  DEFAULT_MATCH_CONFIG,
  IdentityTracker,
  bestMatch,
  euclidean,
  type EnrolledPerson,
} from "./matcher";

// 128-D synthetic embeddings: a base direction per person plus small noise.
function vec(seedIndex: number, noise = 0): number[] {
  const v = Array.from({ length: 128 }, (_, i) =>
    Math.sin(seedIndex * 37 + i) + (noise ? noise * Math.sin(i * 7.3 + seedIndex) : 0),
  );
  const norm = Math.hypot(...v);
  return v.map((x) => x / norm);
}

const GALLERY: EnrolledPerson[] = [
  { residentId: "r-devi", label: "Devi Nair", embeddings: [vec(1), vec(1, 0.05), vec(1, -0.05)] },
  { residentId: "r-goh", label: "Goh Cheng Watt", embeddings: [vec(2), vec(2, 0.05)] },
];

describe("euclidean", () => {
  it("is zero for identical vectors and grows with difference", () => {
    expect(euclidean(vec(1), vec(1))).toBeLessThan(1e-9);
    expect(euclidean(vec(1), vec(2))).toBeGreaterThan(0.5);
  });
});

describe("bestMatch", () => {
  it("matches a noisy probe to the right person", () => {
    const m = bestMatch(vec(1, 0.08), GALLERY);
    expect(m?.residentId).toBe("r-devi");
  });

  it("returns null when nothing is under the threshold", () => {
    expect(bestMatch(vec(9), GALLERY)).toBeNull();
  });

  it("returns null on an empty gallery", () => {
    expect(bestMatch(vec(1), [])).toBeNull();
  });
});

describe("IdentityTracker", () => {
  it("binds only after minHits consecutive-enough matches", () => {
    const t = new IdentityTracker();
    expect(t.update({ residentId: "r-devi", distance: 0.3 }, 0)).toBeNull();
    expect(t.update({ residentId: "r-devi", distance: 0.3 }, 700)?.residentId).toBe(
      "r-devi",
    );
    expect(t.current?.residentId).toBe("r-devi");
  });

  it("one stray frame of a different person does not flip the binding", () => {
    const t = new IdentityTracker();
    t.update({ residentId: "r-devi", distance: 0.3 }, 0);
    t.update({ residentId: "r-devi", distance: 0.3 }, 700);
    t.update({ residentId: "r-goh", distance: 0.35 }, 1400);
    expect(t.current?.residentId).toBe("r-devi");
  });

  it("sustained sightings of someone else eventually rebind", () => {
    const t = new IdentityTracker();
    t.update({ residentId: "r-devi", distance: 0.3 }, 0);
    t.update({ residentId: "r-devi", distance: 0.3 }, 700);
    for (let i = 0; i < 4; i++) {
      t.update({ residentId: "r-goh", distance: 0.3 }, 1400 + i * 700);
    }
    expect(t.current?.residentId).toBe("r-goh");
  });

  it("decays to null after ttl with no sightings", () => {
    const t = new IdentityTracker();
    t.update({ residentId: "r-devi", distance: 0.3 }, 0);
    t.update({ residentId: "r-devi", distance: 0.3 }, 700);
    expect(t.current?.residentId).toBe("r-devi");
    t.update(null, 700 + DEFAULT_MATCH_CONFIG.bindTtlMs + 1);
    expect(t.current).toBeNull();
  });

  it("no-match frames inside the ttl keep the binding (person turned away)", () => {
    const t = new IdentityTracker();
    t.update({ residentId: "r-devi", distance: 0.3 }, 0);
    t.update({ residentId: "r-devi", distance: 0.3 }, 700);
    t.update(null, 1400);
    t.update(null, 2100);
    expect(t.current?.residentId).toBe("r-devi");
  });
});
