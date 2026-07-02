"""SisFall loader tests — format-exact fixtures, loader -> SMV -> detection.

The fixture files are written in the real SisFall on-disk format (9 int fields,
';'-terminated lines) by inverting the ADXL345 conversion, so when the real
dataset lands the loader has already been exercised against the exact format.
"""
from __future__ import annotations

import numpy as np
import pytest
from fastapi.testclient import TestClient

from app.data import loaders
from app.main import app
from app.scoring.acute import FREEFALL_MIN_S, detect_fall, smv

FS = loaders.SISFALL_FS
G_PER_BIT = (2 * 16.0) / (2 ** 13)


def _g_to_raw(g: float) -> int:
    return int(round(g / G_PER_BIT))


def _write_sisfall(path, ax_g: np.ndarray) -> None:
    """Write a SisFall-format file with the given x-axis g profile (y=z=0,
    gyro/MMA columns zeroed — only the ADXL345 columns matter to the loader)."""
    lines = []
    for g in ax_g:
        raw = _g_to_raw(float(g))
        lines.append(f"{raw}, 0, 0, 0, 0, 0, 0, 0, 0;")
    path.write_text("\n".join(lines) + "\n")


def _fall_profile() -> np.ndarray:
    """rest 1s -> free-fall 0.2g for 0.3s -> 5g impact -> still 12s (all on x)."""
    return np.concatenate([
        np.ones(int(1.0 * FS)),
        np.full(int(0.3 * FS), 0.2),
        np.array([5.0, 4.4, 3.2]),
        np.ones(int(12.0 * FS)),
    ])


def _walk_profile() -> np.ndarray:
    """ADL: gait oscillation 0.8..1.5 g, no free-fall dip, no impact."""
    t = np.arange(int(10.0 * FS)) / FS
    return 1.15 + 0.35 * np.sin(2 * np.pi * 2.0 * t)


def test_load_sisfall_trace_converts_to_g(tmp_path):
    f = tmp_path / "F01_SA01_R01.txt"
    _write_sisfall(f, np.array([1.0, 0.2, 5.0]))
    trace = loaders.load_sisfall_trace(f)
    assert trace.shape == (3, 3)
    # quantized to ADXL345 resolution — within half a bit
    assert np.allclose(trace[:, 0], [1.0, 0.2, 5.0], atol=G_PER_BIT)
    assert np.allclose(trace[:, 1:], 0.0)


def test_load_rejects_malformed_line(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("1, 2, 3;\n")  # 3 fields, not 9
    with pytest.raises(ValueError, match="expected 9 fields"):
        loaders.load_sisfall_trace(f)


def test_fall_file_detects_end_to_end(tmp_path):
    f = tmp_path / "F05_SA03_R02.txt"
    _write_sisfall(f, _fall_profile())
    s = loaders.sisfall_smv(f)
    res = detect_fall(s, FS)
    assert res.detected
    assert res.peak_g == pytest.approx(5.0, abs=0.1)
    # detect_fall reports the dip length at the trigger point — the calibrated min
    assert res.freefall_ms >= FREEFALL_MIN_S * 1000


def test_adl_file_does_not_detect(tmp_path):
    f = tmp_path / "D07_SA03_R02.txt"
    _write_sisfall(f, _walk_profile())
    res = detect_fall(loaders.sisfall_smv(f), FS)
    assert not res.detected


def test_default_trace_resolution(tmp_path, monkeypatch):
    # env var wins
    f = tmp_path / "F01.txt"
    _write_sisfall(f, _fall_profile())
    monkeypatch.setenv("SISFALL_TRACE", str(f))
    assert loaders.default_sisfall_trace() == f
    # unset + no data dir -> None (synthetic fallback keeps the demo alive)
    monkeypatch.delenv("SISFALL_TRACE")
    monkeypatch.setattr(loaders, "SISFALL_DIR", tmp_path / "nope")
    assert loaders.default_sisfall_trace() is None


def test_simulate_injects_real_trace(tmp_path, monkeypatch):
    """POST /incidents/simulate with a real-format trace on disk: the event AND
    the subsequent drilldown both score from that trace (consistent numbers)."""
    from app.data import fixtures

    f = tmp_path / "F99_SA01_R01.txt"
    _write_sisfall(f, _fall_profile())
    monkeypatch.setenv("SISFALL_TRACE", str(f))
    try:
        with TestClient(app) as client:
            event = client.post("/incidents/simulate").json()
            assert event["entry"]["score"]["track"] == "acute"
            assert event["entry"]["score"]["risk"] >= 0.9
            assert "5.0 g" in event["detail"]["features"][0]["value"]
            detail = client.get(f"/residents/{event['entry']['id']}").json()
            assert detail["features"][0]["value"] == event["detail"]["features"][0]["value"]
    finally:
        fixtures.set_acute_trace(fixtures._ACUTE_SMV, fixtures.FS)
