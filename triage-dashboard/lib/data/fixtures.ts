/* ============================================================================
 * MOCK FIXTURES — the ONLY hard-coded data in the app.
 *
 * The backend replaces this source (and the /api routes that read it). Nothing
 * in components/ imports this file directly — they go through lib/data/client.ts.
 *
 * Shapes mirror reality so the swap is honest:
 *   - chronic residents on CASAS-style PIR/door ambient signals
 *   - one SisFall-style fall trace (INCIDENT) injected on "Simulate incident"
 * ==========================================================================*/

import type {
  CaseloadEntry,
  IncidentEvent,
  ResidentDetail,
  RiskFeature,
} from "@/lib/types";

/** Internal fixture row: resident + score + the features behind it. */
interface FixtureRow {
  id: string;
  name: string;
  age: number;
  unit: string;
  track: "acute" | "chronic";
  risk: number;
  confidence: number;
  updatedAt: string;
  recency: string;
  sensor: string;
  sensorClass: string;
  rationale: string;
  features: RiskFeature[];
  recommendedAction: string;
}

const now = () => new Date();
const minsAgo = (m: number) => new Date(now().getTime() - m * 60_000).toISOString();
const hrsAgo = (h: number) => new Date(now().getTime() - h * 3_600_000).toISOString();

/** Chronic caseload. Acute is injected at runtime via INCIDENT. */
export const RESIDENTS: FixtureRow[] = [
  {
    id: "r-rajoo",
    name: "Rajoo Subramaniam",
    age: 78,
    unit: "Blk 112 #05-214",
    track: "chronic",
    risk: 0.71,
    confidence: 0.82,
    updatedAt: minsAgo(22),
    recency: "22 min ago",
    sensor: "PIR motion",
    sensorClass: "CASAS ambient",
    rationale: "No kitchen activity in 16h — usually eats by 08:00.",
    features: [
      { label: "Kitchen inactivity", value: "16h 04m", weight: 0.52, baseline: "typ. < 4h" },
      { label: "Last confirmed motion", value: "Bedroom, 22 min ago", weight: 0.19, baseline: "" },
      { label: "Front door", value: "Not opened today", weight: 0.11, baseline: "typ. 08:10" },
    ],
    recommendedAction: "Call resident. If no answer in 15 min, dispatch buddy visit.",
  },
  {
    id: "r-wong",
    name: "Wong Lai Keng",
    age: 85,
    unit: "Blk 108 #11-330",
    track: "chronic",
    risk: 0.63,
    confidence: 0.77,
    updatedAt: hrsAgo(1),
    recency: "1h ago",
    sensor: "Door + PIR",
    sensorClass: "CASAS ambient",
    rationale: "Hasn't left bedroom by 10:00 — 3σ below her routine.",
    features: [
      { label: "Bedroom exit", value: "None by 10:00", weight: 0.44, baseline: "typ. 07:30" },
      { label: "Bathroom visits", value: "0 today", weight: 0.22, baseline: "typ. 2 by 10:00" },
      { label: "Motion variance", value: "3.1σ low", weight: 0.11, baseline: "" },
    ],
    recommendedAction: "Flag for morning check-in call. Low-urgency welfare follow-up.",
  },
  {
    id: "r-lim",
    name: "Lim Boon Huat",
    age: 74,
    unit: "Blk 115 #03-120",
    track: "chronic",
    risk: 0.44,
    confidence: 0.69,
    updatedAt: minsAgo(40),
    recency: "40 min ago",
    sensor: "PIR motion",
    sensorClass: "CASAS ambient",
    rationale: "Night bathroom trips up 3× vs baseline this week.",
    features: [
      { label: "Nocturnal trips", value: "6 / night", weight: 0.31, baseline: "typ. 2" },
      { label: "Sleep fragmentation", value: "High", weight: 0.09, baseline: "" },
      { label: "Daytime activity", value: "Normal", weight: 0.04, baseline: "" },
    ],
    recommendedAction: "Note trend. Suggest GP review of overnight symptoms at next visit.",
  },
  {
    id: "r-devi",
    name: "Devi Nair",
    age: 80,
    unit: "Blk 110 #07-45",
    track: "chronic",
    risk: 0.28,
    confidence: 0.81,
    updatedAt: minsAgo(15),
    recency: "15 min ago",
    sensor: "Door sensor",
    sensorClass: "CASAS ambient",
    rationale: "Morning routine on track — front door 07:50 as usual.",
    features: [
      { label: "Front door", value: "07:50 (on time)", weight: 0.0, baseline: "typ. 07:45" },
      { label: "Kitchen activity", value: "Normal", weight: 0.0, baseline: "" },
    ],
    recommendedAction: "No action needed.",
  },
  {
    id: "r-goh",
    name: "Goh Cheng Watt",
    age: 77,
    unit: "Blk 112 #09-88",
    track: "chronic",
    risk: 0.19,
    confidence: 0.74,
    updatedAt: minsAgo(8),
    recency: "8 min ago",
    sensor: "PIR motion",
    sensorClass: "CASAS ambient",
    rationale: "All routines within normal range today.",
    features: [{ label: "Activity pattern", value: "Nominal", weight: 0.0, baseline: "" }],
    recommendedAction: "No action needed.",
  },
];

