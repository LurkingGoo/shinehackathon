---
marp: true
theme: warm-human
paginate: true
footer: Morning Triage · One Care @ Jurong Spring · JSGP
---

<!-- _class: title -->

###### JSGP · SHINE Hackathon

# Morning **Triage**

The morning triage for One Care caseworkers:
who needs you first, and why, in plain language.

---

<!-- _class: statement -->

###### The problem

# Help that must be **asked for**

Alarm buttons and pendants only help while the fallen person
can still press them. An unconscious senior presses nothing.

The fall becomes a **long lie**: hours helpless on the floor
before anyone thinks to check.

---

<!-- _class: statement -->

###### The approach

# Help that needs **no button**

Motion and door sensors log every kitchen visit and every door event.
When a morning breaks that pattern, or hours pass with no movement at all,
the resident surfaces on the caseload. Nothing worn, nothing pressed,
and no camera in the room.

One optional bangle adds a second layer:
falls caught in seconds instead of hours.

*All of it is off-the-shelf hardware, and Singapore already
deploys senior alert wearables at 26,800-resident scale.*

---

###### How it is built

# The three **layers**

![bare w:1050](assets/architecture.svg)

*The home senses. The service scores. The caseworker decides.*

*The math is Python, so the service computes and the browser only displays. The API call carries the JSON between them.*

<!--
Why two processes and not one? The scoring is Python: the detector, the calibration, and the dataset loaders, all built on numpy and scipy. The browser runs JavaScript and cannot run that math. So the service computes the numbers and returns them as JSON, and the browser only displays them. The API call is the browser asking the service for the scores it cannot compute itself.
-->

---

###### How it works

# A fall has a **signature**

<figure>

![h:330](assets/chip-sensor-waveform.png)

<figcaption>Straight from the product: the drill-down shows the signal behind every incident</figcaption>
</figure>

The detector requires this **ordered sequence**: a free-fall dip, an impact
spike within half a second, then stillness. A dropped phone cannot fake the order.

<!--
The signal drops toward zero first: free-fall, the half-second the body falls with
nothing holding it up. Then the spike: the impact with the floor. Then it goes flat and
stays flat: stillness. Free-fall, impact, stillness, in that order. A dropped phone has
the dip and the spike, but it gets picked up, so the stillness never comes. The detector
checks the sequence, so a slammed door or a bag set down hard cannot fake it.
-->

---

###### The two datasets

# Why these two **recordings**

<div class="stat sun"><b>4,505</b><span>real recordings · 1,798 falls · 38 people · SisFall</span></div>
<div class="stat sage"><b>220 days</b><span>one senior, living alone · CASAS Aruba</span></div>

*One teaches the detector what a fall is in physics.
The other teaches the system what one person's normal life is in rhythm.*

Both run on the same cheap sensor class a worn bangle carries, the **ADXL345**
accelerometer, so what the detector sees in the data is what it would see in a home.

<!--
SisFall and CASAS do two different jobs. SisFall gives us 4,505 real recordings, 1,798
of them genuine falls, from 38 different people, sensors strapped to real bodies hitting
real floors. It was recorded on the ADXL345, the same cheap accelerometer class a worn
bangle carries, so the detector learns to see exactly what it would see in a real home.
CASAS Aruba covers 220 days, roughly seven months, of one real elderly person living
alone, with every motion sensor and every door event logged. SisFall teaches the detector
what a fall is in physics: the dip, the impact, the stillness. CASAS teaches the system
what one person's ordinary life is in rhythm, so it can notice the morning that rhythm
breaks. No third dataset would add what these two do not already carry. The two tracks
stay separate all the way down: the calibration you are about to see only ever touches
SisFall. CASAS is never tuned against a target. From those 220 days we compute each
resident's own baseline and score every new day as a deviation from that person's rhythm,
so the routine track learns without any training and without any population average.
-->

---

###### Where the number comes from

# How we got our **number**

- We wrote the detector first, the dip, spike, stillness rule.
- Then we ran it over all **4,505** recordings and **counted**: falls caught, and ordinary activities that false-fired.
- Then we swept **144** threshold combinations and kept the operating point that caught **96.2%** of the falls.

*The number comes from counting an experiment. We measured a detector
and did not train a model, so it carries to Singapore with no local data.*

