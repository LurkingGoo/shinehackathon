"""CHRONIC track — CASAS routine anomaly (self-baselining, no population prior).

Each resident is scored against THEIR OWN baseline (mean/std per feature from
their history). This is why the method is Singapore-portable — no US routine is
imported. See docs/feature-spec.md §2 and docs/scoring-card.md.
"""
from __future__ import annotations

import numpy as np

Z_CAP = 4.0   # squash cap for the z-score → anomaly 0..1 (tunable)
EPS = 1e-6


def zscore(observed: float, mean: float, std: float) -> float:
    return (observed - mean) / max(std, EPS)


def anomaly(observed: float, mean: float, std: float) -> float:
    """Squashed one-sided anomaly in 0..1 (higher = further above baseline)."""
    z = zscore(observed, mean, std)
    return float(np.clip(z / Z_CAP, 0.0, 1.0))


def gap_ratio_anomaly(observed_gap: float, typical_gap: float) -> float:
    """For gap-type features where a distribution is thin (e.g. inactivity)."""
    if typical_gap <= 0:
        return 0.0
    return float(np.clip((observed_gap / typical_gap - 1.0), 0.0, 1.0))


def aggregate_risk(weighted: list[tuple[float, float]]) -> float:
    """weighted = [(weight, anomaly), ...] → risk in 0..1 (weighted mean)."""
    wsum = sum(w for w, _ in weighted)
    if wsum <= 0:
        return 0.0
    return float(np.clip(sum(w * a for w, a in weighted) / wsum, 0.0, 1.0))


def baseline_maturity(days_of_history: float, target_days: float = 14.0) -> float:
    """New residents score at honestly-low confidence (docs/feature-spec.md §2)."""
    return float(np.clip(days_of_history / target_days, 0.0, 1.0))
