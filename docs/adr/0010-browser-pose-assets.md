---
type: adr
diataxis: reference
title: In-browser MediaPipe pose for the camera track; assets fetched, not committed
status: accepted
tags: [adr, camera, pose, mediapipe]
---

# 0010. In-browser MediaPipe pose for the camera track; assets fetched, not committed
- Status: Accepted
- Date: 2026-07-26

## Context

Feature-spec §1b defines a camera acute source: a browser pose heuristic
(upright → horizontal → still) POSTing `/incidents/cv-detected`. The backend
shipped 2026-07-26 (test_cv.py); the browser half needs a pose engine. Forces:
the demo must run on any laptop (clone-and-run posture, ADR 0008 spirit);
eldercare video is privacy-sensitive; the repo should not bloat with model
binaries; a hackathon demo may face flaky venue Wi-Fi.

Options considered: (a) server-side vision (stream frames to the backend) —
rejected: privacy posture collapses ("frames never leave the browser" is a
pitchable guarantee), and it drags OpenCV/torch into a FastAPI service that is
deliberately lean; (b) TensorFlow.js MoveNet — viable, but heavier JS bundle
and the backend tests/docstrings already name MediaPipe as the intended
engine; (c) MediaPipe Tasks Vision in the browser — chosen.

## Decision

- `@mediapipe/tasks-vision` PoseLandmarker (lite model, VIDEO mode) runs
  entirely in the browser on `/watch`. No frame, landmark, or image ever
  reaches our backend — only the final `{stillnessS, confidence, note}`
  detection event.
- Binary assets are **fetched, not committed**: `npm run fetch-pose-assets`
  copies the wasm bundle out of `node_modules` and downloads
  `pose_landmarker_lite.task` (~5.5 MB, Google's published model URL) into
  `public/mediapipe/` (gitignored). At runtime the page prefers the local
  copies and falls back to the official CDN URLs, so a fresh clone works
  with internet even if the fetch step was skipped, and a pre-fetched laptop
  demos fully offline.
- The fall heuristic itself is a pure TypeScript state machine
  (`lib/pose/fallHeuristic.ts`) with vitest unit tests — MediaPipe supplies
  landmarks only, so detection logic stays testable without a camera.

## Consequences

- (+) Privacy claim is architectural, not policy: video processing is
  client-side by construction.
- (+) Repo stays binary-free; offline demo is a one-command pre-fetch.
- (+) Heuristic logic is unit-tested; the untestable surface is narrowed to
  MediaPipe glue.
- (−) First page load without prefetch needs ~7 MB from a third-party CDN.
- (−) A pose heuristic is far weaker than the calibrated accelerometer
  detector — mitigated by feature-spec §1b honesty rules (own confidence
  band, `Camera (pose)` labelling, no fake waveform).
- vitest enters the dashboard as its first test runner.
