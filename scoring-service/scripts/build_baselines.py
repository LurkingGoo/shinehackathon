"""Precompute per-resident baselines.json from a CASAS event file.

    python scripts/build_baselines.py CASAS_FILE AREA_MAP.json [-o baselines.json]
    python scripts/build_baselines.py CASAS_FILE AREA_MAP.json --demo-day auto

AREA_MAP.json maps sensor ids to areas: {"M003": "kitchen", "D001": "front-door",
"M007": "bathroom"} — the per-home layout file (docs/scoring-card.md).

--demo-day additionally writes real_resident.json (baselines + that day's
observed values) next to the baselines output. This is the small artifact the
service reads at startup to back a demo resident with REAL data — the 61 MB
stream is parsed here, offline, not at serve time. "auto" picks the resident's
most kitchen-anomalous day (the day their routine genuinely broke).
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.baselines import (  # noqa: E402
    compute_baselines,
    observations_for_day,
    save_baselines,
)
from app.data.loaders import load_casas_events  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("casas_file", type=Path)
    ap.add_argument("area_map", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("baselines.json"))
    ap.add_argument("--demo-day", default=None,
                    help="'auto' or YYYY-MM-DD: also write real_resident.json")
    args = ap.parse_args()

    events = load_casas_events(args.casas_file)
    area_map = json.loads(args.area_map.read_text())
    b = compute_baselines(events, area_map)
    save_baselines(b, args.out)
    days = max((s["days"] for s in b.values()), default=0)
    print(f"{len(events)} events -> {len(b)} features over ~{days} days -> {args.out}")
    for feat, s in b.items():
        print(f"  {feat:22s} mean {s['mean']:>8.3f}  std {s['std']:>7.3f}  days {s['days']}")

    if args.demo_day:
        from collections import defaultdict
        buckets: dict[date, list] = defaultdict(list)
        for e in events:
            buckets[e.ts.date()].append(e)
        all_days = sorted(buckets)

        def day_obs(d: date) -> dict:
            # two-day slice: the day + next morning (night-trip attribution)
            from datetime import timedelta
            window = buckets.get(d, []) + buckets.get(d + timedelta(days=1), [])
            return observations_for_day(window, area_map, d)

        if args.demo_day == "auto":
            # the day the routine broke hardest, by kitchen-gap z-score
            kb = b.get("kitchen_gap_h")
            if not kb:
                print("no kitchen baseline — cannot auto-pick a demo day")
                return 1
            def kitchen_z(d: date) -> float:
                o = day_obs(d).get("kitchen_gap_h")
                return -1.0 if o is None else (o - kb["mean"]) / kb["std"]
            # skip first/last day (partial capture windows distort gaps)
            demo_day = max(all_days[1:-1], key=kitchen_z)
        else:
            demo_day = date.fromisoformat(args.demo_day)
        obs = day_obs(demo_day)
        artifact = {
            "source": str(args.casas_file),
            "demo_day": str(demo_day),
            "days_of_history": days,
            "baselines": b,
            "observations": obs,
        }
        out = args.out.parent / "real_resident.json"
        out.write_text(json.dumps(artifact, indent=2) + "\n")
        print(f"\ndemo day {demo_day}: {obs}")
        print(f"real-resident artifact -> {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
