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
> to. Nearly every standalone IP camera on the market — the TP-Link Tapos,
> the Xiaomis, the Hikvisions, exactly the cameras already sitting in
> Singapore households today — publishes its live feed over **RTSP**, an open
> streaming standard that's been the industry norm for twenty years. It's a
> standard output, like HDMI on a laptop. The camera's owner points us at the
> stream; the manufacturer is never in the conversation.
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
- If asked about ecosystem cameras (Ring/Nest): "The closed cloud ecosystems
  lock their streams — but those are the minority in local households, and
  our default kit ships its own forty-dollar RTSP camera, so no existing
  camera is even required."
- If asked about firmware again: "RTSP and ONVIF exist precisely so third
  parties can consume the stream without vendor permission. Every commercial
  video-analytics company works this way; firmware modification isn't how
  this industry integrates."
