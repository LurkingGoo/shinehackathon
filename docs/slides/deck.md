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

# The safety net is **reactive**

Alarm buttons and wearables fail exactly when they're needed —
an unconscious senior presses nothing.

A fall becomes a **long lie**: hours helpless on the floor.

---

<!-- _class: statement -->

###### The insight

# The home **already knows**

Routine is a vital sign. Absence of motion is data.

The senior presses nothing, wears nothing new,
and is *never on camera*.

---

###### The product

# One screen, **calm by default**

![h:395](assets/caseload-calm.png)

*Every resident ranked by need — each row states its reason in one sentence.*

---

###### The demo beat

# A fall **preempts everything**

<figure>

![w:1020](assets/chip-simulate-button.png)

<figcaption>One button stands in for a real fall signal</figcaption>
</figure>
<div class="cols">
<figure>

![](assets/chip-acute-card.png)

<figcaption>A fall preempts everything — seconds, not a morning</figcaption>
</figure>
<figure>

![](assets/chip-recommended-action.png)

<figcaption>The system suggests; the caseworker acts</figcaption>
</figure>
</div>

---

###### How it works

# Sense → Score → **Decide**

![bare w:1050](assets/architecture.svg)

*Deterministic, explainable heuristics — no black box between sensor and caseworker.*

---

###### Explainable by contract

# Every number **decomposes**

<div class="cols">
<figure>

![](assets/chip-feature-decomposition.png)

<figcaption>Every score decomposes — nothing to take on faith</figcaption>
</figure>
<figure>

![](assets/chip-confidence-axis.png)

<figcaption>Trust is shown separately from risk</figcaption>

The system ranks and explains.
**A human decides.**

</figure>
</div>

---

###### Validated on real data

# It's **real**, not a concept

<div class="stat red"><b>96.2%</b><span>falls detected · 1,798 real falls</span></div>
<div class="stat sage"><b>0–5%</b><span>false alarms · elderly-typical</span></div>
<div class="stat sun"><b>220 days</b><span>real home · chronic track</span></div>

<figure>

![w:820](assets/chip-top-row.png)

<figcaption>Rank 1: a real 220-day routine, broken — in plain words</figcaption>
</figure>

---

###### Built for Singapore

# No imported **prior**

- **Self-baselining** — learns each resident's own rhythm in ~2 weeks; no foreign routine assumed.
- **Presence-only dignity** — seniors accept what doesn't watch them.
- Deploys **per HDB unit**; multiplies One Care's existing people, replaces no one.

---

###### Honest limits

# What we **don't** claim

- Shrinks time-to-detection — does **not** promise to catch every event.
- Fall thresholds calibrated on mostly-young-adult recordings; the senior false-alarm rate is extrapolated.
- Irregular lives get wide baselines — surfaced as *low confidence*, never hidden.
- ~2 weeks of history before chronic scores mature.

---

###### Beyond the PoC

# From demo to **pilot**

- **Escalation integrations** — welfare-call automation, MOH/AIC line handoff on unacknowledged falls.
- **Caseworker briefing** — auto-drafted, grounded strictly in the deterministic features.
- **Pilot design** — one One Care cluster; measure time-to-detection and caseworker minutes saved.

---

<!-- _class: statement -->

###### The ask

# Pilot **with us**

One cluster. Commodity sensors. A working system —
validated on **4,505 real recordings** and a **220-day real home**.

*Built at SHINE Hackathon · demo runs live.*
