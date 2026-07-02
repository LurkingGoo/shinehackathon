---
type: doc
diataxis: how-to
title: Demo Runbook
status: active
last_updated: 2026-07-02
tags: [howto, demo, runbook]
---

# Demo Runbook

> **How-to tier.** Run the system and drive the demo's key beat: a fall firing
> mid-shift and re-ranking the caseload live. **The seam is swapped**: the
> frontend serves live from `scoring-service` (Next `/api/*` rewrites proxy it,
> the live channel is real SSE, the mock routes + `fixtures.ts` are deleted).

## Run the full system (live, two processes)

```bash
# 1. scoring service
cd scoring-service
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
pytest -q                                # 30 tests: contract + scoring + stream + loaders + baselines

# 2. frontend (proxies /api/* to :8000 — set SCORING_SERVICE_URL to override)
cd triage-dashboard
npm install
npm run dev          # http://localhost:3000
```

Click a resident → drill-down. Press **Simulate incident** → the frontend POSTs
`/api/incidents/simulate`; the service scores a fall trace through the acute
pipeline and the `IncidentEvent` arrives back over `/api/incidents/stream` (SSE)
— the acute row pins, flashes, and opens its drill-down.

Service endpoints: `GET /caseload`, `GET /residents/{id}`,
`GET /incidents/stream` (SSE), `POST /incidents/simulate`, `GET /health`.

Verified end-to-end through the proxy (2026-07-02): caseload 200 with computed
scores, resident 404, and the SSE event arriving at `:3000` after a simulate POST.

## Real datasets (drop-in; synthetic fallback keeps the demo alive)

Dataset files are **git-ignored** (`scoring-service/data/`). Loaders parse the
real on-disk formats and are tested against format-exact fixtures ([[scoring-card]]
Datasheet for provenance):

- **SisFall** → put trace files in `scoring-service/data/sisfall/` (falls are
  `F*.txt`, ADLs `D*.txt`). `POST /incidents/simulate` automatically injects the
  first real fall on disk (override with `SISFALL_TRACE=<path>`); with no files
  it falls back to the synthetic trace, so the demo never breaks.
- **CASAS** → any event file + a per-home sensor→area map, then:

```bash
cd scoring-service
python scripts/build_baselines.py data/casas/events.txt data/casas/area_map.json -o baselines.json
```

### Calibrate acute thresholds (fills the scoring-card metrics)

```bash
python scripts/calibrate.py            # detection / false-alarm at current thresholds
python scripts/calibrate.py --grid     # sweep, best rows first (sensitivity-ranked)
```

Numbers go into [[scoring-card]] §Metrics **only** from this script's output.

Scores are **computed**, not hardcoded: `app/scoring/pipeline.py` turns raw
signals into `RiskScore` + features (chronic anomaly aggregation via
`contribution_risk`; acute via `detect_fall` over the accelerometer trace).
Computed caseload today — Rajoo 0.652 · Wong 0.504 · Lim 0.368 · Devi/Goh 0.0;
acute Tan Ah Moi 0.97 (5.0 g impact, 40 s stillness). Values differ from the old
hand-set demo numbers by design ([[scoring-card]]); real inputs arrive via
`app/data/loaders.py`.

## Drive the demo (works now; real trace when the dataset is on disk)

1. Start both processes (above), with a real SisFall fall in `data/sisfall/`.
2. Open the dashboard — chronic caseload ranked, calm.
3. Press **Simulate incident** → the real trace runs through `detect_fall` →
   `IncidentEvent` over SSE → the acute row **pins to top, flashes, opens its
   drill-down** (the injected trace also backs the drill-down, so the numbers
   agree on re-fetch).
4. Talk through the deterministic rationale — every number on screen traces to a
   `RiskFeature` ([[feature-spec]]).

## Contract test (works now)

```bash
cd scoring-service
pytest tests/test_contract.py    # each endpoint's JSON validates vs types.ts-derived schema
```

Passing today: live responses validate against the generated
`contract.schema.json`; the committed schema is current with the models; and
**`test_models_match_types_ts` asserts the models match `lib/types.ts` field-for-
field** (the TS↔Python drift catcher — [[0004-contract-parity-guard]]). Plus
separate risk/confidence axes, acute-first ordering, 404, briefing guardrail.

Regenerate the schema artifact after any model change:

```bash
python -m app.contract      # rewrites contract.schema.json (a stale-artifact test enforces this)
```

As long as `pytest` passes, the backend is a drop-in swap for the mock seam.
