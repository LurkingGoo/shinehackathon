"""RiskFeature construction + weight normalization.

The set of features IS the entire explanation of a score — nothing enters
`risk`/`rationale` that isn't a feature (docs/feature-spec.md §0).
"""
from __future__ import annotations

from app.models import RiskFeature


def normalize_weights(features: list[RiskFeature]) -> list[RiskFeature]:
    """Renormalize weights over the features actually present, so they sum to 1
    (features with weight 0 stay 0 — they are context, not drivers)."""
    total = sum(f.weight for f in features)
    if total <= 0:
        return features
    return [f.model_copy(update={"weight": round(f.weight / total, 4)}) for f in features]


def top_feature(features: list[RiskFeature]) -> RiskFeature | None:
    return max(features, key=lambda f: f.weight, default=None)
