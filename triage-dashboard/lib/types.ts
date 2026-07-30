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
  /** null for the honest "Unidentified person" camera identity. */
  age: number | null;
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
  /**
   * Last-motion area from the resident's ambient (PIR/door) track — alert
   * context, not a camera localization claim (ADR 0012). Optional: additive.
   */
  zone?: string;
  /**
   * True for runtime registrants (ADR 0013/0014) — the only rows the UI may
   * offer to delete. Fixture roster rows omit it. Optional: additive.
   */
  registered?: boolean;
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
  /**
   * Same ambient last-motion area as CaseloadEntry.zone (ADR 0013), so the
   * drill-down can render a keyed-in location. Optional: additive.
   */
  zone?: string;
}

/** ---- Runtime resident registry (ADR 0013) ----
 * Keyed-in location parts. All optional; the backend composes the address
 * from whichever parts arrive (unit > block+unitNumber > block > GPS) and an
 * absent/empty zone falls back to the default ("Living room"). */
export interface LocationPayload {
  zone?: string;
  unit?: string;
  block?: string;
  unitNumber?: string;
  lat?: number;
  lon?: number;
}

/** Operator registration (POST /api/residents): a new person by name. */
export interface RegisterResidentPayload extends LocationPayload {
  name: string;
  age?: number;
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

/** ---- Skeleton replay (ADR 0017) ----
 * Like IncidentTrace, a read-only presentation surface OUTSIDE the score
 * contract (not parity-guarded). Frames are opaque quantized integer rows:
 * [tMs, then 13 joints x (x*quantScale, y*quantScale, visibility*100)];
 * a 1-length row means no person was tracked that instant. Coordinates
 * only, never pixels; server retention = the incident's lifetime. */
/** Browser-computed replay facts (phase 2) — folded server-side into the
 * deterministic rationale + feature rows. All optional/fail-open. */
export interface ReplayFactsPayload {
  descentDurationMs: number | null;
  direction: "left" | "right" | "toward-camera" | "unknown";
  protectiveArm: boolean | null;
  postImpactMovement: "none" | "slight" | "moving" | "unknown";
  /** Peak descent velocity (normalized frame-heights/s) + its severity band
   * — the joint-based impact cue (spec 1.16.0). Optional/fail-open. */
  impactSpeed?: number | null;
  impactSeverity?: "gentle" | "moderate" | "hard" | null;
}

export interface ReplayUploadPayload {
  /** The X-Incident-Id nonce from the fall POST — pairs this buffer with
   * exactly one incident (a stale buffer is rejected 409, never retried). */
  incidentId: string;
  fps: number;
  quantScale: number;
  frames: number[][];
  facts?: ReplayFactsPayload | null;
}

/** GET /api/incidents/replay — 404 while calm, for accelerometer incidents,
 * and before the browser's upload lands. */
export interface IncidentReplay extends ReplayUploadPayload {
  receivedAt: string;
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

/** ---- Alert-leg visibility (GET /api/alerts/status) ----
 * Chain-of-custody surface (2026-07-26 test notes): whether the Telegram leg
 * is configured, and what actually happened to the most recent dispatch —
 * so a viewer never has to infer from silence that the caregiver ping did
 * not run. Read-only presentation surface outside the score contract. */
export interface AlertStatus {
  telegram: { configured: boolean };
  lastDispatch: {
    outcome: "sent" | "failed" | "not-configured";
    residentId: string;
    /** ISO 8601 — when the dispatch attempt resolved. */
    at: string;
  } | null;
  /**
   * Caregiver tap on the alert's "I am responding" button (ADR 0012).
   * Null until acknowledged; cleared when a new incident dispatches.
   */
  acknowledged?: { by: string; at: string } | null;
  /**
   * ADR 0017 phase 5: outcome of the most recent replay-GIF follow-up
   * (sent / failed / skipped / no-replay / not-configured). Optional.
   */
  replayAnimation?: { outcome: string; at: string } | null;
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
