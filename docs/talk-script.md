---
type: doc
diataxis: how-to
title: Presenter Script (operator voice pass folded in)
status: active
last_updated: 2026-07-03
tags: [pitch, script, demo]
---

# Presenter Script

> **How to use this.** This version carries the operator's voice pass from
> 2026-07-03. The facts and the slide order are locked. Every claim traces to
> [[solution-overview]] or [[scoring-card]]. Stage directions sit in
> [brackets]. Target: about six minutes before Q&A.

---

## Slide 1: Title

We build the morning triage for One Care care workers. Imagine a care worker
sitting down in the morning. Her dashboard flashes, and she knows immediately
which resident she meets first, and why.

---

## Slide 2: The problem

Today the safety net for a senior living alone is reactive. An alarm button
only works while the person who fell can still press it. An unconscious
person presses nothing. So the fall becomes what geriatricians call a long
lie: hours on the floor before anyone thinks to check. How do we close that
gap?

---

## Slide 3: The insight

Well, we use routines. Think about an elderly person, or anyone staying at
home for a long time. People develop fixed routines. Kitchen at seven, front
door at nine, bathroom trips at night. The home already knows what normal
looks like. So we built two things for this one problem:

1. A bangle for the fall itself. It streams movement readings into our
   detector, so a fall is caught in seconds instead of hours.
2. Ambient sensors for the routine. They learn each resident's own normal,
   and any anomaly is flagged straight onto the dashboard.

To be clear about the split: the routine track needs nothing worn at all.
The bangle only serves the fall alarm.

And none of this hardware is hypothetical. We checked before we built. The
bangle exists as a catalogue item today, an open source programmable one
costs about a hundred and thirty dollars, and the room sensors are twenty
dollar off-the-shelf parts. Singapore already deploys senior alert
wearables at scale: GovTech awarded a contract last year covering about
twenty six thousand eight hundred seniors in rental flats.

So we are not limited to our own hardware. The dashboard is built to
integrate whatever sensors a flat already has, ours or anyone else's. The
main aim of this project is the monitoring layer that makes all of them
speak one language.

---

## Slide 4: The product

And this is the product. One screen, calm by default. Every resident is
ranked by how much they need a visit today, and every row explains itself in
one sentence a human wrote the template for. The top row here is not staged.
It carries two hundred and twenty days of a real elderly resident's sensor
data, and the reason reads kitchen inactivity: an eleven hour gap, where her
normal is about four hours.

---

## Slide 5: The demo beat  [switch to the live dashboard here]

[Press Simulate. Wait for the pin, about two seconds.]

What just happened is not a UI trick. That button took a genuine recorded
fall from a public research dataset and fed it into our live detector, the
same way a worn bangle would stream it. The detector recognised the
signature, pushed the incident to this dashboard, and the resident pinned to
the top with the evidence in plain words: an eleven point two g impact, then
twelve seconds of no movement.

[Point at the drill-down panel, "What the sensor saw".]

Now you do not have to take the detection on faith. This panel shows the
actual signal. You can see the free-fall dip, the impact spike, and the
stillness after it. The system suggests the next step. The care worker makes
the call.

---

## Slide 6: A fall has a signature

So how do we actually ascertain that a fall is a fall? This is the same
panel you just saw in the demo. A fall must show an ordered signature. First
a free-fall dip, then an impact spike within half a second, then stillness.
A dropped phone spikes but never dips first. A hard sit-down dips barely and
recovers instantly. The order is the fingerprint, and that is why a single
threshold would be wrong. Behind it are three layers: the home senses, the
service scores, the care worker decides.

---

## Slide 7: Explainable by contract

Nothing between the sensor and the care worker is a black box. Every score
breaks apart into the sensor facts that produced it, and trust is shown on
its own axis. If a sensor goes stale, confidence drops. Risk does not move.
So a dead battery can never fake a crisis, and a care worker always knows
how much to believe a number before she acts on it.

---

## Slide 8: It's real

We validated this on real data, and we will give you the honest version of
the numbers. The detector catches ninety six point two percent across
seventeen hundred and ninety eight real recorded falls. On the lab's
deliberately fall-like daily activities the false alarm rate is twenty nine
point eight percent, but almost all of that is jogging and jumping over
obstacles. On the movements a monitored senior actually performs, including
stumbling without falling, it fires at zero to five percent. And the routine
track runs on two hundred and twenty days of a real home, where the system
found the genuinely broken day on its own. Nothing here is trained. The
thresholds were calibrated in the open, and anyone can rerun the script.

