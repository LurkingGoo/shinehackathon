"""Dataset loaders — SisFall (acute) + CASAS (chronic).

Real parsers for the public datasets (docs/scoring-card.md Datasheet). The
loaders replace the synthetic fixtures behind the same contract: they produce
raw signals, the pipeline computes the scores.

SisFall file format (Sucerquia et al., 2017 — SisFall: A Fall and Movement
Dataset): plain text, one sample per line at 200 Hz, 9 comma-separated integer
ADC readings terminated by ';':

    ADXL345_x, ADXL345_y, ADXL345_z, ITG3200_x, ITG3200_y, ITG3200_z,
    MMA8451Q_x, MMA8451Q_y, MMA8451Q_z;

Conversion to physical units: value * (2*Range / 2^Resolution).
We use the ADXL345 (13-bit, ±16 g) — the sensor the SisFall thresholds were
published against.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import numpy as np

SISFALL_FS = 200.0  # Hz
_ADXL345_G_PER_BIT = (2 * 16.0) / (2 ** 13)  # 13-bit ADC over ±16 g

# Where real dataset files live. Tier-1 raw (sisfall/) is git-ignored and only
# present on a dev machine; Tier-2 curated (curated/falls.json) is committed, so
# a fresh clone / Render runs the rotation on REAL falls with zero download.
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SISFALL_DIR = DATA_DIR / "sisfall"
CURATED_FALLS = DATA_DIR / "curated" / "falls.json"


def load_sisfall_trace(path: str | Path) -> np.ndarray:
    """Parse one SisFall file -> (N, 3) float array of ADXL345 acceleration in g.

    Tolerates blank lines, trailing ';' and whitespace. Raises ValueError on a
    line that isn't 9 integer fields (a truncated download, not a format drift).
    """
    rows: list[list[float]] = []
    text = Path(path).read_text()
    for ln, line in enumerate(text.splitlines(), start=1):
        line = line.strip().rstrip(";").strip()
        if not line:
            continue
        parts = [p for p in (s.strip() for s in line.split(",")) if p]
        if len(parts) != 9:
            raise ValueError(f"{path}:{ln}: expected 9 fields, got {len(parts)}")
        rows.append([float(parts[0]), float(parts[1]), float(parts[2])])
    if not rows:
        raise ValueError(f"{path}: no samples")
    return np.asarray(rows) * _ADXL345_G_PER_BIT


def sisfall_smv(path: str | Path) -> np.ndarray:
    """One SisFall file -> signal-magnitude vector in g (feed detect_fall)."""
    trace = load_sisfall_trace(path)
    return np.sqrt((trace ** 2).sum(axis=1))


def default_sisfall_trace() -> Path | None:
    """The trace `POST /incidents/simulate` injects, if a real one is on disk.

    Resolution order: $SISFALL_TRACE env var, else the curated demo trace
    pinned by scripts/pick_demo_trace.py (data/sisfall/demo_trace.json), else
    the first .txt under data/sisfall/ (fall files are named F*.txt). None ->
    caller falls back to the synthetic trace, so the demo never breaks.
    """
    env = os.environ.get("SISFALL_TRACE")
    if env and Path(env).is_file():
        return Path(env)
    pin = SISFALL_DIR / "demo_trace.json"
    if pin.is_file():
        import json
        picked = Path(json.loads(pin.read_text())["path"])
        if not picked.is_absolute():
            picked = SISFALL_DIR / picked
        if picked.is_file():
            return picked
    if SISFALL_DIR.is_dir():
        # rglob: the SisFall zip extracts into per-subject folders (SA01/, ...)
        falls = sorted(SISFALL_DIR.rglob("F*.txt")) or sorted(SISFALL_DIR.rglob("*.txt"))
        if falls:
            return falls[0]
    return None


_rotation_cache: list[Path] | None = None


def demo_rotation_traces(n: int = 4) -> list[Path]:
    """A curated set of DISTINCT real SisFall falls for the Simulate rotation.

    `POST /incidents/simulate` round-robins through these so each press shows a
    visibly different fall (different subject, different peak-g / free-fall).
    Selection is deterministic and cached: the curated dramatic pin
    (default_sisfall_trace) first, then one detected fall per distinct subject,
    each with a peak-g at least 0.5 g apart from the ones already chosen so the
    drilldown numbers differ noticeably. Returns [] when no real SisFall data is
    on disk — the caller then falls back to the synthetic rotation so the demo
    never breaks. All picks pass the same production detector.
    """
    global _rotation_cache
    if _rotation_cache is not None:
        return _rotation_cache
    from app.scoring import acute

    picks: list[Path] = []
    peaks: list[float] = []

    def consider(p: Path) -> None:
        if len(picks) >= n or p in picks:
            return
        try:
            res = acute.detect_fall(sisfall_smv(p), SISFALL_FS)
        except (ValueError, OSError):
            return
        if not res.detected:
            return
        if any(abs(res.peak_g - pk) < 0.5 for pk in peaks):
            return
        picks.append(p)
        peaks.append(res.peak_g)

    pin = default_sisfall_trace()
    if pin is not None:
        consider(pin)

    if SISFALL_DIR.is_dir():
        seen_subjects: set[str] = set()
        for p in sorted(SISFALL_DIR.rglob("F*.txt")):
            if len(picks) >= n:
                break
            subj = p.parent.name
            if subj in seen_subjects:
                continue
            seen_subjects.add(subj)
            consider(p)

    _rotation_cache = picks
    return picks


@dataclass
class SmvTrace:
    """A ready-to-score fall: signal-magnitude vector in g + its sample rate.

    The unit the rotation actually feeds the detector, decoupled from where it
    came from (raw Tier-1 file vs committed Tier-2 curated window)."""
    id: str
    smv: np.ndarray
    fs: float


def _curated_falls() -> list[SmvTrace]:
    """Tier-2 fallback: real SisFall SMV windows committed to the repo.

    Read from data/curated/falls.json (produced by scripts/curate.py from the
    raw dataset, full 200 Hz). Lets a fresh clone with no raw data/sisfall/ run
    the Simulate rotation on GENUINE falls. [] if the curated file is absent."""
    if not CURATED_FALLS.is_file():
        return []
    import json
    data = json.loads(CURATED_FALLS.read_text(encoding="utf-8"))
    default_fs = float(data.get("fs", SISFALL_FS))
    out: list[SmvTrace] = []
    for t in data.get("traces", []):
        smv = np.asarray(t["samples"], dtype=float)
        if smv.size:
            out.append(SmvTrace(id=t["id"], smv=smv, fs=float(t.get("fs", default_fs))))
    return out


def demo_rotation_smv(n: int = 4) -> list[SmvTrace]:
    """SMV traces for the Simulate rotation — REAL falls, source-agnostic.

    Prefers raw Tier-1 (data/sisfall/, the live per-subject selection) and falls
    back to committed Tier-2 (data/curated/falls.json) when no raw data is on
    disk. Empty only when NEITHER is present — the caller then uses the synthetic
    rotation so the demo never breaks. Either way every trace passed the same
    production detector at curation time."""
    paths = demo_rotation_traces(n)
    if paths:
        return [SmvTrace(id=p.stem, smv=sisfall_smv(p), fs=SISFALL_FS) for p in paths]
    return _curated_falls()[:n]


@dataclass
class CasasEvent:
    """One CASAS ambient event: PIR motion (M###), door (D###), etc."""
    ts: datetime
    sensor: str
    state: str  # ON/OFF, OPEN/CLOSE, ...


def load_casas_events(path: str | Path) -> list[CasasEvent]:
    """Parse a CASAS annotated-events file -> chronological CasasEvent list.

    On-disk format (WSU CASAS, e.g. Aruba/HH): whitespace-separated
        DATE TIME SENSOR STATE [activity-label begin|end]
        2010-11-04 00:03:50.209589 M003 ON
    Activity labels are ignored (we self-baseline, we don't train on labels).
    """
    events: list[CasasEvent] = []
    for ln, line in enumerate(Path(path).read_text().splitlines(), start=1):
        parts = line.split()
        if not parts:
            continue
        if len(parts) < 4:
            raise ValueError(f"{path}:{ln}: expected 'date time sensor state'")
        stamp = f"{parts[0]} {parts[1]}"
        fmt = "%Y-%m-%d %H:%M:%S.%f" if "." in parts[1] else "%Y-%m-%d %H:%M:%S"
        events.append(CasasEvent(datetime.strptime(stamp, fmt), parts[2], parts[3]))
    events.sort(key=lambda e: e.ts)
    return events
