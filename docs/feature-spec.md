---
type: doc
diataxis: reference
title: Feature Specification (concrete)
status: solidified
spec_version: 1.11.0
last_updated: 2026-07-29
tags: [features, scoring, reference]
---

# Feature Specification

> **Reference tier.** Every `RiskFeature` the scoring service emits, concrete
> enough to implement with zero guessing. Bump `spec_version` on any change and
> run a doc pass ([[README]]). Thresholds marked *(tune)* are starting points to
> calibrate on the real SisFall/CASAS traces: the *method* is fixed, the numbers
> are tunable. Contract these feed: `RiskFeature` in `triage-dashboard/lib/types.ts`.

## 0. Common definitions

- **`RiskFeature`** = `{ label, value, weight, baseline }` (display strings +
  `weight` 0..1). The set of features for a resident is the *entire* explanation
  of their score; nothing enters `risk`/`rationale` that isn't a feature.
- **risk** (0..1) = sum of absolute weighted feature contributions
  (`Σ wᵢ·aᵢ`, clipped), comparable across residents (§2,
  [[0003-absolute-weight-risk-aggregation]]).
- **confidence** (0..1) = data quality axis (completeness · sensor health ·
  baseline maturity). **Never** mixed into risk.
- **rationale** = deterministic template filled from the top feature(s).
- **recommendedAction** = rule-table lookup on `(track, top-feature, risk band)`.
- **Risk bands:** `low < 0.40 ≤ watch < 0.70 ≤ elevated < 0.85 ≤ high`.

---

## 1. ACUTE track: fall detection (SisFall, physics)

**Source signal.** Tri-axial accelerometer, ~200 Hz (SisFall: ADXL345 / MMA8451Q).
Compute the **signal-magnitude vector** per sample:
`SMV = √(ax² + ay² + az²)`, in g (1 g = rest).

**Detection sequence** (a fall is the *ordered* co-occurrence, not any single
threshold; this is what rejects normal ADLs like sitting hard):

1. **Free-fall dip:** `SMV < 0.8 g` sustained ≥ 40 ms.
2. **Impact peak:** within ≤ 500 ms of the dip, `SMV > 2.3 g`.
3. **Post-impact stillness:** for the next ~10 s, `SMV` variance below the
   subject's active-motion band (person is down and not rising).

*(Operating point calibrated 2026-07-02 on the full real SisFall set via
`scripts/calibrate.py --grid`: 96.2 % detection. Trade-off recorded in
[[0005-sensitivity-first-operating-point]] and [[scoring-card]] §Metrics.
Pre-calibration starting points were 0.6 g / 2.7 g / 80 ms.)*

If (1)→(2) fire, emit an **acute** score and an `IncidentEvent`. (3) upgrades
severity (long-lie) but is not required to fire.

### Acute features

| `label` | Inputs | Computation | `weight` source | `baseline` | Edge / failure |
|---------|--------|-------------|-----------------|-----------|----------------|
| Impact severity | SMV peak (g) | `min(1, (peak − 2.7)/(6 − 2.7))` | dominant (0.5–0.6) | `typ. rest ≈ 1.0 g` | Dropped phone mimics peak → require the free-fall dip first |
| Free-fall duration | dip window (ms) | `min(1, dip_ms/300)` | 0.2–0.3 | `typ. 0 ms` | Very short dips (stumble) → lower weight, may route to chronic frailty |
| Post-impact inactivity | SMV variance after impact | inactivity seconds → `min(1, s/120)` | 0.1–0.2, **severity escalator** | `typ. resumes < 20 s` | If the person rises quickly, weight→low; still logged |

**risk (acute).** A *detected* fall is definitionally top-priority (it preempts
the ranking), so risk floors high and scales with impact severity:
`risk = clamp(0.9 + 0.1·severity, 0, 1)`, `severity = (peak − 2.7)/(6 − 2.7)`.
It is **not** a chronic weighted sum. Undetected → a low residual (`0.2·severity`)
so a non-event can never outrank genuine chronic concern.

**confidence (acute)** = `f(signal continuity, sensor sample-rate health)`. A gap
in accelerometer stream during the event lowers confidence but the event still
fires (safety-biased).

**rationale template:** `"Fall detected — {peak} g impact, {dip_ms} ms free-fall."`
**recommendedAction:** always top band → `"Call resident now; dispatch if no
answer within 2 min."` (long-lie present → `"Dispatch now — no movement {mins} min
after impact."`)

---

## 1b. ACUTE source: camera pose heuristic (spec 1.4.0; browser half shipped 1.6.0)

