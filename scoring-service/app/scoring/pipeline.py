"""Scoring pipeline — turns raw signals into a RiskScore + features.

This is the module that WIRES app/scoring/* into what the endpoints serve, so
the API returns COMPUTED numbers, not hardcoded ones. Inputs are raw signals
(accelerometer trace for acute; per-feature observations + baselines for
chronic); outputs are the contract objects. When app/data/loaders.py brings real
data, only the *inputs* change — this pipeline stays put.

Determinism: pure functions of the inputs; no randomness, no LLM
(docs/feature-spec.md §3).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.models import RiskFeature, Track
from app.scoring import acute as _acute
from app.scoring import chronic as _chronic
from app.scoring import features as _feat
from app.scoring import rationale as _rat


@dataclass
class ChronicFeatureInput:
    """One chronic feature's raw input. Either supply (observed, mean, std) to
    compute the anomaly via z-score, or supply `anomaly` directly for a
    qualitative signal not yet numerically featurized (docs/feature-spec.md §2)."""
    label: str
    value: str          # display string, e.g. "16h 04m"
    weight: float       # absolute pre-calibrated importance (0..1)
    baseline: str = ""  # display string, e.g. "typ. < 4h"
    observed: float | None = None
    mean: float | None = None
    std: float | None = None
    anomaly: float | None = None
    side: str = "high"  # directionality: "high" | "low" | "both" (feature-spec §2)


def _anomaly_of(fi: ChronicFeatureInput) -> float:
    if fi.anomaly is not None:
        return float(np.clip(fi.anomaly, 0.0, 1.0))
    if None not in (fi.observed, fi.mean, fi.std):
        return _chronic.anomaly(fi.observed, fi.mean, fi.std, fi.side)  # z-score path
    return 0.0


@dataclass
class ScoreParts:
    risk: float
    confidence: float
    features: list[RiskFeature]
    rationale: str
    recommended_action: str


def score_chronic(
    inputs: list[ChronicFeatureInput],
    *,
    days_of_history: float,
    data_quality: float = 1.0,
    sensor_health: float = 1.0,
) -> ScoreParts:
    features = [
        RiskFeature(label=fi.label, value=fi.value, weight=fi.weight, baseline=fi.baseline)
        for fi in inputs
    ]
    weighted = [(fi.weight, _anomaly_of(fi)) for fi in inputs]
    risk = _chronic.contribution_risk(weighted)
    # confidence is a SEPARATE axis: the weakest of data quality, sensor health,
    # and how mature this resident's own baseline is (docs/feature-spec.md §2).
    confidence = float(min(data_quality, sensor_health,
                           _chronic.baseline_maturity(days_of_history)))
    rationale = _rat.render_rationale("chronic", features)
    top = _feat.top_feature(features)
    action = _rat.recommend_action("chronic", top.label if top else "", risk)
    return ScoreParts(round(risk, 3), round(confidence, 3), features, rationale, action)


def score_acute(smv_signal: np.ndarray, fs: float) -> ScoreParts:
    res = _acute.detect_fall(smv_signal, fs)
    severity = float(np.clip((res.peak_g - _acute.IMPACT_G) / (6.0 - _acute.IMPACT_G),
                             0.0, 1.0))
    features = [
        RiskFeature(label="Peak impact", value=f"{res.peak_g:.1f} g",
                    weight=0.6, baseline="walking < 1.4 g"),
        RiskFeature(label="Post-impact stillness",
                    value=f"{res.post_impact_still_s:.0f} s", weight=0.3),
        RiskFeature(label="Orientation", value="Horizontal", weight=0.1),
    ]
    # A DETECTED fall is definitionally top-priority — it preempts the ranking.
    # Risk floors high and scales with impact severity; it is NOT a chronic
    # weighted sum. Undetected → a low residual so it can't outrank real concern.
    risk = float(np.clip(0.9 + 0.1 * severity, 0.0, 1.0)) if res.detected else 0.2 * severity
    confidence = _acute.acute_confidence(res)
    rationale = _rat.render_rationale("acute", features)
    action = _rat.recommend_action("acute", "Peak impact", risk)
    return ScoreParts(round(risk, 3), round(confidence, 3), features, rationale, action)
