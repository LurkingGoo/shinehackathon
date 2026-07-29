---
diataxis: explanation
title: "ADR 0017 — Skeleton replay: landmark trace upload + privacy claim amendment"
status: accepted
date: 2026-07-29
tags: [adr, replay, privacy, watch, drilldown]
---

# ADR 0017 — Skeleton replay: landmark trace upload + privacy claim amendment

## Status
Accepted 2026-07-29 (operator-approved scope and phasing). **Supersedes the
privacy WORDING of [[0010-browser-pose-assets]]** ("no frame, landmark, or
image ever reaches our backend") **and [[0011-enrolled-face-identity]]**
("only the detection event and the matched resident id are sent") — the
architectural decisions in both ADRs stand unchanged. Plan:
[[2026-07-29-skeleton-replay-phases]].

## Context

Reviewing HOW a fall happened (trip vs. slip vs. buckle vs. faint, direction,
protective arm response) is what drives prevention — the commercial leader
sells exactly this, built on stored video. Our privacy posture forbids video.
A skeleton replay keeps most of the clinical signal by uploading pose
LANDMARKS (joint coordinates) for the 15 s around a confirmed fall: no face,
no room, no pixels. But ADR 0010's guarantee explicitly named landmarks as
never leaving the browser, and that sentence radiates through ~20 surfaces
(privacy box, feature-spec, judge brief, deck, READMEs). The feature is
therefore inseparable from an honest, repo-wide claim amendment.

## Decision

### 1. The amended privacy claim (canonical wording)

> Pixels never leave this browser — no video, image, or face crop is ever
> uploaded, recorded, or streamed. Face embeddings never leave this browser.
> After a confirmed fall, and only then, we send a fifteen-second
> stick-figure trace: pose joint coordinates, never pixels, kept only as
> long as the incident itself.

Every surface repeating the old claim is updated in the SAME phase the
upload ships (Phase 1) for build surfaces, and Phase 4 for pitch artifacts.

### 2. Capture (browser)

Ring buffer in the /watch camera loop: 13-landmark subset (nose + torso +
arms + legs — every bone the overlay draws), downsampled to ~10 fps,
15 s window, gaps recorded as null frames ("no person" is data). Frozen
synchronously when the fall fires; uploaded AFTER `reportCameraFall`
resolves as a fire-and-forget `keepalive` fetch (payload quantized to
integer thousandths, ~25 KB, under the 64 KB keepalive cap so navigating to
the dashboard cannot abort it). The alert path gains zero latency and the
upload inherits ADR 0011's fail-open rule: it can never block, delay, or
alter an alert.

### 3. Stale-upload guard (nonce)

`set_cv_incident()` mints a per-camera-incident id, returned as an
`X-Incident-Id` response header on `POST /incidents/cv-detected` (a header
adds zero contract-guard risk). The upload carries it; a mismatch while a
camera incident is active is rejected 409 (drop, never retry) — a buffer
from a superseded incident can never attach to a newer one.

### 4. Lifecycle = the incident's, exactly

Replay lives in scoring-service module state only: cleared by
`clear_cv_incident()` (Reset demo, accelerometer supersede), replaced on a
new camera incident, dead on TTL via the existing lazy `incident_active()`
gate. Never written to disk, the registry artifact, or logs. Deleting the
named resident mid-incident reverts identity but keeps the replay — it
belongs to the incident (nonce), not the name.

### 5. Serving + contract posture

`GET /incidents/replay` mirrors `/incidents/trace` semantics for the other
sensor: 404 while calm, 404 for ACCELEROMETER incidents, 404 before upload.
`/incidents/trace` keeps 404ing for camera incidents — each sensor drills
into its own raw signal; the pinned no-fake-waveform test stays untouched.
Replay types live in `types.ts` beside `IncidentTrace` as a read-only
presentation surface OUTSIDE the parity guard (same precedent); request
bodies are pydantic in `main.py` with hard size caps (≤200 frames × ≤99
ints, content-length 413 backstop).

### 6. Computed facts are features

Descent duration, fall direction (screen-coords convention), protective arm
response, post-impact movement — computed at freeze time in the browser
(pure, unit-tested), folded server-side into the incident rationale AND
appended as `RiskFeature` rows, because the determinism guarantee
(feature-spec §0/§3, briefing-numbers guardrail) requires every stated
number to trace to a feature. Facts arriving after the alert do NOT
republish the SSE event (a second `acute-detected` would re-toast and
re-speak); they surface through the read-through caseload/drilldown, and
the escalation message naturally carries them.

### 7. Replay player

Dashboard drilldown panel beside the accelerometer waveform slot, keyed per
drilldown id (the waveform's fetch-once pattern would show a stale skeleton
for the wrong resident). Canvas stick figure, play / ¼× slow-mo / scrubber
with phase bands in the waveform's color language; low-visibility joints
drawn faded — the replay shows what the model saw, honestly. Facts render
as the caption (never color-only).

## Consequences

- Fall REVIEW joins the product with the privacy story strengthened, not
  weakened: the claim gets longer but stays architectural (pixels cannot
  leave; landmarks leave only on a confirmed fall, with incident-scoped
  retention).
- ~20 claim surfaces must move in two batches (build surfaces Phase 1,
  pitch artifacts Phase 4) — tracked in the plan's gap register.
- `dataClient.reportCameraFall` starts returning the incident id (seam
  signature change).
- Drilldown screenshots in the deck go stale at Phase 3 — re-rendered in
  Phase 4.
- Optional Phase 5 (Telegram keyframe PNGs as a REPLY to the alert) is
  design-sketched in the plan, not committed to.
