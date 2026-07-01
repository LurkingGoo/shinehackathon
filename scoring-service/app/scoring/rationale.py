"""Deterministic rationale + recommendedAction.

Pure string templates filled from the top feature(s). No randomness, no LLM —
same inputs, same output (docs/feature-spec.md §3). An LLM may only smooth the
`briefing` string downstream (app/briefing.py), never the rationale.
"""
from __future__ import annotations

from app.models import RiskFeature, Track

# Risk bands (docs/feature-spec.md §0).
def band(risk: float) -> str:
    if risk >= 0.85:
        return "high"
    if risk >= 0.70:
        return "elevated"
    if risk >= 0.40:
        return "watch"
    return "low"


def render_rationale(track: Track, features: list[RiskFeature]) -> str:
    if not features:
        return "No contributing signals."
    top = features[0]
    if track == "acute":
        stillness = features[1].value if len(features) > 1 else "sustained"
        return f"Fall detected — {top.value} impact then {stillness} no movement."
    return f"{top.label} — {top.value}" + (
        f" (usually {top.baseline})." if top.baseline else "."
    )


# recommendedAction rule table, keyed on (track, top-feature label, risk band).
def recommend_action(track: Track, top_label: str, risk: float) -> str:
    if track == "acute":
        return "CALL NOW. If no response, escalate to MOH 24/7 line + dispatch."
    b = band(risk)
    label = top_label.lower()
    if "kitchen" in label and b in ("elevated", "high"):
        return "Welfare call; if no answer, request a doorstep check."
    if "night" in label or "nocturnal" in label:
        return "Note pattern; flag for GP review if the trend continues 3+ nights."
    if b in ("elevated", "high"):
        return "Call resident. If no answer in 15 min, dispatch buddy visit."
    if b == "watch":
        return "Flag for morning check-in call. Low-urgency welfare follow-up."
    return "No action needed."
