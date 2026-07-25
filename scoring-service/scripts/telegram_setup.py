"""One-shot Telegram setup helper: validate token, find chat id, send a test.

Secret handling (vault rule 8): the bot token is read ONLY from the env var
SHINEHACKATHON_TELEGRAM_BOT_TOKEN — never passed as an argument, never printed,
never logged. You set it in YOUR terminal so it never transits the chat.

Usage (from scoring-service/):
    # 1. In Telegram, create the bot: message @BotFather -> /newbot -> copy token
    # 2. Put the token in your shell (session-only; it is not echoed back):
    $env:SHINEHACKATHON_TELEGRAM_BOT_TOKEN = "PASTE_TOKEN_HERE"
    # 3. Open Telegram, find your new bot, and send it any message (e.g. "hi")
    # 4. Discover the chat id + send a test alert:
    C:\\Users\\lucas\\anaconda3\\python.exe scripts/telegram_setup.py

The chat id it prints is what you persist as SHINEHACKATHON_TELEGRAM_CHAT_ID
(the script prints the exact command). stdlib only — no requests dependency.
"""
from __future__ import annotations

import json
import os
import sys
from urllib.request import urlopen

TOKEN_ENV = "SHINEHACKATHON_TELEGRAM_BOT_TOKEN"
CHAT_ENV = "SHINEHACKATHON_TELEGRAM_CHAT_ID"
API = "https://api.telegram.org/bot{token}/{method}"


def _call(token: str, method: str, timeout: float = 8.0) -> dict:
    with urlopen(API.format(token=token, method=method), timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def _post(token: str, method: str, payload: dict, timeout: float = 8.0) -> dict:
    from urllib.request import Request
    req = Request(API.format(token=token, method=method),
                  data=json.dumps(payload).encode(),
                  headers={"Content-Type": "application/json"})
    with urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode() or "{}")


def main() -> int:
    token = os.environ.get(TOKEN_ENV)
    if not token:
        print(f"error: {TOKEN_ENV} is not set. Set it in your shell first:")
        print(f'  $env:{TOKEN_ENV} = "PASTE_TOKEN_HERE"')
        return 2

    # 1. validate the token (prints the bot's public @username, never the token)
    me = _call(token, "getMe")
    if not me.get("ok"):
        print("error: token rejected by Telegram (getMe not ok). Re-check the "
              "token from @BotFather.")
        return 1
    bot = me["result"].get("username", "?")
    print(f"token OK — bot @{bot}")

    # 2. discover the chat id from the most recent message sent TO the bot
    updates = _call(token, "getUpdates")
    chats = []
    for u in updates.get("result", []):
        msg = u.get("message") or u.get("channel_post") or {}
        chat = msg.get("chat")
        if chat and chat.get("id") not in [c["id"] for c in chats]:
            chats.append({"id": chat["id"],
                          "who": chat.get("title") or chat.get("username")
                          or chat.get("first_name") or "?"})
    if not chats:
        print("no chats found. Open Telegram, message your bot once (any text), "
              "then re-run this script.")
        return 1
    chat_id = str(chats[-1]["id"])
    print(f"chat id: {chat_id}  ({chats[-1]['who']})")
    if len(chats) > 1:
        print(f"  (note: {len(chats)} chats saw the bot; using the most recent — "
              f"all: {[c['id'] for c in chats]})")

    # 3. send a test alert to that chat
    res = _post(token, "sendMessage", {
        "chat_id": chat_id,
        "text": "\U0001F6A8 Morning Triage — Telegram alerts wired up. "
                "This is a test; fall alerts will look like this.",
    })
    print("test message sent OK" if res.get("ok")
          else f"test send failed: {res.get('description')}")

    # 4. tell the operator how to persist the chat id (token they already have)
    print("\nPersist for future sessions (run in PowerShell):")
    print(f'  [Environment]::SetEnvironmentVariable("{CHAT_ENV}", "{chat_id}", "User")')
    print(f'  [Environment]::SetEnvironmentVariable("{TOKEN_ENV}", '
          f'$env:{TOKEN_ENV}, "User")   # persists the token you already set')
    return 0


if __name__ == "__main__":
    sys.exit(main())
