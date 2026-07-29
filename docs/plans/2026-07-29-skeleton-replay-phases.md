---
type: plan
date: 2026-07-29
title: Skeleton replay — phased deployment plan
status: implementing
tags: [watch, replay, privacy, drilldown, phases]
---

# Skeleton replay — phased deployment

Synthesized from a three-agent pass (frontend plan, backend plan, cross-system
cohesion sweep). Scope decided with the operator: replay panel + computed
rationale facts; Telegram keyframe PNG only if time remains.

**Design rule for the whole rollout: every phase boundary leaves the system
coherent** — no phase ships with a privacy claim, contract, or test asserting
something the running system no longer does.

## Reconciled cross-plan decisions

1. **Contract posture:** replay types live in `lib/types.ts` beside
   `IncidentTrace` in the "read-only presentation surface outside the score
   contract" block. They do NOT enter `MODEL_FOR_INTERFACE` /
   `PAYLOAD_MODELS`; the GET serves a hand-built camelCase dict exactly like
   `acute_trace_payload`. No `contract.schema.json` regen, and
   `test_cv.py::test_cv_incident_has_no_accelerometer_trace` stays green
   because the replay is a NEW route — `/incidents/trace` keeps 404ing for
   camera incidents.
2. **Stale-replay guard:** per-camera-incident nonce minted in
   `set_cv_incident()`, returned as an `X-Incident-Id` response header on
   `POST /incidents/cv-detected` (zero contract risk). Seam change:
   `dataClient.reportCameraFall` returns the header value; the upload carries
   it; backend rejects a mismatch with 409 (drop, never retry).
3. **Facts are features:** every number spoken by the enriched rationale
   ("Fell rightward, 1.9 s descent, no arm protection") enters
   `_cv_score()` as real `RiskFeature` rows — the briefing-numbers guardrail
   (`test_briefing_invents_no_numbers…`) and feature-spec §0/§3 demand it.
4. **No SSE republish when facts arrive** — a second `acute-detected` frame
   would re-toast/re-speak as a new incident. Facts surface via the
   read-through `/caseload` + `/residents/{id}` recompute; the escalation
   message naturally carries them (it rebuilds the event).
5. **Alert latency untouched:** freeze is a synchronous array copy; the
   upload is a fire-and-forget `keepalive` fetch AFTER `reportCameraFall`
   resolves; payload budgeted < 64 KB (13-landmark subset, ~10 fps, 15 s,
   quantized ints ≈ 20–30 KB).
6. **Retention claim:** replay lives in scoring-service module state only —
   cleared by `clear_cv_incident()` (the single choke point: Reset,
   accelerometer supersede), re-minted on a new camera incident, dead on TTL
   via the existing lazy `incident_active()` gate. Never touches disk,
   registry, or logs.

## Phase 0 — Decision record (docs only, ~30 min)

