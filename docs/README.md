---
type: doc-index
title: Documentation Standard & Index
status: active
last_updated: 2026-07-02
tags: [documentation, standard, index]
---

# shinehackathon — Documentation

This project documents to a **defined standard**. New docs go in the right
Diátaxis tier and follow the format for their kind. This file is the index and
the standard; read it before adding docs.

## The standard stack

| Concern | Standard | Where |
|---------|----------|-------|
| Organizing framework | **Diátaxis** (Explanation · Reference · How-to · Tutorial) | tier tag in each doc's frontmatter |
| Architecture | **arc42 (lite)** | [[backend-architecture]] |
| Decisions | **MADR** (Markdown ADR) — one file per decision | `docs/adr/` |
| Scoring, datasets, limits, ethics | **Scoring Card** = Model Card (Mitchell et al.) + Datasheet for Datasets (Gebru et al.) | [[scoring-card]] |
| Concrete features | **Reference spec** — one row per feature, implementable with zero guessing | [[feature-spec]] |

## Index (by Diátaxis tier)

| Tier | Doc | Purpose |
|------|-----|---------|
| Explanation | [[backend-architecture]] | Why the system is shaped this way (arc42-lite) |
| Explanation | [[scoring-card]] | What the scoring does, on what data, with what limits & ethics |
| Reference | [[feature-spec]] | Every `RiskFeature`: inputs, formula, thresholds, weight, rationale template |
| Reference | `triage-dashboard/lib/types.ts` | The authoritative data contract (code is source of truth) |
| How-to | [[demo-runbook]] | Run the service + trigger the live re-rank demo |
| Decisions | [[adr/README]] | ADR index + MADR template |

## The documentation ritual *(mandated)*

Documentation is not optional cleanup — it is part of "done." A **documentation
pass** is required whenever any of these change:

1. **Scoring logic or a feature** → update [[feature-spec]] (bump its `spec_version`)
   and revisit the limitations in [[scoring-card]].
2. **An endpoint or the data contract** → update the Reference tier; if a shape
   changed, regenerate `scoring-service/contract.schema.json`
   (`python -m app.contract`) and check the models↔`types.ts` parity test
   ([[adr/0004-contract-parity-guard]]).
3. **A dataset** (new source, new slice, changed provenance) → update the
   Datasheet section of [[scoring-card]].
4. **A design decision** → add a new ADR in `docs/adr/` (never edit an accepted
   one; supersede it).

**Scope rule (agreed 2026-07-02):** the ritual fires on **method** changes.
Threshold *tuning* — numbers marked *(tune)* in [[feature-spec]] — requires no
doc pass and no `spec_version` bump; only the calibrated results land in
[[scoring-card]] §Metrics, and only from `scripts/calibrate.py` output.

**Definition of done for a doc pass:** the right tier is updated · the change is
concrete enough to implement without asking · limitations/ethics stay honest ·
`_tools/vault-search/index.py` re-run so docs stay searchable.

> To make this ritual fire automatically from the Session Protocol it would need a
> line in the (immutable) project `CLAUDE.md` — that requires operator
> authorization. Until then it is enforced by convention here and in `state.md`.

## Rendered site (localhost)

The suite renders as a browsable **MkDocs Material** site (config: `mkdocs.yml`
at the project root; Obsidian wikilinks handled by `roamlinks`):

```bash
cd shinehackathon
python -m mkdocs serve -a 127.0.0.1:8001    # http://127.0.0.1:8001
python -m mkdocs build                      # static site → .mkdocs-site/ (git-ignored)
```

The markdown in `docs/` remains the single source of truth — the site is only a
renderer. New docs must be added to the `nav:` section of `mkdocs.yml`.

## Data provenance (process-as-code)

No dataset enters the pipeline by hand. `scoring-service/scripts/fetch_datasets.py`
downloads every source, records **URL + sha256 + size + fetch date + citation**
in `scoring-service/data/datasets.lock.json` (committed; the data itself is
git-ignored), and refuses artifacts whose checksum drifts from the lock.
`--verify` re-checks a machine against the lock. The [[scoring-card]] Datasheet
cites the lock as its provenance record. The full data flow — which bytes come
from where and what touches them — is documented in [[scoring-card]] (Datasheet)
and [[backend-architecture]] §Topology/Data flows.

## Conventions

- WikiLinks by basename, kebab-case, no `.md` (vault rule).
- Code is the source of truth for contracts; docs point to it, never fork it.
- Keep each doc in exactly one Diátaxis tier. If it wants to be two, split it.
