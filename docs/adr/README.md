---
type: doc-index
diataxis: reference
title: Architecture Decision Records
status: active
last_updated: 2026-07-02
tags: [adr, decisions]
---

# Architecture Decision Records (ADRs)

Format: **MADR** (Markdown Any Decision Records). One file per decision,
`NNNN-kebab-title.md`, numbered in order. An accepted ADR is **immutable** — to
change a decision, add a new ADR that supersedes it (link both ways).
(Numbering starts at 0002; 0001 covered internal tooling and is not published.)

## Index

| # | Title | Status |
|---|-------|--------|
| [[0002-backend-stack-and-scoring]] | Python/FastAPI backend, SSE, heuristic self-baselining scoring | Accepted |
| [[0003-absolute-weight-risk-aggregation]] | Absolute-weight risk aggregation for cross-resident comparability | Accepted |
| [[0004-contract-parity-guard]] | Contract parity guarded by generated schema + types.ts field-diff | Accepted |
| [[0005-sensitivity-first-operating-point]] | Sensitivity-first acute operating point (96.2% detection / 29.8% ADL false-alarm) | Accepted |
| [[0006-hardware-showcase-b1-scope]] | Hardware showcase scope: B1 companion panel only | Accepted |
| [[0007-public-deploy-topology]] | Public deploy topology: Render Blueprint, two services, synthetic fallback | Accepted |

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
