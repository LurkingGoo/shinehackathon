#!/usr/bin/env bash
# Stop Morning Triage (macOS/Linux twin of stop.bat): kill whatever listens on
# :8000 (scoring service) and :3000 (dashboard). Safe to run twice.
set -uo pipefail

for PORT in 8000 3000; do
  PIDS="$(lsof -ti "tcp:$PORT" 2>/dev/null || true)"
  if [ -n "$PIDS" ]; then
    echo "stopping :$PORT (pid $PIDS)"
    # shellcheck disable=SC2086 — PIDS is a space-separated pid list
    kill $PIDS 2>/dev/null || true
  else
    echo ":$PORT already free"
  fi
done
