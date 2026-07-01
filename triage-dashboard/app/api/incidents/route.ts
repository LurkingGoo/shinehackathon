/* GET /api/incidents  ->  IncidentEvent  (single canned fall, MOCK-only)
 *
 * This one-shot GET exists so the demo's "Simulate incident" button has a
 * shape to fan out. The REAL backend must instead PUSH IncidentEvents over a
 * live channel (SSE or WebSocket) — see CLAUDE.md "Live channel". When that
 * exists, delete this route and dataClient.simulateIncident().
 *
 * Contract: lib/types.ts#IncidentEvent
 */
import { NextResponse } from "next/server";
import { buildIncidentEvent } from "@/lib/data/fixtures";

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json(buildIncidentEvent());
}
