#!/usr/bin/env bash
# Kickstart Morning Triage: scoring service (:8000) + triage dashboard (:3000).
#   ./start.sh          start both, stream logs, Ctrl-C stops both
# Override the interpreter with PYTHON=/path/to/python ./start.sh
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PY="${PYTHON:-C:/Users/lucas/anaconda3/python.exe}"
CHROME="${CHROME_PATH:-C:/Program Files/Google/Chrome/Application/chrome.exe}"

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

echo "▶ scoring service — installing deps (quiet) + starting on :8000 ..."
(
  cd "$ROOT/scoring-service"
  "$PY" -m pip install -q -r requirements.txt
  exec "$PY" -m uvicorn app.main:app --port 8000
) &
SVC_PID=$!

echo "▶ dashboard — starting on :3000 ..."
(
  cd "$ROOT/triage-dashboard"
  [ -d node_modules ] || npm install
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
