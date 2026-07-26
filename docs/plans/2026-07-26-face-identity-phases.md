---
type: plan
diataxis: explanation
title: Face identity for camera incidents — phased build plan
status: awaiting-operator-approval
date: 2026-07-26
tags: [camera, face-recognition, enrollment, privacy, phases]
---

# Plan: named camera incidents via enrolled face identity

Design agreed in discussion 2026-07-26: **enroll first (front + both
profiles + resident selection), recognize while upright, carry the identity
through the pose track, fail open to today's generic incident.** This plan
splits the build into phases that each land behind an existing seam, so any
phase can ship (or be abandoned) without touching the others.

## How it merges with the existing modules

| Phase | New surface | Existing seam it plugs into | Pattern it copies |
|---|---|---|---|
| 0 | ADR 0011, feature-spec §1b addendum | docs/adr, feature-spec | ADR 0009/0010 supersede style |
| 1 | `residentId` on `CvDetectedRequest` | `/incidents/cv-detected`, `fixtures.set_cv_incident` | camelCase optional body fields, TDD in `test_cv.py` style |
| 2 | `lib/face/engine.ts` + `lib/face/matcher.ts` | none (self-contained, like `lib/pose/`) | engine/heuristic split: glue untested, logic vitest-tested |
| 3 | enrollment card on `/watch` | `dataClient.getRankedCaseload()` (resident picker) | components read data only through the seam |
| 4 | identity binding in the watch loop | `dataClient.reportCameraFall(payload)` | same fire path, one new optional field |
| 5 | judge-brief privacy sentence, rehearsal protocol | pitch surfaces, `/alerts/status` chain | locked voice standard; chain-of-custody per incident |

## Phase 0 — decision on record (no code)

ADR 0011: amends ADR 0010's privacy claim, deliberately. New wording: "no
video leaves the browser; only the detection event and the matched resident
id are sent." Enrollment is opt-in, embeddings live on-device only
(localStorage), and the ADR states the fail-open rule: an unmatched or
unenrolled person produces exactly today's generic incident, never a blocked
alert. feature-spec bumps to 1.7.0 with the identity field. The judge brief
sentence is NOT changed here (it changes in phase 5, when the feature is
real).

## Phase 1 — backend identity plumbing (no ML, immediate demo value)

`CvDetectedRequest` gains optional `residentId`. `fixtures.set_cv_incident`
resolves it against the fixture roster: a known id makes THAT resident the
acute row (their name, age, unit flow to /caseload, the SSE event, the
Telegram message, /alerts/status.lastDispatch.residentId); absent or unknown
falls back to today's default. Tests first, in the `test_cv.py` pattern:
named incident ranks the named resident, detail agrees across surfaces,
telegram message carries their name, trace still 404s, unknown id falls
back.

Payoff before any ML exists: `/watch` gets a resident selector next to
"Send test detection", so a NAMED ping ("Devi Nair fell") is demoable from
day one. This is also the permanent demo insurance if face matching
misbehaves on stage.

## Phase 2 — face engine + matcher (isolated browser module)

Mirrors the `lib/pose/` split exactly:

- `lib/face/engine.ts` — model glue only: face detection + 128-D embedding
  extraction from a video frame crop. Model assets vendored by extending
  `fetch-pose-assets.mjs` (same local-first / CDN-fallback policy as ADR
  0010). Candidate: face-api.js recognition net (~6 MB); final pick recorded
  in ADR 0011 when measured.
- `lib/face/matcher.ts` — PURE logic, vitest-tested with synthetic vectors:
  cosine distance against the enrolled gallery, match threshold, a sticky
  "current identity" with decay so one bad frame does not flip the name.

No UI change in this phase; done when `npm test` covers the matcher and the
engine loads in the browser.

## Phase 3 — enrollment UI + on-device gallery

Enrollment card on `/watch`: pick a resident from the live caseload (through
`dataClient.getRankedCaseload()`, no new endpoint), capture front / left /
right (three embeddings per person), store `{residentId, embeddings[]}` in
localStorage. List, re-enroll, delete. Nothing is ever uploaded; the card
says so in plain words. Guest option for non-residents (maps to no id →
generic incident).

## Phase 4 — identity binding in the watch loop

Face matching runs at low cadence (every ~700 ms, on a downscaled crop) and
ONLY while the state machine reports the person upright/monitoring. A match
above threshold binds the identity for the session (sticky, decays after
the person leaves frame). When the fall fires, `reportCameraFall` includes
the bound `residentId`; the log line and Telegram show the name. No match
bound → field omitted → phase-1 fallback. The heuristic itself is untouched
— identity is metadata carried alongside, never an input to fall detection.

## Phase 5 — cohesive test + docs + pitch alignment

- Backend chain E2E (Playwright): named test detection → named caseload row
  → named Telegram outcome on /alerts/status.
- Face matching itself cannot be E2E'd with the fake camera — a written
  rehearsal protocol (enroll on the demo laptop, walk in, fall, confirm
  named ping) goes into the test-notes doc for the operator pass.
- Judge brief: privacy sentence updated per ADR 0011, in the locked voice.
- feature-spec, codebase-index note, push.

## Sequencing and exit ramps

Phases 0+1 ship together first (small, all-backend, high demo value). 2-4
are the ML build, each independently committable. 5 closes. If time runs
out after phase 1, the demo still gains named alerts via the selector; if
face matching proves unreliable in rehearsal, phase 4 stays off and nothing
regresses — the selector remains the on-stage path.

## Out of scope

Multi-person scenes (pose engine stays `numPoses: 1`), server-side
recognition of any kind, storing face images (only embeddings are kept),
and any change to fall-detection logic.
