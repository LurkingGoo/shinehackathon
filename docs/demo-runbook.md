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
> mid-shift and re-ranking the caseload live. Backend (`scoring-service/`) is not
> yet scaffolded — steps marked *(planned)* land with it.

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

## Run the scoring service *(planned)*

```bash
cd scoring-service
python -m venv .venv && . .venv/Scripts/activate   # Windows
pip install -r requirements.txt
python -m app.replay.baselines                     # precompute baselines.json
uvicorn app.main:app --port 8000
```

Then point Next's `/api/*` at it (proxy) and start the frontend as above.

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

## Contract test *(planned)*

```bash
cd scoring-service
pytest tests/test_contract.py    # each endpoint's JSON validates vs types.ts-derived schema
```

If this passes, the backend is a drop-in swap for the mock seam.
