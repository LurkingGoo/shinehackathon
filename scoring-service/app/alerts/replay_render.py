"""Skeleton replay → animated GIF (ADR 0017 phase 5).

Renders the stored landmark trace as a small stick-figure GIF for the
Telegram follow-up: the caregiver sees HOW the fall happened, in motion,
while the image still contains coordinates only — lines and dots, no
pixels of the room or the person. Pillow only (no ffmpeg); the import is
guarded so an environment without it degrades to "no animation" rather
than a broken alert path.
"""
from __future__ import annotations

import io

try:
    from PIL import Image, ImageDraw
    _PIL = True
except ImportError:  # pragma: no cover — degrade, never break
    _PIL = False

W, H = 320, 180
# Bone graph over the 13-point replay subset (mirror of lib/pose/skeleton.ts).
# Subset order: nose, L/R shoulder, L/R elbow, L/R wrist, L/R hip, L/R knee,
# L/R ankle.
BONES = [
    (1, 2), (1, 7), (2, 8), (7, 8),      # torso
    (1, 3), (3, 5), (2, 4), (4, 6),      # arms
    (7, 9), (9, 11), (8, 10), (10, 12),  # legs
]
_BG = (251, 247, 242)    # warm paper — the dashboard's --bg
_INK = (192, 57, 43)     # --red, the acute language
_FADE = (222, 168, 160)  # low-visibility joints, drawn honestly faded
_MUTED = (138, 124, 109)


def _decode(row: list[int], quant: int) -> tuple[int, list[tuple[float, float, float]] | None]:
    """Wire row → (tMs, [(x, y, visibility)...] | None). 1-length row = gap."""
    if len(row) <= 1:
        return (row[0] if row else 0), None
    pts = []
    for i in range(1, len(row) - 2, 3):
        pts.append((row[i] / quant, row[i + 1] / quant, row[i + 2] / 100.0))
    return row[0], pts


def render_replay_gif(
    frames: list[list[int]], quant_scale: int, max_frames: int = 160
) -> bytes | None:
    """GIF bytes, or None when Pillow is absent or fewer than 2 drawable
    frames exist. Frame durations follow the real timestamps, so the GIF
    plays at the speed the fall actually happened."""
    if not _PIL or quant_scale <= 0:
        return None
    decoded = [_decode(r, quant_scale) for r in frames[:max_frames]]
    if sum(1 for _t, p in decoded if p) < 2:
        return None

    images: list = []
    durations: list[int] = []
    for idx, (t, pts) in enumerate(decoded):
        img = Image.new("RGB", (W, H), _BG)
        d = ImageDraw.Draw(img)
        if pts:
            for a, b in BONES:
                if a >= len(pts) or b >= len(pts):
                    continue
                faded = pts[a][2] < 0.5 or pts[b][2] < 0.5
                d.line(
                    [(pts[a][0] * W, pts[a][1] * H), (pts[b][0] * W, pts[b][1] * H)],
                    fill=_FADE if faded else _INK, width=3,
                )
            for i, (x, y, vis) in enumerate(pts):
                r = 4 if i == 0 else 3  # the nose dot reads as the head
                d.ellipse(
                    [x * W - r, y * H - r, x * W + r, y * H + r],
                    fill=_FADE if vis < 0.5 else _INK,
                )
        else:
            d.text((W // 2 - 34, H // 2 - 6), "not tracked", fill=_MUTED)
        images.append(img)
        nxt = decoded[idx + 1][0] if idx + 1 < len(decoded) else t + 100
        durations.append(max(20, nxt - t))

    buf = io.BytesIO()
    images[0].save(
        buf, format="GIF", save_all=True, append_images=images[1:],
        duration=durations, loop=0,
    )
    return buf.getvalue()
