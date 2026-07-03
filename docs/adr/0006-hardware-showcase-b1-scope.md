---
type: adr
diataxis: reference
title: Hardware showcase scope, B1 companion panel only
status: accepted
date: 2026-07-03
tags: [adr, hardware, demo, pitch, bangle]
---

# 0006. Hardware showcase scope: B1 companion panel only

- Status: Accepted
- Date: 2026-07-03

## Context
The judge-facing story took the sense layer for granted. Phase A closed the
narrative gap with sourced research ([[hardware-scan]]), a reference stack
(Bangle.js 2 wearable, Aqara ambient sensors, GovTech WAAS as the Singapore
procurement precedent), deck slide 3 plus backup slide 17, and a Q&A pocket
answer. [[hardware-bridge-plan]] then proposed two optional build phases:

- **B1**: a `/hardware` companion page in the dashboard app showing the
  bangle render, an adaptation card (sample rate, ring buffer, battery
  budget, shared reading format), and a button that streams a recorded fall
  through the existing simulate endpoint so the dashboard pins it via the
  production path. Estimate 3 to 4 hours.
- **B2 (stretch)**: a fall-watch app in the Espruino browser emulator.
  The emulator has no accelerometer and no BLE, so it can never stream
  live; it shows product and app logic only. Timebox 2 hours.

The demo-insurance items (SSE heartbeat, runbook #6, and the timed
run-through) compete for the same pre-demo hours.

## Decision
Build **B1 only**. B2 is not scheduled; it may be picked up only if B1 is
captured and stable and the run-through is comfortably under time. Sequencing
is fixed: SSE heartbeat lands first, then B1, then the timed run-through
against the finished surface. Phase C (real units, BLE adapter, threshold
re-validation at device rate, WAAS channel) stays post-hackathon and is
spoken, not built.

Rationale:

1. **B1 ends on the dashboard pin.** Every hardware surface must resolve to
   the decide layer, which is the product. B1 does exactly that through the
   existing simulate endpoint; nothing parallel is built and the scoring
   path is untouched.
2. **B2's honesty cost exceeds its demo value.** The emulator cannot stream,
   so its beat needs an on-stage disclaimer to avoid overselling; a
   disclaimer mid-pitch spends attention the pin beat earns back for free.
3. **Demo insurance outranks demo garnish.** The heartbeat fix removes the
   top failure mode (a silently dead SSE channel); B1 is additive polish.
   The cut lines in [[hardware-bridge-plan]] apply unchanged.

## Consequences
- New dashboard route `/hardware`; separate page, no scoring-path change,
  revert is one commit. Acceptance per the plan: clean render, pin in under
  3 seconds, no console errors, typecheck and tests pass, one screenshot
  for backup slide 17's chip.
- [[hardware-bridge-plan]] status moves from draft to approved-B1; B2
  remains documented as an unscheduled stretch.
- If B1 destabilises the rehearsed demo path (calm, Simulate, pin,
  drill-down, reset), it is reverted before demo day.
