/**
 * Face-identity matching — the pure logic behind enrolled recognition
 * (ADR 0011). The engine (engine.ts) turns video frames into 128-D
 * embeddings; this module decides who they belong to and keeps a STICKY
 * session identity so one bad frame never flips the name.
 *
 * Deliberately DOM-free and model-free: unit-tested with synthetic vectors
 * (matcher.test.ts), mirroring the pose split (engine = glue, logic = pure).
 */

export interface EnrolledPerson {
  residentId: string;
  label: string;
  /** One 128-D embedding per enrolled angle (front / left / right). */
  embeddings: number[][];
}

export interface FaceMatch {
  residentId: string;
  distance: number;
}

export interface MatchConfig {
  /** Max euclidean distance (L2-normalized 128-D) to count as the person.
   * face-api's conventional same-person threshold is 0.6; we bind slightly
   * stricter and let the tracker's hysteresis do the smoothing. */
  maxDistance: number;
  /** Sightings needed before an identity is reported (hysteresis up). */
  minHits: number;
  /** Consecutive sightings of a DIFFERENT person needed to rebind. */
  rebindHits: number;
  /** Binding survives this long without any sighting (turned away, occluded). */
  bindTtlMs: number;
}

export const DEFAULT_MATCH_CONFIG: MatchConfig = {
  maxDistance: 0.55,
  minHits: 2,
  rebindHits: 3,
  bindTtlMs: 30_000,
};

export function euclidean(a: number[], b: number[]): number {
  let s = 0;
  for (let i = 0; i < a.length; i++) {
    const d = a[i] - b[i];
    s += d * d;
  }
  return Math.sqrt(s);
}

/** Closest enrolled person under the threshold, across ALL their angles. */
export function bestMatch(
  embedding: number[],
  gallery: EnrolledPerson[],
  config: MatchConfig = DEFAULT_MATCH_CONFIG,
): FaceMatch | null {
  let best: FaceMatch | null = null;
  for (const person of gallery) {
    for (const e of person.embeddings) {
      const d = euclidean(embedding, e);
      if (d <= config.maxDistance && (!best || d < best.distance)) {
        best = { residentId: person.residentId, distance: d };
      }
    }
  }
  return best;
}

interface Binding {
  residentId: string;
  lastSeenTs: number;
}

/**
 * Sticky session identity with hysteresis both ways:
 *  - bind after `minHits` sightings of the same person;
 *  - a bound identity survives no-match frames for `bindTtlMs` (a fall turns
 *    the face away — exactly when the binding must hold);
 *  - rebinding to a DIFFERENT person needs `rebindHits` sustained sightings.
 */
export class IdentityTracker {
  private cfg: MatchConfig;
  private bound: Binding | null = null;
  private candidateId: string | null = null;
  private candidateHits = 0;

  constructor(config: MatchConfig = DEFAULT_MATCH_CONFIG) {
    this.cfg = config;
  }

  get current(): Binding | null {
    return this.bound;
  }

  /** Feed one match (or null) per recognition tick. Returns the binding. */
  update(match: FaceMatch | null, timestampMs: number): Binding | null {
    if (this.bound && timestampMs - this.bound.lastSeenTs > this.cfg.bindTtlMs) {
      this.bound = null; // decayed: nobody seen for too long
    }

    if (!match) return this.bound;

    if (this.bound?.residentId === match.residentId) {
      this.bound.lastSeenTs = timestampMs;
      this.candidateId = null;
      this.candidateHits = 0;
      return this.bound;
    }

    // Different person than the binding (or no binding yet): accumulate.
    if (this.candidateId === match.residentId) {
      this.candidateHits += 1;
    } else {
      this.candidateId = match.residentId;
      this.candidateHits = 1;
    }
    const needed = this.bound ? this.cfg.rebindHits : this.cfg.minHits;
    if (this.candidateHits >= needed) {
      this.bound = { residentId: match.residentId, lastSeenTs: timestampMs };
      this.candidateId = null;
      this.candidateHits = 0;
    }
    return this.bound;
  }

  reset(): void {
    this.bound = null;
    this.candidateId = null;
    this.candidateHits = 0;
  }
}
