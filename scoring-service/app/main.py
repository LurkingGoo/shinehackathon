"""FastAPI scoring service — the backend behind the triage-dashboard seam.

Serves the 3 contract surfaces (docs/backend-architecture.md):
  GET  /caseload           -> RankedCaseload
  GET  /residents/{id}     -> ResidentDetail  (404 if unknown)
  GET  /incidents/stream   -> SSE of IncidentEvent
  POST /incidents/simulate -> inject the canned fall (demo / de-risk)

Next.js /api/* proxies these same-origin. Data is fixture-backed today; the
dataset loaders + real detection replace the source without changing shapes.
"""
from __future__ import annotations

import asyncio
import os
import threading
import time

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sse_starlette.sse import EventSourceResponse

from app.alerts import telegram
from app.data import fixtures, loaders
from app.models import IncidentEvent, RankedCaseload, ResidentDetail
from app.replay.engine import hub

app = FastAPI(title="triage scoring-service", version="0.1.0")

# Keepalive cadence for /incidents/stream (demo-runbook fix #6). The client
# watchdog assumes ~2x this interval; keep the two in sync if it changes.
HEARTBEAT_SECONDS = 15.0

# Dev convenience: allow the Next app to connect directly (it also proxies).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"ok": True, "subscribers": hub.subscriber_count}


@app.get("/caseload", response_model=RankedCaseload)
def caseload() -> RankedCaseload:
    return fixtures.build_ranked_caseload()


@app.get("/residents/{rid}", response_model=ResidentDetail)
def resident(rid: str) -> ResidentDetail:
    detail = fixtures.detail_by_id(rid)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"unknown resident: {rid}")
    return detail


# Server-side rotation cursor: each POST /incidents/simulate advances it so the
# demo round-robins through DISTINCT fall traces (different subject / peak-g)
# instead of replaying one pinned trace. Module-level = shared across the process.
_rotation_idx = 0


@app.post("/incidents/simulate", response_model=IncidentEvent)
def simulate() -> IncidentEvent:
    """Inject a fall, ROUND-ROBINING through a set of distinct falls so each
    press looks different. Uses REAL SisFall traces — raw data/sisfall/ when
    present, else the committed curated set (loaders.demo_rotation_smv), so a
    fresh clone still fires genuine falls; only with NEITHER on disk does it fall
    back to synthetic variants so the demo never breaks. The chosen trace runs
    through the same acute pipeline as
    any detection and flows to /caseload, the SSE event and /incidents/trace."""
    global _rotation_idx
    # $SISFALL_TRACE is an explicit single-trace pin (operator override) — honor
    # it verbatim and skip rotation so the injected trace is exactly that file.
    env_pin = os.environ.get("SISFALL_TRACE")
    if env_pin:
        trace = loaders.default_sisfall_trace()
        if trace is not None:
            fixtures.set_acute_trace(loaders.sisfall_smv(trace), loaders.SISFALL_FS)
        fixtures.mark_incident()
        event = fixtures.build_incident_event()
        hub.publish(event)
        _dispatch_alert(event)
        return event

    traces = loaders.demo_rotation_smv()
    if traces:
        t = traces[_rotation_idx % len(traces)]
        fixtures.set_acute_trace(t.smv, t.fs)
    else:
        smv, fs = fixtures.synthetic_rotation_trace(_rotation_idx)
        fixtures.set_acute_trace(smv, fs)
    _rotation_idx += 1
    fixtures.mark_incident()  # /caseload now carries the acute row (refresh-proof)
    event = fixtures.build_incident_event()
    hub.publish(event)
    _dispatch_alert(event)
    return event


def _dispatch_alert(event: IncidentEvent) -> None:
    """Fire the Telegram fall alert off the request path. A no-op when Telegram
    isn't configured (is_configured False), and a daemon thread otherwise so a
    slow/failed send never delays or breaks the incident response."""
    if not telegram.is_configured():
        return
    threading.Thread(
        target=telegram.send_incident_alert, args=(event,), daemon=True
    ).start()


