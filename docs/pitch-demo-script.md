# The 3-minute product demonstration — run sheet + Q&A defence

*Prepared 2026-07-30. Owner: the demo presenter (Lucas). Slot: the product
demonstration, ~3 minutes, immediately after the problem statement and the
two-solutions bridge (see `pitch-script-solutions.md`).*

**Hard constraint: 3 minutes.** That buys exactly one live flow. This run sheet
spends it on the **simulated fall → named voice call-out → replay evidence →
acknowledgement** loop, because that is the one sequence that proves the whole
thesis (push-based, named, explainable, closed loop) in a single unbroken take.
Everything else is answered with words, not clicks.

---

## Part 0 — Pre-flight (do this before you are on stage)

Non-negotiable, in this order:

1. **Both services up.** `./start.sh`; dashboard on the projector tab,
   `/watch` on a second tab, Telegram chat on a third (or a phone held up).
2. **Reset demo** pressed, so the board is calm. An acute card left over from
   rehearsal kills the reveal.
3. **Audio on.** The 🔊 toggle in the dashboard header must read 🔊, not 🔇.
   Tap it once and let one incident speak in rehearsal — browsers block speech
   until the page has had a user gesture. **This is the single most likely
   failure on stage.**
4. **Laptop volume up**, and confirm the room's audio feed carries the laptop
   (not just the mic).
5. **A prior incident's stick-figure GIF already sitting in the Telegram chat**,
   scrolled to just above the fold. You will *not* generate a GIF live —
   see the honesty note below.
6. Telegram badge in the dashboard header shows configured, not "not
   configured". If it is unconfigured, cut beat 4 and say so.

**Honesty note you must respect:** the Simulate button fires an **accelerometer
(bangle)** incident for Tan Ah Moi. Accelerometer incidents carry **no skeleton
replay** — the replay/GIF only exists for a *camera* incident detected on
`/watch`. So the GIF you show is a **genuine artefact from an earlier camera
fall**, and you say that out loud: *"this one is from a fall we recorded
earlier this morning."* Do not imply the simulate press produced it. The one
sentence of honesty costs two seconds and is unattackable; a judge who spots
the mismatch costs you the room.

---

## Part 1 — The run sheet (3:00)

Timings are cumulative. Bracketed text is stage direction; the rest is said.

### Beat 1 · The calm board (0:00 → 0:25)

[Dashboard already on screen, calm.]

> This is what the coordinator opens at the start of a shift. One screen. Every
> senior in the catchment, ranked by who needs them first — and every row
> explains itself in one plain sentence, so nobody has to trust a number they
> can't interrogate.
>
> Nothing is flashing, because nothing is wrong. Calm is the default state —
> that matters, because a dashboard that cries wolf gets closed by lunchtime.

[Point at rank 1.] 

> This resident is top of the list on ambient sensors alone: a sixteen-hour
> kitchen gap, an early door. No camera, no wearable — just the rhythm of the
> flat breaking.

### Beat 2 · The fall preempts everything (0:25 → 1:05)

> Now a fall.

[**Press "Simulate incident".** Then say nothing for two seconds — let the
chime and the voice land.]

*The board will speak, twice:* **"Patient Tan Ah Moi has fallen at Living room!"**

> That is the system talking to the room, not to a screen nobody is looking at.
> It is on-device speech — no network, no cloud voice service — and it names
> her: **who** fell, and **which room to walk into**. And it will keep repeating
> every twenty seconds until a human answers it.
>
> [Point at the pinned card.] She's pinned above the whole caseload in about a
> second, with the evidence in words: free-fall, then impact, then stillness —
> in that order. That ordering is the whole detector. A dropped phone has the
> dip and the spike, but it gets picked up, so the stillness never comes.

*Every press streams a different real SisFall recording through the live
detector — if a judge asks, this is a real recorded fall, not a canned
animation.*

### Beat 3 · The evidence a coordinator can act on (1:05 → 1:45)

[Click the card to open the drilldown.]

> And she can see *why*. The score decomposes into the sensor facts that made
> it — nothing is taken on faith. A stale sensor lowers **confidence**; it
> never inflates risk, so a dead battery can't fake a crisis.

