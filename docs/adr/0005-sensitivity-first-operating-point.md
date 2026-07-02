---
type: adr
diataxis: reference
title: Sensitivity-first acute operating point (96.2% / 29.8%)
status: accepted
date: 2026-07-02
tags: [adr, scoring, calibration, acute]
---

# 0005. Sensitivity-first acute operating point (96.2% / 29.8%)

- Status: Accepted
- Date: 2026-07-02

## Context
Calibrating the acute fall thresholds on the full real SisFall dataset
(1,798 falls / 2,707 ADLs; grid sweep of 144 combos via
`scoring-service/scripts/calibrate.py --grid`, provenance in
`scoring-service/data/datasets.lock.json`) produced a frontier of operating
points, of which the two live candidates were:

| freefall | impact | dip | window | Detection | ADL false-alarm |
|---|---|---|---|---|---|
| 0.8 g | 2.3 g | 40 ms | 500 ms | **96.2%** | 29.8% |
| 0.8 g | 3.0 g | 40 ms | 700 ms | 92.3% | 23.4% |

The pre-calibration defaults (0.6 g / 2.7 g / 80 ms / 500 ms) detected only
51.8% — either candidate is a step change; the choice is where to sit on the
sensitivity/alarm-load trade-off.

## Decision
Adopt **freefall < 0.8 g, impact > 2.3 g, dip ≥ 40 ms, window ≤ 500 ms**
(96.2% detection, 29.8% ADL false-alarm), i.e. the sensitivity-first point,
because:

1. **Missed falls are the costliest error** ([[scoring-card]] §Ethical
   considerations) — a missed fall can be a long-lie death; a false alarm
   costs caseworker attention inside a triage queue that already carries
   confidence scores and a human in the loop. The system alerts a
   caseworker; it does not dispatch an ambulance.
2. **The false-alarm rate is measured on adversarial negatives.** SisFall's
   ADLs are deliberately fall-like and performed by young adults. The
   per-activity split (`scripts/fa_breakdown.py`) shows alarms concentrate
   ~100% in vigorous activities (jogging, jumping obstacles, running stairs,
   car ingress/egress); elderly-typical movements — slow walking, slow sits,
   lying down, stooping, stumbling-without-falling — trigger at 0–5%. The
   expected daily alarm load on a monitored elderly resident is therefore far
   below the 29.8% headline, while the 3.9-point sensitivity gap is real
   falls missed.

## Consequences
- `acute.py` constants carry the calibrated values with provenance in the
  comment; [[scoring-card]] §Metrics publishes the pre/post table and the
  per-activity defense of the headline false-alarm rate.
- The alarm-load argument is an **extrapolation across cohorts** (young-adult
  ADLs → elderly residents) — recorded as a limitation in [[scoring-card]];
  a genuinely elderly negative cohort would be needed to measure it.
- Revisiting the trade-off is a one-line constant change; the full frontier
  is reproducible from `calibrate.py --grid` at any time.
