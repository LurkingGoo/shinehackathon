"""CASAS loader + self-baselining tests over format-exact synthetic history.

14 deterministic days of a routine (kitchen 3x/day, door ~08:10, 2 nightly
bathroom trips) written in the real CASAS on-disk format; asserts the loader
parses it and compute_baselines recovers the routine's mean/spread.
"""
from __future__ import annotations

import pytest

from app.data import baselines
from app.data.loaders import load_casas_events

AREA_MAP = {"M003": "kitchen", "M007": "bathroom", "D001": "front-door"}
DAYS = 14


def _history_lines() -> list[str]:
    lines = []
    for day in range(1, DAYS + 1):
        d = f"2026-06-{day:02d}"
        jitter = (day % 3) * 15  # deterministic minute-level variation (0/15/30)
        lines += [
            f"{d} 02:00:00.000000 M007 ON",       # 2nd night trip (prev evening's)
            f"{d} 02:00:04.500000 M007 OFF",
            f"{d} 08:{10 + jitter // 10:02d}:00.000000 D001 OPEN",
            f"{d} 08:{15 + jitter // 10:02d}:12.250000 M003 ON",
            f"{d} 12:00:00 M003 ON",              # no fractional seconds — also legal
            f"{d} 18:{jitter:02d}:00.000000 M003 ON\tEating begin",  # label ignored
            f"{d} 23:30:00.000000 M007 ON",
        ]
    return lines


@pytest.fixture()
def history(tmp_path):
    f = tmp_path / "casas.txt"
    f.write_text("\n".join(_history_lines()) + "\n")
    return load_casas_events(f)


def test_loader_parses_and_sorts(history):
    assert len(history) == DAYS * 7
    assert all(a.ts <= b.ts for a, b in zip(history, history[1:]))
    assert history[0].sensor == "M007" and history[0].state == "ON"


def test_loader_rejects_short_line(tmp_path):
    f = tmp_path / "bad.txt"
    f.write_text("2026-06-01 08:00:00 M003\n")
    with pytest.raises(ValueError, match="expected"):
        load_casas_events(f)


def test_baselines_recover_the_routine(history):
    b = baselines.compute_baselines(history, AREA_MAP)
    # kitchen: gaps ~3.8h (morning->noon) and ~6h (noon->evening) -> max ~6h
    assert 5.5 <= b["kitchen_gap_h"]["mean"] <= 6.5
    assert b["kitchen_gap_h"]["days"] == DAYS
    # front door first opens ~08:10-08:16
    assert 8.1 <= b["door_first_open_h"]["mean"] <= 8.4
    # ~2 trips a night (boundary nights lose one — that's correct attribution)
    assert 1.5 <= b["night_bathroom_trips"]["mean"] <= 2.05
    # 5 motion-ONs per day (door OPEN is not motion; OFF not counted)
    assert 4.5 <= b["daily_activity"]["mean"] <= 5.1
    # spread floors hold (a metronomic routine can't zero the std)
    for feat, spec in b.items():
        assert spec["std"] >= baselines.MIN_STD[feat]


def test_baselines_roundtrip_json(history, tmp_path):
    b = baselines.compute_baselines(history, AREA_MAP)
    p = tmp_path / "baselines.json"
    baselines.save_baselines(b, p)
    assert baselines.load_baselines(p) == b


def test_thin_history_yields_no_baseline():
    assert baselines.compute_baselines([], AREA_MAP) == {}
