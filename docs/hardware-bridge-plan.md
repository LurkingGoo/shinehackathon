---
type: doc
diataxis: explanation
title: Hardware Bridge Plan (sense layer showcase)
status: draft-for-operator-review
last_updated: 2026-07-03
tags: [hardware, bangle, plan, pitch, demo]
---

# Hardware Bridge Plan

> Goal: judges must see, not just hear, that the sense layer is real. We
> adopt a named reference hardware stack, showcase the wearable itself, show
> how we would adapt it for our needs, and show the link from that device to
> the dashboard. This plan sequences that work and states where the cut
> lines are. Research receipts live in [[hardware-scan]].

## The reference hardware stack (adopted)

| Layer | Adopted product | Role |
|---|---|---|
| Wearable | Bangle.js 2 (Espruino, ≈S$130) | Acute track: raw accelerometer over BLE, open firmware we can program |
| Ambient | Aqara P1 motion (≈US$20/room) + door contact (≈US$15) | Chronic track: presence events |
| Precedent channel | GovTech WAAS (iWOW) | Procurement and installer channel that already exists in Singapore |

The scoring service stays hardware agnostic. These are reference devices
that prove the category, not exclusive dependencies.

## What is already done (Phase A, shipped 2026-07-03)

1. [[hardware-scan]] research note with sources.
2. [[solution-overview]] §The hardware exists today (anchors every number).
3. Deck: spine slide 3 hardware line + backup slide 17 with the bangle
   render and product table.
4. Talk script: hardware beat in slide 3 block + Q&A pocket answer 17.

## Phase B: the showcase build (pre-demo, timeboxed)

### B1. Hardware companion panel with a live link to the dashboard

A presentation surface, not a scoring change. One page in the dashboard app
(route `/hardware`) containing:

1. **The render.** The animated bangle SVG (exists at
   `docs/slides/assets/bangle-render.svg`), BLE arcs pulsing.
2. **The adaptation card.** What we change on the stock product for our
   needs, each line traceable to [[hardware-scan]]:
   - sample rate raised from the shipped slow poll to the rate the detector
     needs (chip supports up to 1600 Hz, we calibrate at the pilot),
   - a ring buffer on the wrist so a BLE dropout does not lose the fall,
   - a battery budget check (streaming costs battery, weeks become days,
     we state that honestly),
   - the stream speaks the same reading format the Simulate button feeds.
3. **The link beat.** A "Stream a recorded fall from this device" button
   that calls the existing simulate endpoint. The dashboard, open beside
   it, pins the incident through the production path. Nothing parallel is
   built. One button, same detector, same SSE stream.

Estimate: 3 to 4 hours including tests and a capture for the deck.
Acceptance: page renders clean, button pins the dashboard in under 3
seconds, no console errors, one new chip screenshot for backup slide 17,
typecheck and all tests pass.

### B2 (stretch only). The emulator beat: the real product running our app

The Espruino Web IDE ships a free browser emulator of the actual Bangle.js
2, running real firmware. We write a minimal fall-watch app: it replays an
embedded SisFall trace, draws the waveform on the watch face, and shows a
FALL banner when the on-watch pre-filter trips.

**Honest constraint we state on stage:** the emulator does not emulate the
accelerometer or Bluetooth. So the emulator shows the product and our app
logic; it cannot stream to the dashboard live. The live link remains B1's
button. We never imply the emulator is transmitting.

Timebox: 2 hours. If it overruns, cut it. The demo loses nothing essential.

### Cut lines

- B1 is built only after the timed run-through and the SSE heartbeat
  (runbook #6) are done. Demo insurance outranks demo garnish.
- B2 is built only after B1 is captured and stable.
- If either phase destabilises the rehearsed demo path, revert it. The
  rehearsed beat (calm, Simulate, pin, drill-down, reset) is sacred.

## Phase C: pilot scope (post-hackathon, stated on slide 11, not built)

1. Buy 2 Bangle.js 2 units. Write the streaming app on real hardware.
2. Ingestion adapter: BLE reading stream into the scoring service, replacing
   the Simulate source. Everything downstream unchanged by design.
3. Re-validate detector thresholds at the device's real output rate
   (calibrated today at SisFall's ~200 Hz).
4. Ambient track on Aqara sensors in one test flat, one-page sensor map.
5. Conversation with the WAAS channel (iWOW / GovTech) about riding the
   existing procurement and installer network.

## Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Time steals from rehearsal + SSE heartbeat | High | Cut lines above; B-phases rank below runbook #6 |
| Judges read us as a hardware company | Medium | Every hardware surface ends on the dashboard pin; the decide layer stays the product |
| Emulator beat oversells (looks like live streaming) | Medium | The constraint is spoken aloud and printed on the panel |
| New page breaks demo build | Low | Separate route, no scoring-path change, revert is one commit |

## Decision needed

Operator approves scope (B1 only / B1+B2 / defer both to after rehearsal).
On approval this plan becomes ADR 0006 and the work is sequenced behind
runbook #6.
