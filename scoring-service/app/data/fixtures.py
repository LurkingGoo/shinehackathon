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
    RiskFeature,
    RiskScore,
)
from app.scoring import pipeline, rationale
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
    # Last-motion area from the ambient track (ADR 0012) — alert context,
    # consistent with the resident's chronic features shown on their row.
    zone: str = "Living room"


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
        zone="Bedroom",
    ),
    ChronicResident(
        "r-wong", "Wong Lai Keng", 85, "Blk 108 #11-330", "Door + PIR",
        "CASAS ambient", 60, "1h ago", days_of_history=30, data_quality=0.77,
        inputs=[
            CFI("Bedroom exit", "not seen by 10:00", 0.44, "typ. 07:30", anomaly=0.72),
            CFI("Bathroom visits", "0 today", 0.22, "typ. 2 by 10:00", anomaly=0.55),
            CFI("Motion variance", "3.1σ low", 0.11, anomaly=0.6),
        ],
        zone="Bedroom",
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
        zone="Bedroom",
    ),
    ChronicResident(
        "r-devi", "Devi Nair", 80, "Blk 110 #07-45", "Door sensor",
        "CASAS ambient", 15, "15 min ago", days_of_history=45, data_quality=0.81,
        inputs=[
            CFI("Front door", "07:50 (on time)", 0.0, "typ. 07:45", anomaly=0.0),
            CFI("Kitchen activity", "Normal", 0.0, anomaly=0.0),
        ],
        zone="Kitchen",
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
    clear_cv_incident()  # a real accelerometer trace supersedes any camera override


# --- Camera / pose fall track (the /watch stretch) -------------------------- #
# When set, the acute row is presented from a browser VISION heuristic instead
# of the accelerometer pipeline. Honest by construction: rule-based, so the
# confidence is the browser's estimate (not the calibrated 96% detector) and
# there is no accelerometer waveform to drill into.
_cv_override: dict | None = None


# Enrolled-identity carry (ADR 0011): a camera incident may NAME the resident.
# Resolved here, fail-open — an unknown/absent id keeps the default identity.
_cv_resident = None  # AcuteResident | None

# Skeleton replay (ADR 0017). PRIVACY INVARIANT: the landmark trace lives in
# these module globals ONLY — exactly as long as the incident. It must never
# be written to disk, the registry artifact, or logs, and never enter a
# Telegram dispatch (until the explicit keyframe phase). The nonce
# (_cv_incident_id) is what a stale upload is rejected against.
_cv_counter: int = 0
_cv_incident_id: str | None = None
_replay: dict | None = None


def set_cv_incident(stillness_s: float = 8.0, confidence: float = 0.7,
                    note: str | None = None,
                    resident_id: str | None = None) -> None:
    global _cv_override, _cv_resident, _cv_counter, _cv_incident_id, _replay
    _cv_counter += 1
    _cv_incident_id = f"cv-{_cv_counter}"
    _replay = None  # a new incident never inherits a previous fall's trace
    conf = float(np.clip(confidence, 0.0, 1.0))
    still = max(0.0, float(stillness_s))
    _cv_override = {
        "sensor": "Camera (pose)",
        "sensor_class": "Vision — browser pose heuristic",
        "confidence": conf,
        "stillness_s": still,
        "rationale": note or f"Camera: upright → horizontal, still {still:.0f}s",
    }
    _cv_resident = _resolve_cv_resident(resident_id)


def current_cv_incident_id() -> str | None:
    """The active camera incident's nonce (None while calm / accelerometer)."""
    return _cv_incident_id if _cv_override is not None else None


def set_replay(incident_id: str, fps: float, quant_scale: int,
               frames: list, facts: dict | None = None) -> str:
    """Attach the browser's landmark trace to the active camera incident.
    Returns 'stored', 'stale' (nonce mismatch — the buffer belongs to a
    superseded incident and must be dropped, never retried) or 'no-incident'
    (calm, TTL-expired, or an accelerometer incident)."""
    global _replay
    if not incident_active() or _cv_override is None:
        return "no-incident"
    if incident_id != _cv_incident_id:
        return "stale"
    _replay = {
        "incidentId": incident_id,
        "fps": fps,
        "quantScale": quant_scale,
        "frames": frames,
        "facts": facts,
        "receivedAt": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    }
    _apply_replay_facts(facts)
    return "stored"


_DIRECTION_WORDS = {
    "left": "leftward", "right": "rightward", "toward-camera": "toward the camera",
}


def _apply_replay_facts(facts: dict | None) -> None:
    """Fold browser-computed replay facts (ADR 0017 phase 2) into the active
    camera incident's DETERMINISTIC rationale, and stage matching feature
    rows — every number the rationale states must trace to a feature
    (feature-spec §0/§3, briefing guardrail). Deliberately NO SSE republish:
    a second acute-detected frame would read as a new incident; the enriched
    incident surfaces through the read-through /caseload + drilldown, and
    the escalation message picks it up naturally."""
    if not facts or _cv_override is None:
        return
    frags: list[str] = []
    feats: list[tuple[str, str, float]] = []
    word = _DIRECTION_WORDS.get(facts.get("direction") or "")
    if word:
        frags.append(f"fell {word}")
        feats.append(("Fall direction", word, 0.15))
    dur = facts.get("descentDurationMs")
    if isinstance(dur, (int, float)) and dur > 0:
        s = dur / 1000.0
        frags.append(f"{s:.1f}s descent")
        feats.append(("Descent", f"{s:.1f}s", 0.15))
    pa = facts.get("protectiveArm")
    if pa is True:
        frags.append("arms broke the fall")
        feats.append(("Protective response", "arms came out", 0.1))
    elif pa is False:
        frags.append("no arm protection")
        feats.append(("Protective response", "none seen", 0.1))
    if not frags:
        return  # nothing usable — the default template stands, honestly
    still = _cv_override["stillness_s"]
    _cv_override["rationale"] = (
        f"Camera: {', '.join(frags)}; still {still:.0f}s after impact"
    )
    _cv_override["replay_features"] = feats


def replay_payload() -> dict | None:
    """The stored replay, or None when calm / accelerometer incident /
    not yet uploaded (the endpoint 404s — mirrors acute_trace_payload)."""
    if not incident_active() or _cv_override is None or _replay is None:
        return None
    return _replay


def _resolve_cv_resident(resident_id: str | None):
    """Map an enrolled residentId onto the roster. Fail open: None or an
    unknown id resolves to the default acute identity (ACUTE)."""
    if not resident_id or resident_id == ACUTE.id:
        return None
    for r in CHRONIC:
        if r.id == resident_id:
            return AcuteResident(
                id=r.id, name=r.name, age=r.age, unit=r.unit,
                sensor="Camera (pose)", sensor_class="Vision — browser pose heuristic",
                updated_min_ago=0, recency="just now", zone=r.zone,
            )
    return None


def acute_identity():
    """Who the active acute row belongs to: the camera-named resident while a
    named camera incident is active, else the default (r-tan)."""
    return _cv_resident if (_cv_override is not None and _cv_resident) else ACUTE


def clear_cv_incident() -> None:
    global _cv_override, _cv_resident, _cv_incident_id, _replay
    _cv_override = None
    _cv_resident = None
    _cv_incident_id = None
    _replay = None  # retention claim: the trace dies with the incident


def _cv_score() -> tuple[RiskScore, list, str, str]:
    """Present the active camera incident as the acute row. Risk is top (a
    detected fall is priority regardless of modality); confidence is the honest
    heuristic estimate; the recommended action is the SAME acute escalation."""
    ov = _cv_override
    feats = [
        RiskFeature(label="Posture", value="upright → horizontal", weight=0.6,
                    baseline="standing / seated"),
        RiskFeature(label="Stillness", value=f"{ov['stillness_s']:.0f}s no movement",
                    weight=0.4, baseline="< 2s normal"),
    ]
    # Replay facts (ADR 0017 phase 2): the rows behind the enriched rationale
    # — every number it states appears here, keeping the briefing guardrail.
    for label, value, weight in ov.get("replay_features", []):
        feats.append(RiskFeature(label=label, value=value, weight=weight, baseline=""))
    action = rationale.recommend_action("acute", "Pose", 1.0)
    score = RiskScore(
        track="acute", risk=1.0, confidence=ov["confidence"],
        updated_at=_iso_min_ago(ACUTE.updated_min_ago), recency=ACUTE.recency,
        sensor=ov["sensor"], sensor_class=ov["sensor_class"], rationale=ov["rationale"],
    )
    return score, feats, action, ov["rationale"]


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
    zone: str = "Living room"


ACUTE = AcuteResident(
    "r-tan", "Tan Ah Moi", 82, "Blk 108 #04-210", "Accelerometer",
    "Wearable bangle", 0, "just now", zone="Living room",
)


# ------------------ runtime resident registry (ADR 0013) ------------------- #
DEFAULT_ZONE = "Living room"
REGISTRY_PATH = Path(__file__).resolve().parents[2] / "data" / "residents.json"

# Fixture locations snapshotted before any keyed-in override, so an empty
# keyed-in zone reverts to the resident's own default.
_DEFAULT_LOCATIONS: dict[str, tuple[str, str]] = {
    r.id: (r.unit, r.zone) for r in [*CHRONIC, ACUTE]
}
_registered_ids: list[str] = []


def _roster() -> list:
    return [*CHRONIC, ACUTE]


def compose_unit(unit: str | None = None, block: str | None = None,
                 unit_number: str | None = None, lat: float | None = None,
                 lon: float | None = None) -> str | None:
    """The address string from whichever parts were keyed in; None when none
    were. GPS is the browser-geolocation form — raw coordinates, honestly
    unresolved (no reverse geocoding: the demo runs offline)."""
    if unit:
        return unit
    if block and unit_number:
        return f"Blk {block} #{unit_number}"
    if block:
        return f"Blk {block}"
    if lat is not None and lon is not None:
        return f"GPS {lat:.4f}, {lon:.4f}"
    return None


def _slug_id(name: str) -> str:
    s = "-".join("".join(c if c.isalnum() else " " for c in name.lower()).split())
    base = f"r-{s or 'resident'}"
    rid, n, ids = base, 2, {r.id for r in _roster()}
    while rid in ids:
        rid, n = f"{base}-{n}", n + 1
    return rid


def _make_registrant(rid: str, name: str, age: int, unit: str | None,
                     zone: str | None) -> ChronicResident:
    # Nominal inputs through the real pipeline: calm risk, and confidence is
    # honestly low because a day-old baseline IS immature (chronic.py
    # baseline_maturity — low confidence here is the truth, not a bug).
    return ChronicResident(
        rid, name, age, unit or "Address not set",
        "PIR motion", "CASAS ambient (just registered)", 0, "just now",
        days_of_history=1, data_quality=0.6,
        inputs=[CFI("Activity pattern", "Nominal (new baseline)", 0.0, anomaly=0.0)],
        zone=zone or DEFAULT_ZONE,
    )


def register_resident(name: str, age: int | None = None, zone: str | None = None,
                      unit: str | None = None, block: str | None = None,
                      unit_number: str | None = None, lat: float | None = None,
                      lon: float | None = None) -> ChronicResident:
    """Operator-registered person (ADR 0013): joins the chronic roster, so the
    caseload, drilldown, Report-as/Enroll-as selectors, camera identity carry
    and the Telegram alert all pick them up. Zone falls back to DEFAULT_ZONE."""
    r = _make_registrant(
        _slug_id(name), name, int(age) if age else 70,
        compose_unit(unit, block, unit_number, lat, lon), zone,
    )
    CHRONIC.append(r)
    _registered_ids.append(r.id)
    _save_registry()
    return r


def set_resident_location(rid: str, zone: str | None = None, unit: str | None = None,
                          block: str | None = None, unit_number: str | None = None,
                          lat: float | None = None, lon: float | None = None):
    """Key in a location for any roster resident (chronic or acute). Fields not
    keyed in stay untouched; zone='' reverts to the fixture default. Returns
    the updated resident, or None for an unknown id."""
    for r in _roster():
        if r.id != rid:
            continue
        if zone == "":
            r.zone = _DEFAULT_LOCATIONS.get(rid, ("", DEFAULT_ZONE))[1]
        elif zone is not None:
            r.zone = zone
        new_unit = compose_unit(unit, block, unit_number, lat, lon)
        if new_unit:
            r.unit = new_unit
        _save_registry()
        return r
    return None


def is_registered(rid: str) -> bool:
    return rid in _registered_ids


def delete_resident(rid: str) -> str:
    """Remove a runtime registrant (ADR 0014). Returns 'deleted', 'builtin'
    (fixture roster rows are demo narrative — not deletable) or 'unknown'.
    Cascade: roster, persistence artifact, and — if they are the active
    camera-named acute identity — the incident KEEPS running but reverts to
    the generic default, so no alert surface ever carries a deleted name."""
    global _cv_resident
    if rid not in _registered_ids:
        return "builtin" if any(r.id == rid for r in _roster()) else "unknown"
    CHRONIC[:] = [r for r in CHRONIC if r.id != rid]
    _registered_ids.remove(rid)
    if _cv_resident is not None and _cv_resident.id == rid:
        _cv_resident = None
    _save_registry()
    return "deleted"


def reset_registry() -> None:
    """Back to the stock roster: drop registrants, restore fixture locations,
    remove the persistence artifact. Deliberately NOT part of /incidents/clear
    — that resets the incident beat, not the roster."""
    global _registered_ids
    drop = set(_registered_ids)
    CHRONIC[:] = [r for r in CHRONIC if r.id not in drop]
    _registered_ids = []
    for r in _roster():
        if r.id in _DEFAULT_LOCATIONS:
            r.unit, r.zone = _DEFAULT_LOCATIONS[r.id]
    if REGISTRY_PATH.exists():
        REGISTRY_PATH.unlink()


def _save_registry() -> None:
    registered = [
        {"id": r.id, "name": r.name, "age": r.age, "unit": r.unit, "zone": r.zone}
        for r in CHRONIC if r.id in set(_registered_ids)
    ]
    overrides = {}
    for r in _roster():
        default = _DEFAULT_LOCATIONS.get(r.id)
        if default and (r.unit, r.zone) != default:
            overrides[r.id] = {"unit": r.unit, "zone": r.zone}
    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_PATH.write_text(
        json.dumps({"registered": registered, "overrides": overrides}, indent=2),
        encoding="utf-8",
    )


def _load_registry() -> None:
    """Rehydrate registrants + keyed-in locations across service restarts
    (the rehearsal ritual restarts both services). A missing or corrupt
    artifact must never break startup — the stock roster stands."""
    if not REGISTRY_PATH.exists():
        return
    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return
    ids = {r.id for r in _roster()}
    for p in data.get("registered", []):
        rid = p.get("id")
        if not rid or rid in ids:
            continue
        CHRONIC.append(_make_registrant(
            rid, p.get("name", rid), int(p.get("age", 70)),
            p.get("unit"), p.get("zone"),
        ))
        _registered_ids.append(rid)
        ids.add(rid)
    for rid, loc in data.get("overrides", {}).items():
        for r in _roster():
            if r.id == rid:
                r.zone = loc.get("zone") or r.zone
                r.unit = loc.get("unit") or r.unit


_load_registry()


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
    if _cv_override is not None:  # camera/pose incident supersedes the accel path
        return _cv_score()
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
                         rank=rank, score=score, zone=r.zone,
                         registered=is_registered(r.id) or None)


