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
  IncidentEvent,
  IncidentTrace,
  RankedCaseload,
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

  getTrainingStats() {
    return getJSON<TrainingStats>("/api/training-stats");
  },

  async getIncidentTrace() {
    const res = await fetch(`${BASE}/api/incidents/trace`, { cache: "no-store" });
    if (res.status === 404) return null;
    if (!res.ok) throw new Error(`/api/incidents/trace -> ${res.status}`);
    return (await res.json()) as IncidentTrace;
  },
};
