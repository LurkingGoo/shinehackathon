---
type: plan
date: 2026-07-29
title: Audio fall alert · resident deletion · enrollment capture gating
status: implementing
tags: [watch, audio, registry, enrollment, sync]
---

# Plan — audio alert, resident lifecycle (delete), enrollment UX, sync guards

Four asks from the operator mission, mapped onto the existing architecture
(seam: `dataClient` → `/api/*` → scoring-service; identity: ADR 0011/0013).

## 1. Audio fall alert (frontend-only)

**Stack choice: Web Speech API (`speechSynthesis`) + a short WebAudio chime.**
Rationale (→ [[0015-on-device-audio-alerts]]): the demo runs offline; local OS
voices need no network, no dependency, no audio asset. The alert speaks at the
*watch station* — the machine that detected the fall — which is also where a
bystander/caregiver in earshot is.

- New `lib/audio/alerts.ts`: pure `buildFallAnnouncement(name?, zone?)`
  (the mandated phrase twice — "Patient has fallen! Patient has fallen!" —
  plus a name/zone context sentence when identity is bound), `speakAlert()`
  (chime → utterance; guards absence of the APIs; cancels a stale queue),
  and an enabled flag persisted to localStorage.
- Wire in `WatchPanel.report()` (fires on detection dispatch — same moment the
  Telegram leg starts) and `escalate()` ("still down" phrasing).
- Sound on/off toggle in the stage bar (default ON).
- Autoplay policy: speech runs after the operator's "Start camera" gesture, so
  the page always has user activation by the time a fall can fire.

**Proposed (not built):** repeat-until-acknowledged siren tied to the ADR 0012
"I am responding" ack; per-resident language preference for the utterance.

## 2. Resident deletion (registered people only)

Fixture roster (r-rajoo … r-tan) is demo narrative — NOT deletable (409).
Only ADR 0013 runtime registrants are. Full cascade → [[0014-resident-deletion-cascade]].

- `DELETE /residents/{rid}`: 200 `{ok}` for a registrant, 409 built-in, 404 unknown.
- Backend cascade (`fixtures.delete_resident`): drop from `CHRONIC` +
  `_registered_ids`, persist registry artifact; if the deleted person is the
  active camera-named acute identity, the incident STAYS but its identity
  falls back to the generic default (fail-open, never a dangling name).
- Contract: `CaseloadEntry.registered?: boolean` (additive, both sides +
  regenerated `contract.schema.json`) so the UI knows who is deletable.
- Frontend cascade on success: forget face gallery entry, reset
  `IdentityTracker` + bound chip if bound to the deleted id, clear Report-as /
  Enroll-as / Who selections pointing at it, refetch roster.
- UI: two-step inline confirm ("Remove …" → "Confirm remove") in People &
  locations — no `window.confirm` (blocks automation).

## 3. Enrollment capture flow

- Move the capture control (Enroll-as + Capture button) to a strip directly
  below the camera feed; the enrollment card keeps the explainer + gallery list.
- Real-time `faceSeen`: the face tick now embeds on cadence whenever the face
  engine is on (previously only when gallery non-empty AND upright), but the
  *tracker* is still fed only on upright ticks with a non-empty gallery —
  ADR 0011 semantics (nothing recognized mid-fall) unchanged.
- Freshness window (2 s since last positive embed) absorbs rapid-movement
  flicker; `enrollBusy` already serializes captures (no double-fire).
- Pure `captureGate()` in `lib/face/enrollUi.ts` returns `{disabled, label}`
  from (engine, faceStatus, target, faceSeen, angles, busy) — unit-tested;
  the component just renders it. Soft cap 5 angles per person.

## 4. Cross-system sync guards

- Deletion during an active named incident → generic fallback (pytest).
- `registered` flag flows through caseload → UI gates the delete affordance.
- E2E (`e2e/watch-system.mjs`): extend with register → delete → roster clean
  (also removes the test's own registry litter, fixing its NOTE).
- Known limitation (documented, accepted): an open dashboard learns of a
  deletion on its next fetch/SSE event — roster changes are not pushed.

## Verification

pytest (registry + contract) · vitest (enrollUi, audio pure fns, matcher) ·
`tsc --noEmit` · e2e script updated (run needs both services restarted).

## Docs pass

ADR 0014 (deletion cascade), ADR 0015 (on-device audio), feature-spec
1.9.0 → 1.10.0 (§ audio alert, § resident lifecycle, § enrollment gating).
