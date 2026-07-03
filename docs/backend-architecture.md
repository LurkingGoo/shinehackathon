---
type: doc
diataxis: explanation
title: Backend Architecture & Scoring Approach
status: solidified
last_updated: 2026-07-01
tags: [architecture, scoring, backend]
---

# Backend Architecture & Scoring Approach

> **Explanation tier · arc42-lite.** The frontend (`triage-dashboard/`) froze the
> **interface**; this doc records what lives *behind* the `lib/data/client.ts`
> seam and why. Doc standard + index: [[README]]. Decision record:
> [[0002-backend-stack-and-scoring]]. Concrete features: [[feature-spec]].
> Scoring card / datasets / limits: [[scoring-card]].
>
> **arc42 section map:** §1 Introduction & goals → the frozen contract (§1 below) ·
> §2 Constraints → the seam + contract · §3 Context → Topology · §5 Building
> blocks → Module layout · §6 Runtime → Data flows / replayer · §9 Decisions →
> [[0002-backend-stack-and-scoring]] · §11 Risks → §6 below.

## 1. What is frozen (do not relitigate)

The frontend contract (`lib/types.ts`) fixes both the endpoints **and** the
data-science content:

- **3 surfaces:** `GET /api/caseload` → `RankedCaseload`,
  `GET /api/residents/:id` → `ResidentDetail`, and a push channel emitting
  `IncidentEvent`.
- **One presentation surface (added 2026-07-03):** `GET /api/incidents/trace` →
  `IncidentTrace`: the downsampled accelerometer window + detected phase
  positions behind the active incident, feeding the drilldown's "What the
  sensor saw" waveform. 404 while calm. Read-only, derived from the same
  trace the acute score is computed on (numbers always agree).
- **Every score must decompose into `RiskFeature[]` with weights.** A black-box
  score that can't produce weighted features is rejected *by the contract*. This
  forces explainability on us (a good constraint).
- `risk` and `confidence` are **separate 0..1 axes**, never conflated.
  `updatedAt` is ISO-8601; `recency` is a pre-formatted display string.

## 2. Solidified stack

| Layer | Choice | Why |
|-------|--------|-----|
| Scoring service | **Python 3.11 · FastAPI · uvicorn** | Team is Python; SisFall/CASAS are Python-native |
| Feature math | numpy / scipy / pandas | Signal magnitude, baselines, z-scores |
| Live channel | **SSE** (`StreamingResponse` / `sse-starlette`) | Client stub already assumes `EventSource`; simpler than WebSocket |
| Origin | **Next.js `/api/*` proxies the service** | Keeps client on relative URLs: no CORS, seam untouched |
| Storage | **None for the demo** | Baselines precompute to JSON; replayer holds shift state in memory. SQLite only if event history must survive restart |
| Briefing drafting | flagged, `briefing` string only | Smooths wording from `score`+`features`; never invents cause. Flag off ⇒ demo still works |

### Topology

```
Browser ──▶ Next.js (frontend + /api proxy) ──▶ FastAPI scoring-service
  /api/caseload          →  GET  :8000/caseload
  /api/residents/:id     →  GET  :8000/residents/:id
  /api/incidents/stream  →  SSE  pipe :8000/incidents/stream
  /api/incidents/trace   →  GET  :8000/incidents/trace   (waveform, 404 calm)
```

The mock `/api/*` routes swap from reading `fixtures.ts` to proxying the service,
the exact swap the seam was built for. `simulateIncident` +
`app/api/incidents/route.ts` are deleted once the live channel exists.

### Module layout

```
scoring-service/
  app/
    main.py            # FastAPI app + the 3 routes
    models.py          # pydantic: MUST serialize to lib/types.ts EXACTLY
    scoring/
      acute.py         #  SisFall fall detection
      chronic.py       #  CASAS baseline + anomaly
      features.py      #  RiskFeature build + weight normalization
      rationale.py     #  deterministic templates + recommendedAction rules
    briefing.py        #  optional Claude smoothing (flagged)
    replay/engine.py   #  accelerated-time replayer + SSE generator + fall injection
    data/loaders.py    #  SisFall + CASAS parsers
  baselines.json       # precomputed per-resident routine baselines
  requirements.txt
```

## 3. Scoring approach: credible heuristics (NO model training)

**We do not train a model.** No labels, no fitted classifier. Datasets are used
as realistic streams to compute over and replay. Two tracks, never blended:

