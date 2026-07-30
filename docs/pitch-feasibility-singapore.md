# Feasibility & Problem Framing — Singapore Deployment Defense

*Prepared 2026-07-30, responding to judge/peer feedback: (1) "camera companies won't
let you alter their firmware", (2) "CV medicine detection — the elderly may just
throw the pill away", (3) "no one is obligated to care for these seniors", (4)
"what if the elderly left the home — your inactivity signal false-alarms".*

Figures marked **[verify]** are from memory as of early 2026 — re-check against
MOH / DOS sources before putting them on a slide.

---

## 1. The problem statement, rebuilt

**Old framing** (what was pitched): *"caring for elderly living in solitude by
watching their routines."* This invites both objections — it names no responsible
actor, and "watching routines" sounds fragile.

**New framing:**

> Singapore will be a super-aged society by 2026 — over 21% of citizens aged 65+,
> heading to ~1 in 4 by 2030 **[verify]**. Around **80,000 seniors live alone
> today, projected toward ~100,000 by 2030** **[verify — DOS/MSF projection]**.
> For this group, the deadliest event is not the fall itself but the **long lie**:
> falling and remaining on the floor for hours because no one knows. Beyond an
> hour on the floor, complications (pressure injury, rhabdomyolysis, dehydration,
> pneumonia) escalate sharply and mortality within a year rises steeply
> **[verify — cite a long-lie study, e.g. Wild et al. or a local geriatrics ref]**.
>
> Singapore's current safety net for this group is **periodic and pull-based**:
> a befriender visits weekly, an Active Ageing Centre calls occasionally, and the
> MOH-funded **Personal Alert Button** in rental flats requires the fallen person
> to *reach and press a button* — exactly what an unconscious or immobilised
> person cannot do. Between touchpoints there is silence, and silence is
> indistinguishable from crisis.
>
> **The gap is not care capacity — it is signal.** The community-care workforce
> that Singapore has already built and funded (AACs, SGO, befrienders, ComLink)
> is flying blind between visits. We give that existing workforce a **push-based,
> privacy-preserving signal layer**: ambient sensors rank the quiet caseload by
> anomaly ("no kitchen activity in 16h"), and an opt-in edge camera turns a fall
> from a silent long lie into a 60-second Telegram alert with skeleton-replay
> evidence — no video ever leaving the flat.

Three deliberate moves in that framing:

1. **The enemy is the long lie, not the fall.** Falls can't be prevented by
   software; the *hours on the floor* can be eliminated. This is a sharper,
   defensible claim.
2. **The user is a funded, mandated workforce that already exists** (§3) — not a
   hypothetical "healthcare worker".
3. **The system is a signal layer on top of Singapore's existing care structure**,
   not a new care service. Infrastructure-shaped ideas survive feasibility
   questions; service-shaped ideas don't.

---

## 2. "Camera companies won't allow firmware alteration" — the objection is category error

**No commercial video-analytics product on Earth modifies camera firmware.** The
industry integration pattern, for two decades, has been:

- **RTSP** (Real Time Streaming Protocol): virtually every consumer/pro IP camera
  — Hikvision, Dahua, Reolink, TP-Link Tapo, Xiaomi (with standard mode) — serves
  its live feed as an RTSP URL on the local network. It is a *published output*,
  like HDMI on a laptop.
- **ONVIF**: the industry interoperability standard (founded by Axis/Bosch/Sony
  precisely so third parties can consume streams and PTZ control without vendor
  permission). "ONVIF-conformant" is a checkbox on the camera's own spec sheet.

The camera vendor is not a stakeholder in this integration. The **customer owns
the camera and its stream**; we are a consumer of a standard output, on the
customer's own LAN. Asking "will Hikvision let you?" is like asking whether Dell
must approve the monitor you plug in.

**Our architecture already assumes this.** The `/watch` page today does pose
estimation on a plain webcam feed in the browser — no camera internals touched.
Production swaps "browser + webcam" for "edge box + RTSP pull". Same model, same
event contract, same scoring service.

And if a deployment rejects cameras entirely, the event contract is
sensor-agnostic: a **mmWave radar** (Vayyar Care class — camera-free, no image
formed at all) emits the same "fall detected" event. Camera vs radar is a swap
at the edge, not a redesign.

---

## 3. "No one is obligated to care for these elderly" — Singapore has already built and funded the obligated actor

The objection assumes the user is a hospital healthcare worker with no duty to a
community-dwelling senior. Correct — and irrelevant, because Singapore's
community-care system *does* assign responsibility for exactly this population:

