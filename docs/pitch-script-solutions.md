# Pitch script — the two solutions

*Slot: immediately after the problem statement (the long lie) and the target
demographic (existing eldercare centres / Active Ageing Centres and their
wellbeing coordinators). Total ~2 min. Stage directions in brackets.*

---

## Bridge (5 seconds)

> So the wellbeing coordinator is our user — and we give them two ways to hear
> a senior who can't call for help. One on the wrist. One on the wall.

---

## Solution 1 — the wearable (30 seconds)

> First, the wrist.
>
> This is the Bangle.js 2 — an open-source smartwatch, about forty dollars,
> with an accelerometer and weeks of battery life. It does two things: it
> detects the *impact* of a fall, and it gives the senior a help button that
> works anywhere in the flat — even where there's no camera, even in the
> bathroom, where most falls actually happen and where a camera will never be
> acceptable.
>
> When it fires, it doesn't go to some vendor cloud. It streams straight into
> the same triage pipeline you'll see in a moment — the coordinator's
> dashboard pins the incident and the family's Telegram pings, all within
> seconds.
>
> [beat] But a watch has one honest weakness: the senior has to *wear* it.
> Compliance fades. So the wearable is our first layer — not our last.

---

## Solution 2 — the camera, without touching anyone's firmware (~75 seconds)

> Second, the wall — and let me deal with the obvious objection head-on.
>
> We are **not** tapping into the firmware of anyone's camera. We don't need
> to. The volume seller in Singapore homes is the **TP-Link Tapo** — the C200
> is on the shelf at Challenger — and every wired Tapo ships with a documented
> **RTSP** and **ONVIF** output that the *owner* switches on in the app, in
> two taps, under "Camera Account". RTSP is an open streaming standard that
> has been the industry norm for twenty years. It's a published output, like
> HDMI on a laptop. The owner enables it and points us at the stream; the
> manufacturer is never in the conversation.
>
> That stream goes to a **Raspberry Pi** inside the flat — a hundred-and-
> thirty-dollar computer, cheap enough to deploy one per household. The Pi
> runs our pose-estimation model locally: it watches the *shape* of the
> person, the skeleton, and recognises the geometry of a fall.
>
> Now you may be wondering — what about storage? Are we recording grandma
> twenty-four seven? **No. Nothing is ever stored.** The Pi keeps only a
> *rolling buffer* — the last few seconds of skeleton data, in memory,
> continuously overwritten. Think of a dashcam that erases itself every ten
> seconds. The video is decoded and discarded inside the flat; the cable
> physically ends at that little box in the senior's own home.
>
> The only time anything leaves is the moment a fall is detected. And what
> leaves is not video — it's an alert, plus a three-second **stick-figure
> replay** from that rolling buffer. [gesture at screen] That goes to the
> family's Telegram instantly, with one button: "I am responding." First
> tap claims it. If the camera sees no recovery and no one has responded,
> the system escalates on its own — a STILL DOWN alert, louder ring,
> wellbeing coordinator, then emergency services.
>
> So our second solution is simple: **the cameras Singapore already owns,
> plus a hundred-and-thirty-dollar box, turn a silent six-hour lie on the
> floor into a sixty-second response — and not one frame of video ever
> leaves the flat.**
>
> [transition] Let me show you what the coordinator actually sees. [demo]

---

## Delivery notes

- The storage question is planted deliberately ("you may be wondering") —
  answer it before a judge asks it; the dashcam analogy is the anchor.
- "Not one frame of video ever leaves the flat" is the applause line — land
  it slowly, then move straight to the demo.
- If asked about ecosystem cameras (Ring/Nest/Arlo/Kasa): "Those are genuine
  walled gardens — Nest dropped RTSP in 2022 and Ring never had it. We don't
  fight them: either we go through the vendor's own cloud API — Google
  publishes one — or the household swaps in a forty-dollar Tapo, which is
  cheaper than the engineering. Our default kit ships its own RTSP camera, so
  no existing camera is even required."
- **Do not say "Xiaomi".** Xiaomi's own support page states the Smart Camera
  C300 supports neither RTSP nor ONVIF, and Aqara's product manager has said
  on their forum that the G3 and G2H Pro have no RTSP either. Stock-firmware
  Xiaomi/Imilab needs community firmware — exactly the "you're modifying our
  camera" accusation we're refusing. The safe brand list to name out loud:
  **Tapo (wired), Reolink (wired), Eufy (wired), Hikvision, Dahua.**
- If asked about firmware again: "RTSP and ONVIF exist precisely so third
  parties can consume the stream without vendor permission. Every commercial
  video-analytics company works this way; firmware modification isn't how
  this industry integrates."
- **If a sharp judge asks "can't a firmware update just take RTSP away?" —
  say yes.** "It happens. Wyze pulled their RTSP firmware in April this year;
  Google removed it from Nest in 2022. That's why we certify a short hardware
  list where RTSP is a documented first-party feature, and why the detector
  never cares what the sensor is: the same pipeline takes an mmWave radar
  feed. Losing a camera brand is a config change for us, not a rewrite."
  Conceding a real risk and showing the architecture already absorbs it is
  stronger than claiming the risk doesn't exist.
