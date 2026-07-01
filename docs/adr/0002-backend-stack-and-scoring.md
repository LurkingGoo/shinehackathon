---
type: adr
diataxis: reference
title: Python/FastAPI backend, SSE, heuristic self-baselining scoring
status: accepted
date: 2026-07-01
tags: [adr, backend, scoring, architecture]
---

# 0002. Python/FastAPI backend, SSE, heuristic self-baselining scoring

- Status: Accepted
- Date: 2026-07-01

## Context
The frontend (`triage-dashboard/`) is built and freezes the data contract
(`lib/types.ts`) and the `lib/data/client.ts` seam. The contract **requires**
every score to decompose into weighted `RiskFeature[]` — explainability is
mandatory. Operator inputs: the team is Python; SisFall + CASAS datasets are in
hand; desired scoring depth is **credible heuristics** (not trained models). The
problem is framed for Singapore (One Care / JSGP / HDB), but no Singapore sensor
dataset is public.

## Decision
- **Python 3.11 + FastAPI** scoring service in a sibling `scoring-service/`;
  Next.js `/api/*` **proxies** it (same-origin, no CORS). **SSE** for the live
  channel.
- **No model training.** Credible heuristics: acute = SisFall accel-magnitude
  fall detection (physics); chronic = **self-baselining** CASAS anomaly (each
  resident scored against their own routine).
- **No database** for the demo (baselines → JSON, replayer in-memory). Claude
  smooths the `briefing` string only, behind a flag.
- Design detail: [[backend-architecture]]; features: [[feature-spec]]; scoring
  card + datasets + limits: [[scoring-card]].

## Consequences
- Explainability satisfied for free (features drive rationale); LLM never invents
  cause.
- **Singapore-portable** with no geographic prior: physics + self-baseline mean a
  real deployment self-calibrates per resident in days; public datasets are
  proxies for method validation.
- Scope is bounded (no training, no DB, SSE not WebSocket, Twilio/Supabase
  deferred). Two lean fallbacks on record if time runs short: precompute chronic
  offline; make the service SSE-only.
- **Biggest risk is the replayer/streaming plumbing**, not the scoring — so
  de-risk the SSE→re-rank path first.
- Thresholds ship uncalibrated; must be tuned on real traces before any accuracy
  claim (see [[scoring-card]] Metrics).