A second acute *source* feeding the SAME incident path (caseload preemption,
SSE, alert dispatch): the browser MediaPipe pose heuristic (upright →
horizontal → still) POSTs `/incidents/cv-detected`. Honesty rules, enforced by
tests (`tests/test_cv.py`):

- `sensor` is labelled **camera (pose)** — never presented as accelerometer.
- `confidence` is the browser heuristic's own estimate (default 0.72-band),
  **never** the calibrated detector's number; the 96.2% claim applies only to
  the SisFall-calibrated accelerometer track (§1).
- `risk = 1.0` — a detected fall is definitionally top-priority (same floor
  rule as §1).
- No fake waveform: `/incidents/trace` **404s** for a camera incident (there is
  no accelerometer trace to show).

**Long-lie escalation, acknowledgement, zone (spec 1.8.0, [[0012-escalation-ack-zone]]).**
Post-fire, the browser state machine keeps watching: still on the ground
**45 s** *(tune)* after the alert → ONE `still-down` event →
`POST /incidents/escalate` → the "STILL DOWN" Telegram message (any upright
frame cancels; escalation is a message, never a new incident). The fall alert
carries an inline **"I am responding"** button; a getUpdates poller records
`{by, at}`, surfaced as `acknowledged` on `/alerts/status` and a dashboard
badge, cleared per incident. The ack is chat-visible (1.8.1): the alert
message is edited to append "✅ <name> is responding — acknowledged HH:MM"
(the edit also drops the button) and a quiet reply pins the responder under
the alert. First responder wins — a second tap is answered with who already
has it and changes nothing. `CaseloadEntry` gains optional `zone` (the
resident's ambient last-motion area); the alert location line is
`{unit} · last motion: {zone}` — PIR context, never a camera localization
claim.

**Named identity (spec 1.7.0, [[0011-enrolled-face-identity]]).** The event
body accepts an optional `residentId`; a known id makes THAT resident the
acute row across every surface (caseload, SSE, Telegram, `/alerts/status`),
and an absent or unknown id falls back to the generic default — recognition
can never block or alter an alert. Identity comes from opt-in on-device
enrollment (front + both profiles → embeddings in localStorage, matched only
while the person is upright, carried through the pose track). Amended privacy
claim: no video leaves the browser; only the detection event and the matched
resident id are sent.

**Browser half (shipped 1.6.0, [[0010-browser-pose-assets]]).** The `/watch`
dashboard page runs MediaPipe PoseLandmarker (lite) entirely in-browser —
no frame leaves the device; assets are vendored by `npm run fetch-pose-assets`
with a CDN fallback. Detection logic is the pure state machine
`lib/pose/fallHeuristic.ts` (vitest-tested): upright → horizontal within
**3.0 s** *(tune; widened from 1.8 s in 1.7.1 — a person mimicking a fall
self-protects and reaches the floor in ~2–2.5 s, which the old window
rejected as a lie-down; the slower descent honestly earns lower confidence)*
→ continuous stillness (mean landmark motion < 0.012
normalized units/frame *(tune)*) for **3.0 s** → fire, then a 10 s cooldown.
Posture from torso lean vs vertical: upright < 35°, horizontal > 48° *(tune;
lowered from 60° in 1.7.1 — a screen-mounted webcam foreshortens a real drop
into the 45–55° band; torso-visibility floor loosened 0.5 → 0.4 alongside).
The transitional dead band is now 35–48°: rehearsal must include
false-positive checks (bend-over, crouch, shoe-tie held still ≥ 3 s).
A slower transition is a deliberate lie-down and never alarms. Confidence =
0.55 + 0.30·(transition speed), capped 0.85 — the heuristic's own band, per
the honesty rules above.

## 2. CHRONIC track: routine anomaly (CASAS, self-baselining)

**Source signal.** CASAS ambient events: PIR motion (`M###`), door (`D###`),
optionally item/temperature sensors. Each event = `(timestamp, sensor, state)`.
Sensors are mapped to **areas** (kitchen, bedroom, bathroom, front-door) via a
per-home layout file.

**Baseline (self-referential, no population prior).** For each resident, from
their **own** trailing history (target ≥ 14 days), precompute per feature a
typical value + spread, stored in `baselines.json`:
`{ mean, std, typical_display }`. This is why the method is **Singapore-portable**:
the resident is their own control; nothing US-specific transfers.

**Live anomaly score** per feature:
`z = (observed − mean) / max(std, ε)`, directed by the feature's **side**, then
squash `a = clamp(z' / Z_CAP, 0, 1)` with `Z_CAP = 4` *(tune)*. Gap-type
features use a ratio `observed_gap / typical_gap` instead of z where a
distribution is thin.

**Directionality (`side`, spec 1.3.0).** Each feature declares which departure
from baseline is concerning: `high` (`z' = z`, e.g. kitchen gap), `low`
(`z' = −z`, e.g. activity volume), or `both` (`z' = |z|`, e.g. night trips,
where more suggests UTI/decline and fewer corroborates inactivity; or door
timing, where any break in the routine is signal). Motivated by the real CASAS resident's broken
day (2011-02-19): two of three signals broke *downward* and scored 0 under
one-sided scoring, dropping the genuinely anomalous resident to rank 2.
Implemented as `chronic.anomaly(..., side)` / `ChronicFeatureInput.side`.

**Aggregate:** `risk = clamp(Σ(weightᵢ · aᵢ), 0, 1)`, the **sum of absolute
weighted contributions**, NOT a per-resident weighted mean. Weights are
pre-calibrated importances that sum to ≤ 1, so a resident with one dominant
feature does not have that feature renormalized to 100 % of their score. This
keeps `risk` **comparable across residents**, the property the ranking depends
on. Implemented as `chronic.contribution_risk`; see
[[0003-absolute-weight-risk-aggregation]]. (`chronic.aggregate_risk`, the
weighted *mean*, remains for relative-weight uses.)

### Chronic features (aligned to current fixtures)

| `label` | Inputs (sensors → area) | Computation | `side` | `weight` | `baseline` display | Edge / failure |
|---------|-------------------------|-------------|--------|----------|--------------------|----------------|
| Kitchen inactivity | kitchen PIR gap since last fire | hours since last kitchen motion → z vs baseline gap | high | 0.45–0.55 | `typ. < 4h` | Resident out (door opened + gone) → suppress, don't score as anomaly |
| Front door timing | front-door sensor, first-open time | today's first open vs typical first-open hour | both | 0.10–0.20 | `typ. 08:10` | Weekend/routine variance → wide std absorbs it |
| Last confirmed motion | any PIR, most recent | recency string + area; low weight, context | high | 0.10–0.20 | `""` | Sensor fault looks like inactivity → cross-check sensor-health feature |
| Night activity (bathroom trips) | bathroom PIR during sleep window | PIR fires clustered into **visits** (fires ≥ 10 min *(tune)* apart = new trip) vs baseline nightly trips | both | 0.15–0.25 | `typ. 3–4` | UTI/decline signal; abnormal count either way ⇒ elevated. Raw fires overcount ~17× (a PIR refires per visit; measured on CASAS Aruba) |
| Activity volume | all PIR fires / hour, rolling | today's daily total vs baseline daily total | low | 0.10–0.20 | `typ. N fires/day` | Whole-day low volume corroborates inactivity |
| Sensor-health / data gap | per-sensor last-seen | stale sensor → flags **confidence**, not risk | n/a | (feeds confidence) | `all reporting` | Prevents a dead sensor from reading as "resident inactive" |

**confidence (chronic)** = `min(data_completeness, sensor_health, baseline_maturity)`
where `baseline_maturity = min(1, days_of_history / 14)`. A resident onboarded 2
days ago scores with honestly *low* confidence; the UI shows it as a separate axis.

**rationale template (example):**
`"No {area} activity in {duration} — usually {baseline_behavior}."`
→ `"No kitchen activity in 16h — usually eats by 08:00."` (matches fixture).

**recommendedAction (rule table, excerpt):**

| Top feature | Risk band | Action |
|-------------|-----------|--------|
| Kitchen inactivity | elevated+ | `"Welfare call; if no answer, request a doorstep check."` |
| Night activity | watch+ | `"Note pattern; flag for GP if trend continues 3+ nights."` |
| Front door not opened | watch | `"Low priority — confirm on next scheduled contact."` |

---

## 3. Determinism guarantee

The pipeline `features → risk → rationale → recommendedAction` is **pure**: same
inputs ⇒ same outputs, no randomness, nothing generative in the scoring path.
The only machine-drafted text is the `briefing` string (see [[scoring-card]]
§Intended use), which paraphrases facts already present in `features` and may
**never** introduce a cause not in the feature set. A contract test asserts the
`briefing` contains no numbers absent from `features`.

## 4. Planned features (post-MVP)

Tracked in [[backend-architecture]] §7. Each new feature: add a row above, define
its baseline source and weight, add a rationale template, bump `spec_version`,
and run a doc pass.

## 5. Outside the scoring path (spec 1.4.0)

Two surfaces that deliberately do NOT participate in `features → risk →
rationale → recommendedAction` and cannot affect any resident's score:

- **`GET /training-stats`** — the ILLUSTRATIVE deterministic logistic
  regression over curated SisFall magnitude features
  ([[0009-illustrative-classifier]]). Serves the judge-metrics page (`/training`
  on the dashboard); its ~80% ceiling motivates the ordered-signature detector
  (§1). Payload carries a `$note` stating it never scores a resident. Since
  spec 1.5.0 it also carries `convergence` (loss + held-out accuracy RECORDED
  from the actual gradient-descent run, sampled every 100 iterations) and
  `splitSensitivity` (real re-fits at 60/40, 70/30, 80/20 train/test on the
  deterministic interleaved order, each with its own held-out confusion
  matrix) — measured numbers only, nothing parametric or simulated.
- **Telegram alert dispatch** (`app/alerts/telegram.py`) — delivery only, off
  the request thread, fired AFTER the incident event is built. A silent no-op
  when `SHINEHACKATHON_TELEGRAM_BOT_TOKEN` / `_CHAT_ID` are unset; best-effort
  otherwise (a failed send never delays or alters the incident). Secrets live
  in env vars only (vault rule 8).
- **Runtime resident registry (spec 1.9.0, [[0013-runtime-resident-registry]])**
  — `POST /residents` (register a person by name; joins the chronic roster
  with a nominal input set scored by the real pipeline — calm risk,
  honestly-low confidence from a day-old baseline) and
  `POST /residents/{id}/location` (key in `zone` and/or an address composed
  from `unit` > `block`+`unitNumber` > `block` > GPS `lat`/`lon`; empty `zone`
  reverts to the fixture default). Nothing keyed in → zone defaults to
  "Living room". `ResidentDetail` gains optional `zone` (additive, mirroring
  `CaseloadEntry.zone` from 1.8.0). Registrants + overrides persist in
  `data/residents.json` (demo state, gitignored) across service restarts.
  No scoring rule changed — the registry only edits who is on the roster and
  where they are.
- **Resident deletion (spec 1.10.0, [[0014-resident-deletion-cascade]])** —
  `DELETE /residents/{id}`: 200 for a runtime registrant, 409 for the fixture
  roster (demo narrative, never deletable), 404 unknown. `CaseloadEntry` gains
  optional `registered?: boolean` (additive) so the UI gates the affordance.
  Cascade: roster + `data/residents.json`; a deleted person who is the active
  camera-named acute identity reverts the incident to the generic default
  (fail-open — no alert surface ever carries a deleted name). Browser-side:
  face embeddings forgotten, sticky binding reset if bound to the deleted id,
  all selectors cleared.
- **On-device audio fall alerts (spec 1.10.0, [[0015-on-device-audio-alerts]])**
  — at dispatch time the watch station chimes and SPEAKS "Patient has fallen!
  Patient has fallen!" (plus the bound name + zone — the same facts the
  Telegram alert carries), via Web Speech + WebAudio, fully offline. The
  long-lie escalation (ADR 0012) speaks a sharper "still down" line. Persisted
  stage-bar toggle, default ON; playback is best-effort and can never delay or
  break the incident path. Outside the scoring path — presentation only.
