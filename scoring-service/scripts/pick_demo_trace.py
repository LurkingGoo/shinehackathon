"""Pin the most demo-legible REAL fall as the simulate-injection trace.

    python scripts/pick_demo_trace.py [--dir data/sisfall]

Scans every fall trace with the calibrated production thresholds and pins the
most dramatic detected one (big impact peak, long post-impact stillness, clear
free-fall) to data/sisfall/demo_trace.json, which
`loaders.default_sisfall_trace()` prefers over first-on-disk. Rehearsal
2026-07-02 (demo-runbook fix #2): first-on-disk F01 is a slip barely over
threshold ("2.4 g, 7 s, 71%") — authentic but weak on stage. Every candidate
is still a genuine recorded human fall through the same pipeline.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.data.loaders import SISFALL_FS, sisfall_smv  # noqa: E402
from app.scoring import acute  # noqa: E402


def drama(res) -> float:
    """Demo legibility: impact severity dominates, stillness (the long-lie
    signal) second, sustained free-fall third. All real, just legible."""
    return (min(res.peak_g, 8.0)
            + 0.05 * min(res.post_impact_still_s, 60.0)
            + 0.002 * min(res.freefall_ms, 500.0))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dir", type=Path,
                    default=Path(__file__).resolve().parents[1] / "data" / "sisfall")
    args = ap.parse_args()

    falls = sorted(args.dir.rglob("F*.txt"))
    if not falls:
        print(f"no F*.txt fall traces under {args.dir}")
        return 1

    best, best_res, best_score = None, None, -1.0
    for i, p in enumerate(falls, 1):
        try:
            res = acute.detect_fall(sisfall_smv(p), SISFALL_FS)
        except ValueError:
            continue
        if res.detected and (s := drama(res)) > best_score:
            best, best_res, best_score = p, res, s
        if i % 300 == 0:
            print(f"  {i}/{len(falls)} scanned ...", file=sys.stderr)

    if best is None:
        print("no fall detected at production thresholds — nothing pinned")
        return 1

    pin = args.dir / "demo_trace.json"
    pin.write_text(json.dumps({
        "path": str(best.relative_to(args.dir)),
        "peak_g": round(best_res.peak_g, 2),
        "post_impact_still_s": round(best_res.post_impact_still_s, 1),
        "freefall_ms": round(best_res.freefall_ms, 1),
        "picked_by": "scripts/pick_demo_trace.py",
    }, indent=2) + "\n")
    print(f"pinned {best.name}: {best_res.peak_g:.1f} g impact, "
          f"{best_res.post_impact_still_s:.0f} s stillness, "
          f"{best_res.freefall_ms:.0f} ms free-fall -> {pin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
