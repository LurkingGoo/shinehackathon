"""Contract tests — the entire risk surface of the seam, drift-guarded.

Three layers:
  1. Live responses validate against contract.schema.json (generated from the
     models) — structural conformance, no hand-maintained key lists.
  2. The on-disk schema is current with the models — no stale artifact.
  3. The models' fields match triage-dashboard/lib/types.ts exactly — the actual
     TS<->Python drift catcher, dependency-free.
Plus behavioural checks (ordering, distinct axes, 404, briefing guardrail).
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import jsonschema
from fastapi.testclient import TestClient

from app import models
from app.contract import PAYLOAD_MODELS, SCHEMA_PATH, contract_schema
from app.main import app

client = TestClient(app)
SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))["payloads"]

TYPES_TS = (
    Path(__file__).resolve().parents[2] / "triage-dashboard" / "lib" / "types.ts"
)

# Which pydantic model mirrors which TS interface.
MODEL_FOR_INTERFACE = {
    "Resident": models.Resident,
    "RiskFeature": models.RiskFeature,
    "RiskScore": models.RiskScore,
    "CaseloadEntry": models.CaseloadEntry,
    "RankedCaseload": models.RankedCaseload,
    "ResidentDetail": models.ResidentDetail,
    "IncidentEvent": models.IncidentEvent,
}


# ----------------------------- layer 1: schema ---------------------------- #
def test_caseload_matches_schema():
    r = client.get("/caseload")
    assert r.status_code == 200
    jsonschema.validate(r.json(), SCHEMA["RankedCaseload"])


def test_resident_detail_matches_schema():
    r = client.get("/residents/r-rajoo")
    assert r.status_code == 200
    jsonschema.validate(r.json(), SCHEMA["ResidentDetail"])


def test_incident_matches_schema():
    r = client.post("/incidents/simulate")
    assert r.status_code == 200
    jsonschema.validate(r.json(), SCHEMA["IncidentEvent"])


# ----------------------- layer 2: artifact is current --------------------- #
def test_committed_schema_is_current():
    """contract.schema.json must equal what the models emit — regenerate with
    `python -m app.contract` after any model change."""
    on_disk = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert on_disk == contract_schema(), "contract.schema.json is stale — run: python -m app.contract"


# --------------------- layer 3: models <-> types.ts ----------------------- #
def _parse_ts_interfaces(src: str) -> dict[str, set[str]]:
    """Extract {interface: {fields}} from types.ts, resolving `extends`.
    Interfaces are flat (no nested braces), so a non-greedy body match is safe."""
    raw: dict[str, tuple[str | None, set[str]]] = {}
    for m in re.finditer(
        r"export\s+interface\s+(\w+)(?:\s+extends\s+(\w+))?\s*\{(.*?)\}",
        src,
        re.DOTALL,
    ):
        name, parent, body = m.group(1), m.group(2), m.group(3)
        fields = set(re.findall(r"^\s*(\w+)\??\s*:", body, re.MULTILINE))
        raw[name] = (parent, fields)

    def resolve(name: str) -> set[str]:
        parent, fields = raw[name]
        return fields | (resolve(parent) if parent in raw else set())

    return {name: resolve(name) for name in raw}


def test_models_match_types_ts():
    if not TYPES_TS.exists():
        import pytest

        pytest.skip("frontend types.ts not present (standalone service checkout)")
    interfaces = _parse_ts_interfaces(TYPES_TS.read_text(encoding="utf-8"))
    for iface, model in MODEL_FOR_INTERFACE.items():
        assert iface in interfaces, f"types.ts lost interface {iface}"
        ts_fields = interfaces[iface]
        py_fields = set(model.model_json_schema(by_alias=True)["properties"])
        assert py_fields == ts_fields, (
            f"{iface}: model {sorted(py_fields)} != types.ts {sorted(ts_fields)}"
        )


def test_all_payload_models_are_checked():
    # Guard the guard: every served payload is covered by the TS parity check.
    assert set(PAYLOAD_MODELS).issubset(MODEL_FOR_INTERFACE)


# --------------------------- behaviour (not shape) ------------------------ #
def test_caseload_ordering_acute_first_then_risk_desc():
    entries = client.get("/caseload").json()["entries"]
    assert entries
    for i, e in enumerate(entries):
        assert e["rank"] == i + 1
    tracks = [e["score"]["track"] for e in entries]
    assert tracks == sorted(tracks, key=lambda t: t != "acute")
    chronic = [e["score"]["risk"] for e in entries if e["score"]["track"] == "chronic"]
    assert chronic == sorted(chronic, reverse=True)


def test_unknown_resident_404():
    assert client.get("/residents/nope").status_code == 404


def test_risk_and_confidence_are_distinct_axes():
    body = client.get("/residents/r-rajoo").json()
    assert body["score"]["risk"] != body["score"]["confidence"]


def test_briefing_invents_no_numbers_absent_from_features():
    body = client.get("/residents/r-rajoo").json()
    nums = lambda s: set(re.findall(r"\d+", s))
    feature_nums: set[str] = set()
    for f in body["features"]:
        feature_nums |= nums(f["value"]) | nums(f["baseline"])
    feature_nums |= nums(str(round(body["score"]["confidence"] * 100)))
    feature_nums |= nums(str(body["age"]))
    assert nums(body["briefing"]) <= feature_nums
