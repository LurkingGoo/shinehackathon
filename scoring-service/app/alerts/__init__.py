"""Outbound alert channels (Telegram). Best-effort, never on the request path's
critical section — an alert failure must not break incident handling."""
