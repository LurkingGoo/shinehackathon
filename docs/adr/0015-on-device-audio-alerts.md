---
diataxis: explanation
title: "ADR 0015 — On-device audio fall alerts (Web Speech + WebAudio chime)"
status: accepted
date: 2026-07-29
tags: [adr, alerts, audio, watch]
---

# ADR 0015 — On-device audio fall alerts (Web Speech + WebAudio chime)

## Status
Accepted 2026-07-29 (operator-directed). Complements the Telegram leg
([[0012-escalation-ack-zone]]); replaces nothing.

## Context

The alert chain was entirely silent at the point of detection: a fall fired
Telegram (a remote caregiver's pocket) and re-ranked the dashboard (a screen
someone must be looking at). A bystander standing next to the watch station —
the most likely first responder — got nothing. The operator asked for a spoken
"Patient has fallen!" call-out, twice, at dispatch time.

## Decision

**Web Speech API (`speechSynthesis`) + a two-tone WebAudio chime, all
on-device.** Rejected alternatives: external TTS APIs (the demo runs offline;
also ships audio of an emergency to a third party) and bundled audio assets
(cannot speak a dynamic name/zone; more repo weight for less information).

- `lib/audio/alerts.ts`: pure announcement builders (unit-tested) + playback.
  The mandated phrase twice, then the SAME identity + zone facts the Telegram
  alert carries — one source of truth, two ears.
- Wired at the two dispatch moments in `WatchPanel`: `report()` (fall) and
  `escalate()` ("still down", sharper phrasing). Fires only after the POST
  succeeds — the voice never claims a dispatch that didn't happen.
- Chime before speech: a voice onset is easy to miss; two rising tones are not.
- Playback is best-effort and exception-swallowed — audio must never break the
  alert path (same fail-open posture as the face leg, ADR 0011).
- Toggle in the stage bar, persisted (`localStorage`, default ON). Autoplay
  policy is satisfied structurally: nothing can fall before the operator's
  "Start camera" click, which grants user activation.

## Proposed follow-ups (not built)

1. **Repeat-until-acknowledged siren:** re-speak every ~20 s while the ADR 0012
   "I am responding" ack is absent, stopping the moment it lands — closes the
   loop between the room and the remote caregiver.
2. **Per-resident utterance language** (Malay / Mandarin / Tamil): the Web
   Speech voice is selectable; the registry could carry a language preference.

## Consequences

- Zero dependencies, zero network, zero assets; works on the demo laptop.
- Test detections also speak (same path, deliberate — it IS the demo beat);
  the toggle silences a rehearsal room instantly.
- feature-spec 1.10.0 documents the audible leg.
