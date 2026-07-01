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
