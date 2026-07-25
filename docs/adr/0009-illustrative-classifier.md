---
type: adr
diataxis: reference
title: Illustrative classifier, /training-stats motivates the shipped detector
status: accepted
date: 2026-07-25
tags: [adr, training, judge-metrics, honesty]
---

# 0009. Illustrative classifier: `/training-stats` motivates, never competes with, the shipped detector

- Status: Accepted
- Date: 2026-07-25

## Context
The shipped fall detector is a calibrated, explainable temporal-signature
threshold (free-fall → impact → stillness) at 96.2% detection / 29.8% ADL
false-alarm on real SisFall ([[0005-sensitivity-first-operating-point]]). Judges
reasonably ask "why not ML?", and the pitch needed a transparent
model-training surface — but a trained model that *competed* with the shipped
detector would either beat it (undermining the shipped design) or lose opaquely
(proving nothing). The honesty posture (2026-07-03 decision: own the
unfavourable number first) demands the answer be shown, not asserted.

## Decision
Ship a deliberately *illustrative* classifier behind `GET /training-stats`:

- A hand-rolled numpy logistic regression (`app/model/training.py`, no sklearn
  dependency) over the four SCALAR magnitude features in the curated table
  ([[0008-two-tier-curated-data]]): peak-g, free-fall depth, impact energy,
  post-impact stillness.
- Fully deterministic — zero-init, fixed iterations, fixed interleaved
  class-balanced train/test split, no RNG — so the payload is byte-identical
  on every call and across processes.
- Honest metrics only: confusion matrix, accuracy, precision, recall on the
  held-out test split; a learning curve over growing train prefixes.
- Its ~80% ceiling IS the point: magnitudes alone cannot separate a hard sit
  from a fall; only the temporal ORDERING can — which is exactly what the
  shipped detector encodes. The payload carries a `$note` stating it is
  illustrative and never scores a resident.

## Consequences
- The judge-metrics page shows real learned numbers that *motivate* the shipped
  detector's design instead of competing with it; the ~16-point gap to 96.2%
  is the narrative.
- The classifier is outside the scoring path (feature-spec §3 determinism
  guarantee untouched); it can never rank or score a resident.
- Risk of a reader mistaking it for the production model is mitigated by the
  `$note` in the payload and matching labels on the frontend page.
- The curated feature table is the classifier's only input; rebaking Tier-2
  data (ADR 0008) can shift its exact numbers — acceptable, since the payload
  is regenerated deterministically from whatever table is committed.
