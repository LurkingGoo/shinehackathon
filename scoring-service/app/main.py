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

from typing import Annotated

from fastapi import FastAPI, HTTPException, Request, Response
from pydantic import Field
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel
from sse_starlette.sse import EventSourceResponse

from app.alerts import telegram
from app.data import fixtures, loaders
from app.models import CaseloadEntry, IncidentEvent, RankedCaseload, ResidentDetail
from app.replay.engine import hub

app = FastAPI(title="triage scoring-service", version="0.1.0")

# Keepalive cadence for /incidents/stream (demo-runbook fix #6). The client
# watchdog assumes ~2x this interval; keep the two in sync if it changes.
HEARTBEAT_SECONDS = 15.0

# Dev convenience: allow the Next app to connect directly (it also proxies).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["*"],
    # ADR 0017: a direct (non-proxied) client must be able to read the
    # replay nonce off the fall response.
    expose_headers=["X-Incident-Id"],
)


@app.on_event("startup")
def _start_ack_poller() -> None:
    # ADR 0012: lazy daemon thread long-polling getUpdates for the alert's
    # "I am responding" button. No-op unless Telegram is configured; disabled
    # by SHINEHACKATHON_TELEGRAM_ACK_POLL=0 (tests set this).
    telegram.start_ack_poller()


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


class RegisterResidentRequest(BaseModel):
    """Operator registration (ADR 0013): a new person under their own name.
    Everything but the name is optional — an unkeyed location falls back to
    the default zone; the address composes from whichever parts arrive."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    name: str
    age: int | None = None
    zone: str | None = None
    unit: str | None = None
    block: str | None = None
    unit_number: str | None = None
    lat: float | None = None
    lon: float | None = None


class LocationRequest(BaseModel):
    """Keyed-in location for an existing roster resident (ADR 0013). Fields
    not sent stay untouched; zone='' reverts to the fixture default."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    zone: str | None = None
    unit: str | None = None
    block: str | None = None
    unit_number: str | None = None
    lat: float | None = None
    lon: float | None = None


@app.post("/residents", response_model=CaseloadEntry)
def register_resident(body: RegisterResidentRequest) -> CaseloadEntry:
    """Register a person into the chronic roster and return their scored
    caseload entry. They immediately appear in /caseload (dashboard, Report-as
    and Enroll-as selectors) and their name + zone flow into any alert."""
    name = body.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="name must not be blank")
    r = fixtures.register_resident(
        name, age=body.age, zone=body.zone, unit=body.unit, block=body.block,
        unit_number=body.unit_number, lat=body.lat, lon=body.lon,
    )
    for entry in fixtures.build_ranked_caseload().entries:
        if entry.id == r.id:
            return entry
    raise HTTPException(status_code=500, detail="registered but not in caseload")


@app.post("/residents/{rid}/location")
def set_resident_location(rid: str, body: LocationRequest | None = None) -> dict:
    """Key in where a resident is. POST (not PATCH) to match every other
    mutation on this service. 404 for an unknown id."""
    b = body or LocationRequest()
    r = fixtures.set_resident_location(
        rid, zone=b.zone, unit=b.unit, block=b.block,
        unit_number=b.unit_number, lat=b.lat, lon=b.lon,
    )
    if r is None:
        raise HTTPException(status_code=404, detail=f"unknown resident: {rid}")
    return {"ok": True, "id": r.id, "zone": r.zone, "unit": r.unit}


@app.delete("/residents/{rid}")
def delete_resident(rid: str) -> dict:
    """Remove a runtime registrant (ADR 0014). Only registered people are
    deletable — the fixture roster is demo narrative (409). An active incident
    named for the deleted person keeps running under the generic identity."""
    outcome = fixtures.delete_resident(rid)
    if outcome == "unknown":
        raise HTTPException(status_code=404, detail=f"unknown resident: {rid}")
    if outcome == "builtin":
        raise HTTPException(
            status_code=409, detail=f"built-in resident cannot be deleted: {rid}"
        )
    return {"ok": True, "id": rid}


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


# Outcome of the most recent alert dispatch, for /alerts/status (chain-of-custody
# visibility, 2026-07-26 test notes): {"outcome", "residentId", "at"} or None.
# Written by the dispatch thread; a plain dict swap is atomic enough for a status
# read — no lock needed.
_last_dispatch: dict | None = None


