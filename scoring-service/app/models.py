"""Pydantic models — MUST serialize to triage-dashboard/lib/types.ts EXACTLY.

Fields are snake_case in Python; a camelCase alias generator makes the JSON keys
match the TS contract (updatedAt, sensorClass, recommendedAction, ...). FastAPI
serializes responses by alias by default, so output keys are camelCase.
This is the entire risk surface of the seam — guarded by tests/test_contract.py.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Track = Literal["acute", "chronic"]


class _Base(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)


class Resident(_Base):
    id: str
    name: str
    age: int
    unit: str


class RiskFeature(_Base):
    label: str
    value: str
    weight: float
    baseline: str = ""


class RiskScore(_Base):
    track: Track
    risk: float
    confidence: float
    updated_at: str
    recency: str
    sensor: str
    sensor_class: str
    rationale: str


class CaseloadEntry(Resident):
    score: RiskScore
    rank: int
    # Last-motion area from the resident's ambient (PIR/door) track — alert
    # context, not a camera localization claim (ADR 0012). Optional: additive
    # to the contract, absent for consumers that predate it.
    zone: str | None = None


class RankedCaseload(_Base):
    generated_at: str
    entries: list[CaseloadEntry]


class ResidentDetail(Resident):
    score: RiskScore
    features: list[RiskFeature]
    recommended_action: str
    briefing: str
    # Same ambient last-motion area as CaseloadEntry.zone (ADR 0013), so the
    # drilldown can render a keyed-in location. Optional: additive.
    zone: str | None = None


class IncidentEvent(_Base):
    type: Literal["incident"] = "incident"
    event: Literal["acute-detected"] = "acute-detected"
    emitted_at: str
    entry: CaseloadEntry
    detail: ResidentDetail
