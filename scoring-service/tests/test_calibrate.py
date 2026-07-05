"""calibrate.py --json-out tests — metrics.json emission and cohort merging.

Uses the same format-exact SisFall fixture writers as test_loaders, arranged
into subject folders (SA01 young adult, SE01 elderly) so the --subjects prefix
filter and the merged-cohort design are both exercised on tiny data.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

from tests.test_loaders import _fall_profile, _walk_profile, _write_sisfall

_SPEC = importlib.util.spec_from_file_location(
    "calibrate", Path(__file__).resolve().parents[1] / "scripts" / "calibrate.py")
calibrate = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(calibrate)  # type: ignore[union-attr]


def _make_dataset(root: Path) -> Path:
    """Two subjects, each with one fall (F*) and one ADL (D*) trace."""
    for subj in ("SA01", "SE01"):
        d = root / subj
        d.mkdir(parents=True)
        _write_sisfall(d / f"F01_{subj}_R01.txt", _fall_profile())
        _write_sisfall(d / f"D01_{subj}_R01.txt", _walk_profile())
    return root


def test_json_out_writes_pooled_metrics(tmp_path):
    data = _make_dataset(tmp_path / "sisfall")
    out = tmp_path / "metrics.json"
    assert calibrate.main(["--dir", str(data), "--json-out", str(out)]) == 0

    doc = json.loads(out.read_text())
    c = doc["cohorts"]["pooled"]
    assert c["subjects"] is None
    assert c["counts"] == {"tp": 2, "fn": 0, "fp": 0, "tn": 2,
                           "falls": 2, "adls": 2}
    assert c["detection_rate"] == 1.0
    assert c["false_alarm_rate"] == 0.0
    op = c["operating_point"]
    assert set(op) == {"freefall_g", "impact_g", "freefall_min_s",
                       "impact_window_s"}
    assert all(v > 0 for v in op.values())


def test_json_out_merges_cohorts_across_runs(tmp_path):
    data = _make_dataset(tmp_path / "sisfall")
    out = tmp_path / "metrics.json"
    assert calibrate.main(["--dir", str(data), "--json-out", str(out)]) == 0
    assert calibrate.main(["--dir", str(data), "--subjects", "SE",
                           "--json-out", str(out)]) == 0

    doc = json.loads(out.read_text())
    assert set(doc["cohorts"]) == {"pooled", "SE"}  # pooled run survived merge
    se = doc["cohorts"]["SE"]
    assert se["subjects"] == "SE"
    assert se["counts"]["falls"] == 1 and se["counts"]["adls"] == 1


def test_json_out_rejects_grid(tmp_path, capsys):
    data = _make_dataset(tmp_path / "sisfall")
    try:
        calibrate.main(["--dir", str(data), "--grid",
                        "--json-out", str(tmp_path / "m.json")])
    except SystemExit as e:
        assert e.code == 2
    else:
        raise AssertionError("expected argparse error for --grid + --json-out")


def test_no_json_out_writes_nothing(tmp_path):
    data = _make_dataset(tmp_path / "sisfall")
    assert calibrate.main(["--dir", str(data)]) == 0
    assert not (calibrate.DEFAULT_JSON_OUT.parent / "nonexistent").exists()
    assert not list(tmp_path.glob("*.json"))