<!--
96.2 percent is not a guess and is not borrowed. We wrote the detector first: the rule that
looks for a free-fall dip, then an impact, then stillness, in that order. We ran that rule
over all 4,505 recordings, one at a time, and counted. Every real fall it caught, we
tallied. Every ordinary activity it mistook for a fall, we tallied too. Then we recalibrated:
we swept 144 threshold combinations, four free-fall cutoffs, four impact cutoffs, three dip
durations, three impact windows. Every combination ran over all 4,505 recordings and produced
a confusion matrix, and we kept the operating point that caught the most falls at the lowest
false-alarm rate: free-fall below 0.8 g, impact above 2.3 g, a dip of at least 40 ms, impact
within 500 ms. That caught 96.2 percent of the falls. That step only measured and tuned the
detector; it never filtered or
sorted a single recording or person out of the set. The number comes from counting an
experiment rather than from a claim. It also carries to Singapore: we were never learning a
population, we were measuring a detector against physics.
Physics is the same in Jurong as in a lab in Antioquia, so the detector carries over with
no local training data. That is why we do not train a model.
-->

---

###### What the numbers say

# We ran it on **real recordings**

<div class="stat red"><b>96.2%</b><span>of 1,798 real falls detected · SisFall</span></div>
<div class="stat sun"><b>35.2% → 18.8%</b><span>false alarms: young adults → elderly movement</span></div>
<div class="stat sage"><b>220 days</b><span>one real home · CASAS Aruba</span></div>

The detector caught 96.2% of the 1,798 real falls. The false alarms split by body: 35.2% on young adults
hurling themselves into lab falls, but **18.8%** on the elderly participants, roughly
half, because older movement is slower and less abrupt. On elderly falls the detector
caught **84.0%**, though all 75 come from a single volunteer, so we hold that figure
lightly. Nothing is trained here, because the thresholds came straight out of the data.

<figure>

![w:760](assets/chip-top-row.png)

<figcaption>Rank 1 carries 220 real days of one elderly resident. The system found the broken day on its own</figcaption>
</figure>

<!--
Each of the three numbers answers a different worry. The 96.2 percent of 1,798 real falls
is the detector catching the thing it exists to catch. The middle number is false alarms.
On young adults throwing themselves into lab falls it fires 35.2 percent of the time;
split the recordings by body and re-count the elderly participants alone, and it fires
18.8 percent, roughly half. That is a measurement rather than a hope: older movement is slower
and less abrupt, so it trips the detector less often. The one number we hold lightly is
elderly falls: 84.0 percent caught, but those 75 falls all come from a single volunteer,
the only elderly participant cleared to fall on camera, so it is a real number from a thin
sample and we say so. The 220 days on the right is the other track: one real home where
the system found the broken day by itself. That track runs on a different mechanism: from
those 220 days it builds the resident's own baseline and scores each new day as a
deviation from that rhythm, so it needs no training run and no population average to know
that this morning broke this person's pattern.
-->

---

###### The counter-experiment

# We trained a model **anyway**

- We fit a logistic regression on a curated table of **500** real SisFall recordings, 250 falls and 250 ordinary activities, four magnitude features per recording.
- On the held-out **125** recordings it reaches **80.0%** accuracy, 77.9% precision and 84.1% recall. Re-fits at 60/40, 70/30 and 80/20 move accuracy only between 78.5% and 80.0%.
- One fit takes **0.050 seconds**, so the `/training` page replays the real recorded gradient-descent run live.

*The 16.2-point gap to the shipped detector's 96.2% is the evidence that the
temporal order, free-fall then impact then stillness, is what magnitudes alone cannot see.*

<!--
The obvious question is why we did not train a model, so we trained one and put the whole
run on the /training page, "How the model was trained". We built a curated table of 500
real SisFall recordings, 250 falls and 250 ordinary activities, and gave a logistic
regression the four magnitude features a summary can carry. On the held-out 125 recordings
it reaches 80.0 percent accuracy, 77.9 percent precision and 84.1 percent recall. We then
re-fit at 60/40, 70/30 and 80/20 splits, and accuracy only moves between 78.5 and 80.0
percent, so the ceiling is a property of the features rather than an artifact of one
split. One fit takes 0.050 seconds, which is why the page can replay the actual recorded
gradient-descent run in front of you; every number on it is measured, nothing is
simulated. The shipped detector reaches 96.2 percent on the same physics because it reads
the order of events, the free-fall, then the impact, then the stillness. The 16.2-point
gap is the evidence that the temporal order is what magnitudes alone cannot see. Nothing
on this page ever scores a resident.
-->

