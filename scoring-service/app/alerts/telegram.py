"""Telegram fall-alert dispatcher — the caregiver notification on an acute event.

Design guarantees (all tested in tests/test_telegram.py + tests/test_escalation.py):
  * SAFE WHEN UNCONFIGURED — with no token/chat-id env vars it is a silent no-op,
    so a fresh clone and the offline demo work with zero setup.
  * BEST-EFFORT — a Telegram outage returns False and never raises, so the
    incident response (the thing that actually matters) is never blocked or
    broken by a notification failure.
  * SECRET-SAFE (vault rule 8) — the bot token comes ONLY from the env var
    SHINEHACKATHON_TELEGRAM_BOT_TOKEN and is never logged, echoed, or placed in
    the message body or any exception text.

ADR 0012 additions:
  * The fall alert carries one inline button ("I am responding"); a lazy
    daemon thread long-polls getUpdates and records the acknowledgement in
    process ({by, at}), surfaced via /alerts/status. Kill-switch:
    SHINEHACKATHON_TELEGRAM_ACK_POLL=0 (set in tests — no test touches the
    network through the poller).
  * format/send_escalation_alert — the long-lie "STILL DOWN" second message,
    fired by /incidents/escalate when the camera sees no recovery.

stdlib only (urllib) — no `requests` dependency, matching scripts/render_set_env.py.

Config (Windows env vars, per vault convention SHINEHACKATHON_<SERVICE>):
    SHINEHACKATHON_TELEGRAM_BOT_TOKEN   the BotFather token (secret)
    SHINEHACKATHON_TELEGRAM_CHAT_ID     the destination chat / group id
"""
from __future__ import annotations

import json
import os
import threading
import time
from urllib.request import Request, urlopen

from app.models import IncidentEvent

_TOKEN_ENV = "SHINEHACKATHON_TELEGRAM_BOT_TOKEN"
_CHAT_ENV = "SHINEHACKATHON_TELEGRAM_CHAT_ID"
_ACK_POLL_ENV = "SHINEHACKATHON_TELEGRAM_ACK_POLL"
_TIMEOUT_S = 4.0  # short: this is best-effort, never hold the caller
_POLL_TIMEOUT_S = 20  # getUpdates long-poll window

# Acknowledgement state (ADR 0012). Written by the poller thread, read by
# /alerts/status, cleared on each new incident dispatch. Whole-dict swaps are
# atomic enough for a status read — same reasoning as _last_dispatch.
_ack: dict | None = None
# message_id of the most recent fall alert, so the ack can strip its button.
_last_alert_msg_id: int | None = None
_poller_started = False


def is_configured() -> bool:
    """True only when BOTH the token and a destination chat id are set."""
    return bool(os.environ.get(_TOKEN_ENV) and os.environ.get(_CHAT_ENV))


def _who(entry) -> str:
    """Name with age when known; the UNIDENTIFIED identity has no age."""
    return f"{entry.name} ({entry.age})" if entry.age is not None else entry.name


def _location_line(entry) -> str:
    """Unit plus the ambient last-motion area (ADR 0012). The zone is PIR
    context — where motion last was — never a camera localization claim."""
    if getattr(entry, "zone", None):
        return f"{entry.unit} · last motion: {entry.zone}"
    return entry.unit


def format_incident_message(event: IncidentEvent) -> str:
    """Human, actionable caregiver alert — no token, no internal ids.

    Pure and side-effect-free so it is unit-testable without a network."""
    e = event.entry
    s = e.score
    return (
        f"\U0001F6A8 FALL ALERT — {_who(e)}\n"
        f"{_location_line(e)}\n"
        f"{s.rationale}\n"
        f"Risk {s.risk:.2f} · confidence {s.confidence:.2f} · {s.recency}\n"
        f"→ {event.detail.recommended_action}"
    )


def format_escalation_message(event: IncidentEvent, still_down_s: float) -> str:
    """The long-lie second message (ADR 0012): the camera saw no recovery."""
    e = event.entry
    return (
        f"⚠️ STILL DOWN — {_who(e)}\n"
        f"{_location_line(e)}\n"
        f"{e.score.rationale}\n"
        f"No movement for {still_down_s:.0f}s since the fall alert.\n"
        f"→ If nobody has responded yet, escalate now."
    )


