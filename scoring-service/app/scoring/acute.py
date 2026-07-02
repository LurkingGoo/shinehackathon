"""ACUTE track — SisFall fall detection (physics, not ML).

A fall is the ORDERED co-occurrence of a free-fall dip then an impact peak within
a short window — never a single threshold (that would fire on sitting hard).
Thresholds mirror docs/feature-spec.md §1 and are tunable on real SisFall traces;
the method is fixed. Input SMV is the signal-magnitude vector in g (rest ~= 1.0).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np

# Tunable thresholds — CALIBRATED on the full real SisFall dataset 2026-07-02
# (scripts/calibrate.py --grid, 1798 falls / 2707 ADLs): detection 96.2%,
# false-alarm 29.8% on SisFall's deliberately fall-like ADLs (see
# scripts/fa_breakdown.py for the per-activity split). The pre-calibration
# values (0.6g / 2.7g / 80ms / 500ms) detected only 51.8%.
FREEFALL_G = 0.8        # SMV below this = free fall
IMPACT_G = 2.3          # SMV above this = impact
FREEFALL_MIN_S = 0.04   # dip must be sustained at least this long
IMPACT_WINDOW_S = 0.5   # impact must follow the dip within this window


@dataclass
class FallResult:
    detected: bool
    peak_g: float
    freefall_ms: float
    post_impact_still_s: float


def smv(ax: np.ndarray, ay: np.ndarray, az: np.ndarray) -> np.ndarray:
    """Signal-magnitude vector in g from tri-axial accelerometer (already in g)."""
    return np.sqrt(np.asarray(ax) ** 2 + np.asarray(ay) ** 2 + np.asarray(az) ** 2)


def detect_fall(
    smv_signal: np.ndarray,
    fs: float,
    *,
    freefall_g: float = FREEFALL_G,
    impact_g: float = IMPACT_G,
    freefall_min_s: float = FREEFALL_MIN_S,
    impact_window_s: float = IMPACT_WINDOW_S,
) -> FallResult:
    """Detect a fall in a signal-magnitude window sampled at `fs` Hz.

    Thresholds default to the module constants; the calibration harness
    (scripts/calibrate.py) sweeps them without touching production values."""
    s = np.asarray(smv_signal, dtype=float)
    if s.size == 0:
        return FallResult(False, 0.0, 0.0, 0.0)

    dt = 1.0 / fs
    freefall_min = max(1, int(freefall_min_s * fs))
    impact_window = max(1, int(impact_window_s * fs))

    below = s < freefall_g
    # find a run of free-fall samples of at least freefall_min length
    run = 0
    for i, b in enumerate(below):
        run = run + 1 if b else 0
        if run >= freefall_min:
            dip_end = i
            seg = s[dip_end + 1: dip_end + 1 + impact_window]
            if seg.size and seg.max() > impact_g:
                impact_idx = dip_end + 1 + int(np.argmax(seg))
                peak = float(seg.max())
                # post-impact stillness: samples near rest after impact
                tail = s[impact_idx:]
                still = float(np.count_nonzero(np.abs(tail - 1.0) < 0.25) * dt)
                return FallResult(True, peak, run * dt * 1000.0, still)
    return FallResult(False, float(s.max()), 0.0, 0.0)


def acute_confidence(res: FallResult) -> float:
    """Confidence from margin past the impact threshold (docs/feature-spec.md)."""
    if not res.detected:
        return 0.0
    margin = (res.peak_g - IMPACT_G) / (6.0 - IMPACT_G)
    return float(np.clip(0.7 + 0.3 * margin, 0.0, 1.0))
