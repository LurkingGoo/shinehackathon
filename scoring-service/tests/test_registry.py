"""ADR 0013 tests — runtime resident registry: keyed-in locations,
operator-registered people, default fallback, persistence.

The registry artifact is redirected to tmp_path so tests never touch the real
data/residents.json; every test ends on the stock roster.
"""
from __future__ import annotations

import json

import pytest
from fastapi.testclient import TestClient

from app.alerts import telegram
from app.data import fixtures
from app.main import app


@pytest.fixture(autouse=True)
def _isolated_registry(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "REGISTRY_PATH", tmp_path / "residents.json")
    yield
    fixtures.clear_incident()
    fixtures.reset_registry()


# ------------------------------ registration ------------------------------- #

def test_register_defaults_zone_when_nothing_keyed_in():
    with TestClient(app) as client:
        entry = client.post("/residents", json={"name": "Judge Judy"}).json()
    assert entry["zone"] == fixtures.DEFAULT_ZONE  # the fallback requirement
    assert entry["name"] == "Judge Judy"
    assert entry["id"] == "r-judge-judy"


def test_registrant_appears_in_caseload_with_honest_confidence():
    with TestClient(app) as client:
        rid = client.post("/residents", json={"name": "Lucas"}).json()["id"]
        entries = client.get("/caseload").json()["entries"]
    mine = next(e for e in entries if e["id"] == rid)
    # day-old baseline → honestly-low confidence, calm risk
    assert mine["score"]["confidence"] < 0.15
    assert mine["score"]["risk"] < 0.4


def test_register_composes_block_and_unit_number():
    with TestClient(app) as client:
        entry = client.post("/residents", json={
            "name": "Amy Tan", "zone": "Study",
            "block": "321", "unitNumber": "10-123",
        }).json()
    assert entry["zone"] == "Study"
    assert entry["unit"] == "Blk 321 #10-123"


def test_register_composes_gps_unit_from_geolocation():
    with TestClient(app) as client:
        entry = client.post("/residents", json={
            "name": "GPS Person", "lat": 1.35213, "lon": 103.81984,
        }).json()
    assert entry["unit"] == "GPS 1.3521, 103.8198"


def test_duplicate_names_get_distinct_ids():
    with TestClient(app) as client:
        a = client.post("/residents", json={"name": "Amy Tan"}).json()["id"]
        b = client.post("/residents", json={"name": "Amy Tan"}).json()["id"]
    assert a != b


def test_blank_name_rejected():
    with TestClient(app) as client:
        assert client.post("/residents", json={"name": "  "}).status_code == 422


# ---------------------------- keyed-in location ---------------------------- #

def test_location_keyed_in_for_default_resident_syncs_to_caseload():
    with TestClient(app) as client:
        res = client.post("/residents/r-devi/location", json={"zone": "Bathroom"})
        assert res.json()["zone"] == "Bathroom"
        entries = client.get("/caseload").json()["entries"]
    assert next(e for e in entries if e["id"] == "r-devi")["zone"] == "Bathroom"


def test_empty_zone_reverts_to_fixture_default():
    with TestClient(app) as client:
        client.post("/residents/r-devi/location", json={"zone": "Bathroom"})
        res = client.post("/residents/r-devi/location", json={"zone": ""})
    assert res.json()["zone"] == "Kitchen"  # r-devi's fixture default


def test_unknown_resident_404s():
    with TestClient(app) as client:
        assert client.post(
            "/residents/r-nobody/location", json={"zone": "X"}
        ).status_code == 404


def test_acute_default_identity_location_can_be_keyed_in():
    fixtures.set_resident_location("r-tan", zone="Bathroom")
    fixtures.mark_incident()
    msg = telegram.format_incident_message(fixtures.build_incident_event())
    assert "last motion: Bathroom" in msg


# ------------------------- alert + detail sync ----------------------------- #