def _chronic_detail(r: ChronicResident) -> ResidentDetail:
    score, feats, action, _r = _chronic_score(r)
    d = ResidentDetail(id=r.id, name=r.name, age=r.age, unit=r.unit, score=score,
                       features=feats, recommended_action=action, briefing="",
                       zone=r.zone)
    return d.model_copy(update={"briefing": deterministic_briefing(d)})


def _acute_entry(rank: int) -> CaseloadEntry:
    who = acute_identity()
    score, _f, _a, _r = _acute_score()
    return CaseloadEntry(id=who.id, name=who.name, age=who.age,
                         unit=who.unit, rank=rank, score=score, zone=who.zone)


def _acute_detail() -> ResidentDetail:
    who = acute_identity()
    score, feats, action, _r = _acute_score()
    d = ResidentDetail(id=who.id, name=who.name, age=who.age, unit=who.unit,
                       score=score, features=feats, recommended_action=action,
                       briefing="", zone=who.zone)
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
    clear_cv_incident()


def incident_active() -> bool:
    return (_incident_at is not None
            and (datetime.now(timezone.utc) - _incident_at).total_seconds()
            < INCIDENT_TTL_S)


def build_ranked_caseload() -> RankedCaseload:
    """Order: acute first (while an incident is active), then chronic by
    COMPUTED risk desc (the ranking rule)."""
    offset = 1 if incident_active() else 0
    # A camera-named resident moves to the acute row — drop their chronic row
    # so they never appear twice (ADR 0011 identity carry).
    acute_id = acute_identity().id if offset else None
    roster = [r for r in CHRONIC if r.id != acute_id]
    ranked = sorted(roster, key=lambda r: _chronic_score(r)[0].risk, reverse=True)
    entries = [_chronic_entry(r, i + 1 + offset) for i, r in enumerate(ranked)]
    if offset:
        entries.insert(0, _acute_entry(1))
    return RankedCaseload(generated_at=_iso_min_ago(0), entries=entries)


def detail_by_id(rid: str) -> ResidentDetail | None:
    # The active acute identity (default r-tan, or the camera-named resident)
    # serves the acute detail; everyone else serves their chronic detail.
    if rid == acute_identity().id and (rid == ACUTE.id or incident_active()):
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

    if not incident_active() or _cv_override is not None:
        return None  # camera incidents have no accelerometer waveform to drill
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
