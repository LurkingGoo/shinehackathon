"""ADR 0017 tests — skeleton replay upload lifecycle (phase 1).

The replay is landmark COORDINATES only, attached to the active camera
incident by a per-incident nonce, living exactly as long as the incident:
cleared on reset, superseded by any new incident (camera or accelerometer),
dead on TTL, and never persisted to disk.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.alerts import telegram
from app.data import fixtures
from app.main import app

# 20 frames × (1 timestamp + 13 joints × 3 ints) = 40 ints per frame
FRAMES = [[i * 100] + [500] * 39 for i in range(20)]


@pytest.fixture(autouse=True)
def _clean(tmp_path, monkeypatch):
    monkeypatch.setattr(fixtures, "REGISTRY_PATH", tmp_path / "residents.json")
    yield
    fixtures.clear_incident()
    fixtures.reset_registry()
    telegram.clear_ack()


def _fire_cv(client) -> str:
    r = client.post("/incidents/cv-detected", json={"stillnessS": 8.0})
    assert r.status_code == 200
    iid = r.headers.get("x-incident-id")
    assert iid
    return iid


def _upload(client, iid, frames=FRAMES):
    return client.post("/incidents/replay", json={
        "incidentId": iid, "fps": 10.0, "quantScale": 1000, "frames": frames,
    })


# ------------------------------ happy path --------------------------------- #

def test_upload_and_fetch_happy_path():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        up = _upload(c, iid)
        assert up.status_code == 200
        assert up.json() == {"ok": True, "incidentId": iid, "frames": len(FRAMES)}
        got = c.get("/incidents/replay")
        assert got.status_code == 200
        body = got.json()
        assert body["incidentId"] == iid
        assert body["frames"] == FRAMES
        assert body["fps"] == 10.0
        assert body["receivedAt"]


# ----------------------------- 404 conditions ------------------------------ #

def test_upload_404_while_calm():
    with TestClient(app) as c:
        assert _upload(c, "cv-1").status_code == 404


def test_upload_404_for_accelerometer_incident():
    with TestClient(app) as c:
        c.post("/incidents/simulate")
        assert _upload(c, "cv-1").status_code == 404


def test_get_404_while_calm_and_for_accel_and_before_upload():
    with TestClient(app) as c:
        assert c.get("/incidents/replay").status_code == 404  # calm
        c.post("/incidents/simulate")
        assert c.get("/incidents/replay").status_code == 404  # accelerometer
        fixtures.clear_incident()
        _fire_cv(c)
        assert c.get("/incidents/replay").status_code == 404  # not yet uploaded


# ----------------------------- stale guard --------------------------------- #

def test_stale_replay_409_and_never_attaches():
    with TestClient(app) as c:
        iid_a = _fire_cv(c)
        iid_b = _fire_cv(c)  # a second fall supersedes the first
        assert iid_a != iid_b
        assert _upload(c, iid_a).status_code == 409
        assert c.get("/incidents/replay").status_code == 404


# ------------------------------- lifecycle --------------------------------- #

def test_clear_incident_drops_replay():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
        c.post("/incidents/clear")
        assert c.get("/incidents/replay").status_code == 404


def test_new_camera_incident_drops_previous_replay():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
        _fire_cv(c)  # fresh incident must not inherit the old fall's trace
        assert c.get("/incidents/replay").status_code == 404


def test_accelerometer_supersede_drops_replay():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
        c.post("/incidents/simulate")  # set_acute_trace → clear_cv_incident
        assert c.get("/incidents/replay").status_code == 404
        assert c.get("/incidents/trace").status_code == 200  # accel drills its own signal


def test_ttl_expiry_kills_both_replay_paths():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
        fixtures._incident_at = datetime.now(timezone.utc) - timedelta(minutes=31)
        assert _upload(c, iid).status_code == 404
        assert c.get("/incidents/replay").status_code == 404


# ------------------------------ size limits -------------------------------- #

def test_oversize_replay_rejected():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        too_many = [[i] + [1] * 39 for i in range(201)]
        assert _upload(c, iid, frames=too_many).status_code == 422
        fat_frame = [[0] + [1] * 99]
        assert _upload(c, iid, frames=fat_frame).status_code == 422


# ---------------------------- privacy retention ---------------------------- #

def test_replay_never_persisted_to_disk():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
    # module state only: the registry artifact was never even created
    assert not fixtures.REGISTRY_PATH.exists()


# --------------------------- orthogonal paths ------------------------------ #

def test_replay_follows_incident_not_the_name():
    """Deleting the named resident mid-incident reverts identity (ADR 0014)
    but the replay belongs to the INCIDENT (nonce) and must survive."""
    with TestClient(app) as c:
        rid = c.post("/residents", json={"name": "Judge Judy"}).json()["id"]
        r = c.post("/incidents/cv-detected", json={"residentId": rid})
        iid = r.headers["x-incident-id"]
        _upload(c, iid)
        assert c.delete(f"/residents/{rid}").status_code == 200
        assert c.get("/incidents/replay").status_code == 200


def test_escalate_and_ack_unaffected_by_replay():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload(c, iid)
        assert c.post("/incidents/escalate", json={"stillDownS": 45}).status_code == 200
        assert c.post("/alerts/ack").status_code == 200
