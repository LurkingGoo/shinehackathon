"""Derive the sensor->area map for a CASAS home from its activity annotations.

    python scripts/derive_area_map.py data/casas/aruba.txt -o data/casas/area_map.json

At a real deployment the installer writes the per-home layout file by hand
(docs/scoring-card.md). For a public CASAS home we don't have the installer, so
we reconstruct it from the dataset's own activity annotations: sensors that fire
predominantly during Meal_Preparation are kitchen; during Bed_to_Toilet are the
bathroom path; the door opened on Enter_Home/Leave_Home is the front door.

NOTE (scoring-card honesty): labels are used ONLY to derive this layout map —
a deployment artifact — never to train or score. Scoring stays label-free.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

ACTIVITY_TO_AREA = {
    "Meal_Preparation": "kitchen",
    "Bed_to_Toilet": "bathroom",
    "Enter_Home": "front-door",
    "Leave_Home": "front-door",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("casas_file", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("area_map.json"))
    ap.add_argument("--top", type=int, default=3, help="sensors kept per area")
    args = ap.parse_args()

    fires: dict[str, Counter] = defaultdict(Counter)  # area -> sensor counts
    active: str | None = None
    for line in args.casas_file.read_text().splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        sensor, state = parts[2], parts[3]
        if len(parts) >= 6 and parts[5] in ("begin", "end"):
            active = parts[4] if parts[5] == "begin" else None
        area = ACTIVITY_TO_AREA.get(active or "")
        if not area:
            continue
        if area == "front-door" and sensor.startswith("D"):
            fires[area][sensor] += 1
        elif sensor.startswith("M") and state.upper() == "ON":
            fires[area][sensor] += 1

    area_map: dict[str, str] = {}
    for area, counter in fires.items():
        keep = 1 if area == "front-door" else args.top
        for sensor, n in counter.most_common(keep):
            area_map[sensor] = area
            print(f"  {sensor} -> {area}  ({n} fires during "
                  f"{[a for a, ar in ACTIVITY_TO_AREA.items() if ar == area]})")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(area_map, indent=2, sort_keys=True) + "\n")
    print(f"\n{len(area_map)} sensors mapped -> {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