| Actor | Mandate | Relationship to our dashboard |
|---|---|---|
| **Active Ageing Centres (AACs)** — 220+ islandwide under **Age Well SG** (multi-agency programme, ~S$800M+ over 2024–2028 **[verify]**) | MOH-funded with **assigned geographic catchments**; explicitly tasked with outreach to and monitoring of vulnerable seniors, *especially those living alone*, tiered well / at-risk / frail | **This is our primary user.** The "caseworker" opening the morning triage screen is an AAC care associate starting shift. The ranked caseload maps 1:1 onto their tiering duty. |
| **Silver Generation Office (SGO)** ambassadors | Door-to-door outreach visits to seniors, needs identification, referral | Consumer of chronic-track flags ("visit this flat first") |
| **Befriender organisations** (Lions Befrienders, TOUCH, Care Corner) | Regular befriending for isolated seniors; several have *already run home-sensor pilots* (§4) | Volunteer ring on the Telegram alert group |
| **ComLink / SSO** | Family-level coordination in rental-flat communities | Escalation path |
| **Family / next-of-kin** | The first ring, wherever they exist | Direct Telegram alert recipients — the acute path needs no institution at all |

So the honest answer to the judge: *"You're right that no doctor is attached to
these seniors — which is why our user isn't a doctor. Singapore spent the last
three years building a funded community workforce whose KPI is literally
'monitor seniors living alone in your catchment.' They currently do it by
knocking on doors. We are the between-visits layer for the workforce that
already has the obligation."*

The concentric-ring escalation (matches our existing ack + STILL-DOWN design):
**family Telegram group → AAC duty staff → befriender volunteer → SCDF 995.**
First responder taps "I am responding"; no response + no recovery on camera
escalates outward. (Same pattern as SCDF's **myResponder** — Singapore-proven
volunteer dispatch.)

---

## 4. Existing Singapore deployments — we extend a proven pattern, we don't invent one

Evidence that ambient monitoring of seniors living alone is *already accepted
practice* here (each **[verify]** the current programme name/status):

- **HDB Smart Enabled Homes trials** (Yuhua, Punggol Northshore): elderly
  monitoring packages using **PIR motion sensors + door contact sensors** with
  alerts to caregivers. Our chronic track is this pattern plus a scoring brain.
- **MOH/AIC Personal Alert Button (PAB)**: deployed across tens of thousands of
  rental-flat units — proves government will fund per-flat safety hardware for
  this exact demographic. Its weakness (requires a conscious button-press) is
  precisely our acute track's value-add.
- **Lions Befrienders sensor pilots**: befriending VWOs have piloted in-home
  sensor monitoring for seniors living alone — the *organisational* appetite
  exists, blocked mainly by alert-fatigue and triage (our core feature).
- **SmartPeep** (Singapore company): AI vision fall/near-fall monitoring in
  local nursing homes — camera-based elderly analytics is already commercially
  deployed *in Singapore institutions*.
- **mmWave radar in community care** (Vayyar Care class pilots): the accepted
  camera-free endgame; our sensor-agnostic contract is built for it.

Positioning sentence for the deck: *"Every hardware element in our stack is
already deployed in Singapore eldercare today — PIR (HDB trials), door sensors
(HDB trials), per-flat alert hardware (PAB), vision analytics (SmartPeep in
nursing homes). What does not exist is the layer that fuses them into one
ranked, explainable caseload for the AAC workforce. That layer is this project."*

---

## 5. The Raspberry Pi edge deployment — concrete BOM and topology

Per-flat kit (all commodity, all installable in one visit, no drilling beyond
adhesive mounts):

| Item | Approx cost (S$) **[verify]** | Role |
|---|---|---|
| Raspberry Pi 5 (4GB) + PSU + case + SD | ~130 | Edge brain: pulls RTSP, runs pose model, hosts event client |
| IP camera (any ONVIF/RTSP, e.g. Tapo) *or* Pi Camera Module 3 | 40–70 | Acute track (opt-in rooms only) |
| 2–3 × Zigbee PIR motion sensors | ~15 each | Chronic track: kitchen / bedroom / bathroom presence |
| 1 × Zigbee **door contact sensor** (main door) | ~10 | Home/Away state — the §6 answer |
| Zigbee USB dongle | ~20 | Sensor radio |
| **Total** | **~S$250–300** | vs. mmWave radar at ~S$700+/room; vs. one A&E fall admission at thousands |

Why the Pi is the right feasibility story:

- **Compute is sufficient**: MoveNet-Lightning (the same pose model our `/watch`
  page runs) executes at usable FPS on a Pi 5 CPU via TFLite; a US$30 Coral USB
  accelerator makes it comfortable at full frame rate **[verify current FPS
  numbers before claiming on stage]**. Fall detection needs ~10 FPS, not 60.
