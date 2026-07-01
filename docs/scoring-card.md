---
type: doc
diataxis: explanation
title: Scoring Card (Model Card + Datasheet)
status: solidified
last_updated: 2026-07-01
tags: [scoring, model-card, datasheet, ethics, limits]
---

# Scoring Card

> Combines a **Model Card** (Mitchell et al., 2019) and a **Datasheet for
> Datasets** (Gebru et al., 2021), adapted for a heuristic (non-trained) scorer.
> Purpose: state honestly what the scoring does, on what data, and where it
> fails. For an eldercare product, documenting limits *is* the credibility.

## Model Card

### Overview
Two-track risk scorer for an eldercare triage caseload. **No trained model** — a
deterministic heuristic pipeline. **Acute**: physics-based fall detection over
accelerometer magnitude. **Chronic**: self-baselining anomaly over ambient
routine signals. Output per resident: `risk` (0..1), `confidence` (0..1),
weighted `features`, deterministic `rationale`. Full mechanics: [[feature-spec]].

### Intended use
- **Primary:** rank a One Care caseworker's shift caseload so scarce attention
  goes to the highest-concern residents first, with an explainable "why".
- **Live beat:** an acute fall preempts the ranking mid-shift (push event).
- **LLM role:** smooth the `briefing` paragraph only, from facts already in
  `features`. It never invents cause and never affects `risk`/`rationale`.

### Out-of-scope / must-not
- **Not** a diagnosis, a clinical device, or a guarantee no one long-lies.
- **Not** an autonomous dispatcher — a human caseworker decides.
- **Not** a surveillance tool: ambient PIR/door presence only, no cameras/audio.
- Must **never** blend acute and chronic into one number, or conflate `risk`
  with `confidence`.

### Honest claim
Shrinks time-to-detection and stretches scarce caseworker manpower. It does not
promise to catch every event.

### Metrics & evaluation
Heuristic, so evaluated by **replayed traces**, not a training metric:
- Acute: detection rate / false-alarm rate across SisFall falls vs ADLs at the
  chosen thresholds (calibrate `2.7 g` / `0.6 g` / `500 ms` on real traces).
- Chronic: whether flagged anomalies correspond to genuine routine breaks in
  CASAS slices; watch false-positives from wide-variance residents.
- **Report numbers once calibrated** — do not claim accuracy pre-calibration.

### Ethical considerations
- **Dignity:** presence-only sensing; second-person, low-anxiety UI (Warm Human).
- **False negatives** (missed event) are the costliest error → acute detection is
  **safety-biased** (fires on suspicion; confidence carries the uncertainty).
- **False positives** cost caseworker time and can erode trust → chronic actions
  are graduated (welfare call before dispatch).
- **Fairness:** self-baselining avoids a population prior, but a resident with an
  irregular lifestyle gets wide baselines (less sensitive) — flagged as a known
  limitation, surfaced via `confidence`.
- **Transparency:** every score decomposes into human-readable features; no
  black box reaches the caseworker.

### Limitations
- Thresholds are uncalibrated until tuned on real traces.
- Chronic needs ~14 days of a resident's history for a mature baseline; new
  residents score at low confidence by design.
- A dead/blinded sensor can masquerade as inactivity — mitigated by the
  sensor-health feature feeding `confidence`, not eliminated.
- Datasets are **proxies** (below), not Singapore field data.

## Datasheet — datasets

### SisFall (acute)
- **What:** tri-axial accelerometer + gyroscope recordings of falls and ADLs.
- **Who/where:** Universidad de Antioquia, Colombia; young + elderly subjects;
  ~200 Hz; multiple fall types and daily activities.
- **Why here:** provides real fall *traces* to detect and to inject as the live
  demo incident. Used as signal, **not** for training.
- **Provenance / limits:** lab-collected, not Singapore, not in-home. Body
  placement and subject demographics differ from deployment — acceptable because
  fall detection is physics (magnitude signature), which transfers.

### CASAS (chronic)
- **What:** ambient smart-home event streams — PIR motion, door, item sensors
  with timestamps.
- **Who/where:** Washington State University CASAS project, US apartments.
- **Why here:** realistic routine/ambient streams to compute per-resident
  baselines and score deviation. Used as signal, **not** for training.
- **Provenance / limits:** US homes, US routines. Mitigated by **self-baselining**
  — each resident is scored against their own history, so no US routine prior is
  imported. Sensor layout differs per home → a per-home area-mapping file is
  required at deployment.

### Singapore deployment note
Public datasets stand in because Singapore eldercare sensor data isn't publicly
available. The method carries no geographic assumption (physics + self-baseline),
so a real deployment self-calibrates from local residents within days. This is a
**proxy for method validation**, not a claim that US/Colombian data equals
Singapore conditions.

## Change log
- 1.0 (2026-07-01) — initial card. Update the Datasheet on any dataset change and
  the Limitations/Metrics after threshold calibration ([[README]] ritual).
