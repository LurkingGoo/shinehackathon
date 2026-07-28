---
diataxis: explanation
title: "ADR 0013 — Runtime resident registry: keyed-in locations + operator-registered people"
status: accepted
date: 2026-07-28
tags: [adr, registry, alerts, dashboard]
---

# ADR 0013 — Runtime resident registry: keyed-in locations + operator-registered people

## Status
Accepted 2026-07-28 (operator-directed). Extends [[0012-escalation-ack-zone]];
does not supersede it.

## Context

The roster is hardcoded Python literals in `app/data/fixtures.py`. The zone
field already flows end-to-end (caseload → dashboard contract → Telegram
`{unit} · last motion: {zone}` line, ADR 0012), but nothing can *change* a
resident's location at runtime, and nobody new can be added. For the demo the
operator wants to key in a location for any default resident, register a person
under their own name (a judge sees a live alert with their name), and have both
sync through the dashboard and the Telegram alert — with a default location
standing in whenever nothing is keyed in.

## Decision

A small mutable registry layered on the existing fixture roster, all additive:

### 1. Registry + endpoints

`fixtures.py` keeps `CHRONIC`/`ACUTE` as the seed roster and gains:

- `register_resident(name, ...)` — appends a `ChronicResident` with a nominal
  input set (`anomaly 0.0`), `days_of_history=1`, `data_quality=0.6`. The
  scoring pipeline is untouched: a just-registered person scores real-but-calm
  risk with **honestly-low confidence** (`baseline_maturity = days/14`,
  feature-spec §2) — low confidence here is the truth, not a bug.
- `set_resident_location(rid, ...)` — updates zone and/or unit for any roster
  resident (chronic or acute). Empty-string `zone` reverts to that resident's
  fixture default (snapshotted at import).
- `reset_registry()` — drops registrants and restores defaults (tests + demo
  reset; deliberately NOT wired into `/incidents/clear`, which resets the
  incident beat, not the roster).

`main.py` gains two mutations, POST like every other mutation on the service:
`POST /residents` (register; returns the new `CaseloadEntry`) and
`POST /residents/{rid}/location` (404 unknown). PATCH was rejected — the
service and CORS config are uniformly GET+POST and the demo gains nothing.

### 2. Location model — zone, and an optional address

"Location" stays two-layer, matching the alert line:

- **zone** — in-flat last-motion area. Keyed in free-text (UI suggests the
  known zones). **Fallback: absent/empty → "Living room"**, the same dataclass
  default as ADR 0012 — nothing keyed in always yields a valid default.
- **unit** — the address string. Composed from optional parts, first match
  wins: explicit `unit` → `Blk {block} #{unitNumber}` → `Blk {block}` →
  `GPS {lat:.4f}, {lon:.4f}` → keep/“Address not set”. The GPS form backs the
  browser's "Use my location" button (`navigator.geolocation`, no reverse
  geocoding — offline demo, no external calls; honest raw coordinates).

### 3. Persistence

Mutations write `data/residents.json` (registrants + per-resident overrides),
loaded at import. Survives the rehearsal ritual of restarting both services;
in-memory-only was rejected for exactly that ritual. Gitignored like the other
`data/` artifacts — demo state, not source.

### 4. Sync surfaces

- Telegram: zero change — the alert already renders the entry's zone/unit.
- Dashboard: `ResidentDetail` gains optional `zone` (additive, mirroring
  `CaseloadEntry.zone`); `CaseloadCard` and `DrilldownPanel` now render it.
- `/watch` gains a "People & locations" card (target picker → name field when
  "New person", zone/block/unit inputs, geolocation button); registering
  refetches the caseload so Report-as and Enroll-as pick up the person.
- The main dashboard reads the caseload on load — a registration made on
  /watch appears there on refresh (no roster-change push channel; an SSE
  roster event was rejected as demo-needless).

## Consequences

- A judge can be registered by name mid-demo and their fall alert names them,
  with their keyed-in location, end to end.
- Two new endpoints, two `next.config.mjs` rewrites (`/api/residents`,
  `/api/residents/:id/location` — the latter must precede the `:id` rewrite).
- `contract.schema.json` regenerated (ResidentDetail.zone); types.ts mirrors.
- `data/residents.json` is demo state: delete it (or `reset_registry()`) to
  return to the stock roster.
- feature-spec bumps to 1.9.0.
