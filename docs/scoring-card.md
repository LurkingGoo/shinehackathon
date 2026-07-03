---
type: doc
diataxis: explanation
title: Scoring Card (Model Card + Datasheet)
status: solidified
last_updated: 2026-07-02
tags: [scoring, model-card, datasheet, ethics, limits]
---

# Scoring Card

> Combines a **Model Card** (Mitchell et al., 2019) and a **Datasheet for
> Datasets** (Gebru et al., 2021), adapted for a heuristic (non-trained) scorer.
> Purpose: state honestly what the scoring does, on what data, and where it
> fails. For an eldercare product, documenting limits *is* the credibility.

## Model Card

### Overview
Two-track risk scorer for an eldercare triage caseload. **No trained model**,
just a deterministic heuristic pipeline. **Acute**: physics-based fall detection over
accelerometer magnitude. **Chronic**: self-baselining anomaly over ambient
routine signals. Output per resident: `risk` (0..1), `confidence` (0..1),
weighted `features`, deterministic `rationale`. Full mechanics: [[feature-spec]].

### Intended use
- **Primary:** rank a One Care caseworker's shift caseload so scarce attention
  goes to the highest-concern residents first, with an explainable "why".
- **Live beat:** an acute fall preempts the ranking mid-shift (push event).
- **Drafting layer's role:** smooth the `briefing` paragraph only, from facts
  already in `features`. It never invents cause and never affects
  `risk`/`rationale`.

### Out-of-scope / must-not
- **Not** a diagnosis, a clinical device, or a guarantee no one long-lies.
- **Not** an autonomous dispatcher: a human caseworker decides.
- **Not** a surveillance tool: ambient PIR/door presence only, no cameras/audio.
- Must **never** blend acute and chronic into one number, or conflate `risk`
  with `confidence`.

### Honest claim
Shrinks time-to-detection and stretches scarce caseworker manpower. It does not
promise to catch every event.

### Metrics & evaluation
Heuristic, so evaluated by **replayed traces**, not a training metric.

**Calibrated 2026-07-02 on the full real SisFall dataset** (1,798 falls /
2,707 ADLs, 38 subjects; `scripts/calibrate.py --grid`, provenance in
`scoring-service/data/datasets.lock.json`):

| Operating point | Detection | False-alarm (ADLs) |
|---|---|---|
| Pre-calibration (0.6 g / 2.7 g / 80 ms / 500 ms) | 51.8% | 17.8% |
| **Calibrated (0.8 g / 2.3 g / 40 ms / 500 ms)** | **96.2%** | 29.8% |

Chosen sensitivity-first (missed falls are the costliest error, below). The
full trade-off and rejected alternative are recorded in
[[0005-sensitivity-first-operating-point]]. The
29.8% false-alarm rate is on SisFall's **deliberately fall-like ADLs**
performed by young adults; per-activity split (`scripts/fa_breakdown.py`):
alarms concentrate ~100% in vigorous activities (jogging, jumping obstacles,
running stairs, car ingress/egress, collapsing into a chair), while
elderly-typical movements (walking slowly, slow sits, lying down, stooping,
even **stumbling without falling**) trigger at 0–5%. Daily alarm load on a
monitored elderly resident is therefore far below the headline ADL rate.

- Demo incident trace (pinned): SisFall `F11_SA16_R03`: **11.2 g** peak
  impact, **12 s** post-impact stillness. This is the fall replayed by
  `POST /incidents/simulate` and the numbers shown on the acute card.
- Chronic: real-resident validation via CASAS Aruba (220 days). The
  self-baselined features recover a genuine routine (typ. kitchen gap 4.2 h,
  first door-open 09:35, 3.8 night bathroom trips) and `--demo-day auto`
  isolates a genuinely broken day (2011-02-19: 11.1 h kitchen gap, z ≈ 3.2).
  Watch false-positives from wide-variance residents.

### Ethical considerations
- **Dignity:** presence-only sensing; second-person, low-anxiety UI (Warm Human).
- **False negatives** (missed event) are the costliest error → acute detection is
  **safety-biased** (fires on suspicion; confidence carries the uncertainty).
- **False positives** cost caseworker time and can erode trust → chronic actions
  are graduated (welfare call before dispatch).
- **Fairness:** self-baselining avoids a population prior, but a resident with an
  irregular lifestyle gets wide baselines (less sensitive), flagged as a known
  limitation, surfaced via `confidence`.
- **Transparency:** every score decomposes into human-readable features; no
  black box reaches the caseworker.

### Limitations
- Acute thresholds are calibrated on SisFall (waist-worn sensor, mostly young
  adults; 15 elderly for ADLs only). The fall physics transfers, but the
  false-alarm profile on a genuinely elderly cohort is extrapolated, not measured.
- Chronic needs ~14 days of a resident's history for a mature baseline; new
  residents score at low confidence by design.
- A dead/blinded sensor can masquerade as inactivity; mitigated by the
  sensor-health feature feeding `confidence`, not eliminated.
- Datasets are **proxies** (below), not Singapore field data.

## Datasheet: datasets

### Provenance (process-as-code)
Datasets are fetched ONLY via `scoring-service/scripts/fetch_datasets.py`, which
pins **source URL + sha256 + size + fetch date + citation** in the committed
`scoring-service/data/datasets.lock.json` and refuses checksum drift. Community
mirrors are used (original SisFall host is down; CASAS moved to a 2.7 GB
all-homes Zenodo bundle); citations below reference the original publications.
The Aruba sensor→area layout file is derived from the dataset's own activity
annotations by `scripts/derive_area_map.py`. Labels reconstruct the *layout*
(a deployment artifact an installer normally writes), they never train or score.

### SisFall (acute)
- **What:** tri-axial accelerometer + gyroscope recordings of falls and ADLs.
- **Who/where:** Universidad de Antioquia, Colombia; young + elderly subjects;
  ~200 Hz; multiple fall types and daily activities.
- **Why here:** provides real fall *traces* to detect and to inject as the live
  demo incident. Used as signal, **not** for training.
- **Provenance / limits:** lab-collected, not Singapore, not in-home. Body
  placement and subject demographics differ from deployment. Acceptable because
  fall detection is physics (magnitude signature), which transfers.

### CASAS (chronic)
- **What:** ambient smart-home event streams (PIR motion, door, item sensors
  with timestamps).
- **Who/where:** Washington State University CASAS project, US apartments.
- **Why here:** realistic routine/ambient streams to compute per-resident
  baselines and score deviation. Used as signal, **not** for training.
- **Provenance / limits:** US homes, US routines. Mitigated by **self-baselining**:
  each resident is scored against their own history, so no US routine prior is
  imported. Sensor layout differs per home → a per-home area-mapping file is
  required at deployment.

### Singapore deployment note
Public datasets stand in because Singapore eldercare sensor data isn't publicly
available. The method carries no geographic assumption (physics + self-baseline),
so a real deployment self-calibrates from local residents within days. This is a
**proxy for method validation**, not a claim that US/Colombian data equals
Singapore conditions.

## Change log
- 1.0 (2026-07-01): initial card. Update the Datasheet on any dataset change and
  the Limitations/Metrics after threshold calibration ([[README]] ritual).