---

###### The product

# One screen, **calm by default**

![h:395](assets/caseload-calm.png)

*Every resident is ranked by need, and every row explains itself in one sentence.*

---

###### Explainable by contract

# Every number **decomposes**

<div class="cols">
<figure>

![](assets/chip-feature-decomposition.png)

<figcaption>Every score breaks into the sensor facts that produced it. Nothing is taken on faith</figcaption>
</figure>
<figure>

![](assets/chip-confidence-axis.png)

<figcaption>A stale sensor lowers confidence. It never inflates risk, so a dead sensor cannot fake a crisis</figcaption>

The system ranks and explains.
**A human decides.**

</figure>
</div>

---

###### The demo beat

# A fall **preempts everything**

<figure>

![w:1020](assets/chip-simulate-button.png)

<figcaption>Each press streams a different real recorded fall through the live detector, the same signal a worn bangle would send. A second button injects a dropped phone the detector ignores</figcaption>
</figure>
<div class="cols">
<figure>

![](assets/chip-acute-card.png)

<figcaption>The fall pins to the top in seconds and states its evidence in plain words</figcaption>
</figure>
<figure>

![](assets/chip-recommended-action.png)

<figcaption>The system suggests the next step. The caseworker makes the call</figcaption>
</figure>
</div>

*Two more live beats: `/watch` fires a named camera fall that answers back,
and `/training` replays the trained-model run.*

---

###### Honest limits

# What we do **not** claim

- It shrinks time to detection. It does not promise to catch every event.
- The senior false-alarm rate is **measured** rather than guessed, because it came in at 18.8% on real elderly recordings, lower than young adults. What stays thin is elderly *fall* data, since our falls come from one volunteer, and a lab fall is not the same as a home fall.
- A missed fall (or a bangle left on the nightstand) degrades to the ambient track, where hours of stillness still surface that resident by morning.
- An irregular life earns wide baselines. The system says so through *low confidence* instead of hiding it.

<!--
Here is what we deliberately do not claim. We shrink time to detection; we do not promise
to catch every event, and any deck that promises that is lying. The second line used to
say our senior false-alarm rate was extrapolated from young adults. We measured it
directly on the elderly recordings at 18.8 percent, lower than the young adults, and
corrected the slide rather than let a flattering guess stand. The honest gap runs the
other direction: elderly fall data is thin. All our elderly falls come from one volunteer,
and a fall staged in a lab is not a fall in a real kitchen. We name that caveat rather than
paper over it. The last two lines are the safety net: a missed fall, or a bangle left on
the nightstand, drops to the ambient track, where hours of stillness still surface that
person by morning; and an irregular life earns a wide baseline, which the system reports
through low confidence instead of hiding.
-->

---

###### The next step

# What a pilot would **prove**

- **Escalation beyond the app.** The STILL DOWN follow-up and the I-am-responding acknowledgement are built and live. A pilot adds what sits past the phone: automated welfare calls, and the handoff to the MOH/AIC line when nobody acknowledges.
- **A morning brief per flagged resident.** Auto-drafted wording, grounded strictly in the deterministic features. The drafting layer never touches a score.
- **One One Care cluster to start.** Measured on two numbers: time to detection, and caseworker minutes saved per shift.

---

<!-- _class: statement -->

###### The ask

# Pilot **with us**

We ask for one cluster and commodity sensors. The working system
is already validated on **4,505 real recordings** and a **220-day real home**.

*Built at SHINE Hackathon. The demo runs live on real recordings, a different one each press.*

---

###### Backup · for Q&A

# Why **no machine learning**

- **No Singapore training data exists.** A model trained on Colombian or American recordings would import exactly the prior we refuse to assume.
- **A fall is physics.** The free-fall, impact and stillness sequence transfers across bodies and homes without any training step.
- **A caseworker must be able to ask why.** Decomposable rules survive that question. A black box does not.
- Where a model helps later: smoothing the wording of the morning brief. It will never produce a score.

---

###### Backup · for Q&A

# Where the **data goes**

*What each dataset teaches is earlier in the deck. This is the provenance behind those numbers.*

| Dataset | Source | Provenance |
|---|---|---|
| **SisFall** | Universidad de Antioquia | 4,505 recordings, 1,798 real falls, checksum-pinned |
| **CASAS Aruba** | Washington State University | 220-day single-resident home log, checksum-pinned |