---

## Slide 9: Built for Singapore

Nothing in this system imports a foreign idea of how a senior should live.
It measures each resident's own kitchen gaps, door times and night trips for
about two weeks, and from then on compares her only to herself. It is
presence only, and that is what makes it acceptable to a senior who values
her dignity. It deploys one HDB unit at a time, with an installer filling in
a one page sensor map. It multiplies One Care's existing people. It replaces
no one.

---

## Slide 10: Honest limits

We would rather tell you the limits than have you find them. This shrinks
time to detection. It does not promise to catch every event. The fall
thresholds were calibrated on mostly young adult recordings, so the senior
false alarm rate is extrapolated, not measured. And if the bangle is on the
nightstand when the fall happens, the ambient track still catches the
stillness that follows. That resident surfaces by morning, which is exactly
the long lie we exist to shorten.

---

## Slide 11: Beyond the PoC

Three things turn this demo into a pilot. First, escalation that completes
the loop: automated welfare calls, and a handoff to the MOH and AIC line
when a fall goes unacknowledged. Second, a drafted morning brief per flagged
resident, grounded strictly in the deterministic features, never touching a
score. Third, a first cluster where we measure two numbers: time to
detection, and care worker minutes saved per shift.

---

## Slide 12: The ask

We are asking for one cluster and commodity sensors. The system works today.
You watched it detect a real fall live, and it is validated on four and a
half thousand real recordings plus a two hundred and twenty day real home.
Pilot with us.

---

# Q&A pocket answers  [backup slides 13 to 18]

**"Why didn't you use machine learning?"**  [slide 14]
Because for this problem it would be worse. There is no Singapore training
data, so any model we trained would import a Colombian or American prior,
which is the exact assumption we refuse. A fall is physics, and physics
transfers without training. And a care worker must be able to ask why. Our
rules survive that question. A black box does not. Where a model will help
later is wording the morning brief. It will never produce a score.

**"So what was the data for, if nothing is trained?"**  [slide 15]
Three jobs. SisFall calibrates the fall thresholds and measures the
detector. That is where ninety six point two comes from. CASAS Aruba
validates that self-baselining recovers a real routine and finds the day it
broke. And one SisFall trace is the fall you watched in the demo. Both
datasets are checksum-pinned in the repo, and every number reproduces from
one script.

**"How does a real fall actually reach this dashboard?"**  [slide 16]
The path you watched is the production path. The bangle streams
accelerometer readings to the scoring service, and to be precise, that
ingestion link is the one piece we simulate, because there is no wristband
hardware in this room. Everything from the detector onward is the real
running system. The detector watches every reading for the ordered
signature. A detection pushes an incident event down a live stream the
dashboard is always listening to, and the resident pins to the top in
seconds. The only thing the demo button changes is the source of the
signal. It feeds a recorded fall into the detector instead of a live
bangle. Everything downstream is identical.

**"Aren't you taking the hardware for granted? How do you know a fall
happened?"**  [slide 17]
That is a fair challenge, so let me be precise about what we own and what
we buy. The hardware is deliberately not our invention, and we researched
it before assuming it. An open source programmable bangle with the exact
accelerometer we need is a catalogue item today at about a hundred and
thirty dollars. The room sensors are twenty dollar parts with five year
batteries. And GovTech already procures this category: a contract awarded
last year puts senior alert hardware, including fall sensors and
wearables, in about one hundred and seventy rental blocks covering twenty
six thousand eight hundred seniors. Buying the sensor is not the hard
part. The hard part is deciding, given a stream of readings, that a fall
is a fall and not a dropped phone. That is the part we built, and you
watched it work live: the ordered signature, dip then spike then
stillness, measured at ninety six point two percent across seventeen
hundred and ninety eight real falls. The one piece we simulate is the
radio link from the wristband into our service, because there is no
wristband in this room. Connecting one is the ingestion adapter, the
first line item of the pilot.

**"What gets installed in a flat?"**  [slide 18]
Motion sensors in the rooms that carry routine: kitchen, bedroom, bathroom,
living room. One contact sensor on the front door. The optional bangle. An
installer fills in a one page sensor-to-area map. No cameras, no
microphones, no rewiring.

**"What happens to the falls you miss?"**
They degrade to the ambient track. A missed fall becomes hours of stillness,
and hours of stillness is exactly what the routine track surfaces. The two
tracks are redundancy, not alternatives.
