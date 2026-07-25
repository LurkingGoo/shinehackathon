"""Illustrative logistic regression over the curated SisFall feature table.

WHY THIS EXISTS (and what it is NOT): the shipped fall detector is the
calibrated, explainable threshold in app/scoring/acute.py — its 96.2% / 29.8%
operating point (data/metrics.json) is the headline. This module trains a tiny
logistic regression on four SCALAR features (peak-g, free-fall depth, impact
energy, post-impact stillness) and lands ~80% — and that gap is the whole point.
Magnitudes alone can't tell a hard sit from a fall; only the TEMPORAL ordering
(free-fall -> impact -> stillness) can, which is exactly what the shipped
detector encodes. So /training-stats backs the judge-metrics page with real
learned numbers that MOTIVATE the ordered detector rather than competing with
it. It never scores a real resident.

No sklearn (not a dependency) — a hand-rolled numpy gradient-descent LR. Fully
DETERMINISTIC: zero-initialised weights, fixed iterations, a fixed interleaved
train/test split, no RNG. So /training-stats returns identical numbers on every
call and in every process.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from app.data.loaders import DATA_DIR

FEATURES_PATH = DATA_DIR / "curated" / "features.json"

# Deterministic training hyperparameters. Chosen so a zero-init GD run converges
# on the (separable) curated table; no early stopping, no RNG — reproducible.
_ITERS = 4000
_LR = 0.5
_TEST_FRACTION = 0.25
# learning-curve x-axis: fractions of the TRAIN split used to fit each point.
_CURVE_FRACTIONS = (0.1, 0.25, 0.5, 0.75, 1.0)


@dataclass
class LogisticModel:
    """Standardised-feature logistic regression: sigmoid(z @ w + b) where z is
    (x - mean) / std. Carries the scaler so it can score raw feature rows."""
    weights: np.ndarray  # (n_features,)
    bias: float
    mean: np.ndarray     # (n_features,) standardisation centre
    std: np.ndarray      # (n_features,) standardisation scale


def load_feature_table() -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Read the committed curated table -> (X (N,4), y (N,), feature_names).

    Real SisFall-derived features baked by scripts/curate.py; no raw dataset
    needed at runtime (same two-tier model as the fall rotation)."""
    data = json.loads(Path(FEATURES_PATH).read_text(encoding="utf-8"))
    X = np.asarray(data["X"], dtype=float)
    y = np.asarray(data["y"], dtype=float)
    return X, y, list(data["featureNames"])


def _sigmoid(z: np.ndarray) -> np.ndarray:
    # clip keeps exp from overflowing on confident separable margins
    return 1.0 / (1.0 + np.exp(-np.clip(z, -60.0, 60.0)))


def train_logistic(X: np.ndarray, y: np.ndarray,
                   iters: int = _ITERS, lr: float = _LR) -> LogisticModel:
    """Fit a standardised logistic regression by batch gradient descent.

    Deterministic: standardise on this X, zero-init, fixed iters. Degenerate
    (zero-variance) columns get std=1 so they simply contribute nothing."""
    mean = X.mean(axis=0)
    std = X.std(axis=0)
    std = np.where(std < 1e-9, 1.0, std)
    Z = (X - mean) / std

    n, d = Z.shape
    w = np.zeros(d)
    b = 0.0
    for _ in range(iters):
        p = _sigmoid(Z @ w + b)
        err = p - y
        w -= lr * (Z.T @ err) / n
        b -= lr * err.mean()
    return LogisticModel(weights=w, bias=float(b), mean=mean, std=std)


def predict_proba(model: LogisticModel, X: np.ndarray) -> np.ndarray:
    Z = (X - model.mean) / model.std
    return _sigmoid(Z @ model.weights + model.bias)


def predict(model: LogisticModel, X: np.ndarray) -> np.ndarray:
    return (predict_proba(model, X) >= 0.5).astype(int)


def accuracy(model: LogisticModel, X: np.ndarray, y: np.ndarray) -> float:
    return float((predict(model, X) == y.astype(int)).mean())


def _interleaved_order(y: np.ndarray) -> np.ndarray:
    """A deterministic, class-balanced index order (no RNG).

    The curated table is falls-then-ADLs, so a naive prefix is all one class.
    Interleaving the two class-index streams makes every prefix balanced — which
    is what the learning curve and the train/test split both need."""
    pos = np.where(y == 1)[0]
    neg = np.where(y == 0)[0]
    order: list[int] = []
    for i in range(max(pos.size, neg.size)):
        if i < pos.size:
            order.append(int(pos[i]))
        if i < neg.size:
            order.append(int(neg[i]))
    return np.asarray(order, dtype=int)


def _confusion(y_true: np.ndarray, y_pred: np.ndarray) -> dict[str, int]:
    yt, yp = y_true.astype(int), y_pred.astype(int)
    return {
        "tp": int(np.sum((yt == 1) & (yp == 1))),
        "fp": int(np.sum((yt == 0) & (yp == 1))),
        "fn": int(np.sum((yt == 1) & (yp == 0))),
        "tn": int(np.sum((yt == 0) & (yp == 0))),
    }


@lru_cache(maxsize=1)
def training_report() -> dict:
    """Assemble the deterministic judge-metrics payload for /training-stats.

    A fixed interleaved train/test split; the confusion matrix + accuracy are on
    the held-out TEST split (honest, not train-set optimism); the learning curve
    fits growing prefixes of the train split and reports test accuracy at each.
    Cached: identical bytes on every call."""
    X, y, names = load_feature_table()
    order = _interleaved_order(y)
    Xo, yo = X[order], y[order]

    n = len(yo)
    n_test = int(round(n * _TEST_FRACTION))
    X_test, y_test = Xo[:n_test], yo[:n_test]
    X_train, y_train = Xo[n_test:], yo[n_test:]

    model = training_model = train_logistic(X_train, y_train)
    y_pred = predict(model, X_test)
    cm = _confusion(y_test, y_pred)

    tp, fp, fn = cm["tp"], cm["fp"], cm["fn"]
    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0

    curve = []
    for frac in _CURVE_FRACTIONS:
        k = max(2, int(round(len(y_train) * frac)))
        m = train_logistic(X_train[:k], y_train[:k])
        curve.append({"trainSize": k, "accuracy": round(accuracy(m, X_test, y_test), 4)})

    return {
        "$note": "ILLUSTRATIVE logistic regression on curated SisFall MAGNITUDE "
                 "features — its ~80% ceiling motivates the ordered-signature "
                 "detector we ship (96.2%, see metrics.json). Not a live scorer.",
        "featureNames": names,
        "coefficients": [round(float(c), 4) for c in training_model.weights],
        "intercept": round(float(training_model.bias), 4),
        "confusionMatrix": cm,
        "accuracy": round(accuracy(model, X_test, y_test), 4),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "learningCurve": curve,
        "counts": {"total": n, "train": len(y_train), "test": n_test},
    }