- **ADR 0017** — skeleton replay: privacy amendment + design. Supersedes the
  privacy WORDING of ADR 0010 ("no frame, landmark, or image ever reaches
  our backend" — the strongest now-false claim) and ADR 0011's amended
  claim, with back-links both ways. Records: landmark subset, nonce guard,
  retention (= incident lifetime), facts-are-features rule, the honest
  distinction to preserve everywhere (pixels/frames never leave — still
  true; face embeddings never leave — still true; pose landmarks now do, on
  a confirmed fall only).
- `docs/adr/README.md` index catch-up (stale since 0011; next number 0017).
- `decisions.md` entry. This plan flips `status: implementing`.

**Coherent because:** nothing shipped yet; the decision trail leads.

## Phase 1 — Capture, upload, lifecycle (+ privacy copy in lockstep)

Frontend: `lib/pose/skeleton.ts` (extract BONES + `REPLAY_LANDMARKS` subset
+ remap), `lib/pose/replayBuffer.ts` (`ReplayRing`: keep-if-elapsed ≥95 ms,
160 slots, `freeze()` deep-copies + rebases, gaps recorded as null frames —
"no person" is data), WatchPanel wiring (push after `eng.detect`, freeze on
fire, fire-and-forget upload, reset in `start()`/`stop()`),
`dataClient.sendIncidentReplay` (keepalive POST), rewrite
`/api/incidents/replay`.

Backend: nonce state + `X-Incident-Id` header; `ReplayUploadRequest`
(pydantic caps: ≤200 frames × ≤99 ints, plus a content-length 413 guard);
`set_replay()` returning stored/stale/no-incident → 200/409/404; clearing
wired into `clear_cv_incident()` + `set_cv_incident()`.

**Privacy copy — same commit, non-negotiable** (user-visible + spec tier):
watch privacy box ("four fields" → adds "and, after a confirmed fall, a
fifteen-second stick-figure trace: joint positions, never pixels"), Honest
labelling card, feature-spec §1b amended claim + 1.13.0 bump,
`lib/pose/engine.ts` docstring ("no frame ever leaves the device" — the
module the buffer attaches to). Pitch artifacts (judge brief, deck, README)
wait for Phase 4 — they describe the product, not the running build, and
batch into one re-render.

Tests: replayBuffer vitest (cadence, 15 s window, deep-copy immunity,
quantize round-trip, <64 KB budget, BONES⊆subset) + backend
`tests/test_replay.py` lifecycle slice (happy path, 404 calm, 404
accelerometer, 409 stale, clear/supersede/TTL drops, oversize 422/413,
never-persisted, escalate/ack unaffected).

**Coherent because:** replay is captured, stored, lifecycle-safe, and every
claim about what leaves the browser is true — nothing displays it yet, which
is fine (an invisible upload with honest copy beats a visible panel with a
false claim).

## Phase 2 — Computed facts → deterministic rationale

`lib/pose/replayFacts.ts` (pure; computed at freeze on the watch page so the
rationale is single-sourced): `findPhases` (backward scan using the
fallHeuristic thresholds), descent duration, fall direction (screen-coords
convention documented; "toward-camera" via torso apparent-size growth),
protective arm (wrist below hip-midpoint pre-impact, null when visibility
< 0.5), post-impact movement. Null-frame policy: facts need ≥3 valid frames
per phase, else honest "not captured" text.

Backend: facts folded into `_cv_override` rationale AND appended as
`RiskFeature` rows (Descent / Fall direction / Protective response);
`/caseload` + drilldown pick them up read-through; no SSE republish.

Tests: replayFacts vitest (scripted falls left/right/toward, torso math
cross-checked against `measureFrame` on padded arrays, protective-arm
true/false/null, unknown degradation, rationale determinism) + pytest
(rationale contains facts, features carry every number, no-facts unchanged,
schema still validates).

**Coherent because:** rationale stays deterministic and guardrail-clean;
Telegram already-sent alerts keep their honest pre-facts text; escalation
upgrades naturally.

## Phase 3 — Replay player (the demo beat)

`GET /incidents/replay` (404 calm / accelerometer / not-yet-uploaded; serves
frames + phase bands shaped like `acute_trace_payload.phases`);
`dataClient.getIncidentReplay` (404 → null); `components/ReplayPlayer.tsx`
mounted beside `{acute && <TraceChart />}` — **keyed on `detail.id`** (the
cohesion sweep caught that TraceChart's empty-dep fetch pattern would show a
stale skeleton for the wrong resident; the replay panel must refetch per
drilldown). Canvas stick figure at 320×180 logical, dequantized once,
low-visibility joints faded (α 0.25), null frame = cleared canvas + "person
not tracked" note; play / ¼× slow-mo / scrubber with phase-band underlay in
the TraceChart color language (sage/sun/red-soft tokens); facts rendered as
the caption; a11y per house rules (never color-only — the facts text carries
meaning). Pure helpers in `lib/pose/replayMath.ts`, vitest-covered.

E2E: the scripted flow uses "Send test detection" (no camera), so the panel
correctly stays ABSENT — assert that, plus GET 404 semantics via the API.
The real replay beat is rehearsal-verified (fall on camera → drilldown shows
your own fall).

**Coherent because:** accelerometer incidents still render the waveform and
404 the replay; camera incidents render the replay and 404 the trace — each
sensor drills into its own raw signal, symmetric and test-pinned.

## Phase 4 — Pitch artifact sync (batch, ~1 h)

judge-brief.html (privacy sentence ×2, "no trace to show" narrowed to
"no *accelerometer* trace", test counts), deck.md slide 261 + speaker notes,
README.md, `_codebase-index.md` rows, slides.pdf re-render + refreshed
drilldown screenshots (the replay panel changes the money shot — that is a
feature). Voice: locked operator standard throughout.

## Phase 5 — OPTIONAL: Telegram keyframe PNG (only if a day remains)

Three keyframes (descent start / impact / stillness) drawn with Pillow,
`telegram.send_photo` via hand-rolled multipart (stdlib constraint), fired
off-thread after a successful `set_replay` iff configured and incident still
active — a REPLY to the alert (the alert text itself stays "written from
those fields," which keeps the ordering honest: alert first, evidence
follows). Touches the ack message-edit flow — scoped its own mini-plan if
attempted.

## Gap register (from the cohesion sweep — tracked to closure)

| Gap | Closed in |
|---|---|
| ADR 0010/0011 privacy wording (accepted, immutable) | Phase 0 supersede |
| Watch privacy box "four fields" + "those fields alone" | Phase 1 |
| feature-spec §1b amended claim + §1b "no fake waveform" split | Phase 1 / 3 |
| engine.ts docstring | Phase 1 |
| Stale replay across Reset / accel supersede / 2nd fall / TTL | Phase 1 tests |
| Facts vs briefing-numbers guardrail | Phase 2 tests |
| SSE republish double-alert trap | Phase 2 (explicitly not done) |
| TraceChart stale-fetch pattern | Phase 3 (keyed panel) |
| trace-404 test must survive | Phase 3 (separate route, test untouched) |
| judge brief / deck / README / index / screenshots / test counts | Phase 4 |
| Deleted resident mid-incident: replay follows the incident (nonce), not the name | Phase 1 test assertion |
| `docs/adr/README.md` stale index | Phase 0 |

Estimated effort: Phase 0 ~30 min · Phase 1 ~half day · Phase 2 ~half day ·
Phase 3 ~half day · Phase 4 ~1 h · Phase 5 ~half day (optional).

## Progress (2026-07-29)

Phases 0–4 SHIPPED same-day (`bbf1277` → phase-4 commit): pytest 136 /
vitest 76 / tsc clean; e2e 15/15 incl. the live replay beat + retention
assertion; slides.pdf re-rendered. Outstanding from Phase 4: the deck's
drilldown SCREENSHOTS still show the pre-replay panel — refresh them at
rehearsal with a real on-camera fall (a synthetic trace draws a single dot,
not a money shot).

**Phase 5 SHIPPED 2026-07-30, upgraded from keyframe PNGs to a full
`sendAnimation` GIF** (the Bot API supports GIF/MP4 to 50 MB; a rendered
trace is ~10 KB, so the whole replay travels, not three stills). Quiet
reply to the alert, enriched-rationale caption, single-sanctioned-exit rule
recorded in fixtures. Live Telegram delivery of the animation is
deliberately unverified — first real on-camera fall at rehearsal proves it
(the send path shares every guarantee with the text sends).
