# Morning Triage — eldercare triage dashboard

A single-screen web app a caseworker opens at shift start: a ranked caseload
where **acute** events (a detected fall) preempt the top and **chronic** anomaly
scores (e.g. "no kitchen activity in 16h") rank the calm caseload beneath.
Every score comes with a deterministic plain-English rationale derived from the
actual sensor features — no invented "why".

| Piece | Stack | Folder |
|-------|-------|--------|
| Dashboard (frontend) | Next.js 14 · React 18 · TypeScript | [`triage-dashboard/`](triage-dashboard/) |
| Scoring service (backend) | Python 3.11 · FastAPI · SSE | [`scoring-service/`](scoring-service/) |

**Live demo:** https://triage-dashboard-zyur.onrender.com
(free tier — cold-starts ~50s after idle; open it once to warm it up)

## Run locally

Prerequisites: **Python 3.11+** and **Node.js 18+** on PATH.

**Windows — one click:** double-click **`start.bat`**. It starts both services
in their own windows and opens http://localhost:3000.

**macOS / Linux / Git Bash:**

```bash
./start.sh
```

**Manually**, in two terminals:

```bash
# terminal 1 — scoring service on :8000
cd scoring-service
pip install -r requirements.txt
python -m uvicorn app.main:app --port 8000

# terminal 2 — dashboard on :3000 (proxies /api/* to :8000)
cd triage-dashboard
npm install
npm run dev
```

Open http://localhost:3000, click a resident to drill down, and press
**Simulate incident** to fire a fall and watch the list re-rank live.

**Camera fall detection:** open http://localhost:3000/watch, allow the
webcam, and fall (fast, then hold still ~3 s) — the incident fires into the
same pipeline. Pose estimation runs entirely in the browser; no video is
uploaded (a confirmed fall sends a stick-figure joint trace — coordinates,
never pixels — which the dashboard drilldown replays).
`npm run fetch-pose-assets` (run automatically by the start
scripts) vendors the model for offline use; otherwise it loads from the CDN.

No database, no secrets, no `.env` needed. The demo runs on a synthetic
fall/near-miss fallback when the licensed datasets are absent (they are
git-ignored), so everything works straight from a fresh clone.

## Deploy (Render — one click-ish)

[`render.yaml`](render.yaml) is a Render Blueprint that deploys **both**
services from one repo connect and wires them together:

1. Push this repo to GitHub.
2. Render dashboard → **New → Blueprint** → pick the repo → **Apply**.
3. Open the `triage-dashboard` URL Render gives you. Done.

Details, the Vercel alternative, and SSE notes: [`DEPLOY.md`](DEPLOY.md).

## Repo layout

```
├── start.bat / start.sh     # one-command local run (both services)
├── render.yaml              # Render Blueprint — deploys both services
├── DEPLOY.md                # full deploy guide
├── scoring-service/         # FastAPI backend: scoring pipeline, replayer, tests
├── triage-dashboard/        # Next.js frontend: ranked caseload UI
├── mockups/                 # static design mockups (pre-build)
└── docs/
    ├── adr/                 # Architecture Decision Records (MADR)
    └── slides/              # pitch deck source (Marp) + assets
```

## Tests

```bash
cd scoring-service && python -m pytest        # backend (143 tests, offline by construction)
cd triage-dashboard && npm run typecheck      # frontend types
cd triage-dashboard && npm test               # fall-heuristic unit tests (vitest)
```
