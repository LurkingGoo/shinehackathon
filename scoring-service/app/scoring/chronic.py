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


def anomaly(observed: float, mean: float, std: float, side: str = "high") -> float:
    """Squashed anomaly in 0..1 with per-feature directionality
    (docs/feature-spec.md §2):
      side="high" — only above baseline is concerning (e.g. kitchen gap)
      side="low"  — only below baseline is concerning (e.g. activity volume)
      side="both" — any departure from routine is signal (e.g. night trips:
                    more suggests UTI/decline, fewer corroborates inactivity)
    """
    z = zscore(observed, mean, std)
    if side == "low":
        z = -z
    elif side == "both":
        z = abs(z)
    return float(np.clip(z / Z_CAP, 0.0, 1.0))


def gap_ratio_anomaly(observed_gap: float, typical_gap: float) -> float:
    """For gap-type features where a distribution is thin (e.g. inactivity)."""
    if typical_gap <= 0:
        return 0.0
    return float(np.clip((observed_gap / typical_gap - 1.0), 0.0, 1.0))


def aggregate_risk(weighted: list[tuple[float, float]]) -> float:
    """weighted = [(weight, anomaly), ...] → risk in 0..1 (weighted MEAN).
    Use when weights are relative importances that should renormalize."""
    wsum = sum(w for w, _ in weighted)
    if wsum <= 0:
        return 0.0
    return float(np.clip(sum(w * a for w, a in weighted) / wsum, 0.0, 1.0))


def contribution_risk(weighted: list[tuple[float, float]]) -> float:
    """weighted = [(weight, anomaly), ...] → risk in 0..1 as the SUM of absolute
    contributions. Weights are pre-calibrated importances that sum to <= 1, so a
    resident with one dominant feature does NOT get that feature renormalized to
    100% of their score — this keeps risk comparable ACROSS residents (the
    ranking axis). This is the aggregation the caseload uses."""
    return float(np.clip(sum(w * a for w, a in weighted), 0.0, 1.0))


def baseline_maturity(days_of_history: float, target_days: float = 14.0) -> float:
    """New residents score at honestly-low confidence (docs/feature-spec.md §2)."""
    return float(np.clip(days_of_history / target_days, 0.0, 1.0))
