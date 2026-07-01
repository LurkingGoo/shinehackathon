/* GET /api/caseload  ->  RankedCaseload
 * MOCK backend. Backend replaces the body (or proxies the real service).
 * Contract: lib/types.ts#RankedCaseload
 */
import { NextResponse } from "next/server";
import { buildRankedEntries, RESIDENTS } from "@/lib/data/fixtures";
import type { RankedCaseload } from "@/lib/types";

export const dynamic = "force-dynamic";

export async function GET() {
  const payload: RankedCaseload = {
    generatedAt: new Date().toISOString(),
    entries: buildRankedEntries(RESIDENTS),
  };
  return NextResponse.json(payload);
}