- **Privacy is structural, not policy**: video is decoded and discarded *inside
  the flat*; only pose skeletons, events, and the 3-second skeleton-replay GIF
  (ADR 0017 — stick figure, no pixels of the person) ever leave the device.
  "The video cable physically ends at a S$130 box in the senior's own home" is
  a sentence a judge can hold onto.
- **Offline-tolerant**: local fall→Telegram path needs only home broadband or a
  4G dongle; chronic scoring degrades gracefully during outages (events queue).
- **Fleet-manageable**: AAC deploys N flats = N Pis phoning home to one scoring
  service — exactly our current architecture (`scoring-service` is already the
  multi-resident aggregation point).

Topology: `[camera →RTSP→ Pi 5 (pose + fall logic)] + [Zigbee PIR/door → Pi] →
events only → scoring service → AAC dashboard + family Telegram.`

---

## 6. "What if the elderly left the home?" — the Away state (and why leaving is itself a signal)

The objection is correct against naive inactivity detection, and it has a
standard, cheap, already-deployed-in-HDB-trials answer: the **main-door contact
sensor** drives a three-state presence machine:

```
            door event + interior motion within T      door event + NO interior
   HOME  ─────────────────────────────────────▶ HOME     motion within T (~10 min)
     │                                                ┌──────────────▶ AWAY
     │  night hours + last motion in bedroom          │
     ▼                                                ▼ any interior motion
   ASLEEP (relaxed thresholds, bathroom still armed)  HOME (auto-return)
```

- **AWAY suppresses all inactivity anomalies.** "No kitchen activity in 16h"
  simply does not fire when the last event sequence was *motion at door → door
  open/close → no interior motion*. This kills the false-positive class the
  judge is pointing at with a S$10 sensor.
- **Ambiguity resolves conservatively and self-corrects**: if state is uncertain,
  hold scoring for the timeout; the first interior motion event flips back to
  HOME. Wrong-AWAY costs a delayed flag, never a false emergency call.
- **Leaving becomes a *feature*, not a bug**: for seniors with dementia risk,
  `AWAY since 21:40, not returned by 01:00` is a *new chronic-track signal* —
  night wandering — that today's system cannot see at all. The objection, taken
  seriously, hands us an additional detector on the same hardware.
- Optional enrichment, all opt-in and non-invasive: the family Telegram bot can
  simply *ask* ("Mdm Tan's flat has been quiet since 2pm — is she with you /
  at the AAC today?") — a human-in-the-loop disambiguation that costs nothing
  and builds trust.

Implementation note for us: the contract already carries `zone` (last-motion
area) per ADR 0012 — a `presence: home|away|asleep` field on the entry is a
small, natural extension, and the fixtures can demo an AWAY-suppressed entry.

---

## 7. The medicine-box pivot — formally dropped

Recorded so the reasoning survives: CV on a pillbox measures *"pill left the
box"*, not *"pill was ingested"* — discard/hoard/double-dose are invisible, a
S$2 lid switch in existing smart pillboxes (a crowded market) captures the same
proxy more reliably, and true ingestion verification needs ingestible-sensor
territory no hackathon should enter. The critique ("they may throw it away") is
accepted as correct and the pivot is closed. We stay on the long-lie problem,
where our detection *is* the ground truth (the camera sees the fall itself, not
a proxy for it).

---

## 8. One-breath answers for Q&A

- **"Vendors won't let you touch their firmware."** — We never touch firmware.
  Every IP camera publishes an RTSP stream on the owner's own network — a
  standard output, like HDMI. We read it on a Raspberry Pi inside the flat.
  ONVIF exists precisely so third parties can do this without vendor permission.
- **"Nobody is obligated to care for these seniors."** — Not doctors — but MOH
  pays 220+ Active Ageing Centres to monitor exactly this population in assigned
  catchments under Age Well SG. They do it by door-knocking. We're the layer
  between the knocks, plus the family ring that needs no institution at all.
- **"What if they just went out?"** — A S$10 door sensor gives us a Home/Away
  state; Away suppresses inactivity alerts entirely. And an Away that lasts all
  night is a *wandering* signal we get for free.
- **"Elderly won't accept cameras."** — The default kit has no camera: PIR +
  door sensor only, the same hardware as HDB's own smart-home trials. Cameras
  are opt-in for high-fall-risk residents, video never leaves the flat, and
  what leaves is a stick figure. The camera-free endgame (mmWave radar) plugs
  into the same event contract.
- **"Why not just the Personal Alert Button?"** — PAB requires the fallen
  person to press it. The scenario that kills — unconscious after a fall — is
  the one scenario PAB structurally cannot cover. We are its complement, not
  its competitor.
