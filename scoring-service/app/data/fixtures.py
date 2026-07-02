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

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

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
            CFI("Bedroom exit", "None by 10:00", 0.44, "typ. 07:30", anomaly=0.72),
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


# ------------------------------ acute trace ------------------------------- #
def _fall_smv() -> np.ndarray:
    """Synthetic SisFall-like signal-magnitude trace (g): rest → free-fall dip →
    impact peak (~5g) → ~40s stillness. Replaced by a real SisFall trace once
    app/data/loaders.py lands."""
    rest = np.ones(int(1.0 * FS))
    freefall = np.full(int(0.3 * FS), 0.2)
    impact = np.array([5.0, 4.6, 3.8])
    still = np.ones(int(40.0 * FS))
    return np.concatenate([rest, freefall, impact, still])


_ACUTE_SMV = _fall_smv()

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


def build_ranked_caseload() -> RankedCaseload:
    """Order: acute first, then chronic by COMPUTED risk desc (the ranking rule)."""
    ranked = sorted(CHRONIC, key=lambda r: _chronic_score(r)[0].risk, reverse=True)
    entries = [_chronic_entry(r, i + 1) for i, r in enumerate(ranked)]
    return RankedCaseload(generated_at=_iso_min_ago(0), entries=entries)


def detail_by_id(rid: str) -> ResidentDetail | None:
    if rid == ACUTE.id:
        return _acute_detail()
    for r in CHRONIC:
        if r.id == rid:
            return _chronic_detail(r)
    return None


def build_incident_event() -> IncidentEvent:
    return IncidentEvent(
        emitted_at=_iso_min_ago(0),
        entry=_acute_entry(1),
        detail=_acute_detail(),
    )
