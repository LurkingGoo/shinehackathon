"""Contract tests — the entire risk surface of the seam.

Assert the JSON the service returns matches triage-dashboard/lib/types.ts:
exact keys (camelCase), separate risk/confidence axes, acute-first ordering,
404 on unknown resident, and the briefing-invents-nothing guardrail.
"""
from __future__ import annotations

import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

CASELOAD_ENTRY_KEYS = {"id", "name", "age", "unit", "rank", "score"}
SCORE_KEYS = {
    "track", "risk", "confidence", "updatedAt", "recency",
    "sensor", "sensorClass", "rationale",
}
DETAIL_KEYS = {
    "id", "name", "age", "unit", "score",
    "features", "recommendedAction", "briefing",
}
FEATURE_KEYS = {"label", "value", "weight", "baseline"}


def test_caseload_shape_and_ordering():
    r = client.get("/caseload")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"generatedAt", "entries"}
    entries = body["entries"]
    assert entries, "caseload must not be empty"

    for i, e in enumerate(entries):
        assert set(e) == CASELOAD_ENTRY_KEYS
        assert set(e["score"]) == SCORE_KEYS
        assert e["rank"] == i + 1
        assert 0.0 <= e["score"]["risk"] <= 1.0
        assert 0.0 <= e["score"]["confidence"] <= 1.0

    # acute-first, then chronic by risk desc
    tracks = [e["score"]["track"] for e in entries]
    assert tracks == sorted(tracks, key=lambda t: t != "acute")
    chronic = [e["score"]["risk"] for e in entries if e["score"]["track"] == "chronic"]
    assert chronic == sorted(chronic, reverse=True)


def test_resident_detail_shape():
    r = client.get("/residents/r-rajoo")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == DETAIL_KEYS
    assert set(body["score"]) == SCORE_KEYS
    for f in body["features"]:
        assert set(f) == FEATURE_KEYS


def test_unknown_resident_404():
    assert client.get("/residents/nope").status_code == 404


def test_risk_and_confidence_are_distinct_axes():
    # A resident where the two axes genuinely differ proves they aren't conflated.
    body = client.get("/residents/r-rajoo").json()
    assert body["score"]["risk"] != body["score"]["confidence"]


def test_briefing_invents_no_numbers_absent_from_features():
    """The LLM guardrail as a test: every number in the briefing must appear in
    the features (the deterministic briefing already honours this)."""
    body = client.get("/residents/r-rajoo").json()
    nums = lambda s: set(re.findall(r"\d+", s))
    feature_nums = set()
    for f in body["features"]:
        feature_nums |= nums(f["value"]) | nums(f["baseline"])
    # confidence % is derived from score.confidence, allow it explicitly
    feature_nums |= nums(str(round(body["score"]["confidence"] * 100)))
    feature_nums |= nums(str(body["age"]))
    assert nums(body["briefing"]) <= feature_nums


def test_incident_event_shape():
    r = client.post("/incidents/simulate")
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "incident"
    assert body["event"] == "acute-detected"
    assert set(body["entry"]) == CASELOAD_ENTRY_KEYS
    assert set(body["detail"]) == DETAIL_KEYS
    assert body["entry"]["score"]["track"] == "acute"