- **Acknowledgement from the dashboard + re-speak loop (spec 1.11.0,
  [[0016-dashboard-ack-and-respeak]])** — `POST /alerts/ack` (`{by}`, default
  "Dashboard"): a second ack source with the SAME first-responder-wins rule as
  the Telegram tap (`already: true` when owned; 404 while calm). The watch
  station re-speaks the fall call-out every 20 s until an ack lands (then
  announces the responder once), the incident clears, or 15 repeats pass;
  the sound toggle mutes ticks without killing the loop. Dashboard shows a
  stop-alert button only while acute + unacknowledged. The ack endpoint never
  touches incident state, so Simulate / Reset are unaffected. A dashboard ack
  is mirrored into the Telegram chat (button stripped + quiet reply) when
  configured. `/watch` also gains the privacy acknowledgment box (what leaves
  the browser: four named fields, never video/images/embeddings).
- **Enrollment capture gating (spec 1.10.0)** — the capture control sits
  directly under the camera feed and enables only when: camera running, face
  models ready, a target chosen, no capture in flight, under the 5-angle cap,
  and a face embed succeeded within the last 2 s (`FACE_SEEN_FRESH_MS`). Face
  embeds now tick whenever the face engine is on; the IDENTITY tracker is
  still fed only on upright ticks with a non-empty gallery (ADR 0011
  semantics unchanged — nothing is recognized mid-fall).
