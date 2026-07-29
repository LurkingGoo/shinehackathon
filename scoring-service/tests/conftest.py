"""Suite-wide guards.

The ack poller (ADR 0012) long-polls api.telegram.org in a daemon thread.
Tests that set the token env vars would otherwise start it through the app
startup hook and touch the real network — the kill-switch keeps every test
run offline by construction.

The REAL bot credentials are stripped outright (gap check 2026-07-30): on a
machine with the demo's env vars set, every pytest run was dispatching
GENUINE fall alerts — and, since ADR 0017 phase 5, replay GIFs — to the
real caregiver chat through the incident endpoints. Tests that exercise the
"configured" path set fake values via monkeypatch; nothing in the suite may
ever reach the real bot.
"""
import os

os.environ["SHINEHACKATHON_TELEGRAM_ACK_POLL"] = "0"
os.environ.pop("SHINEHACKATHON_TELEGRAM_BOT_TOKEN", None)
os.environ.pop("SHINEHACKATHON_TELEGRAM_CHAT_ID", None)