class CvDetectedRequest(BaseModel):
    """Body the browser pose heuristic POSTs when it sees a fall. All optional —
    an empty body fires with sensible defaults so a bare click still demos.
    camelCase aliases so the browser can send {stillnessS, confidence, note}."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    stillness_s: float = 8.0
    confidence: float = 0.7
    note: str | None = None


@app.post("/incidents/cv-detected", response_model=IncidentEvent)
def cv_detected(body: CvDetectedRequest | None = None) -> IncidentEvent:
    """Camera / pose fall track (the /watch stretch). The browser MediaPipe
    heuristic (upright -> horizontal -> still) calls this to fire the SAME
    incident path as an accelerometer fall: it ranks into /caseload, streams over
    SSE and dispatches Telegram. Honestly labelled — sensor = camera, confidence
    = the browser's heuristic estimate (NOT the calibrated 96% detector), and no
    accelerometer waveform is exposed (/incidents/trace 404s for it)."""
    b = body or CvDetectedRequest()
    fixtures.set_cv_incident(b.stillness_s, b.confidence, b.note)
    fixtures.mark_incident()
    event = fixtures.build_incident_event()
    hub.publish(event)
    _dispatch_alert(event)
    return event


@app.post("/incidents/simulate-nearmiss")
def simulate_nearmiss() -> dict:
    """Specificity demo: inject a dropped-phone-like impact spike (no free-fall
    dip before, no stillness after) through the SAME detector. It must NOT
    register as a fall — no incident is marked, the caseload stays calm. Returns
    what the detector saw so the UI can show a calm 'checked, not a fall' note."""
    from app.scoring import acute

    res = acute.detect_fall(fixtures.nearmiss_smv(), fixtures.FS)
    return {
        "detected": res.detected,
        "peakG": round(res.peak_g, 2),
        "reason": "no free-fall dip / no stillness",
    }


@app.post("/incidents/clear")
def clear_incident() -> dict:
    """Demo reset: drop the active incident so /caseload returns to the calm
    chronic ranking and the Simulate beat can be re-run."""
    fixtures.clear_incident()
    return {"ok": True}


@app.get("/training-stats")
def training_stats() -> dict:
    """Judge-metrics page data: the ILLUSTRATIVE logistic regression on curated
    SisFall magnitude features. Its ~80% ceiling is served alongside the shipped
    detector's 96.2% headline to make the honest point that magnitudes alone
    don't separate falls — the ordered signature does. Deterministic + cached, so
    the numbers never drift between calls. See app/model/training.py."""
    from app.model import training

    return training.training_report()


@app.get("/incidents/trace")
def incident_trace() -> dict:
    """The accelerometer signal behind the active incident (drilldown
    waveform): downsampled SMV window + detected phase positions. 404 while
    the caseload is calm — the panel only exists during an incident."""
    payload = fixtures.acute_trace_payload()
    if payload is None:
        raise HTTPException(status_code=404, detail="no active incident")
    return payload


async def incident_frames(request: Request):
    """The SSE frame generator behind /incidents/stream (module-level so the
    heartbeat behaviour is testable without holding a live HTTP stream open).
    Yields incident frames as they arrive and a named `heartbeat` frame every
    HEARTBEAT_SECONDS of quiet so the client can tell a calm stream from a
    dead socket (sleep / Wi-Fi blip)."""
    q = hub.subscribe()
    last_sent = time.monotonic()
    try:
        while True:
            if await request.is_disconnected():
                break
            try:
                event = await asyncio.wait_for(
                    q.get(), timeout=min(1.0, HEARTBEAT_SECONDS)
                )
            except asyncio.TimeoutError:
                # loop so disconnects are noticed promptly; heartbeat when quiet
                if time.monotonic() - last_sent >= HEARTBEAT_SECONDS:
                    last_sent = time.monotonic()
                    yield {"event": "heartbeat", "data": "{}"}
                continue
            last_sent = time.monotonic()
            yield {"data": event.model_dump_json(by_alias=True)}
    finally:
        hub.unsubscribe(q)


@app.get("/incidents/stream")
async def incidents_stream(request: Request) -> EventSourceResponse:
    """SSE: one IncidentEvent JSON per message. The client does
    `new EventSource('/api/incidents/stream')` and JSON.parse(m.data)."""
    # no-transform: the Next dev proxy gzip-buffers proxied responses unless
    # told not to — buffered SSE means events never reach the browser.
    return EventSourceResponse(
        incident_frames(request), headers={"Cache-Control": "no-cache, no-transform"}
    )
