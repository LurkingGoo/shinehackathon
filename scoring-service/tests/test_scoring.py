"""Scoring-logic tests — the heuristics behind the two tracks.

Acute: a synthetic fall trace fires, a hard-sit ADL does not (the ordered
free-fall→impact requirement is what rejects false positives). Chronic: the
self-baselining anomaly behaves monotonically.
"""
from __future__ import annotations

import numpy as np

from app.scoring import acute, chronic


FS = 200.0  # Hz, SisFall-like


def _fall_trace() -> np.ndarray:
    """~1g rest → free-fall dip (~0.2g) → impact spike (~3.2g) → still."""
    rest = np.ones(int(1.0 * FS))
    freefall = np.full(int(0.3 * FS), 0.2)      # sustained dip
    impact = np.array([3.2, 3.0, 2.9])          # sharp peak
    still = np.ones(int(2.0 * FS))
    return np.concatenate([rest, freefall, impact, still])


def _hard_sit_trace() -> np.ndarray:
    """A firm sit: a mild bump to ~1.8g but NO preceding free-fall dip."""
    rest = np.ones(int(1.0 * FS))
    bump = np.array([1.8, 1.7, 1.5])
    settle = np.ones(int(1.0 * FS))
    return np.concatenate([rest, bump, settle])


def test_fall_is_detected():
    res = acute.detect_fall(_fall_trace(), FS)
    assert res.detected
    assert res.peak_g > acute.IMPACT_G
    assert res.freefall_ms >= acute.FREEFALL_MIN_S * 1000
    assert 0.7 <= acute.acute_confidence(res) <= 1.0


def test_hard_sit_is_not_a_fall():
    res = acute.detect_fall(_hard_sit_trace(), FS)
    assert not res.detected
    assert acute.acute_confidence(res) == 0.0


def test_smv_is_rotation_invariant_magnitude():
    # 1g on a single axis at rest → magnitude 1g regardless of which axis.
    z = acute.smv(np.zeros(3), np.zeros(3), np.ones(3))
    x = acute.smv(np.ones(3), np.zeros(3), np.zeros(3))
    assert np.allclose(z, 1.0) and np.allclose(x, 1.0)


def test_chronic_anomaly_monotonic_and_bounded():
    baseline_mean, baseline_std = 4.0, 1.0  # typical kitchen gap hours
    on_time = chronic.anomaly(4.0, baseline_mean, baseline_std)
    late = chronic.anomaly(16.0, baseline_mean, baseline_std)
    assert 0.0 <= on_time < late <= 1.0
    assert late == 1.0  # 12σ over → capped at 1


def test_aggregate_risk_is_weighted_mean():
    assert chronic.aggregate_risk([(0.5, 1.0), (0.5, 0.0)]) == 0.5
    assert chronic.aggregate_risk([]) == 0.0


def test_baseline_maturity_penalises_new_residents():
    assert chronic.baseline_maturity(2) < chronic.baseline_maturity(14) == 1.0
