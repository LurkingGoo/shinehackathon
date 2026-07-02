---
marp: true
theme: warm-human
paginate: true
footer: Morning Triage · One Care @ Jurong Spring · JSGP
---

<!-- _class: title -->

###### JSGP · SHINE Hackathon

# Morning **Triage**

The morning triage for One Care caseworkers —
who needs you first, and why, in plain language.

---

<!-- _class: statement -->

###### The problem

# Help that must be **asked for**

Alarm buttons and pendants only help while the fallen person
can still press them. An unconscious senior presses nothing.

The fall becomes a **long lie** — hours helpless on the floor
before anyone thinks to check.

---

<!-- _class: statement -->

###### The insight

# The home **already knows**

Routine is a vital sign, and absence of motion is data.
The ambient track asks the senior to wear nothing, press nothing,
and puts no camera in the room.

One optional bangle adds a second layer —
falls caught in seconds instead of hours.

---

###### The product

# One screen, **calm by default**

![h:395](assets/caseload-calm.png)

*Every resident is ranked by need, and every row explains itself in one sentence.*

---

###### The demo beat

# A fall **preempts everything**

<figure>

![w:1020](assets/chip-simulate-button.png)

<figcaption>The button replays a real recorded fall through the live detector — the same signal a worn bangle would stream</figcaption>
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

---

###### How it works

# Sense → Score → **Decide**

![bare w:940](assets/architecture.svg)

A fall must show an **ordered signature** — a free-fall dip, an impact spike
within half a second, then stillness. A dropped phone cannot fake the sequence,
and every score comes from deterministic rules a caseworker can read.

---

###### Explainable by contract

# Every number **decomposes**

<div class="cols">
<figure>

![](assets/chip-feature-decomposition.png)

<figcaption>Every score breaks into the sensor facts that produced it — nothing is taken on faith</figcaption>
</figure>
<figure>

![](assets/chip-confidence-axis.png)

<figcaption>A stale sensor lowers confidence. It never inflates risk, so a dead sensor cannot fake a crisis</figcaption>

The system ranks and explains.
**A human decides.**

</figure>
</div>

---

###### Validated on real data

# It's **real**, not a concept

<div class="stat red"><b>96.2%</b><span>of 1,798 real falls detected · SisFall</span></div>
<div class="stat sun"><b>29.8% → 0–5%</b><span>lab alarms → elderly-typical movement</span></div>
<div class="stat sage"><b>220 days</b><span>one real home · CASAS Aruba</span></div>

Nothing is trained. The thresholds were calibrated openly on the full SisFall set,
and the lab false alarms concentrate in jogging and jumping — movements a
monitored senior rarely performs.

<figure>

![w:760](assets/chip-top-row.png)

<figcaption>Rank 1 carries 220 real days of one elderly resident — the system found the broken day on its own</figcaption>
</figure>

---

###### Built for Singapore

# No imported **prior**

- **Self-baselining.** The system measures each resident's own kitchen gaps, door times and night trips for about two weeks, then flags deviation from that person's own normal.
- **Presence-only dignity.** Seniors accept what does not watch them.
- **Per-HDB deployment.** An installer fills in a one-page sensor map. The product multiplies One Care's existing people and replaces no one.

---

###### Honest limits

# What we **don't** claim

- It shrinks time to detection. It does not promise to catch every event.
- Fall thresholds were calibrated on mostly young-adult recordings, so the senior false-alarm rate is extrapolated rather than measured.
- A missed fall — or a bangle left on the nightstand — degrades to the ambient track, where hours of stillness still surface that resident by morning.
- An irregular life earns wide baselines. The system says so through *low confidence* instead of hiding it.

---

###### Beyond the PoC

# From demo to **pilot**

- **Escalation that completes the loop.** Automated welfare calls, and a handoff to the MOH/AIC line when a fall goes unacknowledged.
- **A morning brief per flagged resident.** Auto-drafted wording, grounded strictly in the deterministic features. The drafting layer never touches a score.
- **One One Care cluster to start.** Measure time to detection and caseworker minutes saved per shift.

---

<!-- _class: statement -->

###### The ask

# Pilot **with us**

One cluster. Commodity sensors. A working system —
validated on **4,505 real recordings** and a **220-day real home**.

*Built at SHINE Hackathon. The demo runs live, replaying real recordings.*

---

###### Backup · for Q&A

# Why **no machine learning**

- **No Singapore training data exists.** A model trained on Colombian or American recordings would import exactly the prior we refuse to assume.
- **A fall is physics.** The free-fall, impact and stillness sequence transfers across bodies and homes without any training step.
- **A caseworker must be able to ask why.** Decomposable rules survive that question. A black box does not.
- Where a model helps later — smoothing the wording of the morning brief. It will never produce a score.

---

###### Backup · for Q&A

# Where the **data goes**

| Dataset | Role in the system |
|---|---|
| **SisFall** · Universidad de Antioquia · 4,505 recordings, 1,798 real falls | Calibrates the fall thresholds, measures the detector, and supplies the live demo trace |
| **CASAS Aruba** · Washington State University · 220 days of one elderly resident's home | Validates that self-baselining recovers a real routine — and finds the day it broke |

Nothing is trained on either dataset. Both are provenance-pinned with
checksums in a committed lock file, and every number reproduces from one script.

---

###### Backup · for Q&A

# What a flat **needs**

- Motion sensors in the rooms that carry routine — kitchen, bedroom, bathroom, living room.
- One contact sensor on the front door.
- One optional bangle for the acute track. The routine track works with nothing worn at all.
- An installer fills in a one-page sensor-to-area map. No cameras, no microphones, no rewiring.
