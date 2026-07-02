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

# Where real dataset files live (git-ignored; see docs/demo-runbook.md).
DATA_DIR = Path(__file__).resolve().parents[2] / "data"
SISFALL_DIR = DATA_DIR / "sisfall"


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
