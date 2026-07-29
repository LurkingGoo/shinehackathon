---
type: plan
date: 2026-07-29
title: Re-speak until acknowledged · dashboard stop-alert · privacy notice
status: implementing
tags: [watch, audio, ack, privacy, dashboard]
---

# Plan — re-speak loop, dashboard ack, privacy acknowledgment box

Builds ADR 0015's proposed follow-up 1 and adds a second ack source. Design
→ [[0016-dashboard-ack-and-respeak]].

## 1. Re-speak until "I am responding" (watch station)

After a successful fall dispatch, `WatchPanel` starts a 20 s loop. Each tick
fetches `/alerts/status` (+ `/caseload` when unacked):

- **acknowledged** → speak "Alert acknowledged. <by> is responding." once, stop.
- **no acute row** (Reset demo / TTL expiry) → stop silently.
- **cap reached** (15 repeats ≈ 5 min) → stop silently.
- otherwise → re-speak the fall announcement (toggle OFF mutes the tick but
  keeps the loop alive, so toggling back ON resumes).

Decision logic is a pure `respeakDecision()` in `lib/audio/alerts.ts` —
unit-tested; the component just schedules. One loop at a time (a new fall
restarts it); cleared on unmount.

## 2. Dashboard "I am responding" button

- Backend: `POST /alerts/ack` `{by?}` (default "Dashboard"). First responder
  wins — identical rule to the Telegram tap; if already owned, returns the
  existing owner with `already: true`. 404 while calm (mirrors /escalate).
  When Telegram IS configured, the chat gets the same visibility as a button
  tap (alert edited + quiet reply), off-thread, best-effort.
- `telegram.record_ack(by)` factors the shared first-wins + chat-visibility
  core out of `_handle_update` so both sources converge on one code path.
- Frontend: toolbar button, visible only while an acute row is up AND the
  alert is unacknowledged; on click ack + immediate status refresh (the 5 s
  poll and the watch loop pick it up too). New rewrite `/api/alerts/ack`.
- No Simulate clash: `_dispatch_alert` already `clear_ack()`s per incident,
  so Simulate → ack → Reset → Simulate always starts unacknowledged.

## 3. Privacy acknowledgment box (/watch, operator voice)

Warning-styled box under the camera stage stating exactly what leaves the
browser: one POST with the stillness seconds, a confidence estimate, and the
matched resident id; no video, image, or face crop is ever uploaded; the
Telegram alert is written from those fields alone. Voice per the locked pitch
standard (bold lead-in, "we", no contractions, no em dashes, exact fields).

## Verification

pytest (ack endpoint + record_ack first-wins), vitest (respeakDecision),
tsc, e2e extended: dashboard ack button → "✓ Dashboard is responding" badge.

## Docs

ADR 0016; feature-spec 1.10.0 → 1.11.0. ADR 0015 stays untouched (accepted;
0016 records that follow-up 1 is now built).