def test_registered_person_named_in_telegram_alert_with_their_zone():
    r = fixtures.register_resident("Judge Judy", zone="Study", block="321",
                                   unit_number="10-123")
    fixtures.set_cv_incident(8.0, 0.7, None, r.id)
    fixtures.mark_incident()
    msg = telegram.format_incident_message(fixtures.build_incident_event())
    assert "Judge Judy" in msg
    assert "last motion: Study" in msg
    assert "Blk 321 #10-123" in msg


def test_detail_carries_zone():
    with TestClient(app) as client:
        rid = client.post("/residents", json={"name": "Zed", "zone": "Balcony"}).json()["id"]
        detail = client.get(f"/residents/{rid}").json()
    assert detail["zone"] == "Balcony"


# -------------------------------- deletion --------------------------------- #

def test_delete_registered_resident_cascades_to_caseload_and_registry():
    with TestClient(app) as client:
        rid = client.post("/residents", json={"name": "Judge Judy"}).json()["id"]
        res = client.delete(f"/residents/{rid}")
        assert res.status_code == 200
        assert res.json() == {"ok": True, "id": rid}
        entries = client.get("/caseload").json()["entries"]
    assert all(e["id"] != rid for e in entries)
    saved = json.loads(fixtures.REGISTRY_PATH.read_text(encoding="utf-8"))
    assert all(p["id"] != rid for p in saved["registered"])


def test_builtin_residents_cannot_be_deleted():
    with TestClient(app) as client:
        assert client.delete("/residents/r-rajoo").status_code == 409
        assert client.delete("/residents/r-tan").status_code == 409  # acute default


def test_delete_unknown_resident_404s():
    with TestClient(app) as client:
        assert client.delete("/residents/r-nobody").status_code == 404


def test_caseload_flags_registrants_as_registered():
    with TestClient(app) as client:
        rid = client.post("/residents", json={"name": "Judge Judy"}).json()["id"]
        entries = client.get("/caseload").json()["entries"]
    by_id = {e["id"]: e for e in entries}
    assert by_id[rid]["registered"] is True
    # fixture rows never claim the flag — the UI must not offer to delete them
    assert not by_id["r-rajoo"].get("registered")


def test_deleting_active_camera_identity_falls_back_to_unidentified():
    """Deletion mid-incident must never leave a dangling name: the incident
    stays active, but its identity reverts to UNIDENTIFIED (fail-open — and
    honest: it must not rename the fall to another real resident either)."""
    r = fixtures.register_resident("Judge Judy", zone="Study")
    fixtures.set_cv_incident(8.0, 0.7, None, r.id)
    fixtures.mark_incident()
    assert fixtures.delete_resident(r.id) == "deleted"
    assert fixtures.incident_active()
    event = fixtures.build_incident_event()
    assert event.entry.id == fixtures.UNIDENTIFIED.id
    msg = telegram.format_incident_message(event)
    assert "Judge Judy" not in msg
    assert "Tan Ah Moi" not in msg
    assert "Unidentified person" in msg


# ------------------------------ persistence -------------------------------- #

def test_registry_survives_reload():
    fixtures.register_resident("Judge Judy", zone="Study")
    fixtures.set_resident_location("r-devi", zone="Bathroom")
    saved = fixtures.REGISTRY_PATH.read_text(encoding="utf-8")
    assert "Judge Judy" in saved

    fixtures.reset_registry()  # simulate a fresh process: stock roster
    assert all(r.name != "Judge Judy" for r in fixtures.CHRONIC)

    fixtures.REGISTRY_PATH.write_text(saved, encoding="utf-8")
    fixtures._load_registry()
    assert any(r.name == "Judge Judy" and r.zone == "Study"
               for r in fixtures.CHRONIC)
    assert next(r for r in fixtures.CHRONIC if r.id == "r-devi").zone == "Bathroom"


def test_corrupt_registry_artifact_never_breaks_startup():
    fixtures.REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    fixtures.REGISTRY_PATH.write_text("{not json", encoding="utf-8")
    fixtures._load_registry()  # must not raise
    assert json.loads('"ok"')  # reachable = no exception above
