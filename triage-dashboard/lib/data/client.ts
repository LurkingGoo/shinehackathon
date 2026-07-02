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
  RankedCaseload,
  ResidentDetail,
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
  /** Demo reset: clears the active incident so the beat can be re-run. */
  clearIncident(): Promise<void>;
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
    const es = new EventSource("/api/incidents/stream");
    es.onmessage = (m) => handler(JSON.parse(m.data) as IncidentEvent);
    return () => es.close();
  },

  async simulateIncident() {
    const res = await fetch(`${BASE}/api/incidents/simulate`, { method: "POST" });
    if (!res.ok) throw new Error(`/api/incidents/simulate -> ${res.status}`);
    // The IncidentEvent arrives via the SSE stream — no local fan-out.
  },

  async clearIncident() {
    const res = await fetch(`${BASE}/api/incidents/clear`, { method: "POST" });
    if (!res.ok) throw new Error(`/api/incidents/clear -> ${res.status}`);
  },
};