def _api_call(method: str, payload: dict, timeout: float = _TIMEOUT_S) -> dict | None:
    """POST one Bot API method. Returns the parsed body on HTTP success, None
    on any failure. The token is used only in the URL and never logged."""
    if not is_configured():
        return None
    token = os.environ[_TOKEN_ENV]
    url = f"https://api.telegram.org/bot{token}/{method}"
    req = Request(
        url,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode() or "{}")
    except Exception as exc:  # network, DNS, HTTP, JSON — all best-effort
        # deliberately no token in the log; %s of exc is Telegram-side text only
        print(f"[telegram] {method} not delivered: {type(exc).__name__}: {exc}")
        return None


def send_incident_alert(event: IncidentEvent) -> bool:
    """POST the fall alert (with the ack button) to Telegram. Returns True on
    a delivered message. No-op (False) when unconfigured."""
    global _last_alert_msg_id
    if not is_configured():
        return False
    body = _api_call("sendMessage", {
        "chat_id": os.environ[_CHAT_ENV],
        "text": format_incident_message(event),
        "disable_notification": False,
        "reply_markup": {
            "inline_keyboard": [[{"text": "I am responding", "callback_data": "ack"}]]
        },
    })
    ok = bool(body and body.get("ok"))
    if ok:
        _last_alert_msg_id = (body.get("result") or {}).get("message_id")
    return ok


def send_escalation_alert(event: IncidentEvent, still_down_s: float) -> bool:
    """POST the STILL DOWN escalation. Same guarantees as the fall alert."""
    if not is_configured():
        return False
    body = _api_call("sendMessage", {
        "chat_id": os.environ[_CHAT_ENV],
        "text": format_escalation_message(event, still_down_s),
        "disable_notification": False,
    })
    return bool(body and body.get("ok"))


def _multipart_body(
    fields: dict[str, str], file_field: str, filename: str,
    content: bytes, content_type: str,
) -> tuple[bytes, str]:
    """Hand-rolled multipart/form-data (the module's stdlib-only constraint —
    no `requests`). Returns (body, boundary). Pure, so the encoding is
    testable without a network."""
    boundary = f"----shine{int(time.time() * 1000)}"
    lines: list[bytes] = []
    for k, v in fields.items():
        lines += [
            f"--{boundary}".encode(),
            f'Content-Disposition: form-data; name="{k}"'.encode(),
            b"", str(v).encode(),
        ]
    lines += [
        f"--{boundary}".encode(),
        (f'Content-Disposition: form-data; name="{file_field}"; '
         f'filename="{filename}"').encode(),
        f"Content-Type: {content_type}".encode(), b"", content,
    ]
    lines += [f"--{boundary}--".encode(), b""]
    return b"\r\n".join(lines), boundary


def last_alert_message_id() -> int | None:
    return _last_alert_msg_id


