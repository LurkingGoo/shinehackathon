"""Threshold calibration over real SisFall traces — the one-command loop.

    python scripts/calibrate.py                 # confusion counts at current thresholds
    python scripts/calibrate.py --grid          # sweep thresholds, best rows first
    python scripts/calibrate.py --dir PATH      # dataset dir (default data/sisfall)
    python scripts/calibrate.py --subjects SE   # filter to subject folders starting with SE
    python scripts/calibrate.py --json-out P    # also write metrics JSON (default data/metrics.json)

SisFall naming: F*.txt = falls (positives), D*.txt = ADLs (negatives). Subject
folders: SA## = young adults, SE## = elderly.
Reports detection rate (sensitivity) on falls and false-alarm rate on ADLs.
Numbers go into the judge brief / slide deck (triage-dashboard/public/judge-brief.html,
docs/slides/deck.md) ONLY from this script's output — `--json-out` writes the
machine-readable metrics.json that is the single source of truth for those
headline numbers (no accuracy claims that weren't measured).

metrics.json design: ONE merged file across runs. Each non-grid run upserts a
cohort section keyed by the --subjects prefix ("pooled" when unfiltered), so a
pooled run and cohort runs (SE = elderly, SA = young adults) coexist in the
same document. Each cohort carries its own operating point + raw counts;
dataset provenance (sha256 / fetched date from data/datasets.lock.json) is the
"generated-at" signal — no wall-clock timestamps, so reruns on unchanged data
and thresholds are byte-identical. Grid sweeps are exploratory and never write
JSON (--grid + --json-out is rejected).
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.loaders import SISFALL_DIR, SISFALL_FS, sisfall_smv  # noqa: E402
from app.scoring import acute  # noqa: E402


def load_all(files: list[tuple[Path, bool]]) -> list[tuple, ]:
    """Parse every trace ONCE (the expensive step) so grid sweeps are cheap."""
    data = []
    for i, (path, is_fall) in enumerate(files, 1):
        try:
            data.append((sisfall_smv(path), is_fall))
        except ValueError as e:
            print(f"  skipping unparsable trace: {e}")
        if i % 500 == 0:
            print(f"  parsed {i}/{len(files)} traces ...")
    return data


def evaluate(data: list[tuple], **thresholds) -> dict:
    tp = fn = fp = tn = 0
    for smv, is_fall in data:
        detected = acute.detect_fall(smv, SISFALL_FS, **thresholds).detected
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


DEFAULT_JSON_OUT = Path(__file__).resolve().parents[1] / "data" / "metrics.json"


def dataset_info(dataset_dir: Path) -> dict:
    """Provenance for the metrics file, taken from data/datasets.lock.json."""
    info: dict = {"dir": dataset_dir.name}
    lock = Path(__file__).resolve().parents[1] / "data" / "datasets.lock.json"
    try:
        sisfall = json.loads(lock.read_text())["sisfall"]
        info.update(name="SisFall", sha256=sisfall["sha256"],
                    fetched=sisfall["fetched"], citation=sisfall["citation"])
    except (OSError, KeyError, ValueError):
        pass  # lock file optional — counts/rates are still valid without it
    return info


def write_metrics(path: Path, cohort: str, subjects: str | None,
                  result: dict, dataset_dir: Path) -> None:
    """Upsert one cohort section into the merged metrics.json (see docstring)."""
    doc: dict = {}
    if path.is_file():
        try:
            doc = json.loads(path.read_text())
        except ValueError:
            doc = {}  # corrupt file — rebuild from this run
    doc["dataset"] = dataset_info(dataset_dir)
    tp, fn, fp, tn = result["tp"], result["fn"], result["fp"], result["tn"]
    doc.setdefault("cohorts", {})[cohort] = {
        "subjects": subjects,
        "operating_point": {
            "freefall_g": acute.FREEFALL_G,
            "impact_g": acute.IMPACT_G,
            "freefall_min_s": acute.FREEFALL_MIN_S,
            "impact_window_s": acute.IMPACT_WINDOW_S,
        },
        "counts": {"tp": tp, "fn": fn, "fp": fp, "tn": tn,
                   "falls": tp + fn, "adls": fp + tn},
        "detection_rate": round(result["sensitivity"], 4),
        "false_alarm_rate": round(result["false_alarm"], 4),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc, indent=2) + "\n")
    print(f"wrote cohort '{cohort}' -> {path}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path, default=SISFALL_DIR)
    ap.add_argument("--grid", action="store_true")
    ap.add_argument("--subjects", default=None,
                     help="filter to subject folders whose name starts with this "
                          "prefix (e.g. SE for elderly, SA for young adults)")
    ap.add_argument("--json-out", type=Path, nargs="?", const=DEFAULT_JSON_OUT,
                    default=None, metavar="PATH",
                    help="write/merge machine-readable metrics JSON "
                         f"(default {DEFAULT_JSON_OUT}); incompatible with --grid")
    args = ap.parse_args(argv)
    if args.grid and args.json_out:
        ap.error("--json-out records an operating point; --grid is a sweep — run without --grid")

    if not args.dir.is_dir():
        print(f"no dataset at {args.dir} — download SisFall first")
        return 1
    files = [(p, True) for p in sorted(args.dir.rglob("F*.txt"))] + \
            [(p, False) for p in sorted(args.dir.rglob("D*.txt"))]
    if args.subjects:
        files = [(p, f) for p, f in files if p.parent.name.startswith(args.subjects)]
    if not files:
        print(f"no F*/D* traces in {args.dir}" +
              (f" for subjects {args.subjects}*" if args.subjects else ""))
        return 1
    print(f"{sum(1 for _, f in files if f)} falls, {sum(1 for _, f in files if not f)} ADLs")
    data = load_all(files)
    print()

    if not args.grid:
        r = evaluate(data)
        print(f"current thresholds  freefall<{acute.FREEFALL_G}g  impact>{acute.IMPACT_G}g  "
              f"dip>={acute.FREEFALL_MIN_S*1000:.0f}ms  window<={acute.IMPACT_WINDOW_S*1000:.0f}ms")
        print(f"  detection {r['sensitivity']:.1%} ({r['tp']}/{r['tp']+r['fn']})   "
              f"false-alarm {r['false_alarm']:.1%} ({r['fp']}/{r['fp']+r['tn']})")
        if args.json_out:
            write_metrics(args.json_out, args.subjects or "pooled",
                          args.subjects, r, args.dir)
        return 0

    grid = itertools.product(
        [0.5, 0.6, 0.7, 0.8],          # freefall_g
        [2.0, 2.3, 2.7, 3.0],          # impact_g
        [0.04, 0.06, 0.08],            # freefall_min_s
        [0.4, 0.5, 0.7],               # impact_window_s
    )
    rows = [evaluate(data, freefall_g=fg, impact_g=ig,
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
