---
type: adr
diataxis: reference
title: Two-tier curated data, committed real-data artifacts baked offline
status: accepted
date: 2026-07-25
tags: [adr, data, curation, deploy, sisfall]
---

# 0008. Two-tier curated data: committed real-data artifacts baked offline

- Status: Accepted
- Date: 2026-07-25

## Context
The licensed raw datasets (SisFall, CASAS — ~786 MB) are git-ignored by rule, so
a fresh clone and the Render deploy had only the synthetic fall rotation
([[0007-public-deploy-topology]]). That kept licensed payloads out of the public
repo but meant the public demo never showed a *real* recorded fall, and the
judge-metrics classifier had no real feature table to learn on. Downloading the
raw datasets at build time was rejected earlier (mirror reliability, licence
weight, 786 MB for a demo that needs a handful of traces).

## Decision
Split the data into two tiers with an offline baking step:

- **Tier 1 — raw, git-ignored** (`data/sisfall/**`, `data/casas/**`): present
  only on a dev machine that fetched the datasets; provenance pinned in
  `data/datasets.lock.json`.
- **Tier 2 — curated, committed** (`data/curated/*.json`, ~hundreds of KB):
  baked ONCE by `scripts/curate.py` from Tier 1, using the SAME loaders and
  production detector the service runs:
  - `falls.json` — distinct real SisFall fall windows (full 200 Hz, trimmed to
    dip−1 s … impact+8 s) for the Simulate rotation and drill-down waveform;
  - `features.json` — a balanced `[peak_g, freefall_depth, impact_energy,
    stillness] × label` table for the judge-metrics classifier ([[0009-illustrative-classifier]]).

Runtime resolution order (`loaders.demo_rotation_smv`): raw Tier 1 when on disk
→ curated Tier 2 → synthetic rotation. The synthetic fallback is unchanged and
remains the guarantee that a zero-data clone still boots and demos.

## Consequences
- A fresh clone and the Render deploy now rotate GENUINE SisFall falls with zero
  download; nothing about the signal is faked or resampled (full 200 Hz windows,
  scored by the unchanged production detector).
- The committed payload stays tiny (rotation of 6 + ≤250 features per class).
- Rebake required when the detector operating point or curation logic changes —
  `scripts/curate.py` is the single producer; curated files carry a `$comment`
  naming their generator and source.
- Curated windows are short derived excerpts of a published research dataset,
  cited (Sucerquia et al., 2017); the full licensed corpus stays out of git.
- Supersedes the "synthetic-only public demo" consequence of
  [[0007-public-deploy-topology]] (that ADR's topology is otherwise unchanged).
