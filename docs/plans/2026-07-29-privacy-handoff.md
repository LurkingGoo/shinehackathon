# Privacy handoff — what leaves the machine, what doesn't, and what to fix

Date: 2026-07-29 · Status: draft for discussion
Scope: the /watch camera page, scoring service, and Telegram alert leg.
Verified against code (`WatchPanel.tsx`, `lib/face/*`, `lib/data/client.ts`,
`app/alerts/telegram.py`, `render.yaml`) — not from memory.

## 1. The headline answer

**No video, no frames, no face images ever leave the browser.** All camera
inference is local:

- Pose (MediaPipe) and face recognition (face-api) run in-browser, on-device.
- The `<canvas>` is used only to draw the skeleton overlay; nothing is
  captured from it or uploaded.
- Face enrollment stores 128-number embeddings (a mathematical face
  signature, not a photo) in the browser's localStorage only.
- Model weights load from vendored local files first; the CDN
  (cdn.jsdelivr.net) is a fallback only when local assets are missing.

What DOES go over the network, and only on an incident or registry action:

| Egress | Destination | Payload |
|---|---|---|
| Fall report | scoring service `/api/incidents/*` | stillness seconds, confidence, optional note, `residentId` |
| Still-down escalation | scoring service | seconds down, `residentId` |
| Register / locate resident | scoring service | name, age, zone/block/unit, optional GPS lat/lon |
| Fall + escalation alert | api.telegram.org → caregiver chat | **name, age, location line, risk numbers, recommended action** |
| Model fallback | cdn.jsdelivr.net | request metadata only (IP/UA), no user data |

So: the recording is never sent; the only third-party egress carrying
personal data is the Telegram alert text.

## 2. How a user can *verify* that (trust → proof)

1. **DevTools Network tab** while the camera runs: the only requests are
   status polls and (on a detection) small JSON POSTs — no media uploads,
   no websocket streaming frames.
2. **Offline demo mode**: with pose/face assets vendored, the watch page
   runs with networking disabled entirely; alerts simply queue as
   "not sent". This is the strongest proof — the feature works with the
   cable pulled.
3. **Code audit points**: `engine.ts` (only consumer of the video element),
   `client.ts` (every fetch in one file), `telegram.py`
   (`format_incident_message` is the complete alert payload).

## 3. Open privacy concerns (ranked)

1. **No auth on the scoring service, and it deploys publicly** (Render free
   tier, ADR 0007). Anyone with the URL can read the ranked caseload —
   names, ages, unit locations, risk scores of vulnerable people — and can
   POST fake falls (spamming caregivers) or register bogus residents.
   *Biggest real gap. Fine for a demo with fixture data; not fine the
   moment one real name is entered.*
2. **PII transits Telegram.** Name + age + home location of a vulnerable
   person passes through Telegram's servers into a group chat; anyone
   added to the chat sees the history. Bot token grants send-as-bot to
   whoever holds it (it lives in env vars — good — but rotate if leaked).
3. **Face embeddings are biometric data** (PDPA: likely "personal data"
   and sensitive). Stored unencrypted in localStorage: anyone with access
   to the browser profile can read who is enrolled and impersonate the
   matcher's inputs. No consent capture at enrollment, no expiry.
4. **GPS coordinates of a residence** are collected via browser
   geolocation and stored in the runtime registry / rendered in alerts.
5. **No retention or deletion story.** Registry is in-process memory
   (restart wipes it — accidentally decent), but embeddings persist in
   localStorage indefinitely; incident history persists for the process
   lifetime; Telegram messages persist forever unless manually deleted.
6. **CDN fallback leaks usage metadata** (a jsdelivr request reveals an
   IP is running this app). Mitigated by vendored assets; consider
   removing the fallback in a privacy-hardened build.

## 4. Plan draft (post-hackathon hardening)

- [ ] Add an API key / session auth to every scoring-service route that
      reads or writes resident data; keep `/health` open. (Concern 1)
- [ ] Alert minimization option: first name + unit only, no age, no GPS
      in the Telegram text; full detail stays on the dashboard behind
      auth. (Concern 2)
- [ ] Enrollment consent step in the UI + a visible "delete my face data"
      button (removePerson exists — surface it as a resident-facing
      control) with a localStorage wipe. (Concern 3)
- [ ] Document retention: what lives where, for how long, who can purge.
      One page, linked from the README. (Concern 5)
- [ ] Privacy-hardened build flag: no CDN fallback, hard-fail if local
      assets missing. (Concern 6)
- [ ] Optional: CSP `connect-src` allowlist (self + telegram via backend
      only) so the browser *cannot* exfiltrate frames even if a dependency
      went rogue — turns "we don't upload video" into "the browser blocks
      it".

## 5. One-line pitch answer for judges

"Video never leaves the device — all vision runs in the browser. The only
thing that goes out is a short text alert to the caregiver's Telegram, and
here's the Network tab to prove it."
