---
type: doc
diataxis: reference
title: Sense-Layer Hardware Scan
status: active
last_updated: 2026-07-03
tags: [hardware, sensors, bangle, pitch]
---

# Sense-Layer Hardware Scan

> Purpose: evidence that the sensing hardware this system depends on is
> commodity, buyable today, and already precedented in Singapore eldercare.
> This answers the judge question "aren't you taking the hardware for
> granted?" with receipts. Summarised on deck backup slide "The hardware
> exists today" and in [[solution-overview]] §The hardware exists today.

## What the system needs from hardware

| Track | Signal needed | Minimum device |
|---|---|---|
| Acute (falls) | Tri-axial acceleration stream, tens of Hz or better, wireless | Any wrist wearable exposing raw accelerometer data |
| Chronic (routine) | Room-level presence events + front-door open/close | PIR motion sensors, one contact sensor |

The scoring service is hardware-agnostic by design: the detector consumes a
stream of acceleration samples and the routine track consumes timestamped
presence events. Nothing in the scoring layer knows or cares which vendor
produced the reading.

## The wearable: it literally exists and is called a bangle

**Bangle.js 2** (Espruino) is an open-source, JavaScript-programmable
smartwatch sold today for about £76 (≈S$130), £71 in volume.

- Kionix **KX022 3-axis accelerometer**; the chip's output data rate goes up
  to 1600 Hz (shipped firmware polls slower; the firmware is fully open, so
  the app sets the rate it needs).
- **Bluetooth LE** (Nordic nRF52840), programmable over the air; apps can
  stream accelerometer events off the watch.
- Weeks of battery life; touchscreen; GPS and heart rate on board.

Why it matters for us: it is the existence proof that a programmable,
raw-data wearable is a catalogue item, not a hardware project. Consumer
watches (Apple Watch, Samsung) ship fall detection at mass-market scale but
lock the raw stream; Bangle.js gives us the stream.

Sources: [espruino.com/Bangle.js2](https://www.espruino.com/Bangle.js2),
[banglejs.com](https://banglejs.com/),
[shop.espruino.com/banglejs2](https://shop.espruino.com/banglejs2).

## The ambient sensors: supermarket commodity

- **Aqara Motion Sensor P1** (Zigbee 3.0): ~US$20, 5-year battery,
  configurable timeout. One per routine-carrying room (kitchen, bedroom,
  bathroom, living room).
- **Aqara Door & Window Sensor** (Zigbee): ~US$15. One on the front door.

A whole flat's chronic track is roughly US$100 of sensors plus a hub.
Sources: [aqara.com Motion Sensor P1](https://www.aqara.com/en/product/motion-sensor-p1/),
[amazon.com door/window sensor](https://www.amazon.com/Aqara-Door-Window-Sensor-Kit/dp/B09TP7VMKB).

## The Singapore precedent: government already buys this category

On **2025-02-03, GovTech awarded iWOW Technology** the contract to expand
the **Wireless Alert Alarm System (WAAS)** to about **170 HDB rental
blocks**, benefiting about **26,800 seniors**. The system includes alert
devices (LoRaWAN + 4G voice, 5-year battery, bathroom-rated) with
**fall-detection sensors and wearable alert devices** offered as add-ons.
iWOW had already run WAAS in ~51 blocks since 2019.

Why it matters for us: the procurement channel, installer workforce, and
senior acceptance of worn/installed alert hardware already exist in
Singapore at the exact demographic we target. We are not proposing new
hardware adoption; we are proposing a smarter decide layer on a category
the government already deploys.

Source: [iwow.com.sg press release](https://www.iwow.com.sg/iwow-secures-singapore-government-contract-to-expand-deployment-of-the-wireless-alert-alarm-system-benefitting-26800-vulnerable-seniors-living-in-rental-flats/).

## The honesty caveat we volunteer

Our fall thresholds are calibrated at SisFall's ~200 Hz research-grade
sampling (ADXL345 / MMA8451Q). A pilot wearable streams at whatever rate
its firmware is set to, so the pilot's ingestion adapter includes
re-validating the detector at the device's real output rate. This is
engineering, not research: the signature (free-fall dip, impact within half
a second, stillness) spans hundreds of milliseconds and survives far
coarser sampling than 200 Hz, but we will measure it rather than assert it.

## Related

[[solution-overview]] · [[feature-spec]] · [[scoring-card]] ·
deck backup slide "The hardware exists today" · talk-script Q&A pocket
answer on hardware.
