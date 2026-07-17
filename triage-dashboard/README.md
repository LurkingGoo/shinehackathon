# Triage Dashboard (frontend)

Decide-layer eldercare triage dashboard for the JSGP challenge. One screen: a
ranked caseload a One Care caseworker scans at shift start. Acute (fall) events
preempt the top; chronic anomaly scores rank the calm caseload beneath;
rationale is deterministic. Theme: **Warm Human**.

## Live deployment

| Service | URL |
|---------|-----|
| **Dashboard (the app)** | https://triage-dashboard-zyur.onrender.com |
| Scoring service (API) | https://triage-scoring-service.onrender.com |

Open the **dashboard** URL — that is the app. The scoring service is the FastAPI
backend it proxies `/api/*` to (`/caseload`, `/health` return JSON; `/` is
intentionally 404). Both run on Render free tier and cold-start after ~15 min
idle (~50s first hit), so hit both once to warm them before presenting.

## Quick start

```bash
npm install
npm run dev      # http://localhost:3000
```

To see live data, run the scoring service alongside (see the repo root
`README.md` — or just use the root `start.bat` / `start.sh`, which launches
both). Without it, the app falls back to its built-in fixtures.

Then click a resident to drill down, and press **Simulate incident** to fire a
mock fall and watch the list re-rank.

## Project structure

```
triage-dashboard/
├── app/
│   ├── layout.tsx                # root layout + metadata
│   ├── globals.css               # WARM HUMAN design tokens (:root vars)
│   ├── page.tsx                  # renders <Dashboard/>
│   └── api/                      # MOCK backend (fixtures). Backend replaces this.
│       ├── caseload/route.ts         # GET /api/caseload      -> RankedCaseload
│       ├── residents/[id]/route.ts   # GET /api/residents/:id -> ResidentDetail
│       └── incidents/route.ts        # GET /api/incidents     -> IncidentEvent (mock-only)
├── components/
│   ├── Dashboard.tsx             # client orchestration; reads ONLY dataClient
│   ├── CaseloadCard.tsx          # one ranked row (avatar, rationale, ring, acute actions)
│   ├── DrilldownPanel.tsx        # features, recommended action, briefing
│   ├── RiskRing.tsx              # circular risk gauge
│   └── dashboard.module.css      # component styles (reads tokens)
└── lib/
    ├── types.ts                  # DATA CONTRACT (authoritative)
    ├── ui.ts                     # pure presentation helpers (color, initials)
    └── data/
        ├── client.ts             # ⭐ THE SEAM — sole data-access module
        └── fixtures.ts           # the only hard-coded data; backend replaces
```

## The one rule

Components import data **only** from `lib/data/client.ts`. Never from
`fixtures.ts`, never a raw `fetch`, never `/api` directly. That module is the
seam the backend replaces — keep it the single crossing point.

## Stack & decisions

- Next.js 14 (App Router), React 18, TypeScript.
- CSS Modules + CSS variables, **no Tailwind** — design tokens stay explicit and
  dependencies minimal, so the data seam is the only thing that moves during the
  backend build.
- The app is self-contained in this subfolder; the sibling `scoring-service/`
  is the FastAPI backend it proxies `/api/*` to.

## Backend & scoring documentation

- [`../scoring-service/README.md`](../scoring-service/README.md) — the FastAPI
  backend: scoring pipeline, endpoints, tests.
- [`../docs/adr/`](../docs/adr/) — Architecture Decision Records (MADR).
