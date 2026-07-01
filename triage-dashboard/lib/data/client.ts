/* ============================================================================
 * THE DATA SEAM  —  the single module every component reads data through.
 *
 *   UI  ──imports──▶  dataClient  ──fetch──▶  /api/*  ──reads──▶  fixtures.ts
 *
 * RULE: components/ and app/ import ONLY from here. They never touch fixtures,
 * /api, fetch, or any other data source directly. This is the exact seam the
 * backend replaces.
 *
 * HOW THE BACKEND TAKES OVER (no UI changes):
 *   1. Point the three read methods at the real service (or just make /api/*
 *      proxy the backend — the URLs already exist).
 *   2. Replace `subscribeToIncidents` with a real EventSource / WebSocket to the
 *      live channel (see CLAUDE.md). Delete `simulateIncident` — it is mock-only.
 *
 * Everything below the DataClient interface is disposable mock plumbing.
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
   * MOCK-ONLY. Fires the canned fall so the demo's "Simulate incident" button
   * works with no backend. Delete once the live channel exists.
   */
  simulateIncident(): Promise<void>;
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

/* --------------------- mock live-incident channel ------------------------ */
// A tiny in-process pub/sub standing in for the backend's push channel.
const incidentListeners = new Set<(e: IncidentEvent) => void>();

/* -------------------------------- client --------------------------------- */
export const dataClient: DataClient = {
  getRankedCaseload() {
    return getJSON<RankedCaseload>("/api/caseload");
  },

  getResidentDetail(id: string) {
    return getJSON<ResidentDetail>(`/api/residents/${encodeURIComponent(id)}`);
  },

  subscribeToIncidents(handler) {
    incidentListeners.add(handler);
    return () => incidentListeners.delete(handler);
    // BACKEND: replace with
    //   const es = new EventSource("/api/incidents/stream");
    //   es.onmessage = (m) => handler(JSON.parse(m.data));
    //   return () => es.close();
  },

  async simulateIncident() {
    // Fetch the canned incident shape from the mock endpoint, then fan out
    // to subscribers exactly as a real push would.
    const event = await getJSON<IncidentEvent>("/api/incidents");
    incidentListeners.forEach((fn) => fn(event));
  },
};
