"""Per-resident routine baselines from CASAS events — the self-baselining core.

From a resident's OWN trailing history (target >= 14 days), compute per feature
a typical value + spread (docs/feature-spec.md §2). No population prior, which
is what makes the method Singapore-portable. Output persists to baselines.json;
the live pipeline scores today's observations against these via z-score.

Features (aligned to feature-spec §2):
  kitchen_gap_h        max gap (hours) between kitchen motion events, per day
  door_first_open_h    hour of the day's first front-door event
  night_bathroom_trips bathroom motion-ON count in the sleep window, per night
  daily_activity       all motion-ON events, per day
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

import numpy as np

from app.data.loaders import CasasEvent

SLEEP_START_H = 22  # sleep window: 22:00 -> 07:00 (tunable per home)
SLEEP_END_H = 7
MIN_STD = {  # floor the spread so one metronomic week can't make z explode
    "kitchen_gap_h": 0.25,
    "door_first_open_h": 0.25,
    "night_bathroom_trips": 0.5,
    "daily_activity": 5.0,
}


def _stats(values: list[float], feature: str) -> dict | None:
    if len(values) < 2:
        return None
    arr = np.asarray(values, dtype=float)
    return {
        "mean": round(float(arr.mean()), 3),
        "std": round(max(float(arr.std()), MIN_STD[feature]), 3),
        "days": len(values),
    }


def compute_baselines(events: list[CasasEvent], area_map: dict[str, str]) -> dict:
    """events + sensor->area map -> {feature: {mean, std, days}}.

    area_map maps sensor ids to areas: kitchen, bathroom, front-door, ... —
    the per-home layout file the scoring-card requires at deployment.
    """
    kitchen_by_day: dict[date, list] = defaultdict(list)
    door_first: dict[date, float] = {}
    night_trips: dict[date, int] = defaultdict(int)
    activity: dict[date, int] = defaultdict(int)

    for e in events:
        area = area_map.get(e.sensor)
        d, hour = e.ts.date(), e.ts.hour + e.ts.minute / 60.0
        is_motion_on = e.sensor.startswith("M") and e.state.upper() == "ON"
        if is_motion_on:
            activity[d] += 1
        if area == "kitchen" and is_motion_on:
            kitchen_by_day[d].append(e.ts)
        if area == "front-door" and d not in door_first:
            door_first[d] = hour
        if area == "bathroom" and is_motion_on:
            # a night belongs to the evening it started
            if e.ts.hour >= SLEEP_START_H:
                night_trips[d] += 1
            elif e.ts.hour < SLEEP_END_H:
                night_trips[d - timedelta(days=1)] += 1

    kitchen_gaps = [
        max((b - a).total_seconds() / 3600.0 for a, b in zip(ts, ts[1:]))
        for ts in kitchen_by_day.values() if len(ts) >= 2
    ]
    features = {
        "kitchen_gap_h": _stats(kitchen_gaps, "kitchen_gap_h"),
        "door_first_open_h": _stats(list(door_first.values()), "door_first_open_h"),
        "night_bathroom_trips": _stats([float(v) for v in night_trips.values()],
                                       "night_bathroom_trips"),
        "daily_activity": _stats([float(v) for v in activity.values()],
                                 "daily_activity"),
    }
    return {k: v for k, v in features.items() if v is not None}


def save_baselines(baselines: dict[str, dict], path: str | Path) -> None:
    Path(path).write_text(json.dumps(baselines, indent=2) + "\n")


def load_baselines(path: str | Path) -> dict[str, dict]:
    return json.loads(Path(path).read_text())
