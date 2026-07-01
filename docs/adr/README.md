---
type: doc-index
diataxis: reference
title: Architecture Decision Records
status: active
last_updated: 2026-07-01
tags: [adr, decisions]
---

# Architecture Decision Records (ADRs)

Format: **MADR** (Markdown Any Decision Records). One file per decision,
`NNNN-kebab-title.md`, numbered in order. An accepted ADR is **immutable** — to
change a decision, add a new ADR that supersedes it (link both ways). This
mirrors the append-only `decisions.md` but in the standard per-file form.

## Index

| # | Title | Status |
|---|-------|--------|
| [[0001-filesystem-first-vault]] | Filesystem-first vault + vault-search wiring | Accepted |
| [[0002-backend-stack-and-scoring]] | Python/FastAPI backend, SSE, heuristic self-baselining scoring | Accepted |
| [[0003-absolute-weight-risk-aggregation]] | Absolute-weight risk aggregation for cross-resident comparability | Accepted |
| [[0004-contract-parity-guard]] | Contract parity guarded by generated schema + types.ts field-diff | Accepted |

## Template

```markdown
# NNNN. <title>
- Status: Proposed | Accepted | Superseded by [[NNNN-...]]
- Date: YYYY-MM-DD
## Context
<forces at play; what makes this a decision>
## Decision
<what we chose, stated plainly>
## Consequences
<results, trade-offs, follow-ups — good and bad>
```
