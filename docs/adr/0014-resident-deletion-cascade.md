---
diataxis: explanation
title: "ADR 0014 — Resident deletion: registrants only, full cross-system cascade"
status: accepted
date: 2026-07-29
tags: [adr, registry, identity, lifecycle]
---

# ADR 0014 — Resident deletion: registrants only, full cross-system cascade

## Status
Accepted 2026-07-29 (operator-directed). Extends [[0013-runtime-resident-registry]].

## Context

ADR 0013 lets an operator register a person at runtime, and ADR 0011 lets that
person's face be enrolled on-device. There was no way back: a registrant lived
in the roster (and `data/residents.json`) forever, and their embeddings stayed
matchable in the browser gallery. Deletion must not leave *any* surface able to
produce the deleted identity — a stale face match or a Telegram alert naming a
removed person is worse than no deletion feature at all.

## Decision

### 1. Only runtime registrants are deletable

`DELETE /residents/{rid}` → 200 for an ADR 0013 registrant, **409** for the
fixture roster (r-rajoo … r-tan are demo narrative and anchor
`_DEFAULT_LOCATIONS`, the ranking story, and the acute default identity),
404 for unknown ids. The UI needs to know who is deletable, so
`CaseloadEntry` gains optional `registered?: boolean` (additive; set only for
registrants; contract regenerated, types.ts mirrored, parity-guarded).

### 2. Backend cascade (`fixtures.delete_resident`)

- Drop from `CHRONIC` and `_registered_ids`; rewrite `data/residents.json`.
- **Active-incident guard:** if the deleted person is the camera-named acute
  identity (`_cv_resident`), the incident KEEPS running but reverts to the
  generic default — the same fail-open rule as an unknown `residentId`
  (ADR 0011). An alert leg can outlive a person's registration, but never
  their name.

### 3. Frontend cascade (on-device, in `deletePerson`)

Order matters — server first, then local state, so a failed request changes
nothing locally:

1. `dataClient.deleteResident(id)` (a new seam method).
2. Face gallery: `removePerson(id)` — embeddings gone, so `bestMatch` can
   never return the id again (this alone makes any stale tracker *candidate*
   harmless: it can never accumulate further hits).
3. `IdentityTracker`: reset **only if currently bound to the deleted id**
   (resetting unconditionally would drop a legitimate binding of someone
   else standing in frame).
4. Selectors: Report-as, Enroll-as, and the Who picker each clear if they
   point at the deleted id.
5. Roster refetch — dashboard-side truth realigns.

### 4. Destructive-action UX

Two-step inline confirm ("Remove X…" → "Tap again to confirm"), armed state
disarmed by switching targets. `window.confirm` was rejected: a native modal
blocks the camera loop and every automation path (Playwright, browser agents).

## Consequences

- A mid-demo registrant (a judge) can be cleanly removed; re-registering the
  same name mints a fresh id (`r-name-2`), so no old embedding can bleed into
  the new registration.
- Known, accepted limitation (mirrors ADR 0013): an already-open dashboard
  learns of the deletion on its next fetch/SSE event — roster changes are not
  pushed.
- E2E (`e2e/watch-system.mjs`) now deletes its own registrant through the UI
  and asserts the cascade (caseload clean, re-delete 404s, roster refetch),
  ending the registry-litter problem the old NOTE documented.
- CORS gains DELETE; no new rewrite needed (`/api/residents/:id` already
  proxies). feature-spec bumps to 1.10.0.
