/* ============================================================================
 * DATA CONTRACT — the shapes the UI expects.
 *
 * This is the agreement between frontend (done) and backend (next). The UI
 * renders exactly these types; the backend's job is to return them from the
 * endpoints listed in CLAUDE.md. Change a field here → update both sides.
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
