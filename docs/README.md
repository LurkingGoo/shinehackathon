---
type: doc-index
title: Documentation Standard & Index
status: active
last_updated: 2026-07-01
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
   changed, note the contract-parity impact on the seam.
3. **A dataset** (new source, new slice, changed provenance) → update the
   Datasheet section of [[scoring-card]].
4. **A design decision** → add a new ADR in `docs/adr/` (never edit an accepted
   one; supersede it).

**Definition of done for a doc pass:** the right tier is updated · the change is
concrete enough to implement without asking · limitations/ethics stay honest ·
`_tools/vault-search/index.py` re-run so docs stay searchable.

> To make this ritual fire automatically from the Session Protocol it would need a
> line in the (immutable) project `CLAUDE.md` — that requires operator
> authorization. Until then it is enforced by convention here and in `state.md`.

## Conventions

- WikiLinks by basename, kebab-case, no `.md` (vault rule).
- Code is the source of truth for contracts; docs point to it, never fork it.
- Keep each doc in exactly one Diátaxis tier. If it wants to be two, split it.