def send_replay_animation(gif: bytes, caption: str,
                          reply_to: int | None = None) -> bool:
    """sendAnimation (ADR 0017 phase 5): the skeleton-replay GIF as a QUIET
    reply to the fall alert — the alert already pinged loudly; the moving
    evidence follows a beat later. The caller resolves `reply_to` (gap check
    2026-07-30: reading the mutable global here could thread the GIF under
    the WRONG alert); allow_sending_without_reply degrades a vanished target
    to an un-threaded send instead of a hard 400. Same guarantees as every
    send: silent no-op unconfigured, best-effort, the token never logged."""
    if not is_configured() or not gif:
        return False
    fields = {
        "chat_id": os.environ[_CHAT_ENV],
        "caption": caption,
        "disable_notification": "true",
    }
    if reply_to:
        fields["reply_to_message_id"] = str(reply_to)
        fields["allow_sending_without_reply"] = "true"
    body, boundary = _multipart_body(fields, "animation", "fall-replay.gif",
                                     gif, "image/gif")
    token = os.environ[_TOKEN_ENV]
    req = Request(
        f"https://api.telegram.org/bot{token}/sendAnimation",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with urlopen(req, timeout=15.0) as resp:  # upload — longer than text
            parsed = json.loads(resp.read().decode() or "{}")
        return bool(parsed.get("ok"))
    except Exception as exc:  # best-effort, token-free logging
        print(f"[telegram] sendAnimation not delivered: {type(exc).__name__}: {exc}")
        return False


# ------------------------- acknowledgement poller ------------------------- #

def get_ack() -> dict | None:
    return _ack


def clear_ack() -> None:
    """A new incident starts an unacknowledged alert leg."""
    global _ack
    _ack = None


def _set_ack(by: str) -> tuple[dict, bool]:
    """First responder wins — the ONE state rule both ack sources (Telegram
    tap, dashboard button) share. Returns (ack, created)."""
    global _ack
    if _ack is not None:
        return _ack, False
    _ack = {"by": by, "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return _ack, True


def record_ack(by: str) -> tuple[dict, bool]:
    """Acknowledge from the dashboard (ADR 0016). Same first-wins rule as the
    Telegram button; when Telegram is configured and a fall alert is known,
    the chat gets the same visibility as a tap — the alert loses its button
    and a quiet reply names who took it. Off-thread, best-effort."""
    ack, created = _set_ack(by)
    if created and is_configured() and _last_alert_msg_id:
        msg_id = _last_alert_msg_id

        def _notify() -> None:
            _api_call("editMessageReplyMarkup", {
                "chat_id": os.environ.get(_CHAT_ENV),
                "message_id": msg_id,
                "reply_markup": {"inline_keyboard": []},
            })
            _api_call("sendMessage", {
                "chat_id": os.environ.get(_CHAT_ENV),
                "reply_to_message_id": msg_id,
                "text": f"✅ {by} is responding (acknowledged from the dashboard).",
                "disable_notification": True,
            })

        threading.Thread(target=_notify, daemon=True).start()
    return ack, created


def _handle_update(update: dict) -> bool:
    """Process one getUpdates entry. Pure enough to test without a network:
    the Bot API side effects (answer/edit/reply) go through _api_call, which
    is a no-op unless configured. Returns True when an ack was recorded.

    First responder wins: a second tap is answered with who already has it
    and changes nothing — the caregivers see ONE owner, not the last tap."""
    cq = update.get("callback_query")
    if not cq or cq.get("data") != "ack":
        return False
    who = (cq.get("from") or {}).get("first_name") or "caregiver"

    ack, created = _set_ack(who)
    if not created:
        _api_call("answerCallbackQuery", {
            "callback_query_id": cq.get("id"),
            "text": f"Already acknowledged by {ack['by']}.",
        })
        return False
    # Confirm the tap privately, then make the ack VISIBLE in the chat: the
    # alert itself gains a status line (edit also drops the button), and a
    # quiet reply pins who took it under the alert for the whole group.
    _api_call("answerCallbackQuery", {
        "callback_query_id": cq.get("id"), "text": f"Noted, {who} — on it."
    })
    msg = cq.get("message") or {}
    if msg.get("message_id"):
        stamp = time.strftime("%H:%M", time.localtime())
        if msg.get("text"):
            _api_call("editMessageText", {
                "chat_id": os.environ.get(_CHAT_ENV),
                "message_id": msg["message_id"],
                "text": f"{msg['text']}\n\n✅ {who} is responding — acknowledged {stamp}",
            })
        else:  # no text in the callback payload — at least strip the button
            _api_call("editMessageReplyMarkup", {
                "chat_id": os.environ.get(_CHAT_ENV),
                "message_id": msg["message_id"],
                "reply_markup": {"inline_keyboard": []},
            })
        _api_call("sendMessage", {
            "chat_id": os.environ.get(_CHAT_ENV),
            "reply_to_message_id": msg["message_id"],
            "text": f"✅ {who} is responding.",
            "disable_notification": True,
        })
    return True


def _poll_loop() -> None:
    offset = 0
    while True:
        if not is_configured():
            time.sleep(5)
            continue
        body = _api_call(
            "getUpdates",
            {"timeout": _POLL_TIMEOUT_S, "offset": offset,
             "allowed_updates": ["callback_query"]},
            timeout=_POLL_TIMEOUT_S + 5,
        )
        if not body or not body.get("ok"):
            time.sleep(5)  # outage back-off; best-effort forever
            continue
        for update in body.get("result") or []:
            offset = max(offset, update.get("update_id", 0) + 1)
            _handle_update(update)


def start_ack_poller() -> bool:
    """Start the getUpdates daemon thread once. Called from app startup; a
    no-op unless Telegram is configured, and disabled outright by
    SHINEHACKATHON_TELEGRAM_ACK_POLL=0 (the test suite sets this)."""
    global _poller_started
    if _poller_started or not is_configured():
        return False
    if os.environ.get(_ACK_POLL_ENV, "1") == "0":
        return False
    _poller_started = True
    threading.Thread(target=_poll_loop, daemon=True, name="tg-ack-poll").start()
    return True
