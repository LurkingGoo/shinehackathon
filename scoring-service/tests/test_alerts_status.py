"""Alert-visibility endpoint tests (the chain-of-custody fix from the 2026-07-26
manual test notes).

Telegram dispatch is deliberately a silent no-op when unconfigured — good for a
zero-setup clone, bad for a viewer who cannot tell whether the "ping the
caregiver" leg ran. GET /alerts/status makes all three links checkable in one
place: it reports whether Telegram is configured AND the outcome of the most
recent dispatch attempt (sent / failed / not-configured), stamped with the
resident it was for.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

import app.main as main
from app.alerts import telegram
from app.data import fixtures
from app.main import app


def _client():
    return TestClient(app)


def _reset(monkeypatch):
    monkeypatch.setattr(main, "_last_dispatch", None)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)


def _wait_for_outcome(c, want: str, timeout_s: float = 5.0) -> dict:
    """Dispatch runs on a daemon thread — poll the endpoint until it lands."""
    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        body = c.get("/alerts/status").json()
        ld = body.get("lastDispatch")
        if ld and ld["outcome"] == want:
            return body
        time.sleep(0.05)
    return c.get("/alerts/status").json()


def test_status_unconfigured_and_no_dispatch_yet(monkeypatch):
    _reset(monkeypatch)
    with _client() as c:
        body = c.get("/alerts/status").json()
        assert body["telegram"]["configured"] is False
        assert body["lastDispatch"] is None


def test_unconfigured_incident_records_not_configured(monkeypatch):
    _reset(monkeypatch)
    with _client() as c:
        try:
            ev = c.post("/incidents/simulate").json()
            body = c.get("/alerts/status").json()
            assert body["telegram"]["configured"] is False
            ld = body["lastDispatch"]
            assert ld["outcome"] == "not-configured"
            assert ld["residentId"] == ev["entry"]["id"]
            assert ld["at"]  # ISO timestamp present
        finally:
            fixtures.clear_incident()


def test_configured_delivered_records_sent(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    monkeypatch.setattr("app.alerts.telegram.send_incident_alert", lambda ev: True)
    with _client() as c:
        try:
            assert c.get("/alerts/status").json()["telegram"]["configured"] is True
            c.post("/incidents/simulate")
            body = _wait_for_outcome(c, "sent")
            assert body["lastDispatch"]["outcome"] == "sent"
        finally:
            fixtures.clear_incident()


# ------------------- dashboard acknowledgement (ADR 0016) ------------------ #

def test_ack_requires_active_incident(monkeypatch):
    _reset(monkeypatch)
    telegram.clear_ack()
    fixtures.clear_incident()
    with _client() as c:
        assert c.post("/alerts/ack").status_code == 404


def test_dashboard_ack_first_responder_wins(monkeypatch):
    _reset(monkeypatch)  # unconfigured → zero network side effects
    with _client() as c:
        try:
            c.post("/incidents/simulate")
            r1 = c.post("/alerts/ack", json={"by": "Dashboard"}).json()
            assert r1["acknowledged"]["by"] == "Dashboard"
            assert r1["already"] is False
            # a second source does NOT steal the ack — same rule as Telegram
            r2 = c.post("/alerts/ack", json={"by": "Second Screen"}).json()
            assert r2["already"] is True
            assert r2["acknowledged"]["by"] == "Dashboard"
            assert c.get("/alerts/status").json()["acknowledged"]["by"] == "Dashboard"
        finally:
            fixtures.clear_incident()
            telegram.clear_ack()


def test_new_incident_starts_unacknowledged_after_dashboard_ack(monkeypatch):
    """The Simulate beat must never inherit a stale ack: ack → new incident →
    /alerts/status shows unacknowledged again (so the stop-alert button and
    the watch-station re-speak loop both re-arm)."""
    _reset(monkeypatch)
    with _client() as c:
        try:
            c.post("/incidents/simulate")
            c.post("/alerts/ack")
            assert c.get("/alerts/status").json()["acknowledged"]
            c.post("/incidents/simulate")
            assert c.get("/alerts/status").json()["acknowledged"] is None
        finally:
            fixtures.clear_incident()
            telegram.clear_ack()


def test_configured_failed_send_records_failed(monkeypatch):
    _reset(monkeypatch)
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    monkeypatch.setattr("app.alerts.telegram.send_incident_alert", lambda ev: False)
    with _client() as c:
        try:
            c.post("/incidents/cv-detected", json={"stillnessS": 8.0})
            body = _wait_for_outcome(c, "failed")
            assert body["lastDispatch"]["outcome"] == "failed"
        finally:
            fixtures.clear_incident()
