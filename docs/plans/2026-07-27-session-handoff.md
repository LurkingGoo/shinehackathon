# Session handoff — 2026-07-27

## What happened this session

- Pulled `main` to `7437d27` (start script tweaks + `/watch` test notes).
- `npm install` in `triage-dashboard/` — picked up `@vladmandic/face-api`, which
  was in `package.json` but missing from `node_modules` (cause of the logged
  `/watch` 500).
- Killed two stale background processes left over from a prior session
  (`next-server` on :3000, `uvicorn` on :8000 running pre-pull code — the old
  one 404'd on `/alerts/status` since that route postdated it).
- Restarted both services clean: dashboard on :3000, scoring-service on :8000
  (via `scoring-service/.venv`, since `start.sh`'s system-python path hits
  macOS's externally-managed-environment guard — **not fixed**, see below).
- Tuned the camera fall heuristic
  (`triage-dashboard/lib/pose/fallHeuristic.ts`, `DEFAULT_CONFIG`):
  `horizontalMinDeg` 60→48, `minVisibility` 0.5→0.4. Rationale: a
  screen-mounted webcam sees a real drop at a foreshortened angle, and the old
  60° threshold left genuine falls stuck in the 45–55° "transitional" band,
  which never arms the fall-candidate state machine regardless of how still
  the person stayed afterward. All 12 existing unit tests still pass
  unchanged (timing constants `fallWindowMs`/`stillMs` were left untouched
  since tests pin exact values against them).
- Configured Telegram alerts end-to-end: bot `@ShineDashboardbot`, chat id
  `5060159443`, both persisted in `~/.zshrc`. `GET /alerts/status` now reports
  `"telegram":{"configured":true}`.
  - Note: restarting a service to pick up new `~/.zshrc` exports needs an
    **interactive** shell (`zsh -ic '...'`), not `zsh -lc '...'` — zsh only
    sources `.zshrc` for interactive shells, login-only was silently skipping
    it, which cost a round of debugging.
  - Also: while debugging, a plain `cat ~/.zshrc` printed the raw bot token
    into this chat transcript. Low real-world risk (demo bot), but if that's
    unacceptable, regenerate via `@BotFather` → `/revoke` and swap the new
    token into `~/.zshrc`, then restart the service.

## Open issues (reported by operator, not yet fixed — investigate first)

### 1. Enrolled face name doesn't reach the Telegram alert

Reported symptom: enroll as e.g. "Raju," trigger a real detected fall, the
alert fires but doesn't say "Raju."

Traced root cause (read-only investigation, nothing changed):

- Client-side identity binding works as designed:
  `lib/face/engine.ts` (embed) → `lib/face/matcher.ts` (`bestMatch`,
  `IdentityTracker.update`) → `components/WatchPanel.tsx:284-286` binds
  `boundId`. On a fall, `WatchPanel.tsx:118` sends only **`residentId`** (no
  name) via `dataClient.reportCameraFall` → `POST /api/incidents/cv-detected`
  → `scoring-service/app/main.py:163-177`.
- The drop point: `scoring-service/app/fixtures.py:257-268`
  (`_resolve_cv_resident`) matches `resident_id` only against the hardcoded
  `CHRONIC` demo roster (`fixtures.py:59`). Anything that doesn't match
  returns `None` → `acute_identity()` (`fixtures.py:272-275`) falls back to
  the generic default identity `ACUTE`. `telegram.format_incident_message`
  (`scoring-service/app/alerts/telegram.py:37-46`) reads `e.name` straight
  from that resolved roster entry — never from anything the browser stored.
- Compounding factor: the "Enroll as" control in `WatchPanel.tsx:513-526` is
  a `<select>` bound to the same CHRONIC-backed roster
  (`dataClient.getRankedCaseload()`) — **not free text**. A locally-typed
  label is stored client-side (`lib/face/gallery.ts:29-44`) for on-screen
  display only and is never transmitted to the backend at all.
- This matches the stated design in `docs/adr/0011-enrolled-face-identity.md`:
  enrollment binds to "a caseload resident id chosen from the live roster (no
  free-text identities)," and identity is explicitly "metadata … never an
  input to the fall heuristic." So: enrolling someone who **is** an existing
  CHRONIC roster entry should already carry their name through correctly. The
  reported bug most likely means either (a) the "Raju" test case is a person
  not present in the CHRONIC fixture roster at all — expected fail-open
  behavior per current design, not a code defect — or (b) there's a second,
  narrower bug in the resolution path worth re-testing with a resident that
  *is* on the roster before assuming the whole path is broken.

**Next step**: confirm whether "Raju" was added to the CHRONIC roster before
testing. If yes and it still didn't carry through, that's a real bug in
`_resolve_cv_resident` worth a targeted repro. If no, the fix is a product
decision: either restrict enrollment demos to roster residents, or extend the
roster/backend to accept free-text identities (a bigger change — conflicts
with ADR 0011's explicit "no free-text identities" constraint, so would need
a conscious ADR update, not a quiet patch).

### 2. No per-resident "send to Telegram" toggle exists

Reported ask: when a face is newly enrolled, a dashboard checkbox for
"alert this person to Telegram" should auto-tick.

Confirmed by search: **this toggle doesn't exist anywhere in the codebase.**
No per-resident opt-in field on the resident model
(`scoring-service/app/models.py`, `fixtures.py`), no UI control in
`components/*`, no API surface. The only alert-related UI today is the
global, service-wide Telegram configured/not-configured badge
(`components/Dashboard.tsx:94-103`, backed by `GET /alerts/status`).

This is **not a regression** — it's a net-new feature. Building it would need:
- A per-resident field (e.g. on `ChronicResident`/`CaseloadEntry`).
- An endpoint to read/write it.
- Gating logic added to `_dispatch_alert` (`scoring-service/app/main.py:123-136`)
  so it's checked before a Telegram send.
- A checkbox in the dashboard resident view, defaulted per the ask ("auto-tick
  on enrollment") — meaning the enrollment flow in `WatchPanel.tsx` would also
  need to call whatever endpoint sets that field, at enrollment time.

## Also flagged, not yet addressed

- `start.sh` uses `$(command -v python3)` for the scoring-service, which hits
  macOS's PEP 668 externally-managed-environment guard. Should be changed to
  prefer `scoring-service/.venv/bin/python` when present.
- `npm audit`: 3 vulnerabilities (1 low, 1 high, 1 critical) — not triaged.
- `fsevents` install scripts pending `npm approve-scripts` approval — not
  actioned (benign, macOS file-watcher dep).
