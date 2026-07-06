---
type: adr
diataxis: reference
title: Public deploy topology, Render Blueprint two-service with synthetic fallback
status: accepted
date: 2026-07-06
tags: [adr, deploy, render, vercel, hosting, demo]
---

# 0007. Public deploy topology: Render Blueprint, two services, synthetic fallback

- Status: Accepted (prepared; not yet executed)
- Date: 2026-07-06

## Context
The operator wants the whole project publicly accessible for easy judge access,
not just the static brief. The app is two processes behind one seam: a Next.js
dashboard whose `/api/*` rewrites proxy a FastAPI scoring service
(`SCORING_SERVICE_URL`, per [[docs/adr/0004-contract-parity-guard]] the contract
is stable across the seam). There is no database and no secret. The licensed
datasets (SisFall, CASAS) are git-ignored; `loaders.py` falls back to a synthetic
fall/near-miss rotation when they are absent, so the live demo runs without them.

The build environment has no git remote, no deploy CLIs (`gh`, `vercel`,
`render`, `fly`, `docker` all absent), and no cloud credentials. Account creation
and credential entry are outside what the assistant may perform, so the deploy is
prepared to be turnkey and executed by the operator.

## Decision
Ship a single **Render Blueprint** (`render.yaml`) that brings up both services
from one repo connect and auto-wires `SCORING_SERVICE_URL` from the scoring
service's host. `next.config.mjs` upgrades a scheme-less host to `https://` so the
Blueprint's `fromService property:host` value resolves to a valid rewrite target.
The deployed demo runs on the **synthetic fallback**; the licensed data stays out
of the repo. **Vercel (frontend) + Render (backend)** is documented in `DEPLOY.md`
as the alternative if a faster Next.js host is wanted.

Rationale:

1. **One connect, both services.** The Blueprint is the lowest-friction path for a
   two-process app; the operator's steps reduce to push-repo, connect-blueprint,
   open-URL.
2. **No secrets, no data to move.** Synthetic fallback keeps licensed payloads out
   of a public host and sidesteps the SisFall mirror's reliability. Headline numbers
   come from the committed `metrics.json` and are unaffected.
3. **The account steps are the operator's by rule.** The assistant cannot create
   accounts or enter credentials, so the deliverable is turnkey config plus a runbook.

## Consequences
- New root files: `render.yaml` (blueprint), `DEPLOY.md` (runbook); one-line behavior
  change in `next.config.mjs` (host→https normalization, full URLs pass through).
- Render free web services cold-start after ~15 min idle (~50s first hit); the runbook
  says to warm both URLs before presenting.
- SSE re-rank streams through the proxied path; if a host buffers it, the fallback is
  to point `EventSource` at the backend directly and enable CORS (documented).
- To show real recorded traces live, a backend build step must run
  `scripts/fetch_datasets.py`; weigh the licence terms and mirror reliability first.
- Not executed this session: no remote/CLIs/creds in-environment. Revert is deleting
  two files and one 2-line config change.
