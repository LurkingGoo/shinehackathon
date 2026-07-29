---
type: doc-index
diataxis: reference
title: Architecture Decision Records
status: active
last_updated: 2026-07-29
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
| [[0008-two-tier-curated-data]] | Two-tier curated data: committed real-data artifacts baked offline | Accepted |
| [[0009-illustrative-classifier]] | Illustrative classifier: /training-stats motivates the shipped detector | Accepted |
| [[0010-browser-pose-assets]] | In-browser MediaPipe pose for the camera track; assets fetched, not committed | Accepted |
| [[0011-enrolled-face-identity]] | Enrolled on-device face identity for camera incidents; amends the 0010 privacy claim | Accepted |
| [[0012-escalation-ack-zone]] | STILL DOWN escalation, "I am responding" ack, per-resident zone | Accepted |
| [[0013-runtime-resident-registry]] | Runtime resident registry: keyed-in locations + register-by-name | Accepted |
| [[0014-resident-deletion-cascade]] | Resident deletion: registrants only, full cross-system cascade | Accepted |
| [[0015-on-device-audio-alerts]] | On-device audio fall alerts (Web Speech + WebAudio chime) | Accepted |
| [[0016-dashboard-ack-and-respeak]] | Dashboard acknowledgement + re-speak-until-acknowledged loop | Accepted |
| [[0017-skeleton-replay-privacy-amendment]] | Skeleton replay: landmark trace upload + privacy claim amendment (supersedes 0010/0011 wording) | Accepted |

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
