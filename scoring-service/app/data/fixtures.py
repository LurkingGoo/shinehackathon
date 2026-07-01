"""Mock fixtures — the ONLY hard-coded data, ported 1:1 from the frontend
(triage-dashboard/lib/data/fixtures.ts). This is the demo data source the real
dataset loaders (app/data/loaders.py) replace. Shapes mirror reality so the swap
is honest: chronic residents on CASAS-style signals, one SisFall-style acute
trace injected as the incident.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone

from app.briefing import deterministic_briefing
from app.models import (
    CaseloadEntry,
    IncidentEvent,
    RankedCaseload,
    ResidentDetail,
    RiskFeature,
    RiskScore,
    Track,
)


def _iso_min_ago(m: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=m)).isoformat().replace(
        "+00:00", "Z"
    )


@dataclass
class FixtureRow:
    id: str
    name: str
    age: int
    unit: str
    track: Track
    risk: float
    confidence: float
    updated_min_ago: int
    recency: str
    sensor: str
    sensor_class: str
    rationale: str
    recommended_action: str
    features: list[RiskFeature] = field(default_factory=list)


def _f(label, value, weight, baseline="") -> RiskFeature:
    return RiskFeature(label=label, value=value, weight=weight, baseline=baseline)


RESIDENTS: list[FixtureRow] = [
    FixtureRow(
        "r-rajoo", "Rajoo Subramaniam", 78, "Blk 112 #05-214", "chronic", 0.71, 0.82,
        22, "22 min ago", "PIR motion", "CASAS ambient",
        "No kitchen activity in 16h — usually eats by 08:00.",
        "Call resident. If no answer in 15 min, dispatch buddy visit.",
        [
            _f("Kitchen inactivity", "16h 04m", 0.52, "typ. < 4h"),
            _f("Last confirmed motion", "Bedroom, 22 min ago", 0.19),
            _f("Front door", "Not opened today", 0.11, "typ. 08:10"),
        ],
    ),
    FixtureRow(
        "r-wong", "Wong Lai Keng", 85, "Blk 108 #11-330", "chronic", 0.63, 0.77,
        60, "1h ago", "Door + PIR", "CASAS ambient",
        "Hasn't left bedroom by 10:00 — 3σ below her routine.",
        "Flag for morning check-in call. Low-urgency welfare follow-up.",
        [
            _f("Bedroom exit", "None by 10:00", 0.44, "typ. 07:30"),
            _f("Bathroom visits", "0 today", 0.22, "typ. 2 by 10:00"),
            _f("Motion variance", "3.1σ low", 0.11),
        ],
    ),
    FixtureRow(
        "r-lim", "Lim Boon Huat", 74, "Blk 115 #03-120", "chronic", 0.44, 0.69,
        40, "40 min ago", "PIR motion", "CASAS ambient",
        "Night bathroom trips up 3× vs baseline this week.",
        "Note trend. Suggest GP review of overnight symptoms at next visit.",
        [
            _f("Nocturnal trips", "6 / night", 0.31, "typ. 2"),
            _f("Sleep fragmentation", "High", 0.09),
            _f("Daytime activity", "Normal", 0.04),
        ],
    ),
    FixtureRow(
        "r-devi", "Devi Nair", 80, "Blk 110 #07-45", "chronic", 0.28, 0.81,
        15, "15 min ago", "Door sensor", "CASAS ambient",
        "Morning routine on track — front door 07:50 as usual.",
        "No action needed.",
        [
            _f("Front door", "07:50 (on time)", 0.0, "typ. 07:45"),
            _f("Kitchen activity", "Normal", 0.0),
        ],
    ),
    FixtureRow(
        "r-goh", "Goh Cheng Watt", 77, "Blk 112 #09-88", "chronic", 0.19, 0.74,
        8, "8 min ago", "PIR motion", "CASAS ambient",
        "All routines within normal range today.",
        "No action needed.",
        [_f("Activity pattern", "Nominal", 0.0)],
    ),
]

INCIDENT_ROW = FixtureRow(
    "r-tan", "Tan Ah Moi", 82, "Blk 108 #04-210", "acute", 0.94, 0.94,
    0, "just now", "Accelerometer", "Wearable bangle",
    "Fall detected — 3.1g impact then 40s no movement, bedroom floor.",
    "CALL NOW. If no response, escalate to MOH 24/7 line + dispatch.",
    [
        _f("Peak impact", "3.1 g", 0.6, "walking < 1.4 g"),
        _f("Post-impact stillness", "40 s", 0.3),
        _f("Orientation", "Horizontal", 0.1),
    ],
)


def _score(r: FixtureRow) -> RiskScore:
    return RiskScore(
        track=r.track, risk=r.risk, confidence=r.confidence,
        updated_at=_iso_min_ago(r.updated_min_ago), recency=r.recency,
        sensor=r.sensor, sensor_class=r.sensor_class, rationale=r.rationale,
    )


def _entry(r: FixtureRow, rank: int) -> CaseloadEntry:
    return CaseloadEntry(id=r.id, name=r.name, age=r.age, unit=r.unit,
                         rank=rank, score=_score(r))


def _detail(r: FixtureRow) -> ResidentDetail:
    d = ResidentDetail(
        id=r.id, name=r.name, age=r.age, unit=r.unit, score=_score(r),
        features=r.features, recommended_action=r.recommended_action, briefing="",
    )
    return d.model_copy(update={"briefing": deterministic_briefing(d)})


def build_ranked_caseload() -> RankedCaseload:
    """Order: acute first, then chronic by risk desc (the ranking rule)."""
    acute = [r for r in RESIDENTS if r.track == "acute"]
    chronic = sorted((r for r in RESIDENTS if r.track != "acute"),
                     key=lambda r: r.risk, reverse=True)
    ordered = acute + chronic
    entries = [_entry(r, i + 1) for i, r in enumerate(ordered)]
    return RankedCaseload(generated_at=_iso_min_ago(0), entries=entries)


def detail_by_id(rid: str) -> ResidentDetail | None:
    for r in [*RESIDENTS, INCIDENT_ROW]:
        if r.id == rid:
            return _detail(r)
    return None


def build_incident_event() -> IncidentEvent:
    return IncidentEvent(
        emitted_at=_iso_min_ago(0),
        entry=_entry(INCIDENT_ROW, 1),
        detail=_detail(INCIDENT_ROW),
    )
