"""Shift briefing text.

Deterministic by default. An LLM MAY smooth the wording, but only from
facts already in `score` + `features` — it must never introduce a cause not in
the feature set. Flagged off by default so a missing key / dead network never
breaks the demo.
"""
from __future__ import annotations

import os

from app.models import ResidentDetail

BRIEFING_LLM = os.getenv("SCORING_BRIEFING_LLM", "0") == "1"


def deterministic_briefing(d: ResidentDetail) -> str:
    top = d.features[0] if d.features else None
    conf = round(d.score.confidence * 100)
    if d.score.track == "acute":
        stillness = d.features[1].value if len(d.features) > 1 else "sustained"
        impact = top.value if top else "an impact"
        return (
            f"{d.name} ({d.age}) may have fallen — a {impact} impact then "
            f"{stillness} of no movement, {d.score.recency}. Please reach her "
            f"first. Confidence {conf}%."
        )
    if not top:
        return f"{d.name} ({d.age}) — no contributing signals. Confidence {conf}%."
    tail = f", {top.baseline}" if top.baseline else ""
    return (
        f"{d.name} ({d.age}) is on this list mostly because of "
        f"{top.label.lower()} ({top.value}{tail}). Worth a check this week — "
        f"not urgent. Confidence {conf}%."
    )


def smooth_briefing(d: ResidentDetail) -> str:
    """Return an LLM-smoothed briefing when enabled; else the deterministic one.
    The LLM is fed ONLY score+features and must not invent cause. Guardrail lives
    in tests/test_contract.py (no number absent from features)."""
    if not BRIEFING_LLM:
        return deterministic_briefing(d)
    # Hook: call an LLM here with a strict "paraphrase only, invent nothing"
    # prompt built from d.features. Falls back on any error.
    try:  # pragma: no cover - optional path
        raise NotImplementedError
    except Exception:
        return deterministic_briefing(d)
