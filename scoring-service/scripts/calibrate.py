"""Threshold calibration over real SisFall traces — the one-command loop.

    python scripts/calibrate.py            # confusion counts at current thresholds
    python scripts/calibrate.py --grid     # sweep thresholds, best rows first
    python scripts/calibrate.py --dir PATH # dataset dir (default data/sisfall)

SisFall naming: F*.txt = falls (positives), D*.txt = ADLs (negatives).
Reports detection rate (sensitivity) on falls and false-alarm rate on ADLs.
Numbers go into docs/scoring-card.md §Metrics ONLY from this script's output
(the scoring-card forbids accuracy claims that weren't measured).
"""
from __future__ import annotations

import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.loaders import SISFALL_DIR, SISFALL_FS, sisfall_smv  # noqa: E402
from app.scoring import acute  # noqa: E402


def evaluate(files: list[tuple[Path, bool]], **thresholds) -> dict:
    tp = fn = fp = tn = 0
    for path, is_fall in files:
        detected = acute.detect_fall(sisfall_smv(path), SISFALL_FS, **thresholds).detected
        if is_fall:
            tp, fn = tp + int(detected), fn + int(not detected)
        else:
            fp, tn = fp + int(detected), tn + int(not detected)
    falls, adls = tp + fn, fp + tn
    return {
        "tp": tp, "fn": fn, "fp": fp, "tn": tn,
        "sensitivity": tp / falls if falls else float("nan"),
        "false_alarm": fp / adls if adls else float("nan"),
        **thresholds,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=SISFALL_DIR)
    ap.add_argument("--grid", action="store_true")
    args = ap.parse_args()

    if not args.dir.is_dir():
        print(f"no dataset at {args.dir} — download SisFall first (docs/demo-runbook.md)")
        return 1
    files = [(p, True) for p in sorted(args.dir.glob("F*.txt"))] + \
            [(p, False) for p in sorted(args.dir.glob("D*.txt"))]
    if not files:
        print(f"no F*/D* traces in {args.dir}")
        return 1
    print(f"{sum(1 for _, f in files if f)} falls, {sum(1 for _, f in files if not f)} ADLs\n")

    if not args.grid:
        r = evaluate(files)
        print(f"current thresholds  freefall<{acute.FREEFALL_G}g  impact>{acute.IMPACT_G}g  "
              f"dip>={acute.FREEFALL_MIN_S*1000:.0f}ms  window<={acute.IMPACT_WINDOW_S*1000:.0f}ms")
        print(f"  detection {r['sensitivity']:.1%} ({r['tp']}/{r['tp']+r['fn']})   "
              f"false-alarm {r['false_alarm']:.1%} ({r['fp']}/{r['fp']+r['tn']})")
        return 0

    grid = itertools.product(
        [0.5, 0.6, 0.7, 0.8],          # freefall_g
        [2.0, 2.3, 2.7, 3.0],          # impact_g
        [0.04, 0.06, 0.08],            # freefall_min_s
        [0.4, 0.5, 0.7],               # impact_window_s
    )
    rows = [evaluate(files, freefall_g=fg, impact_g=ig,
                     freefall_min_s=fm, impact_window_s=iw)
            for fg, ig, fm, iw in grid]
    # missed falls are the costliest error (scoring-card): rank by sensitivity,
    # break ties with the lower false-alarm rate.
    rows.sort(key=lambda r: (-r["sensitivity"], r["false_alarm"]))
    print("freefall_g impact_g dip_ms window_ms   detect   false-alarm")
    for r in rows[:15]:
        print(f"{r['freefall_g']:>9.2f} {r['impact_g']:>8.1f} "
              f"{r['freefall_min_s']*1000:>6.0f} {r['impact_window_s']*1000:>9.0f} "
              f"{r['sensitivity']:>8.1%} {r['false_alarm']:>12.1%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
