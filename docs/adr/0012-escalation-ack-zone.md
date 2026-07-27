---
diataxis: explanation
title: "ADR 0012 — Long-lie escalation, caregiver acknowledgement, zone context"
status: accepted
date: 2026-07-27
tags: [adr, camera, alerts, telegram]
---

# ADR 0012 — Long-lie escalation, caregiver acknowledgement, zone context

## Status
Accepted 2026-07-27 (operator-directed). Extends [[0011-enrolled-face-identity]];
does not supersede it.

## Context

The system fires one alert per detected fall and then goes silent. The problem
statement is the *long lie* — yet nothing today distinguishes "fell, got up"
from "fell, still on the floor ten minutes later". The alert leg also ends at
the caregiver's phone with no signal back, and the alert names the block/unit
but not where inside the flat to look, even though the chronic track already
holds each resident's last-motion area.

## Decision

Three extensions, all riding existing infrastructure, all fail-open:

### 1. Long-lie escalation (browser-driven)

The camera is the only component that knows whether the person got up, so the
**browser decides, the service dispatches** — the same split as detection.
`FallStateMachine` gains a post-fire tracker: after a fall event fires, if the
person remains horizontal and still for `escalateAfterMs` (default **45 s**
*(tune)* — long enough to mean "not getting up", short enough to demo), it
emits ONE `still-down` event. Any upright frame cancels the tracker. The
tracker is independent of the cooldown (45 s > the 10 s cooldown, so it must
survive the cooldown→monitoring transition). `/watch` POSTs it to
`POST /incidents/escalate` `{stillDownS, residentId?}`; the service formats an
escalated Telegram message (same identity resolution as ADR 0011) and
dispatches off-thread. No incident state changes — the incident is already
active; escalation is a message, not a new event.

### 2. Caregiver acknowledgement (Telegram inline button)

The fall alert message carries one inline button, **"I am responding"**
(`callback_data: "ack"`). A lazy daemon thread long-polls `getUpdates`
(started on service startup only when Telegram is configured; kill-switch env
`SHINEHACKATHON_TELEGRAM_ACK_POLL=0`, set in the test conftest so no test
ever touches the network). On a callback: record `{by, at}` in-process,
answer the callback, best-effort remove the button. `GET /alerts/status`
gains `acknowledged: {by, at} | null`; a new incident dispatch clears it.
The dashboard toolbar polls `/alerts/status` every 5 s while an incident is
active and shows "Acknowledged — <name>". Everything is best-effort: a dead
poller or failed edit never affects detection or dispatch.

Webhooks were rejected: the demo runs on localhost with no public URL;
long-polling works everywhere the bot token works.

### 3. Zone context in alerts

`ChronicResident` and `AcuteResident` gain `zone: str` — the resident's
last-motion area, consistent with the chronic features already shown on their
dashboard row (Rajoo: Bedroom; Wong: Bedroom; Lim: Bedroom; Devi: Kitchen;
Goh: Living room; default Tan: Living room). `CaseloadEntry` gains an
**optional** `zone` (camelCase alias; additive, so the dashboard contract is
unbroken). The alert location line becomes
`{unit} · last motion: {zone}` — the enrolled identity (ADR 0011) therefore
carries THAT resident's zone, replacing the one-size placeholder. Honesty:
zone is PIR-derived context ("where motion last was"), never a claim about
where the camera is; the camera does not localize.

## Consequences

- The demo beat becomes two-act: named alert, then "STILL DOWN after 45 s"
  escalation — the long-lie story made visible.
- One new endpoint, one poller thread, one optional contract field.
  `next.config.mjs` needs the `/api/incidents/escalate` rewrite (known
  gotcha, handoff warning).
- Escalation dedupe is per-fall (one still-down per fired event); repeated
  falls each get their own.
- The ack poller is the first backend component that *reads* from Telegram;
  the token still never leaves the two env vars.
- feature-spec bumps to 1.8.0.
