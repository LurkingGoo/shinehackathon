"""Judge-metrics classifier tests — the ILLUSTRATIVE trained model.

This is deliberately separate from the shipped, calibrated detector (acute.py /
metrics.json, the 96.2% headline). The logistic regression here trains on four
SCALAR magnitude features and lands ~80% — and that gap is the point: it shows a
judge WHY we ship the ordered-signature detector (free-fall -> impact ->
stillness, 96%) instead of a naive magnitude classifier. Tests pin: it reads the
committed curated feature table, it converges to that honest ceiling, and its
report is DETERMINISTIC so /training-stats returns the same numbers every call.
"""
from __future__ import annotations

import numpy as np

from app.model import training


def test_load_feature_table_shape():
    X, y, names = training.load_feature_table()
    assert X.shape == (500, 4)
    assert y.shape == (500,)
    assert names == ["peakG", "freefallDepth", "impactEnergy", "stillnessS"]
    assert set(np.unique(y).tolist()) == {0, 1}


def test_logistic_converges_to_magnitude_ceiling():
    """Magnitudes alone can't fully separate falls from hard ADLs — the LR
    converges to an honest ~80% ceiling (stable, not an under-training artifact).
    This gap vs the 96% ordered detector is the judge-page narrative."""
    X, y, _ = training.load_feature_table()
    model = training.train_logistic(X, y)
    acc = training.accuracy(model, X, y)
    assert 0.75 <= acc <= 0.92, f"expected the magnitude ceiling, got {acc:.3f}"
    # convergence: 5x the iterations moves accuracy negligibly
    long = training.train_logistic(X, y, iters=training._ITERS * 5)
    assert abs(training.accuracy(long, X, y) - acc) < 0.02


def test_training_report_contract():
    rep = training.training_report()
    # keys the /training-stats endpoint + judge page rely on
    for k in ("featureNames", "coefficients", "confusionMatrix",
              "accuracy", "precision", "recall", "learningCurve", "counts"):
        assert k in rep, f"missing report key {k}"
    assert len(rep["featureNames"]) == len(rep["coefficients"]) == 4
    cm = rep["confusionMatrix"]
    assert set(cm) == {"tp", "fp", "fn", "tn"}
    assert sum(cm.values()) == rep["counts"]["test"]  # matrix covers the test split
    assert 0.0 <= rep["accuracy"] <= 1.0
    assert rep["accuracy"] >= 0.7  # honest magnitude ceiling, not inflated
    # learning curve: increasing train size, each point a real accuracy
    lc = rep["learningCurve"]
    assert len(lc) >= 3
    sizes = [p["trainSize"] for p in lc]
    assert sizes == sorted(sizes)
    assert all(0.0 <= p["accuracy"] <= 1.0 for p in lc)


def test_training_report_is_deterministic():
    """No RNG anywhere — /training-stats must be stable across calls/processes."""
    a = training.training_report()
    b = training.training_report()
    assert a == b


def test_convergence_history_is_real_gd():
    """The convergence chart must be RECORDED from the actual gradient-descent
    run — monotone-ish decreasing log-loss, sampled iterations, real test
    accuracy at each point. Nothing parametric, nothing smoothed."""
    rep = training.training_report()
    conv = rep["convergence"]
    assert len(conv) >= 10  # 4000 iters sampled every 100
    its = [p["iter"] for p in conv]
    assert its == sorted(its) and its[0] == 0
    losses = [p["loss"] for p in conv]
    # GD on a fixed batch: loss must strictly improve start->end and never
    # spike above its starting point
    assert losses[-1] < losses[0]
    assert max(losses) == losses[0]
    assert all(0.0 <= p["testAccuracy"] <= 1.0 for p in conv)


def test_split_sensitivity_three_real_refits():
    """Judge controls 60/40, 70/30, 80/20 are REAL re-fits on the deterministic
    interleaved order — each with its own held-out confusion matrix."""
    rep = training.training_report()
    splits = rep["splitSensitivity"]
    assert [s["split"] for s in splits] == ["60/40", "70/30", "80/20"]
    total = rep["counts"]["total"]
    for s in splits:
        cm = s["confusionMatrix"]
        assert set(cm) == {"tp", "fp", "fn", "tn"}
        assert sum(cm.values()) == s["counts"]["test"]
        assert s["counts"]["train"] + s["counts"]["test"] == total
        assert 0.7 <= s["accuracy"] <= 0.95  # every split stays at the honest ceiling
        assert 0.0 <= s["precision"] <= 1.0 and 0.0 <= s["recall"] <= 1.0
    # more training data should not tank accuracy: 80/20 within a few points of 60/40
    assert splits[2]["accuracy"] >= splits[0]["accuracy"] - 0.05


def test_extension_keys_deterministic_and_serialized():
    """New keys ride the same determinism + endpoint guarantees."""
    from fastapi.testclient import TestClient

    from app.main import app

    a = training.training_report()
    assert a == training.training_report()
    with TestClient(app) as client:
        body = client.get("/training-stats").json()
        assert "convergence" in body and "splitSensitivity" in body


def test_training_stats_endpoint():
    """GET /training-stats serves the report and stays JSON-stable."""
    from fastapi.testclient import TestClient

    from app.main import app

    with TestClient(app) as client:
        r = client.get("/training-stats")
        assert r.status_code == 200
        body = r.json()
        assert body["featureNames"] == ["peakG", "freefallDepth",
                                        "impactEnergy", "stillnessS"]
        assert set(body["confusionMatrix"]) == {"tp", "fp", "fn", "tn"}
        assert 0.7 <= body["accuracy"] <= 0.92  # honest magnitude ceiling
        assert client.get("/training-stats").json() == body  # stable
