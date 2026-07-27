"""Suite-wide guards.

The ack poller (ADR 0012) long-polls api.telegram.org in a daemon thread.
Tests that set the token env vars would otherwise start it through the app
startup hook and touch the real network — the kill-switch keeps every test
run offline by construction.
"""
import os

os.environ["SHINEHACKATHON_TELEGRAM_ACK_POLL"] = "0"
