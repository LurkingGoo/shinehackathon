---
type: doc
diataxis: how-to
title: Presenter Script (rephrase into your own voice)
status: active
last_updated: 2026-07-02
tags: [pitch, script, demo]
---

# Presenter Script

> **How to use this.** Read each block aloud once, then rewrite it the way
> you would actually say it. The facts and the order must survive your
> rewrite. The exact words should not — a memorised script sounds memorised.
> Stage directions sit in [brackets]. Target: about six minutes before Q&A.
> Every claim traces to [[solution-overview]] or [[scoring-card]].

---

## Slide 1 — Title

We build the morning triage for One Care caseworkers. When a caseworker
sits down at eight in the morning, our screen tells her which of her
residents needs her first, and why, in plain language.

---

## Slide 2 — The problem

Today the safety net for seniors who live alone is reactive. An alarm
button only works while the person who fell can still reach it. A senior
who is unconscious presses nothing. So the fall becomes what geriatricians
call a long lie. Hours on the floor before anyone thinks to check. That is
the gap we are closing.

---

## Slide 3 — The insight

Our insight is that the home already knows. A person's routine is a vital
sign, and the absence of motion is data. The ambient track asks the senior
to wear nothing, press nothing, and puts no camera in the room. On top of
that, one optional bangle adds a second layer, so a fall is caught in
seconds instead of hours. To be clear about the split — the routine
monitoring needs nothing worn at all. The bangle only serves the fall
alarm.

---

## Slide 4 — The product

This is the whole product. One screen, calm by default. Every resident is
ranked by how much they need a visit today, and every row explains itself
in one sentence a human wrote the template for. The top row here is not
staged — it carries two hundred and twenty days of a real elderly
resident's sensor data, and the reason reads — kitchen inactivity. An
eleven-hour gap, where her normal is about four hours.

---

## Slide 5 — The demo beat  [switch to the live dashboard here]

[Press Simulate. Wait for the pin — about two seconds.]

What just happened is not a UI trick. That button took a real recorded
fall — a genuine fall from a public research dataset — and fed it into our
live detector, the same way a worn bangle would stream it. The detector
recognised the signature, pushed the incident to this dashboard, and the
resident pinned to the top with the evidence in plain words: an eleven
point two g impact, then twelve seconds of no movement. The system
suggests the next step. The caseworker makes the call.

---

## Slide 6 — How it works

Three layers. The home senses, the service scores, the caseworker decides.
One thing matters on this slide: a fall must show an ordered signature. A
free-fall dip, then an impact spike within half a second, then stillness.
A dropped phone spikes but never dips first. A hard sit-down dips barely
and recovers instantly. The order is the fingerprint, and it is why a
single threshold would be wrong.

---

## Slide 7 — Explainable by contract

Nothing between the sensor and the caseworker is a black box. Every score
breaks apart into the sensor facts that produced it, and trust is shown on
its own axis. If a sensor goes stale, confidence drops. Risk does not
move. So a dead battery can never fake a crisis, and a caseworker always
knows how much to believe a number before she acts on it.

---

## Slide 8 — It's real

We validated this on real data, and we will give you the honest version of
the numbers. The detector catches ninety-six point two percent — across
seventeen hundred and ninety-eight real recorded falls. On the lab's
deliberately fall-like daily activities the false alarm rate is
twenty-nine point eight percent — but almost all of that is jogging and
jumping over obstacles. On the movements a monitored senior actually
performs, including stumbling without falling, it fires at zero to five
percent. And the routine track runs on two hundred and twenty days of a
real home, where the system found the genuinely broken day on its own.
Nothing here is trained. The thresholds were calibrated in the open and
anyone can rerun the script.

---

## Slide 9 — Built for Singapore

Nothing in this system imports a foreign idea of how a senior should
live. It measures each resident's own kitchen gaps, door times and night
trips for about two weeks, and from then on compares her only to herself.
It is presence-only — and that is what makes it acceptable to a senior
who values her dignity. And it deploys one HDB unit at a time, with an
installer filling in a one-page sensor map. It multiplies One Care's
existing people. It replaces no one.

---

## Slide 10 — Honest limits

We would rather tell you the limits than have you find them. It shrinks
time to detection — it does not promise to catch every event. The fall
thresholds were calibrated on mostly young-adult recordings, so the senior
false-alarm rate is extrapolated, not measured. And if the bangle is on
the nightstand when the fall happens, the ambient track still catches the
stillness that follows — that resident surfaces by morning, which is
exactly the long lie we exist to shorten.

---

## Slide 11 — Beyond the PoC

Three things turn this demo into a pilot. Escalation that completes the
loop — automated welfare calls, and a handoff to the MOH and AIC line when
a fall goes unacknowledged. A drafted morning brief per flagged resident,
grounded strictly in the deterministic features, never touching a score.
And a first cluster where we measure two numbers: time to detection, and
caseworker minutes saved per shift.

---

## Slide 12 — The ask

We are asking for one cluster and commodity sensors. The system works
today — you watched it detect a real fall live — and it is validated on
four and a half thousand real recordings plus a two-hundred-and-twenty-day
real home. Pilot with us.

---

# Q&A pocket answers  [backup slides 13–16]

**"Why didn't you use machine learning?"**  [slide 13]
Because for this problem it would be worse. There is no Singapore training
data, so any model we trained would import a Colombian or American prior —
the exact assumption we refuse. A fall is physics, and physics transfers
without training. And a caseworker must be able to ask why. Our rules
survive that question. A black box does not. Where a model will help later
is wording the morning brief. It will never produce a score.

**"So what was the data for, if nothing is trained?"**  [slide 14]
Three jobs. SisFall calibrates the fall thresholds and measures the
detector — that is where ninety-six point two comes from. CASAS Aruba
validates that self-baselining recovers a real routine and finds the day
it broke. And one SisFall trace is the fall you watched in the demo. Both
datasets are checksum-pinned in the repo, and every number reproduces from
one script.

**"How does a real fall actually reach this dashboard?"**  [slide 15]
The path you watched is the production path. The bangle streams
accelerometer readings to the scoring service — and to be precise, that
ingestion link is the one piece we simulate, because there is no wristband
hardware in this room. Everything from the detector onward is the real
running system. The detector watches every reading for the ordered
signature. A detection pushes an incident event
down a live stream the dashboard is always listening to, and the resident
pins to the top in seconds. The only thing the demo button changes is the
source of the signal — it feeds a recorded fall into the detector instead
of a live bangle. Everything downstream is identical.

**"What gets installed in a flat?"**  [slide 16]
Motion sensors in the rooms that carry routine — kitchen, bedroom,
bathroom, living room. One contact sensor on the front door. The optional
bangle. An installer fills in a one-page sensor-to-area map. No cameras,
no microphones, no rewiring.

**"What happens to the falls you miss?"**
They degrade to the ambient track. A missed fall becomes hours of
stillness, and hours of stillness is exactly what the routine track
surfaces. The two tracks are redundancy, not alternatives.
