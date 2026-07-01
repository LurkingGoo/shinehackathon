"""Dataset loaders — SisFall (acute) + CASAS (chronic).

STUB. This is where the real datasets replace the fixtures behind the same
contract. See docs/scoring-card.md (Datasheet) and docs/feature-spec.md.

Planned:
- load_sisfall_trace(path) -> np.ndarray of (ax, ay, az) at ~200 Hz, in g.
  Feed to app.scoring.acute.smv() → detect_fall().
- load_casas_events(path) -> DataFrame[timestamp, sensor, state]; map sensors to
  areas via a per-home layout file; feed app.replay.baselines to precompute
  per-resident baselines.json, then app.scoring.chronic.anomaly() live.

Kept as a stub so the service runs on fixtures today; wiring these in is the
next backend step (state.md / docs/demo-runbook.md).
"""
from __future__ import annotations

from pathlib import Path


def load_sisfall_trace(path: str | Path):  # pragma: no cover - stub
    raise NotImplementedError("Wire SisFall accelerometer parsing here.")


def load_casas_events(path: str | Path):  # pragma: no cover - stub
    raise NotImplementedError("Wire CASAS ambient event parsing here.")
