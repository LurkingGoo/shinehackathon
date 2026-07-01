/* ============================================================================
 * SHARED MOCK CASELOAD — JSGP Eldercare Triage Dashboard (POC)
 * Reused across all 5 visual-direction mockups so the data reads identically.
 *
 * Design rule encoded here:
 *   - ACUTE events (track: "acute") always preempt at the top.
 *   - CHRONIC scores (track: "chronic") rank the non-emergency caseload beneath.
 *   - rationale is DETERMINISTIC — templated from `features`, never invented.
 * Data shapes mirror reality: chronic = CASAS PIR/door; acute = SisFall fall trace.
 * ==========================================================================*/

window.CASELOAD = [
  // ---- CHRONIC caseload (acute injected at runtime by "Simulate incident") ----
  {
    id: "r-rajoo",
    name: "Rajoo Subramaniam",
    age: 78, unit: "Blk 112 #05-214",
    track: "chronic",
    risk: 0.71, confidence: 0.82,
    recency: "22 min ago",
    sensor: "PIR motion", sensorClass: "CASAS ambient",
    rationale: "No kitchen activity in 16h — usually eats by 08:00.",
    features: [
      { label: "Kitchen inactivity", value: "16h 04m", weight: 0.52, baseline: "typ. < 4h" },
      { label: "Last confirmed motion", value: "Bedroom, 22 min ago", weight: 0.19, baseline: "" },
      { label: "Front door", value: "Not opened today", weight: 0.11, baseline: "typ. 08:10" }
    ],
    action: "Call resident. If no answer in 15 min, dispatch buddy visit."
  },
  {
    id: "r-wong",
    name: "Wong Lai Keng",
    age: 85, unit: "Blk 108 #11-330",
    track: "chronic",
    risk: 0.63, confidence: 0.77,
    recency: "1h ago",
    sensor: "Door + PIR", sensorClass: "CASAS ambient",
    rationale: "Hasn't left bedroom by 10:00 — 3σ below her routine.",
    features: [
      { label: "Bedroom exit", value: "None by 10:00", weight: 0.44, baseline: "typ. 07:30" },
      { label: "Bathroom visits", value: "0 today", weight: 0.22, baseline: "typ. 2 by 10:00" },
      { label: "Motion variance", value: "3.1σ low", weight: 0.11, baseline: "" }
    ],
    action: "Flag for morning check-in call. Low-urgency welfare follow-up."
  },
  {
    id: "r-lim",
    name: "Lim Boon Huat",
    age: 74, unit: "Blk 115 #03-120",
    track: "chronic",
    risk: 0.44, confidence: 0.69,
    recency: "40 min ago",
    sensor: "PIR motion", sensorClass: "CASAS ambient",
    rationale: "Night bathroom trips up 3× vs baseline this week.",
    features: [
      { label: "Nocturnal trips", value: "6 / night", weight: 0.31, baseline: "typ. 2" },
      { label: "Sleep fragmentation", value: "High", weight: 0.09, baseline: "" },
      { label: "Daytime activity", value: "Normal", weight: 0.04, baseline: "" }
    ],
    action: "Note trend. Suggest GP review of overnight symptoms at next visit."
  },
  {
    id: "r-devi",
    name: "Devi Nair",
    age: 80, unit: "Blk 110 #07-45",
    track: "chronic",
    risk: 0.28, confidence: 0.81,
    recency: "15 min ago",
    sensor: "Door sensor", sensorClass: "CASAS ambient",
    rationale: "Morning routine on track — front door 07:50 as usual.",
    features: [
      { label: "Front door", value: "07:50 (on time)", weight: 0.0, baseline: "typ. 07:45" },
      { label: "Kitchen activity", value: "Normal", weight: 0.0, baseline: "" }
    ],
    action: "No action needed."
  },
  {
    id: "r-goh",
    name: "Goh Cheng Watt",
    age: 77, unit: "Blk 112 #09-88",
    track: "chronic",
    risk: 0.19, confidence: 0.74,
    recency: "8 min ago",
    sensor: "PIR motion", sensorClass: "CASAS ambient",
    rationale: "All routines within normal range today.",
    features: [
      { label: "Activity pattern", value: "Nominal", weight: 0.0, baseline: "" }
    ],
    action: "No action needed."
  }
];

/* The acute fall trace injected mid-demo by "Simulate incident".
   Modelled on a SisFall forward-fall record: impact spike then stillness. */
window.INCIDENT = {
  id: "r-tan",
  name: "Tan Ah Moi",
  age: 82, unit: "Blk 108 #04-210",
  track: "acute",
  risk: 0.94, confidence: 0.94,
  recency: "just now",
  sensor: "Accelerometer", sensorClass: "Wearable bangle",
  rationale: "Fall detected — 3.1g impact then 40s no movement, bedroom floor.",
  features: [
    { label: "Peak impact", value: "3.1 g", weight: 0.6, baseline: "walking < 1.4 g" },
    { label: "Post-impact stillness", value: "40 s", weight: 0.3, baseline: "" },
    { label: "Orientation", value: "Horizontal", weight: 0.1, baseline: "" }
  ],
  action: "CALL NOW. If no response, escalate to MOH 24/7 line + dispatch."
};
