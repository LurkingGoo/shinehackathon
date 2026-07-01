# Triage Dashboard (frontend)

Decide-layer eldercare triage dashboard for the JSGP challenge. One screen: a
ranked caseload a One Care caseworker scans at shift start. Acute (fall) events
preempt the top; chronic anomaly scores rank the calm caseload beneath;
rationale is deterministic. Theme: **Warm Human**.

**Read `CLAUDE.md` first** — it's the handoff brief (intent, the mock seam,
endpoints the backend must provide, done-vs-next, run commands).

## Quick start

```bash
npm install
npm run dev      # http://localhost:3000
```

> **One-time git fix (first thing in the terminal).** These files were authored
> in a sandbox whose filesystem mount corrupted the repo index and left a stale
> lock. Clear it natively before your first commit:
> ```bash
> # from the repo root: shinehackathon/
> rm -f .git/index.lock .git/index      # (Windows: del .git\index.lock .git\index)
> git reset                              # rebuild index from HEAD
> git add triage-dashboard mockups
> git commit -m "feat: Warm Human triage dashboard frontend + mock seam"
> ```
> The working-tree files are intact; only the git index needs rebuilding.

Then click a resident to drill down, and press **Simulate incident** to fire a
mock fall and watch the list re-rank.

## Project structure

```
triage-dashboard/
├── CLAUDE.md                     # handoff brief — start here
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
  backend build. (Provisional brief allowed a simpler path; this is it.)
- The app lives in a subfolder because the parent `shinehackathon/` folder is an
  Obsidian vault whose root `CLAUDE.md` is immutable. This app is self-contained.
