# Handoff — 3-minute demo script + Singapore feasibility defence

*Written 2026-07-30, end of session. Spec line: docs only, no code touched.*

---

## 1. What the operator asked for (requirements, as given)

Verbatim intent, reconstructed from the session brief:

1. **The presenter's slot is the product demonstration, and it is ~3 minutes.**
   That is the hard constraint everything else bends around. There is no time
   for a live camera fall — only the simulated path.
2. **The demo flow he intends to run:** press **Simulate**, show **Tan Ah Moi**
   surface, let the **voice call-out** load and speak, show a **GIF of a prior
   incident**, and press the **acknowledgement** button.
3. **The points he actually wants to land** (he was explicit that the clicking
   is not the hard part — the *answers* are):
   - *"What if the elderly stepped out of the house?"* — the away-state answer.
   - **Camera placement can respect the senior** — cameras go where the senior
     is comfortable, not where we'd like them.
   - **They foresaw the elderly leaving the home** as a failure mode, and want
     credit for having foreseen it.
4. **Integration with existing technologies must be verified, not asserted.**
   His framing of the objection: *IP camera firmware is strictly not to be
   touched — is RTSP the only workaround?* Plus: *Singapore households use
   products which have RTSP* — a claim he wanted checked, not assumed.
5. **Feasibility in Singapore specifically**, and in particular the pivot:
   **there is no such thing as a dedicated in-home healthcare worker in
   Singapore.** The dashboard's users are **wellbeing coordinators** (Active
   Ageing Centre staff) **on top of existing volunteers** — that is the
   problem-statement pivot the deck must survive questions on.
6. **Method:** deploy sub-agents to verify against existing technologies, and
   generate the script from verified findings + his points.

---

## 2. What was delivered

**`docs/pitch-demo-script.md` (new)** — the 3-minute run sheet:

- Part 0: pre-flight checklist. The load-bearing item is **browser speech
  permission** — the 🔊 toggle must be on *and* the page must have had a user
  gesture before the first Simulate press, or the voice silently no-ops. This
  is the single most likely on-stage failure.
- Part 1: five timed beats (calm board → Simulate + voice → drilldown + GIF →
  STILL DOWN + acknowledge → close), with spoken lines and stage directions.
- Part 2: cut-order if running long, and the recovery line if a beat fails.
- Part 3: the three points from requirement #3, each planted as **one sentence
  inside a beat**, with the full answer held in reserve for Q&A.
- **§4 is a stub.** It is the Singapore-verified Q&A defence and it was not
  written — see §4 below.

**Two honesty findings that changed the run sheet** (both verified in code):

- **The GIF cannot come from Simulate.** `Simulate incident` fires an
  *accelerometer* incident for Tan Ah Moi, and `fixtures.replay_payload()`
  (`scoring-service/app/data/fixtures.py:361`) returns `None` for accelerometer
  incidents — the skeleton replay only exists for a *camera* incident detected
  on `/watch`. `Send test detection` on `/watch` also produces no replay: it
  calls `report()` with no payload, so `replaySnap` is undefined and the upload
  branch never fires (`WatchPanel.tsx:253`). **The GIF shown on stage must be a
  real artefact from an earlier camera fall, and the presenter must say so.**
- **STILL DOWN fires mid-demo.** `still_down_s = 45.0`
  (`scoring-service/app/main.py:468`), which in a 3-minute take lands right on
  beat 4. The run sheet turns this into a scripted beat rather than a surprise.

**Corrections pushed into the two existing pitch docs** from the camera-tech
research (see §3).

---

## 3. Research: camera integration — COMPLETE

The RTSP/ONVIF sub-agent finished and its findings are already folded into
`pitch-script-solutions.md` and `pitch-feasibility-singapore.md` §2 and §5.

Load-bearing corrections, all of which contradicted something we had written:

- **"Xiaomi" must not be said on stage.** Xiaomi's support page states the
  Smart Camera C300 supports neither RTSP nor ONVIF; Aqara's own PM states the
  G3 and G2H Pro have no RTSP. Stock firmware needs community flashing — the
  exact accusation we're disclaiming. Safe list: **Tapo wired, Reolink wired,
  Eufy wired, Hikvision, Dahua.**
- **RTSP on Tapo/Eufy is owner-enabled** (Tapo "Camera Account"). Rhetorically
  stronger than "it just publishes a stream" — *the owner grants it*.
- **Firmware revocation is real and must be conceded**, not denied: Wyze pulled
  its RTSP firmware April 2026; Nest removed RTSP in 2022. Answer is
  sensor-agnosticism, not denial.
- **Profile T, not Profile S** — S conformance submissions close 31 Mar 2027.
- **Hailo-8L (Pi 5 AI Kit) replaces Coral** in the BOM; Coral's 4-TOPS USB
  stick is effectively EOL. Run inference on the **substream** (~640×360, well
  under 1 Mbps), not the 2–4 Mbps main stream.
- **Install gotcha:** Tapo allows only 2 of 3 among Tapo Care cloud, SD-card
  recording, and ONVIF/RTSP. An inserted SD card silently kills the stream.

