"""Live incident channel — the backend's push side of the seam.

An in-process pub/sub hub. The SSE endpoint subscribes; `simulate` (and, later,
the real replayer detecting a fall in a SisFall trace) publishes an
IncidentEvent. This is what makes the demo's key beat work: a fall fires
mid-shift and the caseload re-ranks. Mirrors the frontend's mock pub/sub so the
swap is 1:1 (docs/backend-architecture.md §6).
"""
from __future__ import annotations

import asyncio

from app.models import IncidentEvent


class IncidentHub:
    def __init__(self) -> None:
        self._subscribers: set[asyncio.Queue[IncidentEvent]] = set()

    def subscribe(self) -> "asyncio.Queue[IncidentEvent]":
        q: asyncio.Queue[IncidentEvent] = asyncio.Queue()
        self._subscribers.add(q)
        return q

    def unsubscribe(self, q: "asyncio.Queue[IncidentEvent]") -> None:
        self._subscribers.discard(q)

    def publish(self, event: IncidentEvent) -> int:
        """Fan an event out to all live subscribers. Returns subscriber count."""
        for q in list(self._subscribers):
            q.put_nowait(event)
        return len(self._subscribers)

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


# One process-wide hub.
hub = IncidentHub()
