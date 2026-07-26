---
type: notes
diataxis: explanation
title: /watch manual test pass — observations + open hypotheses
status: draft
date: 2026-07-26
tags: [camera, pose, telegram, testing, draft]
---

# Manual test notes: `/watch` fall detection

First real-human pass on [[2026-07-26-watch-camera-page]] after pulling the
`/watch` + `/training` batch. Recorded as-is for later critique — nothing
here has been actioned yet.

## Observations

- **Confidence on a real drop: 56%.** Operator stood, then intentionally
  dropped to the floor in front of the camera; heuristic fired at 0.56.
  The plan's documented band is ~0.6–0.85 (`fallHeuristic.ts`, transition
  speed + stillness length), so this reading landed just under the floor.
  Not necessarily a bug — a real fall can be slower/softer than the
  synthetic sequences the heuristic was tuned against in
  `fallHeuristic.test.ts` — but it's a real-world data point worth
  weighing against the vitest fixtures rather than dismissing.
- **Camera framing/angle is a bit fiddly** to get right (where to stand,
  how much of the body needs to stay in frame). No fix identified as
  necessary right now — noted as a known rough edge, not a blocker.
- **3.0 s stillness confirmation window: confirmed good.** Felt right in
  practice — long enough to avoid firing on a quick crouch, short enough
  not to feel laggy. Keep as-is.

## Gap: Telegram delivery status is invisible

`telegram.is_configured()` (`scoring-service/app/alerts/telegram.py`) is
checked server-side before every dispatch (`_dispatch_alert` in
`app/main.py`), and is a deliberate silent no-op when unconfigured — by
design, so a fresh clone works with zero setup. But that also means: in
this test session, Telegram was not set up, and nothing in the dashboard
or `/watch` UI said so. A fall fired, the caseload re-ranked, and there
was no visible signal that the "ping the caregiver" leg of the story
didn't run.

**Hypothesis:** surface Telegram configuration state directly in the UI —
e.g. a small badge on the dashboard and/or `/watch` ("Telegram: not
configured" vs "Telegram: connected") — so a viewer never has to *infer*
from silence that an alert leg didn't fire. Needs a way for the frontend
to learn `is_configured()`'s value (not currently exposed over the API).

## Hypothesis: named alerts via face / side-profile recognition

For testing purposes only: use face recognition (or side-profile, for
cases where the fall turns the person away from the camera) to identify
*which* resident fell, and carry that identity through into both the
dashboard entry and the Telegram message — a named ping ("Mdm Tan fell in
Unit 4B") instead of a generic fall alert.

Flagging up front, for critique rather than deciding here: this cuts
against the current privacy stance in [[adr/0010-browser-pose-assets]]
("no frame ever leaves the device") — recognition needs either an
on-device model (feasible, adds weight/latency to the browser bundle) or
a server round-trip (breaks the privacy invariant as currently stated).
Not proposing an approach yet, just logging the idea + the tension it
creates, to be resolved deliberately rather than by default.

## Requirement to check before any of the above ships

Whatever gets built next, the chain of custody from event → visibility
should be traceable end to end against one incident id: camera detection
fires → caseload dashboard shows it → Telegram attempt shows its actual
outcome (sent / not configured / send failed). Right now the first two
links are visible and the third is silent-by-design; any fix should make
all three checkable in one place, not just patch the Telegram gap in
isolation.

## Status

Draft — logged for critique. **Actioned 2026-07-26:** the Telegram visibility
gap is closed — `GET /alerts/status` reports configuration plus the outcome of
the most recent dispatch (sent / failed / not-configured), the dashboard
toolbar badges it ("Telegram: connected / alert sent / send failed / not
configured"), and `/watch` shows the chip and logs each detection's actual
Telegram outcome. All three chain-of-custody links are now visible per
incident. Confidence-band retune remains open.

**Actioned 2026-07-27:** face identity shipped (phases 0–5 of
[[2026-07-26-face-identity-phases]], ADR 0011). What a fake camera cannot
test needs a REAL-WEBCAM REHEARSAL on the demo laptop:

1. `git pull`, start both services, open `/watch`, Start camera. Expect the
   log lines "Camera watching (pose model: local)" and "Face identity ready
   (models: local)" (run `npm run fetch-pose-assets` if either says cdn).
2. Enroll yourself as a resident: pick a name under "Enroll as", capture
   three angles (front, left profile, right profile), each close to the
   camera. The card lists "3 angles".
3. Walk back into frame upright — the chip should flip to "Identified:
   <name>" within a couple of seconds.
4. Fall (fast drop, hold still 3 s). Expect: log "Fall detected as <name>",
   the dashboard pins THAT resident, the Telegram ping names them, and the
   log follows up with the delivery outcome.
5. Note the matcher behavior for the retune: how quickly it identified you,
   whether the identity survived the fall (it should — the binding has a
   30 s no-sighting grace), and any wrong-person flips (raise
   `rebindHits` / lower `maxDistance` in `lib/face/matcher.ts` if so).
6. "forget" your enrollment afterwards if the laptop is shared.
