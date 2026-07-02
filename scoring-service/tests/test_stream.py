"""Live-channel test — the demo's key beat, de-risked.

Prove the pub/sub hub delivers an injected IncidentEvent to a live subscriber
(what the SSE endpoint wraps). This is the plumbing hackathon demos break on, so
it gets its own test independent of the HTTP/SSE layer.
"""
from __future__ import annotations

import asyncio

from app.data.fixtures import build_incident_event
from app.replay.engine import IncidentHub


def test_hub_delivers_event_to_subscriber():
    async def run():
        hub = IncidentHub()
        q = hub.subscribe()
        assert hub.subscriber_count == 1
        n = hub.publish(build_incident_event())
        assert n == 1
        event = await asyncio.wait_for(q.get(), timeout=1.0)
        assert event.type == "incident"
        assert event.entry.score.track == "acute"
        hub.unsubscribe(q)
        assert hub.subscriber_count == 0

    asyncio.run(run())


def test_no_subscribers_is_safe():
    hub = IncidentHub()
    assert hub.publish(build_incident_event()) == 0


def test_incident_persists_into_caseload():
    """A simulated incident must survive a page refresh: after simulate,
    /caseload itself carries the acute row at rank 1 (demo-runbook fix #4)."""
    from fastapi.testclient import TestClient

    from app.data import fixtures
    from app.main import app

    client = TestClient(app)
    fixtures.clear_incident()
    try:
        before = client.get("/caseload").json()
        assert all(e["score"]["track"] == "chronic" for e in before["entries"])

        event = client.post("/incidents/simulate").json()
        after = client.get("/caseload").json()
        top = after["entries"][0]
        assert top["score"]["track"] == "acute"
        assert top["rank"] == 1 and top["id"] == event["entry"]["id"]
        # chronic rows follow, re-ranked from 2 with no gaps
        assert [e["rank"] for e in after["entries"]] == list(range(1, len(after["entries"]) + 1))
    finally:
        fixtures.clear_incident()  # don't leak state into other tests
