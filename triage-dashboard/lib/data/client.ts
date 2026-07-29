/* ============================================================================
 * THE DATA SEAM  —  the single module every component reads data through.
 *
 *   UI  ──imports──▶  dataClient  ──fetch──▶  /api/*  ──proxies──▶  scoring-service
 *
 * RULE: components/ and app/ import ONLY from here. They never touch /api,
 * fetch, or any other data source directly.
 *
 * The mock era is over: /api/* rewrites (next.config.mjs) proxy the FastAPI
 * scoring-service, the live channel is real SSE, and "Simulate incident"
 * POSTs a real injection endpoint on the service.
 * ==========================================================================*/

import type {
  AlertStatus,
  CaseloadEntry,
  IncidentEvent,
  IncidentTrace,
  LocationPayload,
  RankedCaseload,
  RegisterResidentPayload,
  ResidentDetail,
  TrainingStats,
} from "@/lib/types";

export interface DataClient {
  /** Ranked caseload for the current shift (acute first, then chronic desc). */
  getRankedCaseload(): Promise<RankedCaseload>;
  /** Full drill-down for one resident. */
  getResidentDetail(id: string): Promise<ResidentDetail>;
  /**
   * Subscribe to acute incidents pushed from the live channel.
   * Returns an unsubscribe function. Backend swaps the body for SSE/WebSocket.
   */
  subscribeToIncidents(handler: (event: IncidentEvent) => void): () => void;
  /**
   * Demo trigger: asks the scoring-service to inject a fall. The resulting
   * IncidentEvent arrives back through the SSE stream like a real detection.
   */
  simulateIncident(): Promise<void>;
  /**
   * Specificity demo: injects a dropped-phone-like impact through the SAME
   * detector. It returns detected:false and marks NO incident — the caseload
   * stays calm. Resolves with what the detector saw for a calm UI note.
   */
  simulateNearMiss(): Promise<{ detected: boolean; peakG: number; reason: string }>;
  /** Demo reset: clears the active incident so the beat can be re-run. */
  clearIncident(): Promise<void>;
  /**
   * The accelerometer signal behind the active incident (drilldown waveform).
   * Resolves null while the caseload is calm (the endpoint 404s).
   */
  getIncidentTrace(): Promise<IncidentTrace | null>;
  /**
   * Judge-metrics payload: the illustrative classifier's real training run
   * (convergence, splits, confusion matrices). Deterministic on the backend.
   */
  getTrainingStats(): Promise<TrainingStats>;
  /**
   * Camera acute source (/watch, feature-spec §1b): the browser pose heuristic
   * reports a detected fall. Fires the SAME incident path as an accelerometer
   * fall (caseload preemption, SSE, Telegram) — honestly labelled Camera (pose)
   * with the heuristic's own confidence. Empty payload = backend demo defaults.
   */
  reportCameraFall(payload?: {
    stillnessS?: number;
    confidence?: number;
    note?: string;
    /** Enrolled identity (ADR 0011). Optional and fail-open: absent or
     * unknown ids produce the generic incident. */
    residentId?: string;
  }): Promise<void>;
  /**
   * Long-lie escalation (ADR 0012): the camera saw no recovery
   * `stillDownS` seconds after the fall alert. Fires the STILL DOWN
   * Telegram message; never creates a new incident.
   */
  reportStillDown(payload: {
    stillDownS: number;
    residentId?: string;
  }): Promise<void>;
  /**
   * Runtime registry (ADR 0013): register a new person into the roster.
   * Resolves with their scored caseload entry; an unkeyed location falls
   * back to the default zone on the backend.
   */
  registerResident(payload: RegisterResidentPayload): Promise<CaseloadEntry>;
  /**
   * Runtime registry (ADR 0013): key in where an existing resident is.
   * Fields not sent stay untouched; zone: "" reverts to the fixture default.
   */
  setResidentLocation(id: string, payload: LocationPayload): Promise<void>;
  /**
   * Resident lifecycle (ADR 0014): delete a runtime registrant. Rejects for
   * built-in roster residents (409) and unknown ids (404). The caller owns
   * the on-device cascade (face gallery, tracker binding, selectors).
   */
  deleteResident(id: string): Promise<void>;
  /**
   * Alert-leg visibility: whether Telegram is configured and the outcome of
   * the most recent dispatch (sent / failed / not-configured). Backs the
   * status badge so the caregiver-ping leg is never silently unverifiable.
   */
  getAlertStatus(): Promise<AlertStatus>;
}

/* ------------------------------- base url -------------------------------- */
// Same-origin in the browser; absolute for any server-side call.
const BASE =
  typeof window === "undefined" ? "http://localhost:3000" : "";