[Switch to the Telegram tab. Point at the prior incident's stick-figure GIF.]

> Here's what a fall looks like when the camera is the source — this one is
> from a camera fall we recorded earlier, since I'm not going to throw myself
> on the floor in three minutes.
>
> That is the **only** thing that ever leaves the flat: a three-second
> stick figure. Thirteen joints. No pixels of her, no face, nothing that
> could ever be a video of an 82-year-old on her bathroom floor. And it's
> enough to act on — it tells you she fell rightward, a one-point-nine second
> descent, hard impact, no arm protection. A coordinator reads that in a
> second and knows whether to call or to run.

### Beat 4 · The loop closes (1:45 → 2:35)

[If ~45 s have passed since the simulate press, the **STILL DOWN** escalation
will have fired on its own — point at it. If it hasn't yet, describe it.]

> Forty-five seconds with no recovery, and the system escalates by itself:
> **STILL DOWN**, louder, out to the next ring. Standing up cancels it. It
> fires once — we don't spam a group into muting us.

[**Press "🔕 I am responding — stop alert".**]

*The board will say:* **"Alert acknowledged. <name> is responding."**

> One tap. The first tap wins, so the family group always sees exactly one
> owner — no two people running to the same flat and nobody running to it at
> all. The Telegram message itself is edited to say who took it, and the
> dashboard badge shows the name within five seconds.
>
> The voice stops, because a human has the problem now.

### Beat 5 · The close (2:35 → 3:00)

> So: a silent fall on the floor became a **named** alert, in a room, on a
> phone, with evidence, claimed by a human — in under a minute. That's the
> whole product. Not "we detect falls" — **we end the long lie.**

[Stop. Do not add anything. Hand over.]

---

## Part 2 — Cuts, if you are running long

Cut in this order. Never cut beat 2 or beat 4.

1. Beat 1's rank-1 ambient explanation (−10 s) — say only "calm by default".
2. Beat 3's drilldown decomposition (−15 s) — go straight to the GIF.
3. Beat 4's STILL DOWN description (−10 s) — just acknowledge and close.
4. The close's second sentence.

If a beat fails technically: **say what should have happened, in one sentence,
and move on.** "The voice didn't fire — that's a browser audio permission on
this laptop, not the system" is a recoverable answer. Silence and clicking is
not.

---

## Part 3 — The points you want to plant (say these, don't wait to be asked)

You said the demo isn't the hard part — the *answers* are. But you have three
minutes and cannot spend them on caveats. So plant each of these as **one
sentence inside a beat**, and hold the full answer in reserve for Q&A. The
sentence is the hook; the reserve is the payoff if a judge pulls on it.

| Point | The one sentence, planted in… | Full answer lives in |
|---|---|---|
| She stepped out of the house | Beat 1, after "the rhythm of the flat breaking": *"— and a ten-dollar door sensor tells us she's out, so 'quiet flat' never means 'quiet because she went to the market.'"* | §4.1 below |
| Camera placement respects the senior | Beat 3, after "stick figure": *"and the camera goes where she'll accept one — the bathroom, where most falls happen, gets the wearable instead, never a lens."* | §4.2 below |
| We integrate, we don't replace | Beat 5, in the close: *"on cameras Singapore already owns, and into a workforce Singapore already funds."* | §4.3, §4.4 below |

**§4 is not written yet.** The camera-integration half of the verification pass
is complete and already folded into `pitch-script-solutions.md` (delivery notes)
and `pitch-feasibility-singapore.md` §2 — read those for the RTSP/ONVIF answers,
including the brands you must *not* name on stage. The Singapore half
(wellbeing-coordinator titles, PDPA and consent, who responds at 3am, camera
acceptability research) failed mid-research and must be re-run: the brief and
the open questions are in `docs/plans/2026-07-30-demo-script-handoff.md` §4.

Until it lands, answer the Singapore questions from
`pitch-feasibility-singapore.md` §8 ("one-breath answers"), and **do not quote
any figure still marked `[verify]` in that document.**
