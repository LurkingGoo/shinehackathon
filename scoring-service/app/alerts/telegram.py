"""Telegram fall-alert dispatcher — the caregiver notification on an acute event.

Design guarantees (all tested in tests/test_telegram.py):
  * SAFE WHEN UNCONFIGURED — with no token/chat-id env vars it is a silent no-op,
    so a fresh clone and the offline demo work with zero setup.
  * BEST-EFFORT — a Telegram outage returns False and never raises, so the
    incident response (the thing that actually matters) is never blocked or
    broken by a notification failure.
  * SECRET-SAFE (vault rule 8) — the bot token comes ONLY from the env var
    SHINEHACKATHON_TELEGRAM_BOT_TOKEN and is never logged, echoed, or placed in
    the message body or any exception text.

stdlib only (urllib) — no `requests` dependency, matching scripts/render_set_env.py.

Config (Windows env vars, per vault convention SHINEHACKATHON_<SERVICE>):
    SHINEHACKATHON_TELEGRAM_BOT_TOKEN   the BotFather token (secret)
    SHINEHACKATHON_TELEGRAM_CHAT_ID     the destination chat / group id
"""
from __future__ import annotations

import json
import os
from urllib.request import Request, urlopen

from app.models import IncidentEvent

_TOKEN_ENV = "SHINEHACKATHON_TELEGRAM_BOT_TOKEN"
_CHAT_ENV = "SHINEHACKATHON_TELEGRAM_CHAT_ID"
_TIMEOUT_S = 4.0  # short: this is best-effort, never hold the caller


def is_configured() -> bool:
    """True only when BOTH the token and a destination chat id are set."""
    return bool(os.environ.get(_TOKEN_ENV) and os.environ.get(_CHAT_ENV))


def format_incident_message(event: IncidentEvent) -> str:
    """Human, actionable caregiver alert — no token, no internal ids.

    Pure and side-effect-free so it is unit-testable without a network."""
    e = event.entry
    s = e.score
    return (
        f"\U0001F6A8 FALL ALERT — {e.name} ({e.age})\n"
        f"{e.unit}\n"
        f"{s.rationale}\n"
        f"Risk {s.risk:.2f} · confidence {s.confidence:.2f} · {s.recency}\n"
        f"→ {event.detail.recommended_action}"
    )


def send_incident_alert(event: IncidentEvent) -> bool:
    """POST the fall alert to Telegram. Returns True on a delivered message.

    No-op (False) when unconfigured. Any network/HTTP error is swallowed and
    reported as False — callers treat it as fire-and-forget. The token is read
    here and used only to build the URL; it is never logged on any path."""
    if not is_configured():
        return False
    token = os.environ[_TOKEN_ENV]
    chat_id = os.environ[_CHAT_ENV]
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": format_incident_message(event),
        "disable_notification": False,
    }).encode()
    req = Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urlopen(req, timeout=_TIMEOUT_S) as resp:
            body = json.loads(resp.read().decode() or "{}")
        return bool(body.get("ok", resp.status == 200 if hasattr(resp, "status") else True))
    except Exception as exc:  # network, DNS, HTTP, JSON — all best-effort
        # deliberately no token in the log; %r of exc is Telegram-side text only
        print(f"[telegram] alert not delivered: {type(exc).__name__}: {exc}")
        return False