/** SisFall-style fall trace injected on "Simulate incident". */
export const INCIDENT_ROW: FixtureRow = {
  id: "r-tan",
  name: "Tan Ah Moi",
  age: 82,
  unit: "Blk 108 #04-210",
  track: "acute",
  risk: 0.94,
  confidence: 0.94,
  updatedAt: minsAgo(0),
  recency: "just now",
  sensor: "Accelerometer",
  sensorClass: "Wearable bangle",
  rationale: "Fall detected — 3.1g impact then 40s no movement, bedroom floor.",
  features: [
    { label: "Peak impact", value: "3.1 g", weight: 0.6, baseline: "walking < 1.4 g" },
    { label: "Post-impact stillness", value: "40 s", weight: 0.3, baseline: "" },
    { label: "Orientation", value: "Horizontal", weight: 0.1, baseline: "" },
  ],
  recommendedAction: "CALL NOW. If no response, escalate to MOH 24/7 line + dispatch.",
};

/* ---- derivations: fixture rows -> contract payloads ---- */

function toEntry(r: FixtureRow, rank: number): CaseloadEntry {
  return {
    id: r.id,
    name: r.name,
    age: r.age,
    unit: r.unit,
    rank,
    score: {
      track: r.track,
      risk: r.risk,
      confidence: r.confidence,
      updatedAt: r.updatedAt,
      recency: r.recency,
      sensor: r.sensor,
      sensorClass: r.sensorClass,
      rationale: r.rationale,
    },
  };
}

/** Deterministic briefing template. An LLM would only smooth this wording. */
function briefingFor(r: FixtureRow): string {
  const top = r.features[0];
  if (r.track === "acute") {
    return `${r.name} (${r.age}) may have fallen — a ${top.value} impact then ${r.features[1]?.value ?? "sustained"} of no movement on the bedroom floor, ${r.recency}. Please reach her first. Confidence ${Math.round(r.confidence * 100)}%.`;
  }
  return `${r.name} (${r.age}) is on this list mostly because of ${top.label.toLowerCase()} (${top.value}${top.baseline ? `, ${top.baseline}` : ""}). Worth a check this week — not urgent. Confidence ${Math.round(r.confidence * 100)}%.`;
}

function toDetail(r: FixtureRow): ResidentDetail {
  return {
    id: r.id,
    name: r.name,
    age: r.age,
    unit: r.unit,
    score: toEntry(r, 0).score,
    features: r.features,
    recommendedAction: r.recommendedAction,
    briefing: briefingFor(r),
  };
}

/** Order: acute first, then chronic by risk desc. This is the ranking rule. */
export function buildRankedEntries(rows: FixtureRow[]): CaseloadEntry[] {
  const acute = rows.filter((r) => r.track === "acute");
  const chronic = rows.filter((r) => r.track !== "acute").sort((a, b) => b.risk - a.risk);
  return [...acute, ...chronic].map((r, i) => toEntry(r, i + 1));
}

export function fixtureDetailById(id: string): ResidentDetail | undefined {
  const row = [...RESIDENTS, INCIDENT_ROW].find((r) => r.id === id);
  return row ? toDetail(row) : undefined;
}

export function buildIncidentEvent(): IncidentEvent {
  const detail = toDetail(INCIDENT_ROW);
  return {
    type: "incident",
    event: "acute-detected",
    emittedAt: new Date().toISOString(),
    entry: toEntry(INCIDENT_ROW, 1),
    detail,
  };
}
