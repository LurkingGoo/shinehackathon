"""Camera / pose fall-detection endpoint tests (the /watch stretch track).

The browser pose heuristic (MediaPipe: upright -> horizontal -> still) POSTs to
/incidents/cv-detected, which fires the SAME incident path as an accelerometer
fall — so it ranks into /caseload, streams over SSE, and dispatches a Telegram
alert. It is HONESTLY labelled: sensor = camera, confidence = the browser's
heuristic estimate (not the calibrated 96% detector), and it exposes no
accelerometer waveform (there isn't one). These tests pin that consistency
across /caseload, the event, and /residents/{id}.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.data import fixtures
from app.main import app


def _client():
    return TestClient(app)


def test_cv_detected_fires_camera_incident():
    with _client() as c:
        try:
            r = c.post("/incidents/cv-detected",
                       json={"stillnessS": 9.0, "confidence": 0.72})
            assert r.status_code == 200
            ev = r.json()
            assert ev["event"] == "acute-detected"
            s = ev["entry"]["score"]
            assert s["track"] == "acute"
            assert s["risk"] >= 0.9
            assert s["sensor"] == "Camera (pose)"
            assert "pose" in s["sensorClass"].lower() or "vision" in s["sensorClass"].lower()
            # honest: confidence is the browser estimate, not 1.0
            assert abs(s["confidence"] - 0.72) < 0.02
        finally:
            fixtures.clear_incident()


def test_cv_incident_is_consistent_across_surfaces():
    """/caseload, the event and /residents/{id} must all agree it's a camera
    incident — no surface showing 'Accelerometer' for a camera detection."""
    with _client() as c:
        try:
            ev = c.post("/incidents/cv-detected",
                        json={"stillnessS": 8.0, "confidence": 0.7}).json()
            rid = ev["entry"]["id"]

            top = c.get("/caseload").json()["entries"][0]
            assert top["id"] == rid
            assert top["score"]["sensor"] == "Camera (pose)"

            detail = c.get(f"/residents/{rid}").json()
            assert detail["score"]["sensor"] == "Camera (pose)"
            assert abs(detail["score"]["confidence"]
                       - ev["entry"]["score"]["confidence"]) < 1e-6
        finally:
            fixtures.clear_incident()


def test_cv_incident_has_no_accelerometer_trace():
    """A camera incident exposes no accelerometer drilldown — /incidents/trace
    404s (honest: there is no SMV waveform behind a vision detection)."""
    with _client() as c:
        try:
            c.post("/incidents/cv-detected", json={"stillnessS": 8.0})
            assert c.get("/incidents/trace").status_code == 404
        finally:
            fixtures.clear_incident()


def test_cv_detected_defaults_on_empty_body():
    with _client() as c:
        try:
            r = c.post("/incidents/cv-detected")
            assert r.status_code == 200
            s = r.json()["entry"]["score"]
            assert s["sensor"] == "Camera (pose)"
            assert 0.0 < s["confidence"] <= 1.0
        finally:
            fixtures.clear_incident()


def test_accelerometer_sim_clears_camera_override():
    """After a camera incident, an accelerometer simulate must present as
    Accelerometer again — the camera override doesn't leak."""
    import os
    with _client() as c:
        try:
            os.environ.pop("SISFALL_TRACE", None)
            c.post("/incidents/cv-detected", json={"stillnessS": 8.0})
            assert c.get("/caseload").json()["entries"][0]["score"]["sensor"] == "Camera (pose)"
            ev = c.post("/incidents/simulate").json()
            assert ev["entry"]["score"]["sensor"] == "Accelerometer"
            assert c.get("/caseload").json()["entries"][0]["score"]["sensor"] == "Accelerometer"
        finally:
            fixtures.clear_incident()


def test_cv_detected_dispatches_alert_when_configured(monkeypatch):
    import threading

    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", "TESTTOKEN123")
    monkeypatch.setenv("SHINEHACKATHON_TELEGRAM_CHAT_ID", "999")
    fired = threading.Event()
    monkeypatch.setattr("app.alerts.telegram.send_incident_alert",
                        lambda ev: fired.set() or True)
    with _client() as c:
        try:
            assert c.post("/incidents/cv-detected", json={"stillnessS": 8.0}).status_code == 200
            assert fired.wait(timeout=5.0)
        finally:
            fixtures.clear_incident()