def _record_dispatch(event: IncidentEvent, outcome: str) -> None:
    global _last_dispatch
    _last_dispatch = {
        "outcome": outcome,
        "residentId": event.entry.id,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _dispatch_alert(event: IncidentEvent) -> None:
    """Fire the Telegram fall alert off the request path. A no-op when Telegram
    isn't configured (is_configured False), and a daemon thread otherwise so a
    slow/failed send never delays or breaks the incident response. Every path
    records its outcome for /alerts/status — silence stays out of the UI."""
    telegram.clear_ack()  # a new incident starts an unacknowledged alert leg
    if not telegram.is_configured():
        _record_dispatch(event, "not-configured")
        return

    def _send() -> None:
        ok = telegram.send_incident_alert(event)
        _record_dispatch(event, "sent" if ok else "failed")

    threading.Thread(target=_send, daemon=True).start()


@app.get("/alerts/status")
def alerts_status() -> dict:
    """Alert-leg visibility: is Telegram configured, and what happened to the
    most recent dispatch. Lets the dashboard show 'Telegram: connected / not
    configured' instead of leaving the caregiver ping silently unverifiable."""
    return {
        "telegram": {"configured": telegram.is_configured()},
        "lastDispatch": _last_dispatch,
        # ADR 0012: {by, at} once a caregiver taps "I am responding" on the
        # alert; null until then, cleared on each new incident.
        "acknowledged": telegram.get_ack(),
        # ADR 0017 phase 5: outcome of the most recent replay-GIF follow-up
        # (sent / failed / skipped / no-replay / not-configured).
        "replayAnimation": _last_animation,
    }


class AckRequest(BaseModel):
    """Body for the dashboard's stop-alert button (ADR 0016)."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    by: str = "Dashboard"


@app.post("/alerts/ack")
def acknowledge_alert(body: AckRequest | None = None) -> dict:
    """Second acknowledgement source (ADR 0016): the dashboard's own
    'I am responding' button. Identical first-responder-wins rule as the
    Telegram tap — whoever acks first owns the response, later sources get
    `already: true` and the existing owner. 404 while the caseload is calm
    (nothing to acknowledge), mirroring /incidents/escalate."""
    if not fixtures.incident_active():
        raise HTTPException(status_code=404, detail="no active incident")
    b = body or AckRequest()
    ack, created = telegram.record_ack(b.by.strip() or "Dashboard")
    return {"ok": True, "acknowledged": ack, "already": not created}


class CvDetectedRequest(BaseModel):
    """Body the browser pose heuristic POSTs when it sees a fall. All optional —
    an empty body fires with sensible defaults so a bare click still demos.
    camelCase aliases so the browser can send {stillnessS, confidence, note}."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    stillness_s: float = 8.0
    confidence: float = 0.7
    note: str | None = None
    # Enrolled identity (ADR 0011): which caseload resident this fall belongs
    # to. Optional and fail-open — absent/unknown keeps the default identity.
    resident_id: str | None = None


@app.post("/incidents/cv-detected", response_model=IncidentEvent)
def cv_detected(response: Response, body: CvDetectedRequest | None = None) -> IncidentEvent:
    """Camera / pose fall track (the /watch stretch). The browser MediaPipe
    heuristic (upright -> horizontal -> still) calls this to fire the SAME
    incident path as an accelerometer fall: it ranks into /caseload, streams over
    SSE and dispatches Telegram. Honestly labelled — sensor = camera, confidence
    = the browser's heuristic estimate (NOT the calibrated 96% detector), and no
    accelerometer waveform is exposed (/incidents/trace 404s for it)."""
    b = body or CvDetectedRequest()
    fixtures.set_cv_incident(b.stillness_s, b.confidence, b.note, b.resident_id)
    fixtures.mark_incident()
    # ADR 0017: the per-incident nonce rides a HEADER (not the contract-guarded
    # IncidentEvent body) — only the detecting browser needs it, to pair its
    # follow-up replay upload with THIS incident and no other.
    iid = fixtures.current_cv_incident_id()
    if iid:
        response.headers["X-Incident-Id"] = iid
    event = fixtures.build_incident_event()
    hub.publish(event)
    _dispatch_alert(event)
    return event


class ReplayFacts(BaseModel):
    """Browser-computed replay facts (ADR 0017, folded into the rationale in
    phase 2). All optional — fail-open, like everything on the camera path."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    descent_duration_ms: int | None = None
    direction: str | None = None
    protective_arm: bool | None = None
    post_impact_movement: str | None = None


class ReplayUploadRequest(BaseModel):
    """The frozen landmark ring buffer (ADR 0017): quantized integer rows,
    [tMs, then 13 joints x (x*1000, y*1000, visibility*100)]; a 1-length row
    means no person was tracked that instant. Hard caps are the DoS guard."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    incident_id: str
    fps: float = Field(10.0, gt=0, le=120)
    quant_scale: int = Field(1000, gt=0)
    frames: list[Annotated[list[int], Field(max_length=99)]] = Field(max_length=200)
    facts: ReplayFacts | None = None


@app.post("/incidents/replay")
def upload_replay(body: ReplayUploadRequest, request: Request) -> dict:
    """Attach the skeleton trace to the active camera incident (ADR 0017).
    404: nothing to attach to (calm / TTL / accelerometer incident).
    409: nonce mismatch — the buffer belongs to a superseded incident; the
    client must drop it, never retry. Never persisted, never dispatched."""
    cl = request.headers.get("content-length")
    if cl and cl.isdigit() and int(cl) > 1_500_000:
        raise HTTPException(status_code=413, detail="replay too large")
    outcome = fixtures.set_replay(
        body.incident_id, body.fps, body.quant_scale, body.frames,
        body.facts.model_dump(by_alias=True) if body.facts else None,
    )
    if outcome == "no-incident":
        raise HTTPException(status_code=404, detail="no active camera incident")
    if outcome == "stale":
        raise HTTPException(
            status_code=409, detail="stale replay for a superseded incident"
        )
    _dispatch_replay_animation()
    return {"ok": True, "incidentId": body.incident_id, "frames": len(body.frames)}


# Outcome of the most recent animation follow-up, surfaced on /alerts/status
# so a missing GIF is never silently undiagnosable (gap check 2026-07-30).
_last_animation: dict | None = None


def _record_animation(outcome: str) -> None:
    global _last_animation
    _last_animation = {
        "outcome": outcome,
        "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }


def _dispatch_replay_animation() -> None:
    """Phase 5 (ADR 0017): render the stored replay as a stick-figure GIF and
    send it as a quiet REPLY to the fall alert. This is the single sanctioned
    exit for the landmark data — to the same chat that already received the
    alert, as coordinates drawn into lines, never pixels. Entirely
    best-effort and off the request thread; a no-op unconfigured or when
    Pillow is absent.

    Race guards (gap check 2026-07-30): the caption is captured HERE on the
    request thread — a Reset or second fall while the render thread runs can
    never caption this GIF with another incident's rationale — and the reply
    target is resolved only after THIS dispatch's alert leg settles, else
    the GIF goes un-threaded rather than under a stale alert."""
    if not telegram.is_configured():
        _record_animation("not-configured")
        return
    payload = fixtures.replay_payload()
    if payload is None:
        _record_animation("no-replay")
        return
    caption_rationale = fixtures.build_incident_event().entry.score.rationale
    dispatch_before = _last_dispatch  # identity snapshot, not a copy

    def _send() -> None:
        try:
            from app.alerts import replay_render

            gif = replay_render.render_replay_gif(
                payload["frames"], payload["quantScale"]
            )
            if not gif:
                _record_animation("skipped")
                return
            deadline = time.monotonic() + 5.0
            while time.monotonic() < deadline and _last_dispatch is dispatch_before:
                time.sleep(0.2)
            settled = _last_dispatch
            reply_to = (
                telegram.last_alert_message_id()
                if settled is not dispatch_before
                and settled and settled.get("outcome") == "sent"
                else None
            )
            ok = telegram.send_replay_animation(
                gif,
                f"How the fall happened: {caption_rationale}\n"
                "(joint positions only, no pixels)",
                reply_to=reply_to,
            )
            _record_animation("sent" if ok else "failed")
        except Exception as exc:  # never let the follow-up harm anything
            _record_animation("failed")
            print(f"[replay] animation follow-up skipped: {type(exc).__name__}: {exc}")

    threading.Thread(target=_send, daemon=True).start()


@app.get("/incidents/replay")
def get_replay() -> dict:
    """The skeleton trace behind the active CAMERA incident — the camera's
    native equivalent of /incidents/trace (each sensor drills into its own
    raw signal). 404 while calm, for accelerometer incidents, and before the
    browser's upload lands."""
    payload = fixtures.replay_payload()
    if payload is None:
        raise HTTPException(status_code=404, detail="no replay for the active incident")
    return payload


class EscalateRequest(BaseModel):
    """Body the browser posts when the fallen person is STILL down (ADR 0012).
    The camera is the only component that knows nobody got up, so the browser
    decides and this endpoint dispatches."""
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True)
    still_down_s: float = 45.0
    resident_id: str | None = None


@app.post("/incidents/escalate")
def escalate(body: EscalateRequest | None = None) -> dict:
    """Long-lie escalation: a second, sharper Telegram message when the camera
    sees no recovery after the fall alert. Escalation is a message, not a new
    incident — the active incident and caseload are untouched. 404 while the
    caseload is calm (nothing to escalate), mirroring /incidents/trace."""
    if not fixtures.incident_active():
        raise HTTPException(status_code=404, detail="no active incident")
    b = body or EscalateRequest()
    event = fixtures.build_incident_event()

    if not telegram.is_configured():
        _record_dispatch(event, "not-configured")
        return {"dispatched": False, "reason": "not-configured"}

    def _send() -> None:
        ok = telegram.send_escalation_alert(event, b.still_down_s)
        _record_dispatch(event, "sent" if ok else "failed")

    threading.Thread(target=_send, daemon=True).start()
    return {"dispatched": True}


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
