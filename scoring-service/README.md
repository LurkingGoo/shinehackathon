# scoring-service (backend)

The Python backend behind the `triage-dashboard` seam. Serves the caseload +
resident surfaces, the SSE live channel, the incident simulation/camera tracks,
the judge-metrics endpoint, and off-thread Telegram fall alerts. Scoring runs on
real SisFall physics (acute) and CASAS self-baselining (chronic) behind the
frozen frontend contract. **Design & spec:**
[`../docs/feature-spec.md`](../docs/feature-spec.md),
[`../docs/scoring-card.md`](../docs/scoring-card.md), decisions in
[`../docs/adr/`](../docs/adr/).

## Run

```bash
cd scoring-service
python -m venv .venv && . .venv/Scripts/activate    # Windows; use bin/activate on *nix
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

- `GET  /caseload`                  → `RankedCaseload`
- `GET  /residents/{id}`            → `ResidentDetail` (404 if unknown)
- `GET  /incidents/stream`          → SSE, one `IncidentEvent` per message
- `POST /incidents/simulate`        → inject a real SisFall fall (rotating traces)
- `POST /incidents/simulate-nearmiss` → dropped-phone spike; must NOT detect (specificity demo)
- `POST /incidents/cv-detected`     → camera/pose fall track; same incident path, honestly labelled
- `POST /incidents/clear`           → demo reset to the calm chronic ranking
- `GET  /incidents/trace`           → "what the sensor saw" waveform (404 while calm / for camera incidents)
- `GET  /training-stats`            → judge-metrics page: the illustrative classifier (never scores a resident)
- `GET  /health`

Fall incidents also dispatch a **Telegram alert** off-thread when
`SHINEHACKATHON_TELEGRAM_BOT_TOKEN` + `SHINEHACKATHON_TELEGRAM_CHAT_ID` are set
(silent no-op otherwise; `scripts/telegram_setup.py` wires them up).

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
  demo's re-rank beat), incl. Telegram dispatch off the request path.
- `tests/test_loaders.py`  — real SisFall/CASAS parsing + curated Tier-2 fallback.
- `tests/test_cv.py`       — camera track: shared incident path, honest labels,
  no fake waveform (trace 404s).
- `tests/test_training.py` — deterministic judge-metrics payload.
- `tests/test_telegram.py` — dispatcher no-ops unconfigured, never raises.

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
  alerts/telegram.py   # stdlib-only Telegram dispatcher (env-var config, best-effort)
  model/training.py    # illustrative deterministic logistic regression (/training-stats)
  data/
    fixtures.py        # demo cast + incident state (real-trace rotation, camera override)
    loaders.py         # real SisFall/CASAS parsers + two-tier curated fallback (ADR 0008)
data/curated/          # committed Tier-2 real-data artifacts baked by scripts/curate.py
baselines.json         # sample per-resident self-baselines
```

## Status
All endpoints live on real scoring math: SisFall-calibrated acute detection
(96.2% detection / 29.8% ADL false-alarm, `data/metrics.json` via
`scripts/calibrate.py`), CASAS self-baselining chronic anomaly, real-trace
Simulate rotation with a committed curated fallback (ADR 0008), camera/pose
track, judge-metrics classifier (ADR 0009), and Telegram alert dispatch.
Test suite: 62 passing.
