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
   * face-api's conventional same-person threshold is 0.6; we bind notably
   * stricter — a stranger matching a resident is worse than a resident
   * occasionally going unrecognized (fail-open makes that a generic alert). */
  maxDistance: number;
  /** Angles a person must have enrolled before they are matchable at all —
   * one blurry capture is not an identity. */
  minAngles: number;
  /** Sightings needed before an identity is reported (hysteresis up). */
  minHits: number;
  /** Consecutive sightings of a DIFFERENT person needed to rebind. */
  rebindHits: number;
  /** Binding survives this long with NO face in view (turned away, fallen,
   * occluded) — the fall case this whole design exists for. */
  bindTtlMs: number;
  /** Consecutive VISIBLE-but-unmatched faces that unbind: a face we can see
   * yet cannot match is evidence of a different person, unlike no face. */
  unbindMisses: number;
}

export const DEFAULT_MATCH_CONFIG: MatchConfig = {
  maxDistance: 0.48,
  minAngles: 2,
  minHits: 2,
  rebindHits: 3,
  bindTtlMs: 30_000,
  unbindMisses: 4,
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
    if (person.embeddings.length < config.minAngles) continue;
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
 *  - a bound identity survives NO-FACE frames for `bindTtlMs` (a fall turns
 *    the face away — exactly when the binding must hold);
 *  - a VISIBLE face that matches nobody for `unbindMisses` ticks unbinds —
 *    someone we can see but not recognize is not the bound person;
 *  - rebinding to a DIFFERENT person needs `rebindHits` sustained sightings.
 */
export class IdentityTracker {
  private cfg: MatchConfig;
  private bound: Binding | null = null;
  private candidateId: string | null = null;
  private candidateHits = 0;
  private missCount = 0;

  constructor(config: MatchConfig = DEFAULT_MATCH_CONFIG) {
    this.cfg = config;
  }

  get current(): Binding | null {
    return this.bound;
  }

  /**
   * Feed one recognition tick. `faceSeen` distinguishes "no face in view"
   * (binding survives on the TTL) from "face visible but unmatched" (counts
   * toward unbinding). Callers that pass a match imply faceSeen.
   */
  update(
    match: FaceMatch | null,
    timestampMs: number,
    faceSeen: boolean = match !== null,
  ): Binding | null {
    if (this.bound && timestampMs - this.bound.lastSeenTs > this.cfg.bindTtlMs) {
      this.bound = null; // decayed: nobody seen for too long
    }

    if (!match) {
      if (faceSeen && this.bound) {
        this.missCount += 1;
        if (this.missCount >= this.cfg.unbindMisses) {
          this.bound = null;
          this.missCount = 0;
        }
      }
      return this.bound;
    }

    this.missCount = 0;
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
    this.missCount = 0;
  }
}
