---
type: doc
diataxis: reference
title: Feature Specification (concrete)
status: solidified
spec_version: 1.1.0
last_updated: 2026-07-01
tags: [features, scoring, reference]
---

# Feature Specification

> **Reference tier.** Every `RiskFeature` the scoring service emits, concrete
> enough to implement with zero guessing. Bump `spec_version` on any change and
> run a doc pass ([[README]]). Thresholds marked *(tune)* are starting points to
> calibrate on the real SisFall/CASAS traces — the *method* is fixed, the numbers
> are tunable. Contract these feed: `RiskFeature` in `triage-dashboard/lib/types.ts`.

## 0. Common definitions

- **`RiskFeature`** = `{ label, value, weight, baseline }` (display strings +
  `weight` 0..1). The set of features for a resident is the *entire* explanation
  of their score — nothing enters `risk`/`rationale` that isn't a feature.
- **risk** (0..1) = sum of absolute weighted feature contributions
  (`Σ wᵢ·aᵢ`, clipped) — comparable across residents (§2,
  [[0003-absolute-weight-risk-aggregation]]).
- **confidence** (0..1) = data quality axis (completeness · sensor health ·
  baseline maturity). **Never** mixed into risk.
- **rationale** = deterministic template filled from the top feature(s).
- **recommendedAction** = rule-table lookup on `(track, top-feature, risk band)`.
- **Risk bands:** `low < 0.40 ≤ watch < 0.70 ≤ elevated < 0.85 ≤ high`.

---

## 1. ACUTE track — fall detection (SisFall, physics)

**Source signal.** Tri-axial accelerometer, ~200 Hz (SisFall: ADXL345 / MMA8451Q).
Compute the **signal-magnitude vector** per sample:
`SMV = √(ax² + ay² + az²)`, in g (1 g = rest).

**Detection sequence** (a fall is the *ordered* co-occurrence, not any single
threshold — this is what rejects normal ADLs like sitting hard):

1. **Free-fall dip:** `SMV < 0.6 g` *(tune)* sustained ≥ 80 ms.
2. **Impact peak:** within ≤ 500 ms *(tune)* of the dip, `SMV > 2.7 g` *(tune)*.
3. **Post-impact stillness:** for the next ~10 s, `SMV` variance below the
   subject's active-motion band (person is down and not rising).

If (1)→(2) fire, emit an **acute** score and an `IncidentEvent`. (3) upgrades
severity (long-lie) but is not required to fire.

### Acute features

| `label` | Inputs | Computation | `weight` source | `baseline` | Edge / failure |
|---------|--------|-------------|-----------------|-----------|----------------|
| Impact severity | SMV peak (g) | `min(1, (peak − 2.7)/(6 − 2.7))` | dominant (0.5–0.6) | `typ. rest ≈ 1.0 g` | Dropped phone mimics peak → require the free-fall dip first |
| Free-fall duration | dip window (ms) | `min(1, dip_ms/300)` | 0.2–0.3 | `typ. 0 ms` | Very short dips (stumble) → lower weight, may route to chronic frailty |
| Post-impact inactivity | SMV variance after impact | inactivity seconds → `min(1, s/120)` | 0.1–0.2, **severity escalator** | `typ. resumes < 20 s` | If the person rises quickly, weight→low; still logged |

**risk (acute)** — a *detected* fall is definitionally top-priority (it preempts
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

## 2. CHRONIC track — routine anomaly (CASAS, self-baselining)

**Source signal.** CASAS ambient events: PIR motion (`M###`), door (`D###`),
optionally item/temperature sensors. Each event = `(timestamp, sensor, state)`.
Sensors are mapped to **areas** (kitchen, bedroom, bathroom, front-door) via a
per-home layout file.

**Baseline (self-referential — no population prior).** For each resident, from
their **own** trailing history (target ≥ 14 days), precompute per feature a
typical value + spread, stored in `baselines.json`:
`{ mean, std, typical_display }`. This is why the method is **Singapore-portable**:
the resident is their own control; nothing US-specific transfers.

**Live anomaly score** per feature:
`z = (observed − mean) / max(std, ε)`, then squash `a = clamp(z / Z_CAP, 0, 1)`
with `Z_CAP = 4` *(tune)*. Gap-type features use a ratio
`observed_gap / typical_gap` instead of z where a distribution is thin.

**Aggregate:** `risk = clamp(Σ(weightᵢ · aᵢ), 0, 1)` — the **sum of absolute
weighted contributions**, NOT a per-resident weighted mean. Weights are
pre-calibrated importances that sum to ≤ 1, so a resident with one dominant
feature does not have that feature renormalized to 100 % of their score. This
keeps `risk` **comparable across residents** — the property the ranking depends
on. Implemented as `chronic.contribution_risk`; see
[[0003-absolute-weight-risk-aggregation]]. (`chronic.aggregate_risk`, the
weighted *mean*, remains for relative-weight uses.)

### Chronic features (aligned to current fixtures)

| `label` | Inputs (sensors → area) | Computation | `weight` | `baseline` display | Edge / failure |
|---------|-------------------------|-------------|----------|--------------------|----------------|
| Kitchen inactivity | kitchen PIR gap since last fire | hours since last kitchen motion → z vs baseline gap | 0.45–0.55 | `typ. < 4h` | Resident out (door opened + gone) → suppress, don't score as anomaly |
| Front door not opened | front-door sensor, first-open time | today's first open vs typical first-open hour | 0.10–0.20 | `typ. 08:10` | Weekend/routine variance → wide std absorbs it |
| Last confirmed motion | any PIR, most recent | recency string + area; low weight, context | 0.10–0.20 | `""` | Sensor fault looks like inactivity → cross-check sensor-health feature |
| Night activity (bathroom trips) | bathroom PIR during sleep window | count vs baseline nightly count | 0.15–0.25 | `typ. 0–1` | UTI/decline signal; high count ⇒ elevated |
| Activity volume | all PIR fires / hour, rolling | today's daily total vs baseline daily total | 0.10–0.20 | `typ. N fires/day` | Whole-day low volume corroborates inactivity |
| Sensor-health / data gap | per-sensor last-seen | stale sensor → flags **confidence**, not risk | (feeds confidence) | `all reporting` | Prevents a dead sensor from reading as "resident inactive" |

**confidence (chronic)** = `min(data_completeness, sensor_health, baseline_maturity)`
where `baseline_maturity = min(1, days_of_history / 14)`. A resident onboarded 2
days ago scores with honestly *low* confidence — the UI shows it as a separate axis.

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
inputs ⇒ same outputs, no randomness, no LLM. The only LLM touch is the
`briefing` string (see [[scoring-card]] §Intended use), which paraphrases facts
already present in `features` and may **never** introduce a cause not in the
feature set. A contract test asserts the `briefing` contains no numbers absent
from `features`.

## 4. Planned features (post-MVP)

Tracked in [[backend-architecture]] §7. Each new feature: add a row above, define
its baseline source and weight, add a rationale template, bump `spec_version`,
and run a doc pass.
