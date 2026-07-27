"""ADR 0012 tests — long-lie escalation, acknowledgement, zone context.

Network fully mocked; the ack poller is disabled suite-wide (conftest).
"""
from __future__ import annotations

import threading
from unittest import mock

from fastapi.testclient import TestClient

from app.alerts import telegram
from app.data import fixtures
from app.main import app


def _named_event(rid: str = "r-rajoo"):
    fixtures.set_cv_incident(8.0, 0.7, None, rid)
    fixtures.mark_incident()
    ev = fixtures.build_incident_event()
    return ev


def teardown_function(_fn):
    fixtures.clear_incident()
    telegram.clear_ack()


# ------------------------------- zone context ------------------------------ #

def test_alert_carries_the_residents_zone():
    """The enrolled identity's own last-motion area replaces the placeholder."""
    ev = _named_event("r-rajoo")
    msg = telegram.format_incident_message(ev)
    assert "Rajoo Subramaniam" in msg
    assert "last motion: Bedroom" in msg
    assert "Blk 112 #05-214" in msg  # unit stays — it finds the home


def test_default_identity_zone_differs_from_named():
    fixtures.mark_incident()  # generic acute (Tan)
    msg = telegram.format_incident_message(fixtures.build_incident_event())
    assert "Tan Ah Moi" in msg
    assert "last motion: Living room" in msg


def test_caseload_entries_expose_zone():
    with TestClient(app) as client:
        entries = client.get("/caseload").json()["entries"]
    zones = {e["id"]: e.get("zone") for e in entries}
    assert zones["r-rajoo"] == "Bedroom"
    assert zones["r-devi"] == "Kitchen"


# ------------------------------- escalation -------------------------------- #

def test_escalation_message_shape():
    ev = _named_event("r-rajoo")
    msg = telegram.format_escalation_message(ev, 45.0)
    assert "STILL DOWN" in msg
    assert "Rajoo Subramaniam" in msg
    assert "45s" in msg
    assert "last motion: Bedroom" in msg


def test_escalate_404_when_calm():
    with TestClient(app) as client:
        assert client.post("/incidents/escalate").status_code == 404


def test_escalate_dispatches_when_configured(monkeypatch):
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    _named_event("r-rajoo")

    fired = threading.Event()
    seen = {}

    def _capture(event, still_down_s):
        seen["name"] = event.entry.name
        seen["s"] = still_down_s
        fired.set()
        return True

    monkeypatch.setattr("app.alerts.telegram.send_escalation_alert", _capture)
    with TestClient(app) as client:
        r = client.post("/incidents/escalate", json={"stillDownS": 61.5})
        assert r.status_code == 200
        assert r.json()["dispatched"] is True
    assert fired.wait(timeout=5.0), "escalation dispatch thread never ran"
    assert seen["name"] == "Rajoo Subramaniam"
    assert seen["s"] == 61.5


def test_escalate_noop_when_unconfigured(monkeypatch):
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    _named_event("r-rajoo")
    with TestClient(app) as client:
        r = client.post("/incidents/escalate")
    assert r.status_code == 200
    assert r.json() == {"dispatched": False, "reason": "not-configured"}


# ----------------------------- acknowledgement ----------------------------- #

def test_ack_recorded_from_callback_update(monkeypatch):
    """The poller's update handler records {by, at} without any network: the
    Bot API side effects go through _api_call, a no-op when unconfigured."""
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    telegram.clear_ack()
    handled = telegram._handle_update({
        "update_id": 7,
        "callback_query": {
            "id": "cbq1", "data": "ack",
            "from": {"first_name": "Mei Ling"},
            "message": {"message_id": 42},
        },
    })
    assert handled is True
    ack = telegram.get_ack()
    assert ack and ack["by"] == "Mei Ling" and ack["at"]


def test_non_ack_updates_ignored():
    telegram.clear_ack()
    assert telegram._handle_update({"update_id": 8, "message": {"text": "hi"}}) is False
    assert telegram._handle_update({
        "update_id": 9, "callback_query": {"id": "x", "data": "other"}
    }) is False
    assert telegram.get_ack() is None


def test_status_surfaces_and_new_incident_clears_ack(monkeypatch):
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("SISFALL_TRACE", raising=False)
    telegram._handle_update({
        "update_id": 10,
        "callback_query": {"id": "c", "data": "ack", "from": {"first_name": "Ana"}},
    })
    with TestClient(app) as client:
        assert client.get("/alerts/status").json()["acknowledged"]["by"] == "Ana"
        # a fresh incident starts an unacknowledged alert leg
        assert client.post("/incidents/cv-detected").status_code == 200
        assert client.get("/alerts/status").json()["acknowledged"] is None


def test_alert_send_includes_ack_button(monkeypatch):
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    ev = _named_event("r-rajoo")
    captured = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok":true,"result":{"message_id":5}}'

    def _fake_urlopen(req, timeout=None):
        import json as _json
        captured["body"] = _json.loads(req.data.decode())
        return _Resp()

    with mock.patch("app.alerts.telegram.urlopen", _fake_urlopen):
        assert telegram.send_incident_alert(ev) is True
    kb = captured["body"]["reply_markup"]["inline_keyboard"]
    assert kb[0][0]["callback_data"] == "ack"
