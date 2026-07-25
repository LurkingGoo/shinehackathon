/* ============================================================================
 * DATA CONTRACT — the shapes the UI expects.
 *
 * This is the agreement between frontend and backend. The UI renders exactly
 * these types; the backend returns them from `/api/caseload`,
 * `/api/residents/:id`, and `/api/incidents/stream`. Change a field here →
 * update both sides.
 *
 * Design law encoded in these types:
 *   - `track` separates ACUTE (a "now" interrupt) from CHRONIC (a "this-week"
 *     concern). They are NEVER blended into one number. Acute always pins top.
 *   - `rationale` is DETERMINISTIC — templated from `features`. An LLM may
 *     smooth wording downstream (`briefing`), but must not invent the "why".
 * ==========================================================================*/

/** Which of the two tracks produced this score. Acute always preempts chronic. */
export type Track = "acute" | "chronic";

/** Provenance of the signal — the product is deliberately sensor-agnostic. */
export type SensorClass = "Wearable bangle" | "CASAS ambient" | string;

/** A monitored person. Stable identity fields only. */
export interface Resident {
  id: string;
  name: string;
  age: number;
  /** HDB-style address, e.g. "Blk 112 #05-214". */
  unit: string;
}

/**
 * One feature that contributed to a score. The ranked rationale and the
 * drill-down bars are built from these — this is what makes "why" deterministic.
 */
export interface RiskFeature {
  /** Human label, e.g. "Kitchen inactivity". */
  label: string;
  /** Observed value as display string, e.g. "16h 04m". */
  value: string;
  /** Contribution to the score, 0..1. Drives the drill-down bar width. */
  weight: number;
  /** Expected/normal range for context, e.g. "typ. < 4h". "" if not applicable. */
  baseline: string;
}

/** The score attached to a resident at a point in time. */
export interface RiskScore {
  track: Track;
  /** Normalised risk, 0..1. Rendered as 0–100 in the UI. */
  risk: number;
  /** Model confidence, 0..1. A separate axis from risk — never conflate. */
  confidence: number;
  /** Backend-authoritative timestamp of the signal (ISO 8601). */
  updatedAt: string;
  /** Pre-formatted relative string for display, e.g. "22 min ago". */
  recency: string;
  /** Specific sensor, e.g. "PIR motion", "Accelerometer". */
  sensor: string;
  /** Provenance class. */
  sensorClass: SensorClass;
  /** DETERMINISTIC one-line explanation, templated from `features`. */
  rationale: string;
}

/** A resident + their current score + computed rank. The ranked-list row shape. */
export interface CaseloadEntry extends Resident {
  score: RiskScore;
  /** 1-based position after ordering (acute first, then chronic by risk desc). */
  rank: number;
}

/** ---- Ranked-list payload (GET /api/caseload) ---- */
export interface RankedCaseload {
  /** ISO 8601 — when this ranking was computed. */
  generatedAt: string;
  /**
   * Ordered rows. Backend SHOULD send them ordered (acute first, then chronic
   * by risk desc); the UI re-sorts defensively so ordering is never trusted blind.
   */
  entries: CaseloadEntry[];
}

/** ---- Drill-down payload (GET /api/residents/:id) ---- */
export interface ResidentDetail extends Resident {
  score: RiskScore;
  /** The features behind the score, highest weight first. */
  features: RiskFeature[];
  /** Deterministic recommended next step for the caseworker. */
  recommendedAction: string;
  /**
   * Shift briefing paragraph. Wording MAY be LLM-smoothed; the facts it states
   * must come only from `score` + `features`. Never let the model invent cause.
   */
  briefing: string;
}

/** ---- Incident signal trace (GET /api/incidents/trace) ----
 * The accelerometer window behind the active incident, for the drilldown
 * waveform. 404 while calm — the panel only exists during an incident.
 */
export interface IncidentTrace {
  /** Seconds between consecutive samples (after downsampling). */
  dtS: number;
  /** SMV in g. Rest sits near 1.0; the impact peak is preserved. */
  samples: number[];
  /** Detected phase positions, in seconds from the window start. */
  phases: {
    /** [start, end] of the free-fall dip. */
    freefall: [number, number];
    impactS: number;
    stillFromS: number;
  };
  thresholds: { freefallG: number; impactG: number };
  peakG: number;
  freefallMs: number;
}

/** ---- Judge-metrics payload (GET /api/training-stats) ----
 * The ILLUSTRATIVE magnitude-feature logistic regression (ADR 0009). Every
 * number is measured from real deterministic GD runs on the curated SisFall
 * table — nothing simulated. It never scores a resident; its ~80% ceiling
 * motivates the shipped ordered-signature detector (96.2%). Like
 * IncidentTrace, a read-only presentation surface outside the score contract. */
export interface TrainingSplit {
  /** e.g. "60/40" (train/test). */
  split: string;
  testFraction: number;
  confusionMatrix: { tp: number; fp: number; fn: number; tn: number };
  accuracy: number;
  precision: number;
  recall: number;
  counts: { train: number; test: number };
}

export interface TrainingStats {
  /** Honesty label — rendered, not hidden. */
  $note: string;
  featureNames: string[];
  /** Standardised LR coefficients, aligned with featureNames. */
  coefficients: number[];
  intercept: number;
  confusionMatrix: { tp: number; fp: number; fn: number; tn: number };
  accuracy: number;
  precision: number;
  recall: number;
  learningCurve: { trainSize: number; accuracy: number }[];
  /** Recorded from the actual gradient-descent run (headline split). */
  convergence: { iter: number; loss: number; testAccuracy: number }[];
  /** Real re-fits at 60/40, 70/30, 80/20. */
  splitSensitivity: TrainingSplit[];
  counts: { total: number; train: number; test: number };
}

/** ---- Incident / re-rank event (pushed over the live channel) ----
 * Emitted when an acute event fires mid-shift. The UI pins `entry` to the top
 * and can open `detail` immediately without a second fetch.
 */
export interface IncidentEvent {
  type: "incident";
  event: "acute-detected";
  /** ISO 8601 — when the event was emitted. */
  emittedAt: string;
  /** The new acute row to pin at the top of the caseload. */
  entry: CaseloadEntry;
  /** Full drill-down so the UI can open it on arrival. */
  detail: ResidentDetail;
}
