---
type: adr
diataxis: reference
title: Enrolled on-device face identity for camera incidents; amends the 0010 privacy claim
status: accepted
tags: [adr, camera, face-recognition, privacy, enrollment]
---

# 0011. Enrolled on-device face identity for camera incidents
- Status: Accepted
- Date: 2026-07-26
- Amends: [[0010-browser-pose-assets]] (privacy claim wording; asset policy unchanged)

## Context

Camera incidents (feature-spec §1b) fire generically — the acute row is always
the default demo resident. The 2026-07-26 manual test pass logged the wish for
NAMED alerts ("Mdm Tan fell in Unit 4B") carried through the dashboard and the
Telegram ping. Open-set face recognition is infeasible and privacy-hostile;
recognizing the fallen person is unreliable (floor-facing, blurred, distant
face). Two design insights resolve both problems: **enroll first** (a tiny
opt-in gallery of known residents makes matching easy and doubles as a consent
artifact), and **recognize while upright, then carry the identity** through
the pose track so nothing needs to be recognized mid-fall.

ADR 0010 states "no frame ever leaves the device." Identity adds one string to
the outbound event, so the claim must be amended deliberately — it is printed
in the judge brief.

## Decision

- **Enrollment, on-device only.** Front + left + right face embeddings per
  person, computed in the browser and stored in localStorage bound to a
  caseload resident id chosen from the live roster (no free-text identities).
  No face image is ever stored or transmitted; embeddings never leave the
  device.
- **Recognize while upright; carry identity.** Matching runs at low cadence
  only while the pose state machine reports the person upright. A
  match binds a sticky session identity; the fall event then carries the
  bound `residentId`. Identity is metadata alongside detection — never an
  input to the fall heuristic.
- **Amended privacy claim:** "No video leaves the browser; only the detection
  event and the matched resident id are sent."
- **Fail open.** Unmatched, unenrolled, or below-threshold identity produces
  exactly the generic incident shipped today. A recognition failure can never
  block, delay, or alter a fall alert.
- **Same asset policy as 0010:** recognition model assets are fetched/vendored
  by script, gitignored, CDN fallback at runtime.

## Consequences

- (+) Named chain of custody: camera detection → named caseload row → named
  Telegram ping, each leg checkable via /alerts/status.
- (+) Enrollment is an explicit consent step — a stronger deployment story
  than ambient recognition, and honest to state on stage.
- (+) The resident selector (phase 1) remains as permanent demo insurance:
  named alerts are demoable with recognition switched off entirely.
- (−) The judge-brief privacy sentence must be updated in lockstep (phase 5)
  or the brief overstates the guarantee.
- (−) A small identity-model download joins the vendored assets; first
  no-prefetch load grows by its size.
- (−) Matching quality depends on demo-venue lighting; the fail-open rule and
  the selector cap the blast radius at "generic instead of named".
