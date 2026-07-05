"""Demo data — RAW SIGNALS, not scores.

Ported in spirit from the frontend fixtures, but restructured: instead of
hard-coding risk/confidence/rationale, this holds the raw inputs (per-feature
observations + baselines for chronic; an accelerometer trace for acute) and the
pipeline (app/scoring/pipeline.py) COMPUTES the scores. This is what wires the
scoring modules into what the API serves.

The real dataset loaders (app/data/loaders.py) replace these raw inputs; the
pipeline and contract stay unchanged. Because scores are computed, values differ
from the old hand-set demo numbers — by design (docs/scoring-card.md).
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

from app.briefing import deterministic_briefing
from app.models import (
    CaseloadEntry,
    IncidentEvent,
    RankedCaseload,
    ResidentDetail,
    RiskScore,
)
from app.scoring import pipeline
from app.scoring.pipeline import ChronicFeatureInput as CFI

FS = 200.0  # accelerometer sample rate (Hz), SisFall-like


def _iso_min_ago(m: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat().replace(
        "+00:00", "Z"
    )


# --------------------------- chronic residents ---------------------------- #
@dataclass
class ChronicResident:
    id: str
    name: str
    age: int
    unit: str
    sensor: str
    sensor_class: str
    updated_min_ago: int
    recency: str
    days_of_history: int
    data_quality: float
    inputs: list[CFI] = field(default_factory=list)


CHRONIC: list[ChronicResident] = [
    ChronicResident(
        "r-rajoo", "Rajoo Subramaniam", 78, "Blk 112 #05-214", "PIR motion",
        "CASAS ambient", 22, "22 min ago", days_of_history=21, data_quality=0.82,
        inputs=[
            # z-score path: 16h kitchen gap vs a ~3.5h baseline is a huge anomaly
            CFI("Kitchen inactivity", "16h 04m", 0.52, "typ. < 4h",
                observed=16.07, mean=3.5, std=1.2),
            CFI("Last confirmed motion", "Bedroom, 22 min ago", 0.19, anomaly=0.35),
            CFI("Front door", "Not opened today", 0.11, "typ. 08:10", anomaly=0.6),
        ],
    ),
    ChronicResident(
        "r-wong", "Wong Lai Keng", 85, "Blk 108 #11-330", "Door + PIR",
        "CASAS ambient", 60, "1h ago", days_of_history=30, data_quality=0.77,
        inputs=[
            CFI("Bedroom exit", "not seen by 10:00", 0.44, "typ. 07:30", anomaly=0.72),
            CFI("Bathroom visits", "0 today", 0.22, "typ. 2 by 10:00", anomaly=0.55),
            CFI("Motion variance", "3.1σ low", 0.11, anomaly=0.6),
        ],
    ),
    ChronicResident(
        "r-lim", "Lim Boon Huat", 74, "Blk 115 #03-120", "PIR motion",
        "CASAS ambient", 40, "40 min ago", days_of_history=14, data_quality=0.69,
        inputs=[
            # z-score path: 6 nocturnal trips vs typical 2 (std 0.8) → strong
            CFI("Nocturnal trips", "6 / night", 0.31, "typ. 2",
                observed=6, mean=2, std=0.8),
            CFI("Sleep fragmentation", "High", 0.09, anomaly=0.6),
            CFI("Daytime activity", "Normal", 0.04, anomaly=0.1),
        ],
    ),
    ChronicResident(
        "r-devi", "Devi Nair", 80, "Blk 110 #07-45", "Door sensor",
        "CASAS ambient", 15, "15 min ago", days_of_history=45, data_quality=0.81,
        inputs=[
            CFI("Front door", "07:50 (on time)", 0.0, "typ. 07:45", anomaly=0.0),
            CFI("Kitchen activity", "Normal", 0.0, anomaly=0.0),
        ],
    ),
    ChronicResident(
        "r-goh", "Goh Cheng Watt", 77, "Blk 112 #09-88", "PIR motion",
        "CASAS ambient", 8, "8 min ago", days_of_history=60, data_quality=0.74,
        inputs=[CFI("Activity pattern", "Nominal", 0.0, anomaly=0.0)],
    ),
]


def _try_real_resident() -> None:
    """Back r-rajoo with the REAL CASAS resident when the offline artifact
    exists (scripts/build_baselines.py --demo-day). One caseload row then
    carries genuinely observed numbers scored by the same pipeline; without
    the artifact the synthetic inputs stand and nothing breaks."""
    path = Path(__file__).resolve().parents[2] / "data" / "casas" / "real_resident.json"
    if not path.exists():
        return
    art = json.loads(path.read_text())
    b, o = art["baselines"], art["observations"]
    inputs: list[CFI] = []

    if "kitchen_gap_h" in o and "kitchen_gap_h" in b:
        kb = b["kitchen_gap_h"]
        inputs.append(CFI(
            "Kitchen inactivity", f"{o['kitchen_gap_h']:.1f}h gap", 0.52,
            f"typ. {kb['mean']:.1f}h",
            observed=o["kitchen_gap_h"], mean=kb["mean"], std=kb["std"]))
    if "door_first_open_h" in b:
        db = b["door_first_open_h"]
        if "door_first_open_h" in o:
            h = o["door_first_open_h"]
            inputs.append(CFI(
                "Front door", f"first opened {int(h):02d}:{int(h % 1 * 60):02d}",
                0.15, f"typ. {int(db['mean']):02d}:{int(db['mean'] % 1 * 60):02d}",
                observed=h, mean=db["mean"], std=db["std"],
                side="both"))  # departure from the door routine either way
        else:
            inputs.append(CFI("Front door", "Not opened today", 0.15,
                              f"typ. {int(db['mean']):02d}:{int(db['mean'] % 1 * 60):02d}",
                              anomaly=0.7))
    if "night_bathroom_trips" in o and "night_bathroom_trips" in b:
        nb = b["night_bathroom_trips"]
        inputs.append(CFI(
            "Night bathroom trips", f"{o['night_bathroom_trips']:.0f} / night", 0.20,
            f"typ. {nb['mean']:.0f}",
            observed=o["night_bathroom_trips"], mean=nb["mean"], std=nb["std"],
            side="both"))  # more = UTI/decline; fewer corroborates inactivity
    if "daily_activity" in o and "daily_activity" in b:
        ab = b["daily_activity"]
        inputs.append(CFI(
            "Activity volume", f"{o['daily_activity']:.0f} events today", 0.13,
            f"typ. {ab['mean']:.0f}/day",
            observed=o["daily_activity"], mean=ab["mean"], std=ab["std"],
            side="low"))  # whole-day low volume corroborates inactivity
    if not inputs:
        return

    r = CHRONIC[0]  # r-rajoo — the elevated-concern demo row
    r.inputs = inputs
    r.days_of_history = int(art.get("days_of_history", r.days_of_history))
    r.sensor = "PIR + door"
    r.sensor_class = "CASAS ambient (real stream)"


_try_real_resident()


# ------------------------------ acute trace ------------------------------- #
def _fall_smv(
    peak: float = 5.0, freefall_s: float = 0.3, still_s: float = 40.0
) -> np.ndarray:
    """Synthetic SisFall-like signal-magnitude trace (g): rest → free-fall dip →
    impact peak → stillness. Parametrised so the rotation can offer visibly
    different falls when no real SisFall data is on disk. Used as the fallback
    for a real trace once app/data/loaders.py lands."""
    rest = np.ones(int(1.0 * FS))
    freefall = np.full(int(freefall_s * FS), 0.2)
    impact = np.array([peak, peak * 0.92, peak * 0.76])
    still = np.ones(int(still_s * FS))
    return np.concatenate([rest, freefall, impact, still])


_ACUTE_SMV = _fall_smv()

# Synthetic rotation — the fallback when data/sisfall/ is empty. Distinct
# peak-g and free-fall durations so successive Simulate presses still differ
# visibly (the drilldown waveform, peakG and freefallMs all change).
_SYNTHETIC_ROTATION: list[np.ndarray] = [
    _fall_smv(peak=5.0, freefall_s=0.30, still_s=40.0),
    _fall_smv(peak=3.4, freefall_s=0.12, still_s=25.0),
    _fall_smv(peak=6.8, freefall_s=0.45, still_s=50.0),
]


def synthetic_rotation_trace(i: int) -> tuple[np.ndarray, float]:
    """The i-th synthetic fall variant (round-robin) + its sample rate."""
    smv = _SYNTHETIC_ROTATION[i % len(_SYNTHETIC_ROTATION)]
    return smv, FS


def nearmiss_smv() -> np.ndarray:
    """A dropped-phone-like SMV: a sharp impact spike with NO free-fall dip
    before it and NO sustained stillness after (continued handling motion). Fed
    to the SAME acute.detect_fall, it must return detected=False — the
    specificity demo. Signal never dips below the free-fall threshold, so the
    ordered fall signature is absent."""
    rest = np.ones(int(1.0 * FS))
    # sharp impact-like spike (above the impact threshold) but no preceding dip
    spike = np.array([4.6, 4.1, 3.3, 2.0])
    # afterwards: the phone keeps being handled — jittery motion, never still,
    # and never dips into free-fall territory
    rng = np.random.default_rng(7)
    after = 1.0 + 0.18 * np.sin(np.linspace(0, 30, int(3.0 * FS))) \
        + 0.05 * rng.standard_normal(int(3.0 * FS))
    return np.concatenate([rest, spike, np.clip(after, 0.85, None)])

# The trace behind r-tan's acute score. Injection (a real SisFall trace via
# POST /incidents/simulate) replaces it so the drilldown fetched later matches
# the numbers the IncidentEvent carried.
_current_acute_smv: np.ndarray = _ACUTE_SMV
_current_acute_fs: float = FS


def set_acute_trace(smv: np.ndarray, fs: float = FS) -> None:
    global _current_acute_smv, _current_acute_fs
    _current_acute_smv = smv
    _current_acute_fs = fs


@dataclass
class AcuteResident:
    id: str
    name: str
    age: int
    unit: str
    sensor: str
    sensor_class: str
    updated_min_ago: int
    recency: str


ACUTE = AcuteResident(
    "r-tan", "Tan Ah Moi", 82, "Blk 108 #04-210", "Accelerometer",
    "Wearable bangle", 0, "just now",
)


# --------------------------- build contract objects ----------------------- #
def _chronic_score(r: ChronicResident) -> tuple[RiskScore, list, str, str]:
    parts = pipeline.score_chronic(
        r.inputs, days_of_history=r.days_of_history, data_quality=r.data_quality
    )
    score = RiskScore(
        track="chronic", risk=parts.risk, confidence=parts.confidence,
        updated_at=_iso_min_ago(r.updated_min_ago), recency=r.recency,
        sensor=r.sensor, sensor_class=r.sensor_class, rationale=parts.rationale,
    )
    return score, parts.features, parts.recommended_action, parts.rationale


def _acute_score() -> tuple[RiskScore, list, str, str]:
    parts = pipeline.score_acute(_current_acute_smv, _current_acute_fs)
    score = RiskScore(
        track="acute", risk=parts.risk, confidence=parts.confidence,
        updated_at=_iso_min_ago(ACUTE.updated_min_ago), recency=ACUTE.recency,
        sensor=ACUTE.sensor, sensor_class=ACUTE.sensor_class, rationale=parts.rationale,
    )
    return score, parts.features, parts.recommended_action, parts.rationale


def _chronic_entry(r: ChronicResident, rank: int) -> CaseloadEntry:
    score, _f, _a, _r = _chronic_score(r)
    return CaseloadEntry(id=r.id, name=r.name, age=r.age, unit=r.unit,
                         rank=rank, score=score)


def _chronic_detail(r: ChronicResident) -> ResidentDetail:
    score, feats, action, _r = _chronic_score(r)
    d = ResidentDetail(id=r.id, name=r.name, age=r.age, unit=r.unit, score=score,
                       features=feats, recommended_action=action, briefing="")
    return d.model_copy(update={"briefing": deterministic_briefing(d)})


def _acute_entry(rank: int) -> CaseloadEntry:
    score, _f, _a, _r = _acute_score()
    return CaseloadEntry(id=ACUTE.id, name=ACUTE.name, age=ACUTE.age,
                         unit=ACUTE.unit, rank=rank, score=score)


def _acute_detail() -> ResidentDetail:
    score, feats, action, _r = _acute_score()
    d = ResidentDetail(id=ACUTE.id, name=ACUTE.name, age=ACUTE.age, unit=ACUTE.unit,
                       score=score, features=feats, recommended_action=action,
                       briefing="")
    return d.model_copy(update={"briefing": deterministic_briefing(d)})


# An injected incident persists here so /caseload agrees with the SSE event
# (a page refresh mid-demo must not erase the fall — demo-runbook fix #4).
INCIDENT_TTL_S = 30 * 60
_incident_at: datetime | None = None


def mark_incident() -> None:
    global _incident_at
    _incident_at = datetime.now(timezone.utc)


def clear_incident() -> None:
    global _incident_at
    _incident_at = None


def incident_active() -> bool:
    return (_incident_at is not None
            and (datetime.now(timezone.utc) - _incident_at).total_seconds()
            < INCIDENT_TTL_S)


def build_ranked_caseload() -> RankedCaseload:
    """Order: acute first (while an incident is active), then chronic by
    COMPUTED risk desc (the ranking rule)."""
    ranked = sorted(CHRONIC, key=lambda r: _chronic_score(r)[0].risk, reverse=True)
    offset = 1 if incident_active() else 0
    entries = [_chronic_entry(r, i + 1 + offset) for i, r in enumerate(ranked)]
    if offset:
        entries.insert(0, _acute_entry(1))
    return RankedCaseload(generated_at=_iso_min_ago(0), entries=entries)


def detail_by_id(rid: str) -> ResidentDetail | None:
    if rid == ACUTE.id:
        return _acute_detail()
    for r in CHRONIC:
        if r.id == rid:
            return _chronic_detail(r)
    return None


def acute_trace_payload(max_points: int = 360) -> dict | None:
    """The signal behind the incident, shaped for the drilldown waveform:
    a window around the detected fall, downsampled with extremes preserved
    (a plain stride would drop the 1–3-sample impact peak at 200 Hz), plus
    phase positions in seconds so the UI can band free-fall / impact / still.
    None when no incident is active (the endpoint 404s)."""
    from app.scoring import acute

    if not incident_active():
        return None
    s = np.asarray(_current_acute_smv, dtype=float)
    fs = _current_acute_fs
    res = acute.detect_fall(s, fs)
    if not res.detected:
        return None

    # window: 1 s of rest before the dip → 4 s past the impact
    start = max(0, res.dip_start_idx - int(1.0 * fs))
    end = min(s.size, res.impact_idx + int(4.0 * fs))
    win = s[start:end]

    stride = max(1, int(np.ceil(win.size / max_points)))
    samples: list[float] = []
    for i in range(0, win.size, stride):
        bucket = win[i:i + stride]
        samples.append(float(bucket[np.argmax(np.abs(bucket - 1.0))]))

    to_s = lambda idx: (idx - start) / fs  # noqa: E731 — window-relative seconds
    # camelCase keys — matches the by_alias contract the rest of the API serves
    return {
        "dtS": stride / fs,
        "samples": samples,
        "phases": {
            "freefall": [to_s(res.dip_start_idx), to_s(res.dip_end_idx)],
            "impactS": to_s(res.impact_idx),
            "stillFromS": to_s(res.impact_idx) + 0.25,
        },
        "thresholds": {"freefallG": acute.FREEFALL_G, "impactG": acute.IMPACT_G},
        "peakG": res.peak_g,
        "freefallMs": res.freefall_ms,
    }


def build_incident_event() -> IncidentEvent:
    return IncidentEvent(
        emitted_at=_iso_min_ago(0),
        entry=_acute_entry(1),
        detail=_acute_detail(),
    )
