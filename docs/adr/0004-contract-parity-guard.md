---
type: adr
diataxis: reference
title: Contract parity guarded by generated schema + types.ts field-diff
status: accepted
date: 2026-07-02
tags: [adr, contract, testing, seam]
---

# 0004. Contract parity guarded by generated schema + types.ts field-diff

- Status: Accepted
- Date: 2026-07-02

## Context
`scoring-service/app/models.py` mirrors `triage-dashboard/lib/types.ts` by hand.
The two are the whole risk surface of the seam ([[backend-architecture]] §8), yet
nothing stopped them drifting: the frontend TS compiler checks TS, FastAPI checks
responses against the models, but neither checks TS **against** the models. The
original contract test also asserted key-sets typed out by hand — itself a mirror
that could rot.

## Decision
Guard parity in three dependency-light layers (no npm build in the test path):

1. **Generated artifact** — `python -m app.contract` emits `contract.schema.json`
   (JSON Schema per endpoint payload, from the pydantic models). Live responses
   are validated against it with `jsonschema`; a test fails if the committed
   artifact is stale.
2. **TS↔Python field-diff** — `test_models_match_types_ts` parses `types.ts`
   (resolving `extends`) and asserts each interface's field set equals the
   pydantic model's aliased properties. This is the actual drift catcher.
3. **Behavioural tests** stay separate (ordering, distinct axes, 404, briefing
   guardrail).

The doc-ritual requires regenerating `contract.schema.json` on any model change.

## Consequences
- A rename/added/removed field on **either** side fails CI immediately (verified:
  a simulated `sensorClass`→`sensorKlass` rename fails the diff).
- No hand-maintained key lists; `types.ts` stays the authoritative shape.
- **Limitation:** layer 2 checks field-name parity, not deep type parity (e.g. it
  won't catch `age: string` vs `age: number`). Layer 1's schema constrains types
  on the Python side, and the frontend compiler on the TS side, so the gap is
  narrow. A stricter check (generate JSON Schema from `types.ts` via
  `ts-json-schema-generator` — node is available) is a future option if needed.
- The service stays testable standalone: layer 2 skips if `types.ts` is absent.
