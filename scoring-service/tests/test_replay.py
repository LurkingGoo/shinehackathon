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


# ------------------------ facts → rationale (phase 2) ---------------------- #

def _upload_with_facts(client, iid, facts):
    return client.post("/incidents/replay", json={
        "incidentId": iid, "fps": 10.0, "quantScale": 1000, "frames": FRAMES,
        "facts": facts,
    })


def test_facts_enrich_rationale_and_features():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        r = _upload_with_facts(c, iid, {
            "descentDurationMs": 1900, "direction": "right",
            "protectiveArm": False, "postImpactMovement": "none",
        })
        assert r.status_code == 200
        top = c.get("/caseload").json()["entries"][0]
        rationale = top["score"]["rationale"]
        assert "rightward" in rationale
        assert "1.9" in rationale
        assert "no arm protection" in rationale
        detail = c.get(f"/residents/{top['id']}").json()
        by_label = {f["label"]: f["value"] for f in detail["features"]}
        # briefing guardrail: every rationale number traces to a feature value
        assert by_label["Descent"] == "1.9s"
        assert by_label["Fall direction"] == "rightward"
        assert by_label["Protective response"] == "none seen"


def test_partial_facts_compose_partially():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload_with_facts(c, iid, {"direction": "left"})
        rationale = c.get("/caseload").json()["entries"][0]["score"]["rationale"]
        assert "leftward" in rationale
        assert "descent" not in rationale
        assert "arm" not in rationale


def test_unknown_facts_leave_rationale_unchanged():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        before = c.get("/caseload").json()["entries"][0]["score"]["rationale"]
        _upload_with_facts(c, iid, {
            "descentDurationMs": None, "direction": "unknown",
            "protectiveArm": None, "postImpactMovement": "unknown",
        })
        after = c.get("/caseload").json()["entries"][0]["score"]["rationale"]
        assert after == before  # nothing usable → the honest default stands


def test_no_facts_upload_leaves_rationale_unchanged():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        before = c.get("/caseload").json()["entries"][0]["score"]["rationale"]
        _upload(c, iid)
        assert c.get("/caseload").json()["entries"][0]["score"]["rationale"] == before


def test_enriched_features_die_with_the_incident():
    with TestClient(app) as c:
        iid = _fire_cv(c)
        _upload_with_facts(c, iid, {"direction": "right", "descentDurationMs": 1900})
        c.post("/incidents/clear")
        _fire_cv(c)  # fresh incident must NOT inherit the enrichment
        rationale = c.get("/caseload").json()["entries"][0]["score"]["rationale"]
        assert "rightward" not in rationale


# --------------------- GIF follow-up (phase 5) ----------------------------- #

def _moving_frames(n: int = 12) -> list[list[int]]:
    """Rows with 13 joints drifting across the frame — enough to draw."""
    rows = []
    for i in range(n):
        row = [i * 100]
        for _j in range(13):
            row += [300 + i * 20, 400 + i * 10, 90]
        rows.append(row)
    return rows


def test_render_replay_gif_produces_an_animated_gif():
    from app.alerts import replay_render
    gif = replay_render.render_replay_gif(_moving_frames(), 1000)
    assert gif is not None
    assert gif[:6] in (b"GIF87a", b"GIF89a")
    assert len(gif) > 500  # more than a single trivial frame


def test_render_replay_gif_refuses_undrawable_buffers():
    from app.alerts import replay_render
    assert replay_render.render_replay_gif([[0], [100]], 1000) is None  # all gaps
    assert replay_render.render_replay_gif(_moving_frames(1), 1000) is None  # 1 frame


def test_multipart_body_is_wellformed():
    body, boundary = telegram._multipart_body(
        {"chat_id": "999", "caption": "hi"},
        "animation", "fall-replay.gif", b"GIFDATA", "image/gif",
    )
    assert boundary.encode() in body
    assert b'name="chat_id"' in body and b"999" in body
    assert b'filename="fall-replay.gif"' in body
    assert b"Content-Type: image/gif" in body
    assert b"GIFDATA" in body
    assert body.endswith(f"--{boundary}--\r\n".encode())


def test_send_replay_animation_noop_unconfigured(monkeypatch):
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    assert telegram.send_replay_animation(b"GIF89a....", "cap") is False


def test_upload_dispatches_animation_when_configured(monkeypatch):
    """The follow-up fires off-thread after a stored upload — assert the
    render+send path is invoked with the stored frames, without a network."""
    sent: dict = {}
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    monkeypatch.setattr(
        telegram, "send_replay_animation",
        lambda gif, caption: sent.update(gif=gif, caption=caption) or True,
    )
    with TestClient(app) as c:
        iid = _fire_cv(c)
        assert _upload(c, iid, frames=_moving_frames()).status_code == 200
        deadline = __import__("time").monotonic() + 5
        while not sent and __import__("time").monotonic() < deadline:
            __import__("time").sleep(0.05)
    assert sent, "animation follow-up never dispatched"
    assert sent["gif"][:6] in (b"GIF87a", b"GIF89a")
    assert "no pixels" in sent["caption"]


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
