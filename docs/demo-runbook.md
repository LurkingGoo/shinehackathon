---
type: doc
diataxis: how-to
title: Demo Runbook
status: draft
last_updated: 2026-07-01
tags: [howto, demo, runbook]
---

# Demo Runbook

> **How-to tier.** Run the system and drive the demo's key beat: a fall firing
> mid-shift and re-ranking the caseload live. Backend (`scoring-service/`) is
> **scaffolded and fixture-backed** — endpoints + SSE work and are tested. Steps
> marked *(planned)* are the remaining real-dataset wiring.

## Run the frontend (works today, mock-backed)

```bash
cd triage-dashboard
npm install
npm run dev          # http://localhost:3000
npm run typecheck    # tsc --noEmit
```

Click a resident → drill-down. Press **Simulate incident** → the canned fall fires
through the in-process pub/sub and the list re-ranks (this is the mock the backend
replaces).

## Run the scoring service (works now, fixture-backed)

```bash
cd scoring-service
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q                                          # 14 tests: contract + scoring + stream
```

Endpoints: `GET /caseload`, `GET /residents/{id}`, `GET /incidents/stream` (SSE),
`POST /incidents/simulate`, `GET /health`. Then point Next's `/api/*` at it
(proxy) *(planned)* and start the frontend as above.

Verified end-to-end (2026-07-01): open the stream, `POST /incidents/simulate`,
and the acute row arrives over SSE — the re-rank beat works at the backend layer
before any frontend wiring.

Scores are **computed**, not hardcoded: `app/scoring/pipeline.py` turns raw
signals into `RiskScore` + features (chronic anomaly aggregation via
`contribution_risk`; acute via `detect_fall` over the accelerometer trace).
Computed caseload today — Rajoo 0.652 · Wong 0.504 · Lim 0.368 · Devi/Goh 0.0;
acute Tan Ah Moi 0.97 (5.0 g impact, 40 s stillness). Values differ from the old
hand-set demo numbers by design ([[scoring-card]]); real inputs arrive via
`app/data/loaders.py`.

## Drive the demo *(planned)*

1. Start the service with a **shift replay** loaded (a CASAS slice + a SisFall
   trace scheduled to fire).
2. Open the dashboard — chronic caseload ranked, calm.
3. At the scripted moment (or via **Simulate incident**), the replayer injects the
   fall → service detects it → emits an `IncidentEvent` over
   `GET /api/incidents/stream` (SSE) → the acute row **pins to top, flashes, opens
   its drill-down**.
4. Talk through the deterministic rationale — every number on screen traces to a
   `RiskFeature` ([[feature-spec]]).

## De-risk first (do this before real detection)

Prove the streaming path end-to-end with a **fake** event every ~5 s
(`IncidentEvent` shape only) → confirm the UI re-ranks. The replayer/SSE plumbing
is the demo's biggest risk, not the scoring ([[backend-architecture]] §6).

## Contract test (works now)

```bash
cd scoring-service
pytest tests/test_contract.py    # each endpoint's JSON validates vs types.ts-derived schema
```

Passing today: exact camelCase keys, separate risk/confidence axes, acute-first
ordering, 404 on unknown resident, and the briefing-invents-no-numbers guardrail.
As long as this passes, the backend is a drop-in swap for the mock seam.
