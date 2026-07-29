---
diataxis: explanation
title: "ADR 0016 — Dashboard acknowledgement + re-speak-until-acknowledged loop"
status: accepted
date: 2026-07-29
tags: [adr, alerts, audio, ack, dashboard]
---

# ADR 0016 — Dashboard acknowledgement + re-speak-until-acknowledged loop

## Status
Accepted 2026-07-29 (operator-directed). Extends [[0012-escalation-ack-zone]]
and builds [[0015-on-device-audio-alerts]] proposed follow-up 1.

## Context

ADR 0015 speaks the fall call-out once at dispatch. A single utterance is easy
to miss, and the only way to acknowledge an alert was the Telegram button — a
caseworker looking at the dashboard itself had no way to say "I have this" or
to silence the room. The operator asked for both, with the constraint that the
Simulate / Reset demo beat must keep working unchanged.

## Decision

### 1. One ack state, two sources

`telegram._set_ack(by)` now holds the single first-responder-wins rule; the
existing getUpdates tap handler and the new `record_ack(by)` (dashboard path)
both go through it. `POST /alerts/ack` (`{by}`, default "Dashboard") returns
the owning ack plus `already: true` when someone beat the caller to it; 404
while calm, mirroring `/incidents/escalate`. When Telegram is configured, a
dashboard ack gets the SAME chat visibility as a tap — the alert loses its
button and a quiet reply names the responder — off-thread, best-effort.

**No Simulate clash, by construction:** the ack endpoint never touches the
incident (`mark/clear_incident` untouched), and `_dispatch_alert` already
clears the ack per new incident, so Simulate → ack → Reset → Simulate always
starts a fresh unacknowledged leg and the button re-arms.

### 2. Re-speak loop (watch station)

After a successful dispatch `WatchPanel` repeats the call-out every 20 s.
The per-tick decision is a pure `respeakDecision()` (unit-tested):

- **acknowledged** → speak "Alert acknowledged. <by> is responding." once and
  stop — the loop's closure states who owns the response, from either source.
- **no acute row** (Reset demo, TTL expiry) → stop silently.
- **cap** (15 repeats ≈ 5 min) → stop silently; anything longer is the
  ADR 0012 escalation path's job, not a louder room.
- otherwise → speak again. The stage-bar toggle mutes a tick without killing
  the loop, so re-enabling sound resumes mid-incident.

Polling reuses `/alerts/status` (+ `/caseload` only while unacked) — no new
read surface, and the dashboard's existing 5 s ack poll is untouched.

### 3. Dashboard button

"🔕 I am responding — stop alert" in the toolbar, rendered only while an acute
row is up AND the alert is unacknowledged; on success the existing
"✓ <by> responding" badge replaces it. A 404 (incident cleared mid-click) is
swallowed — the poll realigns the UI.

### 4. Privacy acknowledgment box (same session, /watch)

A warning-toned box under the camera stage states exactly what leaves the
browser: one POST with four fields (fall timing, stillness seconds,
confidence estimate, matched resident id), no video/image/face crop ever
uploaded, embeddings stored locally as numbers. Copy follows the locked
operator voice standard (first-person "we", no contractions, no em dashes,
exact fields named).

## Consequences

- The room stops being silent after the first call-out, and stops being loud
  the moment anyone — Telegram or dashboard — takes ownership.
- New rewrite `/api/alerts/ack`; `AlertStatus` contract unchanged (the ack
  field existed since ADR 0012).
- E2E now covers dashboard ack (badge up, button retired, status agrees).
- feature-spec bumps to 1.11.0.
