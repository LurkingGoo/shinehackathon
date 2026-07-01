/* GET /api/residents/:id  ->  ResidentDetail
 * MOCK backend. Contract: lib/types.ts#ResidentDetail
 */
import { NextResponse } from "next/server";
import { fixtureDetailById } from "@/lib/data/fixtures";

export const dynamic = "force-dynamic";

export async function GET(
  _req: Request,
  { params }: { params: { id: string } }
) {
  const detail = fixtureDetailById(params.id);
  if (!detail) {
    return NextResponse.json({ error: "resident not found" }, { status: 404 });
  }
  return NextResponse.json(detail);
}
