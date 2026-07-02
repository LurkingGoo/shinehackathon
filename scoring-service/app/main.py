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

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse

from app.data import fixtures, loaders
from app.models import IncidentEvent, RankedCaseload, ResidentDetail
from app.replay.engine import hub

app = FastAPI(title="triage scoring-service", version="0.1.0")

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


@app.post("/incidents/simulate", response_model=IncidentEvent)
def simulate() -> IncidentEvent:
    """Inject a fall: a REAL SisFall trace when one is on disk (data/sisfall/
    or $SISFALL_TRACE), else the synthetic trace so the demo never breaks.
    The trace runs through the same acute pipeline as any detection."""
    trace = loaders.default_sisfall_trace()
    if trace is not None:
        fixtures.set_acute_trace(loaders.sisfall_smv(trace), loaders.SISFALL_FS)
    event = fixtures.build_incident_event()
    hub.publish(event)
    return event


@app.get("/incidents/stream")
async def incidents_stream(request: Request) -> EventSourceResponse:
    """SSE: one IncidentEvent JSON per message. The client does
    `new EventSource('/api/incidents/stream')` and JSON.parse(m.data)."""
    async def gen():
        q = hub.subscribe()
        try:
            while True:
                if await request.is_disconnected():
                    break
                try:
                    event = await asyncio.wait_for(q.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue  # loop so disconnects are noticed promptly
                yield {"data": event.model_dump_json(by_alias=True)}
        finally:
            hub.unsubscribe(q)

    return EventSourceResponse(gen())
