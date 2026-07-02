"""Precompute per-resident baselines.json from a CASAS event file.

    python scripts/build_baselines.py CASAS_FILE AREA_MAP.json [-o baselines.json]

AREA_MAP.json maps sensor ids to areas: {"M003": "kitchen", "D001": "front-door",
"M007": "bathroom"} — the per-home layout file (docs/scoring-card.md).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.baselines import compute_baselines, save_baselines  # noqa: E402
from app.data.loaders import load_casas_events  # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("casas_file", type=Path)
    ap.add_argument("area_map", type=Path)
    ap.add_argument("-o", "--out", type=Path, default=Path("baselines.json"))
    args = ap.parse_args()

    events = load_casas_events(args.casas_file)
    area_map = json.loads(args.area_map.read_text())
    b = compute_baselines(events, area_map)
    save_baselines(b, args.out)
    days = max((s["days"] for s in b.values()), default=0)
    print(f"{len(events)} events -> {len(b)} features over ~{days} days -> {args.out}")
    for feat, s in b.items():
        print(f"  {feat:22s} mean {s['mean']:>8.3f}  std {s['std']:>7.3f}  days {s['days']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
