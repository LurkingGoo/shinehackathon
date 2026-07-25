"""Telegram incident-alert dispatcher tests — network fully mocked.

The dispatcher must be safe by construction: a no-op when unconfigured (so a
fresh clone / the demo never needs a token), best-effort when configured (a
Telegram outage must NEVER break the incident response), and it must never leak
the bot token into logs or exceptions.
"""
from __future__ import annotations

import json
from unittest import mock

from app.alerts import telegram


def _event():
    """A real IncidentEvent from the fixture pipeline (acute fall)."""
    from app.data import fixtures
    fixtures.mark_incident()
    ev = fixtures.build_incident_event()
    fixtures.clear_incident()
    return ev


def test_unconfigured_is_noop(monkeypatch):
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    assert telegram.is_configured() is False
    # must not attempt any network call when unconfigured
    with mock.patch("app.alerts.telegram.urlopen") as up:
        assert telegram.send_incident_alert(_event()) is False
        up.assert_not_called()


def test_configured_sends_expected_request(monkeypatch):
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    assert telegram.is_configured() is True

    captured = {}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok":true}'

    def _fake_urlopen(req, timeout=None):
        captured["url"] = req.full_url
        captured["body"] = json.loads(req.data.decode())
        return _Resp()

    with mock.patch("app.alerts.telegram.urlopen", _fake_urlopen):
        assert telegram.send_incident_alert(_event()) is True

    assert "TESTTOKEN123" in captured["url"]
    assert captured["url"].endswith("/sendMessage")
    assert captured["body"]["chat_id"] == "999"
    text = captured["body"]["text"]
    assert "FALL" in text.upper()
    assert "g" in text  # impact magnitude present


def test_network_failure_never_raises(monkeypatch):
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")

    def _boom(req, timeout=None):
        raise OSError("connection refused")

    with mock.patch("app.alerts.telegram.urlopen", _boom):
        # best-effort: returns False, does not propagate
        assert telegram.send_incident_alert(_event()) is False


def test_token_never_in_message(monkeypatch, capsys):
    """The token must not appear in the formatted message or any stdout log."""
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "SECRET-abc123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")

    def _boom(req, timeout=None):
        raise OSError("down")

    with mock.patch("app.alerts.telegram.urlopen", _boom):
        telegram.send_incident_alert(_event())
    out = capsys.readouterr()
    assert "SECRET-abc123" not in out.out
    assert "SECRET-abc123" not in out.err


def test_format_incident_message_shape(monkeypatch):
    msg = telegram.format_incident_message(_event())
    assert isinstance(msg, str) and msg
    # resident-identifying + actionable content a caregiver needs
    ev = _event()
    assert ev.entry.name in msg
    assert ev.entry.unit in msg
    assert ev.detail.recommended_action in msg


def test_simulate_dispatches_alert_when_configured(monkeypatch):
    """POST /incidents/simulate fires the Telegram alert (off-thread) when
    configured — and the endpoint returns 200 regardless."""
    import threading

    from fastapi.testclient import TestClient

    from app.data import fixtures
    from app.main import app

    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    monkeypatch.delenv("SISFALL_TRACE", raising=False)

    fired = threading.Event()
    seen = {}

    def _capture(event):
        seen["name"] = event.entry.name
        fired.set()
        return True

    monkeypatch.setattr("app.alerts.telegram.send_incident_alert", _capture)
    try:
        with TestClient(app) as client:
            r = client.post("/incidents/simulate")
            assert r.status_code == 200
        assert fired.wait(timeout=5.0), "alert dispatch thread never ran"
        assert seen.get("name")
    finally:
        fixtures.clear_incident()


def test_simulate_unaffected_when_unconfigured(monkeypatch):
    """No token -> no dispatch, endpoint behaves exactly as before."""
    from fastapi.testclient import TestClient

    from app.data import fixtures
    from app.main import app

    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", raising=False)
    monkeypatch.delenv("SISFALL_TRACE", raising=False)

    with mock.patch("app.alerts.telegram.send_incident_alert") as send:
        try:
            with TestClient(app) as client:
                assert client.post("/incidents/simulate").status_code == 200
            send.assert_not_called()
        finally:
            fixtures.clear_incident()