async function getJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return (await res.json()) as T;
}

/* -------------------------------- client --------------------------------- */
export const dataClient: DataClient = {
  getRankedCaseload() {
    return getJSON<RankedCaseload>("/api/caseload");
  },

  getResidentDetail(id: string) {
    return getJSON<ResidentDetail>(`/api/residents/${encodeURIComponent(id)}`);
  },

  subscribeToIncidents(handler) {
    // Keepalive watchdog (demo-runbook fix #6): the service emits a named
    // "heartbeat" event every ~15s. If nothing (message or heartbeat) lands
    // within WATCHDOG_MS, or the stream errors (laptop sleep, Wi-Fi blip),
    // silently tear down and reconnect. No user action, no UI change.
    const WATCHDOG_MS = 35_000; // ~2x the server heartbeat interval
    const RECONNECT_DELAY_MS = 2_000;
    let es: EventSource | null = null;
    let watchdog: ReturnType<typeof setTimeout> | undefined;
    let reconnect: ReturnType<typeof setTimeout> | undefined;
    let closed = false;

    const armWatchdog = () => {
      clearTimeout(watchdog);
      watchdog = setTimeout(
        () => restart(`no message or heartbeat in ${WATCHDOG_MS}ms`),
        WATCHDOG_MS,
      );
    };

    const restart = (reason: string) => {
      if (closed) return;
      console.warn(`[incidents/stream] reconnecting: ${reason}`);
      es?.close();
      clearTimeout(watchdog);
      clearTimeout(reconnect);
      reconnect = setTimeout(connect, RECONNECT_DELAY_MS);
    };

    const connect = () => {
      if (closed) return;
      es = new EventSource("/api/incidents/stream");
      armWatchdog();
      es.onmessage = (m) => {
        armWatchdog();
        handler(JSON.parse(m.data) as IncidentEvent);
      };
      es.addEventListener("heartbeat", armWatchdog);
      es.onerror = () => restart("stream error");
    };

    connect();
    return () => {
      closed = true;
      clearTimeout(watchdog);
      clearTimeout(reconnect);
      es?.close();
    };
  },

  async simulateIncident() {
    const res = await fetch(`${BASE}/api/incidents/simulate`, { method: "POST" });
    if (!res.ok) throw new Error(`/api/incidents/simulate -> ${res.status}`);
    // The IncidentEvent arrives via the SSE stream — no local fan-out.
  },

  async simulateNearMiss() {
    const res = await fetch(`${BASE}/api/incidents/simulate-nearmiss`, {
      method: "POST",
    });
    if (!res.ok) throw new Error(`/api/incidents/simulate-nearmiss -> ${res.status}`);
    return (await res.json()) as { detected: boolean; peakG: number; reason: string };
  },

  async clearIncident() {
    const res = await fetch(`${BASE}/api/incidents/clear`, { method: "POST" });
    if (!res.ok) throw new Error(`/api/incidents/clear -> ${res.status}`);
  },

  async registerResident(payload) {
    const res = await fetch(`${BASE}/api/residents`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`/api/residents -> ${res.status}`);
    return (await res.json()) as CaseloadEntry;
  },

  async setResidentLocation(id, payload) {
    const res = await fetch(
      `${BASE}/api/residents/${encodeURIComponent(id)}/location`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      },
    );
    if (!res.ok) throw new Error(`/api/residents/${id}/location -> ${res.status}`);
  },

  async deleteResident(id) {
    const res = await fetch(`${BASE}/api/residents/${encodeURIComponent(id)}`, {
      method: "DELETE",
    });
    if (!res.ok) throw new Error(`/api/residents/${id} -> ${res.status}`);
  },

  getTrainingStats() {
    return getJSON<TrainingStats>("/api/training-stats");
  },

  getAlertStatus() {
    return getJSON<AlertStatus>("/api/alerts/status");
  },

  async reportCameraFall(payload) {
    const res = await fetch(`${BASE}/api/incidents/cv-detected`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload ?? {}),
    });
    if (!res.ok) throw new Error(`/api/incidents/cv-detected -> ${res.status}`);
    // The IncidentEvent arrives via the SSE stream — no local fan-out.
  },

  async reportStillDown(payload) {
    const res = await fetch(`${BASE}/api/incidents/escalate`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(`/api/incidents/escalate -> ${res.status}`);
  },

  async getIncidentTrace() {
    const res = await fetch(`${BASE}/api/incidents/trace`, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`/api/incidents/trace -> ${res.status}`);
    return (await res.json()) as IncidentTrace;
  },
};