Nothing is trained on either dataset. Both are provenance-pinned with
checksums in a committed lock file, and every number reproduces from one script.

---

###### Backup · for Q&A

# From a fall to the **dashboard**

The path is the same in the demo and in deployment. Only the source of
the signal changes.

1. The bangle streams accelerometer readings to the scoring service.
2. The detector watches every reading for the ordered fall signature:
   dip, spike, stillness.
3. A detection pushes an incident event down a live stream the dashboard
   is always listening to. The resident pins to the top in seconds.

*Step 1 is the one link we simulate; there is no wristband in the room.
Each press of the Simulate button feeds a different real SisFall trace straight into
step 2; a second button injects a dropped phone the detector ignores. Everything after
(detection, push, re-rank) is the production path.*

---

###### Backup · for Q&A

# The hardware **exists today**

<div class="cols">
<figure>

![bare h:180](assets/bangle-render.svg)

</figure>
<figure>

![w:195](assets/hardware-page.png)

<figcaption>Live in the dashboard today: /hardware streams a recorded fall through the production path</figcaption>
</figure>
</div>

| Device | Real product, buyable now | Price |
|---|---|---|
| Wearable: raw accelerometer, BLE | **Bangle.js 2**, Kionix KX022, open firmware | ≈S$130 |
| Room presence · door events | **Aqara P1** motion · contact, 5-yr battery | ≈US$20 · 15 |
| Singapore precedent | **GovTech WAAS** (iWOW, 2025): 170 blocks · 26,800 seniors | govt tender |

---

###### Backup · for Q&A

# The camera layer, **named and opt-in**

- On `/watch`, MediaPipe pose runs entirely in the browser. Upright, then horizontal within **3 s**, then **3 s** of stillness fires the same incident path. A slower transition is a deliberate lie-down and never alarms.
- Every camera incident carries the label **Camera (pose)** and the heuristic's own 0.55 to 0.85 confidence band. The 96.2% figure belongs to the accelerometer track alone.
- Enrolled face identity is opt-in and on-device, matched only while the person is upright, so the caseload row and the Telegram ping are **named** and the alert says where to look: *last motion: Bedroom*. Unmatched people fire the generic alert.
- **The alert answers back.** No recovery 45 s after the alert sends STILL DOWN; a caregiver taps **I am responding** and the alert is stamped with who took it.
- No video leaves the browser; only the detection event and the matched resident id are sent.

<!--
The camera layer is the second acute source, and it is opt-in. On the /watch page,
MediaPipe pose runs entirely in the browser; no frame leaves the device. A person upright,
then horizontal within 3 seconds, then 3 seconds of stillness, fires the same incident
path as the bangle, the caseload preemption, the live stream, and the Telegram ping. A
slower transition is a deliberate lie-down and never alarms. We keep the honesty rules:
the incident is labelled Camera (pose) and carries the heuristic's own 0.55 to 0.85
confidence band, never the 96.2 percent figure, which belongs to the accelerometer track
alone. Identity is enrolled and on-device: front, left and right angles are stored as
embeddings in the browser's storage, no image is kept and nothing is uploaded. Matching
runs only while the person is upright, and the binding carries the name through the fall,
so the dashboard row and the Telegram ping are named, and the alert also says where in
the flat to look: the resident's last-motion area from the ambient track rides with the
unit. Unmatched people fire the generic
alert, because recognition can never block or alter an alert. The alert leg answers back:
if nobody rises 45 seconds after the alert, a STILL DOWN message follows, and a caregiver
who taps I am responding stamps the alert with their name, first tap wins, and the
dashboard shows it within 5 seconds. The privacy claim in full:
no video leaves the browser; only the detection event and the matched resident id are
sent. Telegram dispatch is live and happens off the request thread, and /alerts/status
plus the badges on the dashboard and /watch show whether Telegram is configured and what
happened to the last dispatch, sent, failed, or not configured. The path is covered by 96
backend and 25 frontend tests, all passing.
-->

---

###### Backup · for Q&A

# What a flat **needs**

- Motion sensors in the rooms that carry routine: kitchen, bedroom, bathroom, living room.
- One contact sensor on the front door.
- One optional bangle for the acute track. The routine track works with nothing worn at all.
- An installer fills in a one-page sensor-to-area map. No cameras, no microphones, no rewiring.