### Acute: SisFall fall detection (physics, not ML)
- Signal-magnitude vector `SMV = √(ax²+ay²+az²)`.
- Fall pattern = free-fall dip below a low threshold → impact peak above a high
  threshold within a short window → post-impact stillness.
- `features`: peak-g, free-fall duration, post-impact inactivity.
- `confidence` = margin past the thresholds.
- Acute always pins to the top of the caseload (a "now" interrupt).

### Chronic: CASAS ambient anomaly (self-baselining)
- Precompute each resident's **own** routine baseline: first-kitchen-motion hour,
  per-hour activity counts, typical inter-event gaps.
- Live score = deviation from that baseline (z-score / gap-vs-typical).
- `features` map onto the existing fixtures: "Kitchen inactivity 16h vs typ. <4h",
  "Front door not opened", "Last confirmed motion".
- `risk` = normalized weighted sum of feature contributions.
- `confidence` = data completeness / signal quality, a **separate axis**.

### The deterministic spine (contract-critical)
Every score decomposes into `RiskFeature[]` with weights →
`rationale` and `recommendedAction` are **templates filled from the top
features**, not free text. The drafting layer never touches the "why"; it may
only smooth the `briefing` paragraph from facts already in `score`+`features`.

## 4. Singapore fit

CASAS (US) and SisFall (Colombia) are **not** Singapore data, but the method
carries **no geographic assumption**:

- **Fall detection is physics**: same accelerometer signature in an HDB flat as
  anywhere. Zero transfer risk.
- **Chronic is self-referential**: each resident is their *own* baseline, so no
  foreign "routine prior" is baked in. Deployed locally, it learns each
  resident's rhythm in days.
- **Singapore fit lives in the framing** (HDB units, One Care, JSGP), already in
  the frozen Warm Human UI, not in the math.
- **Judging answer:** public datasets are *proxies* (Singapore eldercare sensor
  data isn't public); the method needs no local training, so real deployment
  self-calibrates from local residents. Proxy for method validation, not a claim
  that US routines equal Singapore routines.

## 5. Scope discipline: is it overengineered?

**Appropriately scoped, not over-built.** Guardrails:

- **Justified:** two-track split + deterministic rationale (contract-required and
  the differentiator); a Python service (dataset-native); SSE (demo climax needs
  a stream).
- **Already trimmed:** no model training; no DB; SSE not WebSocket;
  Twilio/Supabase deferred until the flow is agreed.
- **Explicit fallbacks if time runs short (a decision, not a scramble):**
  1. **Precompute the entire chronic caseload offline to JSON.** Chronic is not a
     "now" concern, so the only running-server duty becomes the acute SSE replayer.
  2. **Make the service SSE-only.** Serve the two GETs as static JSON.
- **Watch:** do not add a DB or start training "because we have the data."

## 6. Biggest risk: the replayer, not the scoring

The demo climax is a fall firing mid-shift → live re-rank. That's timing/streaming
plumbing (accelerated clock, scripted injection, SSE piped through Next) and it's
where hackathon demos break. **De-risk first:** build a thin end-to-end SSE spike
(fake event every 5s → UI re-ranks) before investing in real detection.

## 7. Feature roadmap (additions, post-MVP)

Ordered by value-to-effort. None required for the demo.

| Track | Addition | Notes |
|-------|----------|-------|
| Chronic | Bathroom/toilet frequency vs baseline | Classic UTI / decline signal in CASAS |
| Chronic | Night-wandering (motion during typical sleep hours) | High-signal, easy from PIR timestamps |
| Chronic | Multi-day trend (risk slope, not just point deviation) | Distinguishes "bad day" from "declining" |
| Acute | Post-fall long-lie detection (no motion N min after impact) | Escalates severity; strong story |
| Acute | Near-fall / stumble precursors | Lower confidence, feeds chronic frailty |
| Cross | Sensor-health / data-gap flag as its own feature | Honest about blind spots; feeds `confidence` |
| Ops | Wire Call now / Escalate → Twilio | Deferred until comms flow agreed |
| Ops | Persist events + baselines (SQLite/Supabase) | Only when multi-session/restart matters |

## 8. The one discipline that keeps the seam honest

`models.py` must serialize to **exactly** the `lib/types.ts` shapes. Add a tiny
**contract test**: hit each endpoint, validate the JSON against a schema derived
from `types.ts`. That is the entire risk surface of the swap; guard it and the
backend is truly drop-in.
