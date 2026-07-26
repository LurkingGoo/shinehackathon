---
type: plan
diataxis: explanation
title: /watch — browser camera fall detection page
status: done
date: 2026-07-26
tags: [camera, pose, mediapipe, acute-track]
---

# Plan: `/watch` — browser camera fall detection

## Goal

Ship the browser half of the camera acute source specified in
[[feature-spec]] §1b. The backend (`POST /incidents/cv-detected`, honesty
rules, 6 tests in `tests/test_cv.py`) already exists; nothing calls it yet.
After this plan, a caseworker (or judge) opens `/watch`, grants webcam
access, and a real human fall in front of the camera fires the SAME incident
path as an accelerometer fall: caseload preemption, SSE re-rank, Telegram.

## Design

### Pose engine — MediaPipe Tasks Vision, in-browser only

`@mediapipe/tasks-vision` PoseLandmarker (lite model, VIDEO running mode).
All inference stays in the browser: no frame ever leaves the device (privacy
note shown on the page). Assets policy (see [[adr/0010-browser-pose-assets]]):
wasm copied from node_modules and the `pose_landmarker_lite.task` model
(~5.5 MB) downloaded into `public/mediapipe/` by `npm run fetch-pose-assets`
(gitignored); runtime falls back to the official CDN URLs when local assets
are absent, so a fresh clone still works with internet.

### Fall heuristic — pure TS state machine (TDD)

`lib/pose/fallHeuristic.ts`, no DOM/MediaPipe imports — takes per-frame
derived measurements so it is unit-testable with synthetic sequences
(vitest, first test runner in the dashboard).

- Per frame in: 33 normalized landmarks + timestamp.
- Derived: torso angle vs vertical (shoulder-mid → hip-mid), mean landmark
  motion vs previous frame, mean visibility.
- Posture: `upright` (angle < 35°), `horizontal` (> 60°), else
  `transitional`; `no-person` under a visibility floor.
- State machine: upright → horizontal within 1.8 s (fast transition = fall
  candidate; slower = deliberate lying down, never fires) → continuous
  stillness (motion < ε) for 3.0 s → emit `{stillnessS, confidence}` →
  10 s cooldown.
- Confidence is the heuristic's own honest estimate (~0.6–0.85 band from
  transition speed + stillness length) — NEVER the calibrated 96.2% number
  (feature-spec §1b rule).

### Seam

`dataClient.reportCameraFall({stillnessS, confidence, note})` → POST
`/api/incidents/cv-detected` (camelCase body, matching `CvDetectedRequest`).
WatchPanel imports the seam only — no raw fetch (repo rule).

### UI — `app/watch/page.tsx` + `components/WatchPanel.tsx`

Warm Human theme. Video + canvas skeleton overlay, posture/state chip
(upright / horizontal / stillness countdown / cooldown), start–stop camera
button (getUserMedia needs a user gesture), event log of fired incidents.
On fire: seam call + "incident sent — open the dashboard" confirmation.
A small "send test detection" affordance POSTs the empty body (backend
defaults) as demo insurance when no one can physically fall. Honesty note
(heuristic camera source, not the calibrated detector) + privacy note
(frames never leave the browser). Header links from Dashboard.

## Steps

1. ADR 0010 (assets + in-browser posture decision).
2. vitest setup + failing tests for the heuristic; implement to green.
3. Seam method; typecheck.
4. WatchPanel + page + styles + nav link.
5. `scripts/fetch-pose-assets.mjs` + gitignore entries.
6. Verify: pytest (backend unchanged, 75 green), vitest green, typecheck,
   Playwright smoke (`/watch` renders, engine loads or shows its fallback),
   then a real-webcam manual pass by the operator.
7. Docs pass: feature-spec §1b note (page shipped), codebase-index, README.

## Out of scope

Recording/storing video, multi-person handling, fall detection on the
depth/rgb SHINE26 frame dataset (labels only were fetched — decision
2026-07-26), and any server-side vision.
