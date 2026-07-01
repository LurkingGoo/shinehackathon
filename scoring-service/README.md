# scoring-service (backend)

The Python backend behind the `triage-dashboard` seam. Serves the two GET
surfaces + the SSE live channel the frontend expects; fixture-backed today, with
real SisFall (acute) / CASAS (chronic) detection wiring in behind the same
contract. **Design & spec:** [`../docs/`](../docs/) — start with
[`../docs/backend-architecture.md`](../docs/backend-architecture.md),
[`../docs/feature-spec.md`](../docs/feature-spec.md),
[`../docs/scoring-card.md`](../docs/scoring-card.md).

## Run

```bash
cd scoring-service
python -m venv .venv && . .venv/Scripts/activate    # Windows; use bin/activate on *nix
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- `GET  /caseload`           → `RankedCaseload`
- `GET  /residents/{id}`     → `ResidentDetail` (404 if unknown)
- `GET  /incidents/stream`   → SSE, one `IncidentEvent` per message
- `POST /incidents/simulate` → inject the canned fall (demo / de-risk)
- `GET  /health`

## Wire to the frontend

Next.js `/api/*` proxies these same-origin (no CORS); the seam
(`triage-dashboard/lib/data/client.ts`) then needs no component changes:

- `getRankedCaseload` → `GET /api/caseload`
- `getResidentDetail` → `GET /api/residents/:id`
- `subscribeToIncidents` → `new EventSource('/api/incidents/stream')`
- delete `simulateIncident` + `app/api/incidents/route.ts`; the button POSTs
  `/api/incidents/simulate` instead.

CORS also allows `http://localhost:3000` directly for quick local testing.

## Test

```bash
pytest -q          # contract + scoring + live-channel
```

- `tests/test_contract.py` — JSON matches `lib/types.ts` exactly (the seam guard).
- `tests/test_scoring.py`  — fall detection fires on a fall, not on a hard sit;
  chronic anomaly is monotonic & bounded.
- `tests/test_stream.py`   — the pub/sub hub delivers an injected incident (the
  demo's re-rank beat, de-risked independent of HTTP).

## Layout

```
app/
  main.py              # FastAPI app + the 4 routes
  models.py            # pydantic ⇒ exact lib/types.ts JSON (camelCase aliases)
  scoring/
    acute.py           # SisFall fall detection (SMV, free-fall→impact)
    chronic.py         # CASAS self-baselining anomaly (z-score)
    features.py        # RiskFeature weight normalization
    rationale.py       # deterministic templates + recommendedAction table
  briefing.py          # deterministic briefing; optional flagged LLM smoothing
  replay/engine.py     # IncidentHub pub/sub (SSE push side of the seam)
  data/
    fixtures.py        # mock data, ported 1:1 from the frontend fixtures
    loaders.py         # SisFall/CASAS parsers — STUB (next step)
baselines.json         # sample per-resident self-baselines
```

## Status
Fixture-backed endpoints + working SSE hub + real (unit-tested) scoring math.
**Next:** `data/loaders.py` (parse the real datasets), a replayer that streams a
shift in accelerated time and injects a real fall trace, then threshold
calibration (docs/scoring-card.md Metrics — no accuracy claims until then).