**The strategic finding not yet written up:** HDB's own assistive-living
programme lists **SoundEye (LiDAR + audio)**, **PreSAGE (thermal,
privacy-preserving)** and **WeCare (mmWave)** — all deliberately **non-camera**
— following a Queenstown pilot, with commercial fall-detection packages sold
onward. This is simultaneously our **strongest validation** (Singapore already
buys ambient fall detection for HDB flats) and our **most serious competitor**,
and it argues for repositioning the camera as the *cheap retrofit tier that
reuses hardware the household already owns*, with radar as the endgame the same
event contract already accepts. **This belongs in `pitch-feasibility-singapore.md`
§4 and was deliberately not written this session** to avoid colliding with the
Singapore sub-agent that was running over the same ground.

---

## 4. Research: Singapore eldercare ecosystem — FAILED, MUST BE RE-RUN

The second sub-agent **terminated on an API connection error** and returned
nothing usable. Its last emitted line was: *"GALE is a major find. Fetching the
MOH source."* — **treat "GALE" as an unverified lead, not a fact.** Nothing
about it survived; do not cite it until it is independently re-verified from an
MOH/AIC source. It may be an acronym, a programme name, or a mis-read.

**Re-run the brief below.** It is the blocker on §4 of the demo script.

Questions it must answer, Singapore-specific, with citations, marking anything
unverifiable as UNVERIFIED rather than guessing:

1. **Who actually does home-based elderly monitoring today** — AIC, Active
   Ageing Centres under Age Well SG, Silver Generation Office ambassadors,
   Lions Befrienders, TOUCH, Care Corner, ComLink. **Is "wellbeing coordinator"
   a real job title in Singapore?** The whole problem-statement pivot rests on
   this; if the title is wrong, find the correct one. Case-load ratios if
   published.
2. **Existing deployed tech we'd be compared to** — HDB/GovTech Smart Elderly
   Alert System, the MOH/AIC Personal Alert Button, pull-cord alarms in
   studio/2-room flexi flats, GovTech WAAS (iWOW, 170 blocks / 26,800 seniors
   — already cited in the deck, re-verify), CareLine, SmartPeep, plus the
   SoundEye / PreSAGE / WeCare trio above. What each does, who pays, known
   limitation.
3. **Who is the actual buyer and what funds it** — MOH, AIC, HDB, the AAC
   operator, or the town council? Which grant line.
4. **Privacy and regulation** — PDPA for video in a private home; who consents
   for a senior with possible dementia (Mental Capacity Act / LPA); whether a
   fall-alert dashboard is Software as a Medical Device under HSA, and the
   wellness-vs-medical-claim boundary. *Note the incumbent framing to borrow:
   Aqara's FP2 copy says explicitly "not a medical device… for notification
   purposes."*
5. **The presenter's own edge cases** — (a) senior leaves the home: what is the
   accepted SG approach (Dementia Friendly Singapore, Safe Return Card, CARA,
   Go-To Points)? (b) published SG research on **where seniors will accept a
   camera** — the bathroom is highest fall risk and least acceptable, which is
   exactly requirement #3's second point and currently rests on assertion.
   (c) **who responds at 3am** — is AAC/befriender coverage office-hours only?
   This is the most likely killer question and we do not have a verified answer.

Deliverable: the fact, the source URL, and a one-line "how the presenter uses
this" — ending with the five hardest questions this exposes, and **anything our
current framing gets factually wrong and must not be said on stage.**

---

## 5. Instruction to the next session: leverage, then critique

**Leverage.** Do not regenerate what exists. `pitch-feasibility-singapore.md`
(253 lines) already contains the rebuilt problem statement, the obligated-actor
table, the away-state machine, the BOM, and the one-breath Q&A answers.
`pitch-script-solutions.md` holds the spoken two-solutions script.
`docs/slides/deck.md` holds the measured numbers (96.2% / 18.8% / 220 days /
80.0% counter-experiment) and the honest-limits slide. **Read all three before
writing a line.** The demo script's §4 should *point at* those documents, not
restate them.

**Then critique.** Every one of those documents was written before this
session's verification pass, and the camera research proved that at least one
confidently-worded claim in them was simply false. Assume more are. Specifically:

- **Hunt the `[verify]` markers.** `pitch-feasibility-singapore.md` carries them
  on the 21%-super-aged figure, the ~80,000-seniors-living-alone figure, the
  long-lie mortality claim, the 220+ AAC count, the ~S$800M Age Well SG figure,
  and the BOM prices. Each is a number a judge could know better than we do.
  **A wrong Singapore-specific number on stage is worse than a gap.**
- **Re-read §4 of that document against the SoundEye/PreSAGE/WeCare finding.**
  Its current claim — "every hardware element in our stack is already deployed
  in Singapore eldercare today" — is defensible but was written without knowing
  that HDB's own programme deliberately chose *non-camera* sensing. The
  positioning sentence needs rewriting in light of that, and the competitive
  claim needs to become sharper, not softer.
- **Challenge the pivot itself.** Requirement #5 asserts there is no dedicated
  healthcare worker in Singapore and that wellbeing coordinators are the user.
  That is a strong, useful framing — but it is currently *our* assertion.
  Verify it or find the language that is actually true, because the entire
  target-user slide falls if a judge from AIC is in the room.
- **Preserve the honesty discipline this repo already keeps.** The deck names
  its own weak number (elderly falls, 84.0%, one volunteer, "held lightly");
  the run sheet makes the presenter say the GIF is from an earlier fall. That
  discipline is a differentiator in the room — do not let a tidier-sounding
  claim erode it.

**Open threads carried forward:** everything in `undone.txt` (ADR 0018 unwritten,
parity test for `ReplayFactsPayload`↔`ReplayFacts`, stale `slides.pdf`, leaked
bot token revoke) is untouched by this session and still stands.
