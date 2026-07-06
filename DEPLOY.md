# Deploy — Morning Triage (public, live)

Two services go live: the **FastAPI scoring service** and the **Next.js dashboard**
that proxies `/api/*` to it. No database, no secrets. The demo runs on a synthetic
fall/near-miss fallback when the licensed datasets are absent (they are git-ignored),
so nothing extra is needed to make Simulate work.

The steps that need **your** accounts are marked 🔑 — I cannot create accounts or
enter credentials for you.

---

## Prerequisites (one-time, yours 🔑)

1. A **GitHub** account and this repo pushed to it (there is no git remote yet):
   ```bash
   gh repo create shinehackathon-triage --private --source=. --push   # if you have gh
   # or make an empty repo on github.com, then:
   git remote add origin https://github.com/<you>/<repo>.git
   git push -u origin main
   ```
2. A **Render** account (free): https://render.com — sign in with GitHub.

---

## Primary path — one platform, one connect (Render Blueprint)

`render.yaml` in the repo root defines **both** services and wires them together.

1. 🔑 Render dashboard → **New → Blueprint** → pick this repo.
2. Render reads `render.yaml` and creates `triage-scoring-service` + `triage-dashboard`.
   Click **Apply**. First build takes a few minutes.
3. Open the **triage-dashboard** URL Render gives you. Done — that URL is the app.
   `SCORING_SERVICE_URL` is set automatically from the scoring service's host.

**Warm-up:** free services sleep after ~15 min idle and cold-start (~50s). Before you
present, open the scoring-service URL (`/caseload` should return JSON) and the
dashboard once so both are awake.

---

## Alternative — Vercel (frontend) + Render (backend)

Vercel is faster for Next.js if you'd rather split them.

1. 🔑 Deploy the backend on Render as a standalone **Web Service** (not blueprint):
   root dir `scoring-service`, build `pip install -r requirements.txt`,
   start `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. Copy its URL.
2. 🔑 Vercel → **New Project** → this repo → set **Root Directory = `triage-dashboard`**.
3. 🔑 In Vercel project settings add env var **`SCORING_SERVICE_URL`** = the Render
   backend URL (with `https://`). Redeploy.
4. Open the Vercel URL.

---

## Live-channel (SSE) note

The fall re-rank streams over SSE (`/api/incidents/stream`) proxied through the
frontend host. Both Render and Vercel stream proxied responses, and the client has a
watchdog that reconnects, so the Simulate → re-rank beat works. If a host ever buffers
the stream, point the browser's `EventSource` straight at the backend URL and enable
CORS on FastAPI — but try the proxied path first; it normally just works.

## Optional — real SisFall traces instead of synthetic

The deployed demo uses the synthetic fall rotation because SisFall/CASAS payloads are
git-ignored (licensed, large). To show the **real** recorded traces on the live site,
add a backend build step that fetches them:
`python scripts/fetch_datasets.py` before start. Weigh the licence terms and the
mirror's reliability first (the pinned SisFall host is a mirror). Headline numbers in
the brief/deck come from the committed `metrics.json` and are unaffected either way.

---

## Before deploying

- Commit the pending pitch edits + these deploy files (one commit).
- `metrics.json` and `datasets.lock.json` are committed; the data dirs are not.
- Nothing here writes secrets to the repo.
