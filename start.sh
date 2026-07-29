#!/usr/bin/env bash
# Kickstart Morning Triage: scoring service (:8000) + triage dashboard (:3000).
#   ./start.sh          start both, stream logs, Ctrl-C stops both
#   ./stop.sh           stop both (when this shell is gone)
# Override the interpreter with PYTHON=/path/to/python ./start.sh
# macOS/Linux entry point — Windows uses start.bat / stop.bat.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-$(command -v python3 || command -v python)}"
CHROME="${CHROME_PATH:-C:/Program Files/Google/Chrome/Application/chrome.exe}"

# --- Telegram config check (mirrors start.bat). On macOS the env vars live in
# ~/.zshrc, which bash — and anything launched non-interactively, including an
# AI agent running this script — never sources. So the service silently came
# up unconfigured. Hydrate the two vars from the usual rc files when missing.
# Values are never printed (vault rule 8).
for RC in "$HOME/.zshrc" "$HOME/.zprofile" "$HOME/.bashrc" "$HOME/.bash_profile"; do
  if [ -z "${SHINEHACKATHON_TELEGRAM_BOT_TOKEN:-}" ] || [ -z "${SHINEHACKATHON_TELEGRAM_CHAT_ID:-}" ]; then
    if [ -f "$RC" ]; then
      eval "$(grep -hE '^[[:space:]]*(export[[:space:]]+)?SHINEHACKATHON_TELEGRAM_(BOT_TOKEN|CHAT_ID)=' "$RC" 2>/dev/null || true)"
    fi
  fi
done
export SHINEHACKATHON_TELEGRAM_BOT_TOKEN="${SHINEHACKATHON_TELEGRAM_BOT_TOKEN:-}"
export SHINEHACKATHON_TELEGRAM_CHAT_ID="${SHINEHACKATHON_TELEGRAM_CHAT_ID:-}"
if [ -n "$SHINEHACKATHON_TELEGRAM_BOT_TOKEN" ] && [ -n "$SHINEHACKATHON_TELEGRAM_CHAT_ID" ]; then
  echo "[telegram] configured — falls will send REAL Telegram pings"
elif [ -n "$SHINEHACKATHON_TELEGRAM_BOT_TOKEN$SHINEHACKATHON_TELEGRAM_CHAT_ID" ]; then
  echo "[telegram] PARTIAL config — need BOTH SHINEHACKATHON_TELEGRAM_BOT_TOKEN and _CHAT_ID; alerts will NOT send"
else
  echo "[telegram] not configured — dashboard-only, no Telegram alerts"
fi

# Re-render slides.pdf from the Marp source when it's stale (never blocks startup).
DECK="$ROOT/docs/slides/deck.md"
SLIDES_PDF="$ROOT/triage-dashboard/public/slides.pdf"
if [ ! -f "$SLIDES_PDF" ] || [ "$DECK" -nt "$SLIDES_PDF" ]; then
  if [ -x "$CHROME" ]; then
    echo "▶ slides — deck.md newer than slides.pdf, re-rendering via marp ..."
    (
      cd "$ROOT/docs/slides"
      CHROME_PATH="$CHROME" npx --yes @marp-team/marp-cli@latest deck.md \
        --theme warm-human.css --allow-local-files --pdf -o "$SLIDES_PDF"
    ) || echo "⚠ slides render failed — continuing with the existing slides.pdf (if any)."
  else
    echo "⚠ Chrome not found at $CHROME — skipping slides render."
  fi
else
  echo "✓ slides.pdf up to date."
fi

echo "▶ scoring service — venv + deps (quiet) + starting on :8000 ..."
(
  cd "$ROOT/scoring-service"
  # Project venv: Homebrew/system python is PEP-668 externally-managed, so a
  # bare `pip install` dies (the long-standing start.sh failure). A venv makes
  # the install legal AND survives on any machine profile.
  if [ ! -x ".venv/bin/python" ]; then
    echo "  creating scoring-service/.venv ..."
    "$PY" -m venv .venv
  fi
  ".venv/bin/python" -m pip install -q -r requirements.txt
  exec ".venv/bin/python" -m uvicorn app.main:app --port 8000
) &
SVC_PID=$!

echo "▶ dashboard — starting on :3000 ..."
(
  cd "$ROOT/triage-dashboard"
  # Unconditional: a pull can add deps while node_modules already exists
  # (bit us 2026-07-27 — /watch 500 on the demo laptop). No-op when current.
  npm install
  # /watch pose assets (offline demo insurance) — never blocks startup;
  # without them the page falls back to the CDN at runtime.
  npm run fetch-pose-assets || echo "⚠ pose assets fetch failed — /watch will use the CDN."
  exec npm run dev
) &
WEB_PID=$!

cleanup() { echo; echo "stopping…"; kill "$SVC_PID" "$WEB_PID" 2>/dev/null || true; }
trap cleanup INT TERM

cat <<EOF

  ─────────────────────────────────────────────
   dashboard    →  http://localhost:3000
   judge brief  →  http://localhost:3000/judge-brief.html
   slides (pdf) →  http://localhost:3000/slides.pdf
   service API  →  http://localhost:8000
  ─────────────────────────────────────────────
  Ctrl-C to stop both.

EOF

wait
