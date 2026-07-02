"""False-alarm breakdown by SisFall ADL category at the chosen thresholds.

    python scripts/fa_breakdown.py [--dir data/sisfall]

SisFall's ADLs are deliberately fall-like (jogging, jumping, stumbling, quick
sits) — a raw false-alarm % overstates daily-life alarm load. This reports the
rate per activity code so the scoring-card can state where alarms concentrate.
Activity names from the dataset's Readme.txt.
"""
from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.loaders import SISFALL_FS, sisfall_smv  # noqa: E402
from app.scoring import acute  # noqa: E402

ADL_NAMES = {
    "D01": "Walking slowly", "D02": "Walking quickly",
    "D03": "Jogging slowly", "D04": "Jogging quickly",
    "D05": "Walking up/down stairs slowly", "D06": "Walking up/down stairs quickly",
    "D07": "Sit in half-height chair, slow", "D08": "Sit in half-height chair, QUICK",
    "D09": "Sit in low chair, slow", "D10": "Sit in low chair, QUICK",
    "D11": "Sitting, then collapsing into chair", "D12": "Lying down / rising, slow",
    "D13": "Lying down / rising, QUICK", "D14": "On knees, standing up",
    "D15": "Stoop to pick object", "D16": "Gently jump (reach object)",
    "D17": "Stumble while walking", "D18": "Gently jog + JUMP over obstacle",
    "D19": "Get in/out of a car",
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path,
                    default=Path(__file__).resolve().parents[1] / "data" / "sisfall")
    args = ap.parse_args()

    hits: dict[str, int] = defaultdict(int)
    totals: dict[str, int] = defaultdict(int)
    files = sorted(args.dir.rglob("D*.txt"))
    if not files:
        print(f"no D*.txt ADL traces under {args.dir}")
        return 1
    for i, p in enumerate(files, 1):
        code = p.name.split("_")[0]
        try:
            s = sisfall_smv(p)
        except ValueError:
            continue
        totals[code] += 1
        if acute.detect_fall(s, SISFALL_FS).detected:
            hits[code] += 1
        if i % 500 == 0:
            print(f"  {i}/{len(files)} ...", file=sys.stderr)

    print(f"thresholds  freefall<{acute.FREEFALL_G}g  impact>{acute.IMPACT_G}g  "
          f"dip>={acute.FREEFALL_MIN_S*1000:.0f}ms  window<={acute.IMPACT_WINDOW_S*1000:.0f}ms\n")
    print(f"{'code':5s} {'activity':38s} {'alarms':>6s} {'n':>5s} {'rate':>7s}")
    grand_h = grand_n = 0
    for code in sorted(totals):
        h, n = hits[code], totals[code]
        grand_h, grand_n = grand_h + h, grand_n + n
        print(f"{code:5s} {ADL_NAMES.get(code, '?'):38s} {h:6d} {n:5d} {h/n:6.1%}")
    print(f"\noverall ADL false-alarm rate: {grand_h}/{grand_n} = {grand_h/grand_n:.1%}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
