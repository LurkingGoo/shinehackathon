---
type: adr
diataxis: reference
title: Absolute-weight risk aggregation (cross-resident comparability)
status: accepted
date: 2026-07-01
tags: [adr, scoring, ranking]
---

# 0003. Absolute-weight risk aggregation (cross-resident comparability)

- Status: Accepted
- Date: 2026-07-01

## Context
Wiring the scoring pipeline into the served caseload
([[0002-backend-stack-and-scoring]]) forced a concrete choice for how per-feature
anomalies combine into a resident's `risk`. The obvious first form — a weighted
**mean** `Σ(wᵢ·aᵢ)/Σwᵢ` — renormalizes weights per resident. That breaks the
ranking: a resident with a single dominant feature (e.g. Lim, whose one big
signal is "6 nocturnal trips") has that feature renormalized to ~100 % of their
score, inflating them above a resident with a genuinely more urgent but
differently-weighted profile (e.g. Rajoo's 16 h kitchen inactivity). Risk must be
**comparable across residents** because the whole product is a ranking.

## Decision
Aggregate chronic risk as the **sum of absolute weighted contributions**:
`risk = clamp(Σ(wᵢ·aᵢ), 0, 1)`, where weights are pre-calibrated importances that
sum to ≤ 1 (implemented as `chronic.contribution_risk`). The weighted-mean form
(`chronic.aggregate_risk`) is retained for relative-weight uses but is **not** the
caseload ranking function. Acute risk is separate: a detected fall floors high
(`0.9 + 0.1·severity`) because it preempts the ranking by definition
([[feature-spec]] §1).

## Consequences
- Cross-resident ranking is stable and matches clinical intent (Rajoo > Wong >
  Lim); "normal" residents (all-zero weights) score exactly 0.
- Weights are now load-bearing calibration, not just drill-down bar widths — they
  must sum to ≤ 1 per resident and are tuned per feature ([[feature-spec]] §2).
- Served scores are **computed**, so their values differ from the old hand-set
  demo numbers — expected and honest ([[scoring-card]]).
- One-sided anomalies only: "less activity than usual" (e.g. 0 bathroom visits)
  is not captured by the above-baseline z-score and is currently supplied as a
  direct `anomaly` pending proper two-sided featurization (tracked in
  [[feature-spec]] §2 / §4).
