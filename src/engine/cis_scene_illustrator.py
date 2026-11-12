# Created by Atharv Hatwar
"""
cis_scene_illustrator.py - Modular Multi-Sprite & Adaptive-Theme B1/B2/B3 Illustrator.

Generates tightly bounded, transparent RGBA actor/prop sprites plus a per-scene
`_sprite_plan` & `_vector_plan` choreography spec so `cis_manifest_builder.py`
animates every character and object independently (walking, hopping stairs,
tilting balance beams, toppling dominoes, sweeping spotlight beams, shaking phones,
cross-fading mirror reflections, cursor click animations, etc.).

Supports three distinct visual themes (B1 Ink Sketchbook, B2 Editorial Cream,
B3 Obsidian Dark Chalkboard) with zero Unicode tofu emojis and 100% offline PIL +
optional local LCM DreamShaper atmospheric wash.
"""

from __future__ import annotations

import logging
import math
import os
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

logger = logging.getLogger(__name__)

CANVAS_W, CANVAS_H = 1080, 1920

PAPER_BG = "#FAF8F3"
INK = "#191916"
INK_MUTED = "#4E5358"
INK_FAINT = "#8A9096"
WHITE = "#FFFFFF"

ACCENT_CORAL = "#E63946"
ACCENT_BLUE = "#1D70B8"
ACCENT_GOLD = "#D97706"
ACCENT_GREEN = "#2A9D8F"

LOCAL_FONT_DIR = Path("assets/fonts")
SKILL_FONT_DIR = Path(r"C:\Users\athar\.gemini\config\skills\directing-stickman-videos\assets\fonts")
FONT_DIR = LOCAL_FONT_DIR if (LOCAL_FONT_DIR / "Caveat.ttf").exists() else SKILL_FONT_DIR


# ---------------------------------------------------------------------------
# Color & PRNG Helpers
# ---------------------------------------------------------------------------

def safe_hex_color(color: Optional[str], fallback: str = ACCENT_CORAL) -> str:
    if isinstance(color, str):
        c = color.strip()
        if c.startswith("#") and len(c) in (4, 7):
            try:
                int(c[1:], 16)
                if len(c) == 4:
                    c = "#" + "".join(ch * 2 for ch in c[1:])
                return c.upper()
            except ValueError:
                pass
    return fallback


def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    c = safe_hex_color(hex_color, ACCENT_CORAL)
    return int(c[1:3], 16), int(c[3:5], 16), int(c[5:7], 16)


def rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(hex_color)
    return (r, g, b, max(0, min(255, int(alpha))))


def soft_tint_bg(hex_color: str, strength: float = 0.14, base_hex: str = "#FCFBF8") -> str:
    r, g, b = _hex_to_rgb(hex_color)
    br, bg, bb = _hex_to_rgb(base_hex)
    tr = int(br * (1.0 - strength) + r * strength)
    tg = int(bg * (1.0 - strength) + g * strength)
    tb = int(bb * (1.0 - strength) + b * strength)
    return f"#{tr:02X}{tg:02X}{tb:02X}"


def _theme_of(scene: dict) -> dict[str, Any]:
    t = scene.get("theme")
    is_dark = bool(t.get("is_dark", False)) if isinstance(t, dict) else False
    base: dict[str, Any] = {
        "style": scene.get("visual_style", "B1"),
        "is_dark": is_dark,
        "paper_bg": "#111316" if is_dark else PAPER_BG,
        "card_bg": "#1B1F27" if is_dark else WHITE,
        "ink": "#F4F5F6" if is_dark else INK,
        "ink_muted": "#94A3B8" if is_dark else INK_MUTED,
        "ink_faint": "#334155" if is_dark else INK_FAINT,
    }
    if isinstance(t, dict):
        base.update(t)
    return base


def mulberry32(seed: int):
    a = seed & 0xFFFFFFFF

    def rng() -> float:
        nonlocal a
        a = (a + 0x6D2B79F5) & 0xFFFFFFFF
        t = (a ^ (a >> 15)) * (1 | a) & 0xFFFFFFFF
        t = (t + ((t ^ (t >> 7)) * (61 | t) & 0xFFFFFFFF)) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296.0

    return rng


# ---------------------------------------------------------------------------
# Hand-Drawn Vector Primitives
# ---------------------------------------------------------------------------

def hand_line(
    draw: ImageDraw.ImageDraw,
    x1: float,
    y1: float,
    x2: float,
    y2: float,
    seed: int = 1,
    lw: int = 5,
    color: Any = INK,
    jitter: float = 1.3,
) -> None:
    rng = mulberry32(seed)
    dist = math.hypot(x2 - x1, y2 - y1)
    steps = max(3, int(dist / 20))
    pts: list[tuple[float, float]] = [(x1, y1)]
    for i in range(1, steps):
        t = i / float(steps)
        bx = x1 + (x2 - x1) * t + (rng() - 0.5) * jitter * 2
        by = y1 + (y2 - y1) * t + (rng() - 0.5) * jitter * 2
        pts.append((bx, by))
    pts.append((x2, y2))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=lw)


def hand_circle(
    draw: ImageDraw.ImageDraw,
    cx: float,
    cy: float,
    r: float,
    seed: int = 10,
    lw: int = 5,
    color: Any = INK,
    fill: Any = None,
) -> None:
    rng = mulberry32(seed)
    pts_count = 36
    pts: list[tuple[float, float]] = []
    for i in range(pts_count + 1):
        ang = (i / pts_count) * math.pi * 2
        wobble = (rng() - 0.5) * 1.9
        px = cx + math.cos(ang) * (r + wobble)
        py = cy + math.sin(ang) * (r + wobble * 0.9)
        pts.append((px, py))
    if fill:
        draw.polygon(pts, fill=fill)
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=color, width=lw)


def hand_rect(
    draw: ImageDraw.ImageDraw,
    x: float,
    y: float,
    w: float,
    h: float,
    seed: int = 15,
    lw: int = 4,
    color: Any = INK,
    fill: Any = WHITE,
    r: int = 20,
    shadow: bool = False,
) -> None:
    r = max(2, min(r, int(min(w, h) // 2) - 1))
    if shadow:
        draw.rounded_rectangle([x + 6, y + 8, x + w + 6, y + h + 8], radius=r, fill=(10, 12, 16, 40))
    if fill:
        draw.rounded_rectangle([x, y, x + w, y + h], radius=r, fill=fill)
    hand_line(draw, x + r, y, x + w - r, y, seed, lw, color)
    hand_line(draw, x + w, y + r, x + w, y + h - r, seed + 1, lw, color)
    hand_line(draw, x + w - r, y + h, x + r, y + h, seed + 2, lw, color)
    hand_line(draw, x, y + h - r, x, y + r, seed + 3, lw, color)
    draw.arc([x, y, x + 2 * r, y + 2 * r], 180, 270, fill=color, width=lw)
    draw.arc([x + w - 2 * r, y, x + w, y + 2 * r], 270, 360, fill=color, width=lw)
    draw.arc([x + w - 2 * r, y + h - 2 * r, x + w, y + h], 0, 90, fill=color, width=lw)
    draw.arc([x, y + h - 2 * r, x + 2 * r, y + h], 90, 180, fill=color, width=lw)


def hand_curve(
    draw: ImageDraw.ImageDraw,
    pts: list[tuple[float, float]],
    seed: int = 20,
    lw: int = 5,
    color: Any = INK,
) -> None:
    if len(pts) < 2:
        return
    rng = mulberry32(seed)
    wobbled = [(p[0] + (rng() - 0.5) * 1.8, p[1] + (rng() - 0.5) * 1.8) for p in pts]
    for i in range(len(wobbled) - 1):
        draw.line([wobbled[i], wobbled[i + 1]], fill=color, width=lw)


# ---------------------------------------------------------------------------
# Typography Helpers
# ---------------------------------------------------------------------------

def _load_font(family: str = "noto", size: int = 32, bold: bool = False):
    try:
        p = FONT_DIR / ("Caveat.ttf" if family.lower() == "caveat" else "NotoSans.ttf")
        if p.exists():
            return ImageFont.truetype(str(p), size)
    except Exception:
        pass
    for cand in [
        "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf",
        "C:/Windows/Fonts/arialbd.ttf" if bold else "C:/Windows/Fonts/arial.ttf",
    ]:
        if os.path.exists(cand):
            try:
                return ImageFont.truetype(cand, size)
            except Exception:
                pass
    return ImageFont.load_default()


def _text_width(draw: ImageDraw.ImageDraw, text: str, font) -> float:
    bbox = draw.textbbox((0, 0), text, font=font)
    return float(bbox[2] - bbox[0])


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font, max_w: float, max_lines: int = 2) -> list[str]:
    words = text.split()
    if not words:
        return [""]
    lines: list[str] = []
    cur: list[str] = []
    for w in words:
        cand = " ".join(cur + [w])
        if _text_width(draw, cand, font) <= max_w or not cur:
            cur.append(w)
        else:
            lines.append(" ".join(cur))
            cur = [w]
            if len(lines) >= max_lines:
                break
    if cur and len(lines) < max_lines:
        lines.append(" ".join(cur))
    elif cur and len(lines) == max_lines:
        lines[-1] = lines[-1] + " " + " ".join(cur)
    return lines


def draw_fitted_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    cx: float,
    cy: float,
    max_w: float,
    target_size: int,
    family: str = "noto",
    fill: str = INK,
    bold: bool = False,
    max_lines: int = 1,
    min_size: int = 16,
    line_spacing: float = 1.18,
) -> None:
    clean = " ".join((text or "").split())
    if not clean:
        return
    size = target_size
    font = _load_font(family, size, bold=bold)
    lines = _wrap_lines(draw, clean, font, max_w, max_lines=max_lines)
    while size > min_size and any(_text_width(draw, ln, font) > max_w for ln in lines):
        size -= 2
        font = _load_font(family, size, bold=bold)
        lines = _wrap_lines(draw, clean, font, max_w, max_lines=max_lines)
    total_h = (len(lines) - 1) * size * line_spacing
    start_y = cy - total_h / 2.0
    for i, ln in enumerate(lines):
        draw.text((cx, start_y + i * size * line_spacing), ln, fill=fill, font=font, anchor="mm")


# ---------------------------------------------------------------------------
# Expressive Stickman Character Builder (Supports 8 Dynamic Poses & Light/Dark)
# ---------------------------------------------------------------------------

def draw_stickman_figure(
    draw: ImageDraw.ImageDraw,
    cx: int,
    cy: int,
    scale: float = 1.0,
    pose: str = "neutral",
    accent_color: str = ACCENT_CORAL,
    ink: str = INK,
    head_fill: str = WHITE,
    seed: int = 100,
) -> None:
    """
    Draw an expressive, high-clarity stickman at (cx, cy) head center.
    Poses: neutral, pondering, sprinting, climbing, shielding, gesturing,
           peaceful, spotlight_crown, pointing_cta, vulnerable, anxious
    """
    head_r = int(42 * scale)
    torso_len = int(170 * scale)
    leg_len = int(152 * scale)
    lw = max(4, int(5.5 * scale))

    hand_circle(draw, cx, cy, head_r, seed=seed, lw=lw, color=ink, fill=head_fill)
    eye_y = cy - int(4 * scale)
    er = max(3, int(4 * scale))

    if pose == "anxious":
        # Furrowed brows + wiggly mouth
        draw.line([cx - int(18 * scale), eye_y - int(11 * scale), cx - int(6 * scale), eye_y - int(5 * scale)], fill=ink, width=3)
        draw.line([cx + int(6 * scale), eye_y - int(5 * scale), cx + int(18 * scale), eye_y - int(11 * scale)], fill=ink, width=3)
        draw.ellipse([cx - int(12 * scale), eye_y - er, cx - int(6 * scale), eye_y + er], fill=ink)
        draw.ellipse([cx + int(6 * scale), eye_y - er, cx + int(12 * scale), eye_y + er], fill=ink)
        hand_curve(draw, [(cx - 12, cy + 16), (cx - 4, cy + 12), (cx + 4, cy + 18), (cx + 12, cy + 14)], seed=seed + 1, lw=3, color=ink)
    else:
        draw.ellipse([cx - int(12 * scale), eye_y - er, cx - int(6 * scale), eye_y + er], fill=ink)
        draw.ellipse([cx + int(6 * scale), eye_y - er, cx + int(12 * scale), eye_y + er], fill=ink)

    neck_y = cy + head_r
    torso_end_x = cx
    torso_bot_y = neck_y + torso_len

    if pose == "sprinting":
        torso_end_x = cx - int(28 * scale)
        torso_bot_y = neck_y + int(155 * scale)
        draw.arc([cx - 8, cy + 10, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        hand_line(draw, cx, neck_y, torso_end_x, torso_bot_y, seed=seed + 2, lw=lw, color=ink)
        # Striding legs
        hand_curve(draw, [(torso_end_x, torso_bot_y), (torso_end_x + 42 * scale, torso_bot_y + 72 * scale), (torso_end_x + 76 * scale, torso_bot_y + 132 * scale)], seed=seed + 5, lw=lw, color=ink)
        hand_curve(draw, [(torso_end_x, torso_bot_y), (torso_end_x - 36 * scale, torso_bot_y + 68 * scale), (torso_end_x - 74 * scale, torso_bot_y + 118 * scale)], seed=seed + 6, lw=lw, color=ink)
        # Pumping arms
        hand_curve(draw, [(cx, neck_y + 24), (cx + 48 * scale, neck_y + 52 * scale), (cx + 76 * scale, neck_y + 28 * scale)], seed=seed + 3, lw=lw, color=accent_color)
        hand_curve(draw, [(cx, neck_y + 24), (cx - 48 * scale, neck_y + 60 * scale), (cx - 68 * scale, neck_y + 92 * scale)], seed=seed + 4, lw=lw, color=ink)
        return

    if pose == "climbing":
        draw.arc([cx - 8, cy + 8, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        hand_line(draw, cx, neck_y, cx - 10, torso_bot_y, seed=seed + 2, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 28), (cx + 52 * scale, neck_y + 10), (cx + 72 * scale, neck_y - 26 * scale)], seed=seed + 3, lw=lw, color=accent_color)
        hand_curve(draw, [(cx, neck_y + 28), (cx - 42 * scale, neck_y + 42), (cx - 56 * scale, neck_y + 12)], seed=seed + 4, lw=lw, color=ink)
        hand_curve(draw, [(cx - 10, torso_bot_y), (cx + 34 * scale, torso_bot_y + 52 * scale), (cx + 22 * scale, torso_bot_y + 128 * scale)], seed=seed + 5, lw=lw, color=ink)
        hand_curve(draw, [(cx - 10, torso_bot_y), (cx - 40 * scale, torso_bot_y + 80 * scale), (cx - 28 * scale, torso_bot_y + 148 * scale)], seed=seed + 6, lw=lw, color=ink)
        return

    hand_line(draw, cx, neck_y, torso_end_x, torso_bot_y, seed=seed + 2, lw=lw, color=ink)

    if pose == "pondering":
        draw.line([cx - 8, cy + 16, cx + 8, cy + 16], fill=ink, width=3)
        # Hand on chin!
        hand_curve(draw, [(cx, neck_y + 30), (cx + 38 * scale, neck_y + 20 * scale), (cx + 18 * scale, cy + head_r + 2)], seed=seed + 3, lw=lw, color=accent_color)
        hand_curve(draw, [(cx, neck_y + 30), (cx - 40 * scale, neck_y + 68 * scale), (cx + 12 * scale, neck_y + 72 * scale)], seed=seed + 4, lw=lw, color=ink)
    elif pose == "vulnerable" or pose == "anxious":
        if pose == "vulnerable":
            draw.arc([cx - 9, cy + 12, cx + 9, cy + 25], 180, 360, fill=ink, width=3)
        hand_curve(draw, [(cx, neck_y + 32), (cx + 28 * scale, neck_y + 60 * scale), (cx + 12 * scale, neck_y + 88 * scale)], seed=seed + 3, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 32), (cx - 28 * scale, neck_y + 70 * scale), (cx - 34 * scale, neck_y + 108 * scale)], seed=seed + 4, lw=lw, color=ink)
    elif pose == "shielding":
        draw.line([cx - 8, cy + 16, cx + 10, cy + 14], fill=ink, width=3)
        # Outstretched palm blocking left
        hand_curve(draw, [(cx, neck_y + 26), (cx - 56 * scale, neck_y + 10 * scale), (cx - 84 * scale, neck_y - 10 * scale)], seed=seed + 3, lw=lw + 1, color=accent_color)
        hand_curve(draw, [(cx, neck_y + 26), (cx + 36 * scale, neck_y + 74 * scale)], seed=seed + 4, lw=lw, color=ink)
    elif pose in ("peaceful", "waving_cta"):
        draw.arc([cx - 10, cy + 8, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        hand_curve(draw, [(cx, neck_y + 32), (cx - 46 * scale, neck_y + 15), (cx - 64 * scale, neck_y - 22)], seed=seed + 3, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 32), (cx + 46 * scale, neck_y + 15), (cx + 66 * scale, neck_y - 24)], seed=seed + 4, lw=lw, color=accent_color)
    elif pose == "gesturing":
        draw.ellipse([cx - 8, cy + 10, cx + 8, cy + 24], outline=ink, fill=head_fill, width=3)
        hand_curve(draw, [(cx, neck_y + 28), (cx - 46 * scale, neck_y + 14), (cx - 84 * scale, neck_y - 6)], seed=seed + 3, lw=lw, color=accent_color)
        hand_curve(draw, [(cx, neck_y + 28), (cx + 42 * scale, neck_y + 20), (cx + 60 * scale, neck_y - 10)], seed=seed + 4, lw=lw, color=ink)
    elif pose == "spotlight_crown":
        draw.arc([cx - 10, cy + 8, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        crown_pts = [
            (cx - 22, cy - head_r - 2),
            (cx - 28, cy - head_r - 28),
            (cx - 11, cy - head_r - 14),
            (cx, cy - head_r - 34),
            (cx + 11, cy - head_r - 14),
            (cx + 28, cy - head_r - 28),
            (cx + 22, cy - head_r - 2),
        ]
        draw.polygon(crown_pts, fill=ACCENT_GOLD, outline=ink)
        hand_curve(draw, [(cx, neck_y + 28), (cx - 52 * scale, neck_y + 16), (cx - 78 * scale, neck_y - 14)], seed=seed + 3, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 28), (cx + 52 * scale, neck_y + 16), (cx + 78 * scale, neck_y - 14)], seed=seed + 4, lw=lw, color=ink)
    elif pose == "pointing_cta":
        draw.arc([cx - 10, cy + 8, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        hand_curve(draw, [(cx, neck_y + 28), (cx - 44 * scale, neck_y + 52)], seed=seed + 3, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 28), (cx + 56 * scale, neck_y + 6), (cx + 96 * scale, neck_y - 26)], seed=seed + 4, lw=lw + 1, color=accent_color)
    else:
        draw.line([cx - 8, cy + 18, cx + 8, cy + 18], fill=ink, width=3)
        hand_curve(draw, [(cx, neck_y + 30), (cx - 36 * scale, neck_y + 76 * scale)], seed=seed + 3, lw=lw, color=ink)
        hand_curve(draw, [(cx, neck_y + 30), (cx + 36 * scale, neck_y + 76 * scale)], seed=seed + 4, lw=lw, color=ink)

    hand_line(draw, torso_end_x, torso_bot_y, torso_end_x - int(26 * scale), torso_bot_y + leg_len, seed=seed + 5, lw=lw, color=ink)
    hand_line(draw, torso_end_x, torso_bot_y, torso_end_x + int(26 * scale), torso_bot_y + leg_len, seed=seed + 6, lw=lw, color=ink)


# ---------------------------------------------------------------------------
# Hand-Drawn Vector Prop Icons (100% Zero Unicode Tofu)
# ---------------------------------------------------------------------------

def draw_icon_sparkle(draw: ImageDraw.ImageDraw, cx: int, cy: int, r: int, color: str, ink: str = INK) -> None:
    ir = max(3, int(r * 0.28))
    pts = [
        (cx, cy - r), (cx + ir, cy - ir), (cx + r, cy), (cx + ir, cy + ir),
        (cx, cy + r), (cx - ir, cy + ir), (cx - r, cy), (cx - ir, cy - ir),
    ]
    draw.polygon(pts, fill=color, outline=ink)


def draw_icon_bell(draw: ImageDraw.ImageDraw, cx: int, cy: int, accent: str, ink: str = INK, card_bg: str = WHITE) -> None:
    fill_c = soft_tint_bg(accent, 0.28, base_hex=card_bg)
    draw.arc([cx - 9, cy - 42, cx + 9, cy - 24], 160, 380, fill=ink, width=4)
    bell_pts = [(cx - 17, cy - 25), (cx + 17, cy - 25), (cx + 26, cy + 6), (cx + 36, cy + 18), (cx - 36, cy + 18), (cx - 26, cy + 6)]
    draw.polygon(bell_pts, fill=fill_c, outline=ink)
    hand_line(draw, cx - 36, cy + 18, cx + 36, cy + 18, seed=802, lw=4, color=ink)
    hand_circle(draw, cx, cy + 26, 7, seed=803, lw=3, color=ink, fill=accent)


def draw_icon_cursor_pointer(draw: ImageDraw.ImageDraw, cx: int, cy: int, accent: str, ink: str = INK) -> None:
    pts = [
        (cx, cy), (cx, cy + 62), (cx + 17, cy + 46), (cx + 32, cy + 76),
        (cx + 44, cy + 70), (cx + 30, cy + 40), (cx + 52, cy + 38),
    ]
    draw.polygon([(p[0] + 4, p[1] + 5) for p in pts], fill=(10, 12, 16, 55))
    draw.polygon(pts, fill=WHITE, outline=ink)
    hand_line(draw, cx - 18, cy - 14, cx - 6, cy - 6, seed=901, lw=4, color=accent)
    hand_line(draw, cx - 22, cy + 8, cx - 10, cy + 8, seed=902, lw=4, color=accent)


def draw_icon_lightbulb(draw: ImageDraw.ImageDraw, cx: int, cy: int, accent: str, ink: str = INK, card_bg: str = WHITE) -> None:
    # Glow aura + bulb
    r, g, b = _hex_to_rgb(accent)
    draw.ellipse([cx - 86, cy - 86, cx + 86, cy + 86], fill=(r, g, b, 38))
    hand_circle(draw, cx, cy - 12, 48, seed=310, lw=5, color=ink, fill=soft_tint_bg(accent, 0.35, base_hex=card_bg))
    hand_rect(draw, cx - 22, cy + 32, 44, 24, seed=311, lw=4, color=ink, fill=ink, r=6)
    hand_line(draw, cx - 14, cy + 64, cx + 14, cy + 64, seed=312, lw=4, color=ink)
    # Rays
    for ang_deg in range(-150, 30, 30):
        a = math.radians(ang_deg)
        hand_line(draw, cx + math.cos(a) * 60, cy - 12 + math.sin(a) * 60, cx + math.cos(a) * 82, cy - 12 + math.sin(a) * 82, seed=320 + ang_deg, lw=4, color=accent)


def draw_icon_heart(draw: ImageDraw.ImageDraw, cx: int, cy: int, accent: str, ink: str = INK, card_bg: str = WHITE) -> None:
    hand_circle(draw, cx, cy, 52, seed=41, lw=4, color=accent, fill=soft_tint_bg(accent, 0.22, base_hex=card_bg))
    pts: list[tuple[float, float]] = []
    for deg in range(0, 360, 10):
        t = math.radians(deg)
        hx = 16 * (math.sin(t) ** 3)
        hy = -(13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + hx * 1.4, cy + hy * 1.4))
    draw.polygon(pts, fill=accent, outline=ink)


def draw_semantic_prop(
    draw: ImageDraw.ImageDraw,
    prop_kind: str,
    cx: int,
    cy: int,
    r: int,
    accent: str,
    ink: str = INK,
    card_bg: str = WHITE,
    seed: int = 55,
) -> None:
    """Draw a clean vector icon matching the literal subject spoken in the sentence."""
    pk = (prop_kind or "spark").lower()
    tint = soft_tint_bg(accent, 0.26, base_hex=card_bg)
    if pk == "heart":
        draw_icon_heart(draw, cx, cy, accent=accent, ink=ink, card_bg=card_bg)
        return
    if pk == "coin":
        hand_circle(draw, cx, cy, r, seed=seed, lw=5, color=ink, fill=tint)
        hand_circle(draw, cx, cy, int(r * 0.72), seed=seed + 1, lw=3, color=accent)
        draw_fitted_text(draw, "$", cx, cy, max_w=int(r * 1.1), target_size=max(26, int(r * 0.9)), family="noto", fill=ink, bold=True)
        return
    if pk == "book":
        hw, hh = int(r * 0.95), int(r * 0.75)
        hand_rect(draw, cx - hw, cy - hh, hw * 2, hh * 2, seed=seed, lw=4, color=ink, fill=card_bg, r=10)
        hand_line(draw, cx, cy - hh, cx, cy + hh, seed=seed + 1, lw=4, color=accent)
        for dy in (-int(hh * 0.45), 0, int(hh * 0.45)):
            hand_line(draw, cx - hw + 14, cy + dy, cx - 12, cy + dy, seed=seed + 2 + dy, lw=3, color=ink)
            hand_line(draw, cx + 12, cy + dy, cx + hw - 14, cy + dy, seed=seed + 5 + dy, lw=3, color=ink)
        return
    if pk == "shield":
        pts = [
            (cx - int(r * 0.8), cy - int(r * 0.85)),
            (cx + int(r * 0.8), cy - int(r * 0.85)),
            (cx + int(r * 0.75), cy + int(r * 0.12)),
            (cx, cy + int(r * 0.95)),
            (cx - int(r * 0.75), cy + int(r * 0.12)),
        ]
        draw.polygon(pts, fill=tint, outline=ink)
        draw.line([pts[0], pts[1], pts[2], pts[3], pts[4], pts[0]], fill=ink, width=5)
        hand_line(draw, cx, cy - int(r * 0.55), cx, cy + int(r * 0.55), seed=seed + 1, lw=5, color=accent)
        return
    if pk == "clock":
        hand_circle(draw, cx, cy, r, seed=seed, lw=5, color=ink, fill=card_bg)
        hand_line(draw, cx, cy, cx, cy - int(r * 0.62), seed=seed + 1, lw=5, color=accent)
        hand_line(draw, cx, cy, cx + int(r * 0.48), cy + int(r * 0.2), seed=seed + 2, lw=4, color=ink)
        return
    if pk == "lightning":
        pts = [
            (cx + int(r * 0.15), cy - r),
            (cx - int(r * 0.45), cy + 4),
            (cx + int(r * 0.05), cy + 4),
            (cx - int(r * 0.2), cy + r),
            (cx + int(r * 0.52), cy - 8),
            (cx, cy - 8),
        ]
        draw.polygon(pts, fill=accent, outline=ink)
        return
    if pk == "brain":
        hand_circle(draw, cx - int(r * 0.3), cy, int(r * 0.65), seed=seed, lw=4, color=ink, fill=tint)
        hand_circle(draw, cx + int(r * 0.3), cy, int(r * 0.65), seed=seed + 1, lw=4, color=ink, fill=tint)
        draw_icon_sparkle(draw, cx, cy - int(r * 0.82), max(12, int(r * 0.28)), color=accent, ink=ink)
        return
    if pk == "key":
        hand_circle(draw, cx - int(r * 0.42), cy, int(r * 0.38), seed=seed, lw=5, color=ink, fill=tint)
        hand_line(draw, cx - int(r * 0.04), cy, cx + int(r * 0.85), cy, seed=seed + 1, lw=6, color=accent)
        hand_line(draw, cx + int(r * 0.55), cy, cx + int(r * 0.55), cy + int(r * 0.35), seed=seed + 2, lw=5, color=ink)
        hand_line(draw, cx + int(r * 0.80), cy, cx + int(r * 0.80), cy + int(r * 0.28), seed=seed + 3, lw=5, color=ink)
        return
    if pk == "crown":
        pts = [
            (cx - int(r * 0.82), cy + int(r * 0.45)),
            (cx - int(r * 0.88), cy - int(r * 0.45)),
            (cx - int(r * 0.35), cy),
            (cx, cy - int(r * 0.72)),
            (cx + int(r * 0.35), cy),
            (cx + int(r * 0.88), cy - int(r * 0.45)),
            (cx + int(r * 0.82), cy + int(r * 0.45)),
        ]
        draw.polygon(pts, fill=ACCENT_GOLD, outline=ink)
        return
    if pk == "phone":
        pw, ph = int(r * 0.85), int(r * 1.45)
        hand_rect(draw, cx - pw // 2, cy - ph // 2, pw, ph, seed=seed, lw=5, color=ink, fill=card_bg, r=12)
        hand_circle(draw, cx, cy, max(12, r // 3), seed=seed + 1, lw=4, color=accent, fill=accent)
        return
    # Default radiant sun/spark
    draw_icon_sparkle(draw, cx, cy, r, color=accent, ink=ink)


# ---------------------------------------------------------------------------
# Sprite Canvas Helper & Registry
# ---------------------------------------------------------------------------

def _make_sprite(w: int, h: int) -> tuple[Image.Image, ImageDraw.ImageDraw]:
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save_sprite(sprites_dict: dict[str, Any], name: str, img: Image.Image, out_dir: Path, prefix: str) -> str:
    p = out_dir / f"{prefix}_{name}.png"
    img.save(str(p), "PNG")
    sprites_dict[name] = {"path": str(p), "w": img.width, "h": img.height}
    return str(p)


# ---------------------------------------------------------------------------
# 14 Distinct Choreographed Scene Sprite Generators
# ---------------------------------------------------------------------------

def _choreo_question_burst(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 11))
    sprites: dict[str, Any] = {}

    # 1. Ponderer stickman
    im, d = _make_sprite(320, 460)
    draw_stickman_figure(d, 160, 82, scale=1.02, pose="pondering", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "hero", im, out_dir, prefix)

    # 2. Giant "?" cloud + mini "?" orbiters
    im_q, dq = _make_sprite(220, 220)
    hand_circle(dq, 110, 110, 88, seed=seed + 2, lw=5, color=ink, fill=soft_tint_bg(accent, 0.22, card_bg))
    draw_fitted_text(dq, "?", 110, 110, max_w=140, target_size=110, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "q_main", im_q, out_dir, prefix)

    im_q2, dq2 = _make_sprite(130, 130)
    hand_circle(dq2, 65, 65, 48, seed=seed + 3, lw=4, color=muted, fill=card_bg)
    draw_fitted_text(dq2, "WHY?", 65, 65, max_w=90, target_size=30, family="noto", fill=ink, bold=True)
    _save_sprite(sprites, "q_mini", im_q2, out_dir, prefix)

    # 3. Lightbulb breakthrough (Beat B)
    im_b, db = _make_sprite(240, 240)
    draw_icon_lightbulb(db, 120, 122, accent=accent, ink=ink, card_bg=card_bg)
    _save_sprite(sprites, "bulb", im_b, out_dir, prefix)

    # 4. Impact insight badge (Beat B)
    im_p, dp = _make_sprite(560, 160)
    hand_rect(dp, 14, 14, 532, 132, seed=seed + 5, lw=5, color=accent, fill=card_bg, r=24, shadow=True)
    draw_fitted_text(dp, scene.get("beat_b_label") or "THE PATTERN EXPLAINS IT", 280, 80, max_w=485, target_size=36, family="caveat", fill=ink, bold=True, max_lines=2)
    _save_sprite(sprites, "pill", im_p, out_dir, prefix)

    sprite_plan = [
        {"sprite": "hero", "anim": "walk_to", "cx0": 320, "cy0": 1150, "cx1": 365, "cy1": 1140, "w": 440, "from_f": 0.0, "to_f": 1.0, "hops": 1},
        {"sprite": "q_main", "anim": "orbit_burst", "cx0": 770, "cy0": 740, "cx1": 940, "cy1": 570, "w": 310, "from_f": 0.0, "to_f": 0.50},
        {"sprite": "q_mini", "anim": "orbit_burst", "cx0": 490, "cy0": 650, "cx1": 290, "cy1": 490, "w": 185, "from_f": 0.05, "to_f": 0.50},
        {"sprite": "bulb", "anim": "pop_bounce", "cx0": 800, "cy0": 780, "w": 330, "from_f": 0.45, "to_f": 1.0},
        {"sprite": "pill", "anim": "slide_in", "cx0": 1020, "cy0": 1490, "cx1": 640, "cy1": 1490, "w": 780, "from_f": 0.52, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "p1": [100, 1410], "p2": [1180, 1410], "color": muted, "lw": 3, "from_f": 0.0, "to_f": 0.52},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_phone_trap(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 22))
    sprites: dict[str, Any] = {}

    # 1. Giant hand-drawn smartphone
    im_ph, dp = _make_sprite(320, 560)
    hand_rect(dp, 18, 18, 284, 524, seed=seed, lw=6, color=ink, fill=card_bg, r=36, shadow=True)
    hand_rect(dp, 36, 62, 248, 420, seed=seed + 1, lw=3, color=muted, fill=soft_tint_bg(accent, 0.12, card_bg), r=18)
    hand_line(draw=dp, x1=120, y1=40, x2=200, y2=40, seed=seed + 2, lw=5, color=ink)
    hand_circle(dp, 160, 512, 16, seed=seed + 3, lw=4, color=ink)
    draw_icon_bell(dp, 160, 225, accent=accent, ink=ink, card_bg=card_bg)
    draw_fitted_text(dp, scene.get("left_tag") or "ALERT", 160, 345, max_w=210, target_size=34, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "phone", im_ph, out_dir, prefix)

    # 2. Popping notification badge
    im_n, dn = _make_sprite(320, 120)
    hand_rect(dn, 10, 10, 300, 100, seed=seed + 4, lw=4, color=accent, fill=accent, r=24, shadow=True)
    draw_fitted_text(dn, scene.get("right_tag") or "DISTRACTION", 160, 60, max_w=270, target_size=28, family="noto", fill=WHITE, bold=True)
    _save_sprite(sprites, "badge1", im_n, out_dir, prefix)

    # 3. Hero stickman stepping back peacefully with raised hand
    im_h, dh = _make_sprite(320, 460)
    draw_stickman_figure(dh, 160, 82, scale=1.02, pose="shielding", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 5)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "phone", "anim": "shake_ring", "cx0": 330, "cy0": 970, "w": 395, "from_f": 0.0, "to_f": 1.0, "amp": 0.075},
        {"sprite": "badge1", "anim": "pop_bounce", "cx0": 470, "cy0": 585, "w": 430, "from_f": 0.20, "to_f": 1.0},
        {"sprite": "hero", "anim": "walk_to", "cx0": 810, "cy0": 1060, "cx1": 965, "cy1": 1060, "w": 415, "from_f": 0.0, "to_f": 1.0, "hops": 2},
    ]
    vector_plan = [
        {"kind": "line", "p1": [100, 1395], "p2": [1180, 1395], "color": muted, "lw": 3, "from_f": 0.0, "to_f": 1.0},
        {"kind": "line", "p1": [640, 620], "p2": [640, 1350], "color": accent, "lw": 6, "from_f": 0.42, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_scale_tipping(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 33))
    sprites: dict[str, Any] = {}

    # 1. Fulcrum base triangle
    im_f, df = _make_sprite(220, 220)
    pts = [(110, 24), (20, 198), (200, 198)]
    df.polygon(pts, fill=soft_tint_bg(accent, 0.2, card_bg), outline=ink)
    hand_line(df, 110, 24, 20, 198, seed=seed, lw=6, color=ink)
    hand_line(df, 110, 24, 200, 198, seed=seed + 1, lw=6, color=ink)
    hand_line(df, 14, 198, 206, 198, seed=seed + 2, lw=6, color=ink)
    _save_sprite(sprites, "fulcrum", im_f, out_dir, prefix)

    # 2. Pivoting beam
    im_bm, db = _make_sprite(760, 70)
    hand_rect(db, 16, 16, 728, 38, seed=seed + 3, lw=5, color=ink, fill=card_bg, r=18)
    hand_circle(db, 380, 35, 16, seed=seed + 4, lw=4, color=ink, fill=accent)
    _save_sprite(sprites, "beam", im_bm, out_dir, prefix)

    # 3. Left weight tray (muted) & Right weight tray (accent winning!)
    im_wl, dl = _make_sprite(300, 200)
    hand_rect(dl, 12, 12, 276, 176, seed=seed + 5, lw=4, color=muted, fill=card_bg, r=24, shadow=True)
    draw_fitted_text(dl, scene.get("left_tag") or "EXCUSE", 150, 100, max_w=240, target_size=34, family="noto", fill=muted, bold=True, max_lines=2)
    _save_sprite(sprites, "w_left", im_wl, out_dir, prefix)

    im_wr, dr = _make_sprite(320, 220)
    hand_rect(dr, 12, 12, 296, 196, seed=seed + 6, lw=6, color=accent, fill=soft_tint_bg(accent, 0.22, card_bg), r=24, shadow=True)
    draw_fitted_text(dr, scene.get("right_tag") or "CHOICE", 160, 110, max_w=260, target_size=38, family="noto", fill=accent, bold=True, max_lines=2)
    _save_sprite(sprites, "w_right", im_wr, out_dir, prefix)

    sprite_plan = [
        {"sprite": "fulcrum", "anim": "pop_bounce", "cx0": 640, "cy0": 1220, "w": 220, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "beam", "anim": "tilt_pivot", "cx0": 640, "cy0": 1070, "w": 840, "ang0": -0.18, "ang_mid": 0.04, "ang1": 0.17, "anchor": [0.5, 0.5], "from_f": 0.0, "to_f": 1.0},
        {"sprite": "w_left", "anim": "sweep", "pts": [[280, 1010], [280, 910], [280, 825]], "w": 310, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "w_right", "anim": "sweep", "pts": [[1000, 840], [1000, 955], [1000, 1070]], "w": 340, "from_f": 0.1, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_staircase_climb(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 44))
    steps = scene.get("steps") or ["Start", "Habit", "Mastery"]
    sprites: dict[str, Any] = {}

    heights = [260, 410, 560]
    for i, sh in enumerate(heights):
        is_top = (i == 2)
        im_s, ds = _make_sprite(270, sh)
        fill_c = soft_tint_bg(accent, 0.28 if is_top else 0.10 * (i + 1), card_bg)
        hand_rect(ds, 10, 10, 250, sh - 20, seed=seed + i, lw=6 if is_top else 4, color=accent if is_top else ink, fill=fill_c, r=20, shadow=True)
        draw_fitted_text(ds, f"{i + 1}", 135, 56, max_w=200, target_size=34, family="noto", fill=accent if is_top else muted, bold=True)
        draw_fitted_text(ds, str(steps[i]), 135, 130, max_w=215, target_size=36, family="caveat", fill=ink, bold=True, max_lines=2)
        _save_sprite(sprites, f"step{i+1}", im_s, out_dir, prefix)

    # Climbing stickman who hops step 1 -> step 2 -> step 3!
    im_c, dc = _make_sprite(280, 420)
    draw_stickman_figure(dc, 140, 78, scale=0.88, pose="climbing", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 10)
    _save_sprite(sprites, "climber", im_c, out_dir, prefix)

    # Crown sparkle at peak
    im_sp, dsp = _make_sprite(140, 140)
    draw_icon_sparkle(dsp, 70, 70, 52, color=ACCENT_GOLD, ink=ink)
    _save_sprite(sprites, "spark", im_sp, out_dir, prefix)

    sprite_plan = [
        {"sprite": "step1", "anim": "slide_in", "cx0": 265, "cy0": 1520, "cx1": 265, "cy1": 1270, "w": 280, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "step2", "anim": "slide_in", "cx0": 620, "cy0": 1520, "cx1": 620, "cy1": 1190, "w": 280, "from_f": 0.18, "to_f": 1.0},
        {"sprite": "step3", "anim": "slide_in", "cx0": 975, "cy0": 1520, "cx1": 975, "cy1": 1110, "w": 280, "from_f": 0.35, "to_f": 1.0},
        {"sprite": "climber", "anim": "hop_steps", "pts": [[265, 955], [620, 795], [975, 640]], "w": 240, "from_f": 0.08, "to_f": 1.0},
        {"sprite": "spark", "anim": "pop_bounce", "cx0": 975, "cy0": 425, "w": 135, "from_f": 0.72, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_domino_ripple(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 55))
    steps = scene.get("steps") or ["Spark", "Action", "Habit", "Impact"]
    sprites: dict[str, Any] = {}

    for i in range(4):
        is_last = (i == 3)
        im_d, dd = _make_sprite(140, 340)
        hand_rect(
            dd, 10, 10, 120, 320, seed=seed + i, lw=5 if is_last else 4,
            color=accent if is_last else ink,
            fill=soft_tint_bg(accent, 0.25 if is_last else 0.08, card_bg), r=16, shadow=True,
        )
        hand_line(dd, 25, 170, 115, 170, seed=seed + 20 + i, lw=3, color=muted)
        draw_fitted_text(dd, str(steps[i])[:10], 70, 95, max_w=96, target_size=26, family="noto", fill=accent if is_last else ink, bold=True, max_lines=2)
        hand_circle(dd, 70, 245, 14, seed=seed + 30 + i, lw=3, color=accent if is_last else ink, fill=accent if i == 0 or is_last else muted)
        _save_sprite(sprites, f"dom{i+1}", im_d, out_dir, prefix)

    sprite_plan = [
        {"sprite": "dom1", "anim": "tilt_pivot", "cx0": 210, "cy0": 1420, "w": 190, "ang0": 0.0, "ang_mid": 0.22, "ang1": 0.48, "anchor": [0.5, 1.0], "from_f": 0.0, "to_f": 1.0},
        {"sprite": "dom2", "anim": "tilt_pivot", "cx0": 495, "cy0": 1420, "w": 190, "ang0": 0.0, "ang_mid": 0.0, "ang1": 0.44, "anchor": [0.5, 1.0], "from_f": 0.0, "to_f": 1.0},
        {"sprite": "dom3", "anim": "tilt_pivot", "cx0": 780, "cy0": 1420, "w": 190, "ang0": 0.0, "ang_mid": 0.0, "ang1": 0.40, "anchor": [0.5, 1.0], "from_f": 0.0, "to_f": 1.0},
        {"sprite": "dom4", "anim": "tilt_pivot", "cx0": 1065, "cy0": 1420, "w": 200, "ang0": 0.0, "ang_mid": 0.0, "ang1": 0.28, "anchor": [0.5, 1.0], "from_f": 0.0, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "p1": [100, 1425], "p2": [1180, 1425], "color": ink, "lw": 5, "from_f": 0.0, "to_f": 1.0},
        {"kind": "arrow", "x": 300, "y": 720, "w": 680, "color": accent, "lw": 7, "from_f": 0.25, "to_f": 0.85},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_spotlight_shift(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 66))
    sprites: dict[str, Any] = {}

    # Moving golden/accent spotlight cone
    im_cone, dc = _make_sprite(460, 820)
    r, g, b = _hex_to_rgb(accent)
    dc.polygon([(145, 0), (315, 0), (455, 815), (5, 815)], fill=(r, g, b, 62))
    _save_sprite(sprites, "cone", im_cone, out_dir, prefix)

    # Left & Right contrasting stickmen
    im_l, dl = _make_sprite(320, 460)
    draw_stickman_figure(dl, 160, 82, scale=1.0, pose="vulnerable", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "left_fig", im_l, out_dir, prefix)

    im_r, dr = _make_sprite(320, 480)
    draw_stickman_figure(dr, 160, 96, scale=1.06, pose="spotlight_crown", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "right_fig", im_r, out_dir, prefix)

    sprite_plan = [
        {"sprite": "left_fig", "anim": "pop_bounce", "cx0": 320, "cy0": 1070, "w": 330, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "right_fig", "anim": "pop_bounce", "cx0": 950, "cy0": 1060, "w": 345, "from_f": 0.15, "to_f": 1.0},
        # Cone starts illuminating Left -> slides cleanly onto Right hero!
        {"sprite": "cone", "anim": "sweep", "pts": [[320, 910], [320, 910], [950, 910], [950, 910]], "w": 490, "from_f": 0.0, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "p1": [120, 1340], "p2": [1160, 1340], "color": muted, "lw": 4, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_mirror_truth(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 77))
    sprites: dict[str, Any] = {}

    # Ornate standing mirror
    im_m, dm = _make_sprite(420, 740)
    hand_rect(dm, 16, 16, 388, 708, seed=seed, lw=8, color=ink, fill=soft_tint_bg(accent, 0.10, card_bg), r=180, shadow=True)
    hand_rect(dm, 38, 38, 344, 664, seed=seed + 1, lw=3, color=muted, fill=None, r=160)
    hand_line(dm, 100, 130, 160, 75, seed=seed + 2, lw=3, color=WHITE if th["is_dark"] else muted)
    _save_sprite(sprites, "mirror", im_m, out_dir, prefix)

    # Beat A reflection: anxious faded silhouette
    im_ra, dra = _make_sprite(260, 420)
    draw_stickman_figure(dra, 130, 78, scale=0.88, pose="anxious", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed + 3)
    _save_sprite(sprites, "ref_a", im_ra, out_dir, prefix)

    # Beat B reflection: glowing peaceful crown self
    im_rb, drb = _make_sprite(280, 440)
    draw_stickman_figure(drb, 140, 92, scale=0.92, pose="spotlight_crown", accent_color=accent, ink=accent, head_fill=card_bg, seed=seed + 4)
    _save_sprite(sprites, "ref_b", im_rb, out_dir, prefix)

    # Foreground Hero walking smoothly closer to mirror
    im_h, dh = _make_sprite(320, 480)
    draw_stickman_figure(dh, 160, 86, scale=1.08, pose="neutral", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 5)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "mirror", "anim": "pop_bounce", "cx0": 840, "cy0": 950, "w": 430, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "ref_a", "anim": "crossfade", "cx0": 840, "cy0": 975, "w": 270, "a0": 0.85, "a1": 0.0, "from_f": 0.0, "to_f": 0.65},
        {"sprite": "ref_b", "anim": "crossfade", "cx0": 840, "cy0": 970, "w": 290, "a0": 0.0, "a1": 1.0, "from_f": 0.42, "to_f": 1.0},
        {"sprite": "hero", "anim": "walk_to", "cx0": 260, "cy0": 1080, "cx1": 420, "cy1": 1070, "w": 360, "from_f": 0.0, "to_f": 1.0, "hops": 2},
    ]
    vector_plan = [
        {"kind": "line", "p1": [120, 1360], "p2": [1160, 1360], "color": muted, "lw": 3, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_hourglass_sprint(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 88))
    sprites: dict[str, Any] = {}

    # Hand-drawn Hourglass
    im_hg, dh = _make_sprite(260, 340)
    hand_line(dh, 40, 28, 220, 28, seed=seed, lw=7, color=ink)
    hand_line(dh, 40, 312, 220, 312, seed=seed + 1, lw=7, color=ink)
    glass_top = [(58, 32), (202, 32), (138, 166), (122, 166)]
    glass_bot = [(122, 174), (138, 174), (202, 308), (58, 308)]
    dh.polygon(glass_top, fill=card_bg, outline=ink)
    dh.polygon(glass_bot, fill=soft_tint_bg(accent, 0.30, card_bg), outline=ink)
    hand_line(dh, 58, 32, 202, 308, seed=seed + 2, lw=5, color=ink)
    hand_line(dh, 202, 32, 58, 308, seed=seed + 3, lw=5, color=ink)
    _save_sprite(sprites, "hourglass", im_hg, out_dir, prefix)

    # Sprinting Stickman dashing across track
    im_sp, dsp = _make_sprite(340, 440)
    draw_stickman_figure(dsp, 170, 82, scale=0.98, pose="sprinting", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 4)
    # Speed lines behind runner
    hand_line(dsp, 18, 165, 92, 165, seed=seed + 5, lw=4, color=accent)
    hand_line(dsp, 8, 215, 78, 215, seed=seed + 6, lw=4, color=muted)
    _save_sprite(sprites, "runner", im_sp, out_dir, prefix)

    sprite_plan = [
        {"sprite": "hourglass", "anim": "shake_ring", "cx0": 640, "cy0": 660, "w": 330, "from_f": 0.0, "to_f": 1.0, "amp": 0.06},
        {"sprite": "runner", "anim": "walk_to", "cx0": 210, "cy0": 1165, "cx1": 980, "cy1": 1165, "w": 440, "from_f": 0.0, "to_f": 1.0, "hops": 4},
    ]
    vector_plan = [
        {"kind": "line", "p1": [90, 1420], "p2": [1190, 1420], "color": accent, "lw": 5, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_bridge_cross(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 99))
    sprites: dict[str, Any] = {}

    im_cl, dcl = _make_sprite(320, 320)
    hand_rect(dcl, 10, 10, 300, 300, seed=seed, lw=5, color=ink, fill=card_bg, r=18, shadow=True)
    draw_fitted_text(dcl, scene.get("left_tag") or "HERE", 160, 85, max_w=250, target_size=34, family="noto", fill=muted, bold=True)
    _save_sprite(sprites, "cliff_l", im_cl, out_dir, prefix)

    im_cr, dcr = _make_sprite(320, 320)
    hand_rect(dcr, 10, 10, 300, 300, seed=seed + 1, lw=6, color=accent, fill=soft_tint_bg(accent, 0.20, card_bg), r=18, shadow=True)
    draw_fitted_text(dcr, scene.get("right_tag") or "BEYOND", 160, 85, max_w=250, target_size=34, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "cliff_r", im_cr, out_dir, prefix)

    # Glowing bridge plank
    im_pl, dpl = _make_sprite(460, 56)
    hand_rect(dpl, 8, 8, 444, 40, seed=seed + 2, lw=5, color=ink, fill=accent, r=14, shadow=True)
    _save_sprite(sprites, "bridge", im_pl, out_dir, prefix)

    im_h, dh = _make_sprite(280, 420)
    draw_stickman_figure(dh, 140, 76, scale=0.88, pose="climbing", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 3)
    _save_sprite(sprites, "walker", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "cliff_l", "anim": "pop_bounce", "cx0": 220, "cy0": 1240, "w": 330, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "cliff_r", "anim": "pop_bounce", "cx0": 1060, "cy0": 1240, "w": 330, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "bridge", "anim": "slide_in", "cx0": 640, "cy0": 920, "cx1": 640, "cy1": 1090, "w": 520, "from_f": 0.25, "to_f": 1.0},
        {"sprite": "walker", "anim": "walk_to", "cx0": 230, "cy0": 900, "cx1": 1040, "cy1": 900, "w": 240, "from_f": 0.0, "to_f": 1.0, "hops": 4},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_magnet_orbit(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 111))
    steps = scene.get("steps") or ["Time", "Energy", "Focus"]
    sprites: dict[str, Any] = {}

    # U-Magnet
    im_mg, dmg = _make_sprite(320, 320)
    hand_rect(dmg, 46, 30, 62, 200, seed=seed, lw=5, color=ink, fill=accent, r=18)
    hand_rect(dmg, 212, 30, 62, 200, seed=seed + 1, lw=5, color=ink, fill=accent, r=18)
    hand_rect(dmg, 46, 190, 228, 72, seed=seed + 2, lw=5, color=ink, fill=card_bg, r=30)
    hand_line(dmg, 46, 72, 108, 72, seed=seed + 3, lw=5, color=ink)
    hand_line(dmg, 212, 72, 274, 72, seed=seed + 4, lw=5, color=ink)
    _save_sprite(sprites, "magnet", im_mg, out_dir, prefix)

    for i in range(3):
        im_t, dt = _make_sprite(220, 100)
        hand_rect(dt, 8, 8, 204, 84, seed=seed + 10 + i, lw=4, color=accent if i == 1 else ink, fill=card_bg, r=24, shadow=True)
        draw_fitted_text(dt, str(steps[i]), 110, 50, max_w=175, target_size=28, family="noto", fill=accent if i == 1 else ink, bold=True)
        _save_sprite(sprites, f"tok{i+1}", im_t, out_dir, prefix)

    sprite_plan = [
        {"sprite": "magnet", "anim": "shake_ring", "cx0": 640, "cy0": 1150, "w": 330, "from_f": 0.0, "to_f": 1.0, "amp": 0.04},
        {"sprite": "tok1", "anim": "slide_in", "cx0": 210, "cy0": 520, "cx1": 430, "cy1": 840, "w": 240, "from_f": 0.1, "to_f": 1.0},
        {"sprite": "tok2", "anim": "slide_in", "cx0": 640, "cy0": 430, "cx1": 640, "cy1": 740, "w": 250, "from_f": 0.25, "to_f": 1.0},
        {"sprite": "tok3", "anim": "slide_in", "cx0": 1070, "cy0": 520, "cx1": 850, "cy1": 840, "w": 240, "from_f": 0.4, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_split_cards_slide(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 123))
    sprites: dict[str, Any] = {}

    # Left card (muted / myth / before)
    im_l, dl = _make_sprite(460, 620)
    hand_rect(dl, 12, 12, 436, 596, seed=seed, lw=4, color=muted, fill=card_bg, r=28, shadow=True)
    draw_stickman_figure(dl, 230, 155, scale=0.82, pose="vulnerable", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed + 1)
    draw_fitted_text(dl, scene.get("left_label") or "SURFACE", 230, 505, max_w=385, target_size=34, family="caveat", fill=muted, bold=True, max_lines=2)
    _save_sprite(sprites, "card_l", im_l, out_dir, prefix)

    # Right card (vivid / truth / reality)
    im_r, dr = _make_sprite(460, 620)
    hand_rect(dr, 12, 12, 436, 596, seed=seed + 2, lw=6, color=accent, fill=soft_tint_bg(accent, 0.16, card_bg), r=28, shadow=True)
    draw_stickman_figure(dr, 230, 155, scale=0.86, pose="peaceful", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 3)
    draw_fitted_text(dr, scene.get("right_label") or "REALITY", 230, 505, max_w=385, target_size=36, family="caveat", fill=accent, bold=True, max_lines=2)
    _save_sprite(sprites, "card_r", im_r, out_dir, prefix)

    sprite_plan = [
        {"sprite": "card_l", "anim": "slide_in", "cx0": -280, "cy0": 980, "cx1": 345, "cy1": 980, "w": 480, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "card_r", "anim": "slide_in", "cx0": 1560, "cy0": 980, "cx1": 935, "cy1": 980, "w": 480, "from_f": 0.25, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "p1": [640, 580], "p2": [640, 1380], "color": accent, "lw": 6, "from_f": 0.05, "to_f": 0.85},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_rocket_breakthrough(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 145))
    sprites: dict[str, Any] = {}

    # Crisp Paper Airplane / Rocket flying diagonally upward
    im_rk, drk = _make_sprite(280, 220)
    plane_pts = [(24, 150), (255, 42), (168, 198), (118, 138)]
    drk.polygon(plane_pts, fill=soft_tint_bg(accent, 0.28, card_bg), outline=ink)
    hand_line(drk, 24, 150, 255, 42, seed=seed, lw=5, color=ink)
    hand_line(drk, 255, 42, 168, 198, seed=seed + 1, lw=5, color=ink)
    hand_line(drk, 118, 138, 255, 42, seed=seed + 2, lw=4, color=accent)
    _save_sprite(sprites, "rocket", im_rk, out_dir, prefix)

    im_st, dst = _make_sprite(220, 120)
    hand_rect(dst, 8, 8, 204, 104, seed=seed + 3, lw=4, color=accent, fill=card_bg, r=24, shadow=True)
    draw_fitted_text(dst, scene.get("right_tag") or "LIFT OFF", 110, 60, max_w=175, target_size=30, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "goal", im_st, out_dir, prefix)

    sprite_plan = [
        {"sprite": "rocket", "anim": "sweep", "pts": [[240, 1220], [580, 960], [920, 660]], "w": 300, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "goal", "anim": "pop_bounce", "cx0": 950, "cy0": 480, "w": 250, "from_f": 0.50, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "p1": [140, 1260], "p2": [860, 720], "color": accent, "lw": 5, "from_f": 0.0, "to_f": 0.9},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_crowd_filter(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 155))
    sprites: dict[str, Any] = {}

    # 3 noisy background crowd silhouettes
    im_cr, dcr = _make_sprite(760, 290)
    for i, x in enumerate([130, 380, 630]):
        draw_stickman_figure(dcr, x, 58, scale=0.62, pose="gesturing" if i % 2 else "anxious", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed + i)
    _save_sprite(sprites, "crowd", im_cr, out_dir, prefix)

    # Clear standout hero stepping forward
    im_h, dh = _make_sprite(320, 480)
    draw_stickman_figure(dh, 160, 92, scale=1.08, pose="peaceful", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 10)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "crowd", "anim": "crossfade", "cx0": 640, "cy0": 710, "w": 860, "a0": 0.95, "a1": 0.28, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "hero", "anim": "walk_to", "cx0": 640, "cy0": 1240, "cx1": 640, "cy1": 1070, "w": 360, "from_f": 0.15, "to_f": 1.0, "hops": 2},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_cta_celebration(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 777))
    sprites: dict[str, Any] = {}

    cta_headline = scene.get("cta_headline") or "Follow this page"
    btn_label = scene.get("cta_button_label") or "+ FOLLOW"
    subtext = scene.get("cta_subtext") or "More insights coming soon"

    # Waving / pointing Stickman on left
    im_h, dh = _make_sprite(340, 480)
    draw_stickman_figure(dh, 170, 90, scale=1.08, pose="pointing_cta", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    # CTA Headline text sprite
    im_hl, dhl = _make_sprite(640, 180)
    draw_fitted_text(dhl, cta_headline, 320, 90, max_w=590, target_size=54, family="caveat", fill=ink, bold=True, max_lines=2)
    _save_sprite(sprites, "headline", im_hl, out_dir, prefix)

    # Interactive Pill Button
    im_btn, dbtn = _make_sprite(460, 150)
    hand_rect(dbtn, 10, 10, 440, 130, seed=seed + 1, lw=5, color=ink, fill=accent, r=36, shadow=True)
    draw_fitted_text(dbtn, btn_label, 230, 75, max_w=390, target_size=40, family="noto", fill=WHITE, bold=True)
    _save_sprite(sprites, "button", im_btn, out_dir, prefix)

    # Bell shaking + Clicking Pointer Cursor
    im_bell, db = _make_sprite(120, 120)
    draw_icon_bell(db, 60, 58, accent=accent, ink=ink, card_bg=card_bg)
    _save_sprite(sprites, "bell", im_bell, out_dir, prefix)

    im_cur, dcur = _make_sprite(110, 120)
    draw_icon_cursor_pointer(dcur, 32, 22, accent=accent, ink=ink)
    _save_sprite(sprites, "cursor", im_cur, out_dir, prefix)

    im_sub, dsub = _make_sprite(640, 110)
    draw_fitted_text(dsub, subtext, 320, 55, max_w=600, target_size=28, family="noto", fill=muted, max_lines=2)
    _save_sprite(sprites, "sub", im_sub, out_dir, prefix)

    sprite_plan = [
        {"sprite": "hero", "anim": "pop_bounce", "cx0": 270, "cy0": 1030, "w": 360, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "headline", "anim": "slide_in", "cx0": 820, "cy0": 690, "cx1": 800, "cy1": 750, "w": 660, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "button", "anim": "pop_bounce", "cx0": 800, "cy0": 950, "w": 500, "from_f": 0.15, "to_f": 1.0},
        {"sprite": "bell", "anim": "shake_ring", "cx0": 1085, "cy0": 910, "w": 130, "from_f": 0.25, "to_f": 1.0, "amp": 0.14},
        # Cursor glides right onto the button and taps it!
        {"sprite": "cursor", "anim": "sweep", "pts": [[1120, 1260], [990, 1080], [945, 995], [955, 1010]], "w": 120, "from_f": 0.30, "to_f": 1.0},
        {"sprite": "sub", "anim": "slide_in", "cx0": 800, "cy0": 1220, "cx1": 800, "cy1": 1160, "w": 660, "from_f": 0.25, "to_f": 1.0},
    ]
    vector_plan: list[dict] = []
    return sprites, sprite_plan, vector_plan


def _choreo_give_and_withdraw(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Visual metaphor: Person A offers help/favor prop while Person B takes it and turns away."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 211))
    prop_kind = str(scene.get("prop_kind", "heart"))
    sprites: dict[str, Any] = {}

    im_g, dg = _make_sprite(320, 460)
    draw_stickman_figure(dg, 140, 82, scale=1.02, pose="gesturing", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "giver", im_g, out_dir, prefix)

    im_t, dt = _make_sprite(320, 460)
    draw_stickman_figure(dt, 160, 82, scale=1.02, pose="vulnerable", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed + 2)
    _save_sprite(sprites, "taker", im_t, out_dir, prefix)

    im_p, dp = _make_sprite(170, 170)
    draw_semantic_prop(dp, prop_kind, 85, 85, 58, accent=accent, ink=ink, card_bg=card_bg, seed=seed + 5)
    _save_sprite(sprites, "favor_prop", im_p, out_dir, prefix)

    im_card, dc = _make_sprite(560, 140)
    hand_rect(dc, 12, 12, 536, 116, seed=seed + 7, lw=4, color=accent, fill=card_bg, r=24, shadow=True)
    draw_fitted_text(dc, scene.get("beat_b_label") or "Present only while needed", 280, 70, max_w=490, target_size=34, family="caveat", fill=ink, bold=True, max_lines=2)
    _save_sprite(sprites, "note", im_card, out_dir, prefix)

    sprite_plan = [
        {"sprite": "giver", "anim": "pop_bounce", "cx0": 290, "cy0": 950, "w": 320, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "favor_prop", "anim": "sweep", "pts": [[450, 910], [640, 880], [920, 890]], "w": 155, "from_f": 0.08, "to_f": 0.65},
        {"sprite": "taker", "anim": "walk_to", "cx0": 770, "cy0": 950, "cx1": 1070, "cy1": 950, "w": 310, "from_f": 0.18, "to_f": 1.0, "hops": 3},
        {"sprite": "note", "anim": "slide_in", "cx0": 640, "cy0": 1460, "cx1": 640, "cy1": 1350, "w": 580, "from_f": 0.42, "to_f": 1.0},
    ]
    vector_plan: list[dict] = []
    return sprites, sprite_plan, vector_plan


def _choreo_boundary_shield(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Stickman raises a crisp glowing boundary shield deflecting noisy incoming chaos."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 223))
    sprites: dict[str, Any] = {}

    im_h, dh = _make_sprite(320, 460)
    draw_stickman_figure(dh, 180, 82, scale=1.02, pose="shielding", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    im_sh, dsh = _make_sprite(220, 260)
    draw_semantic_prop(dsh, "shield", 110, 130, 86, accent=accent, ink=ink, card_bg=card_bg, seed=seed + 3)
    _save_sprite(sprites, "shield", im_sh, out_dir, prefix)

    im_sp1, dsp1 = _make_sprite(160, 160)
    draw_semantic_prop(dsp1, "lightning", 80, 80, 56, accent=ACCENT_CORAL, ink=ink, card_bg=card_bg, seed=seed + 5)
    _save_sprite(sprites, "noise1", im_sp1, out_dir, prefix)

    im_tag, dtag = _make_sprite(460, 120)
    hand_rect(dtag, 10, 10, 440, 100, seed=seed + 8, lw=4, color=accent, fill=card_bg, r=22, shadow=True)
    draw_fitted_text(dtag, scene.get("stamp_word") or "PROTECT YOUR PEACE", 230, 60, max_w=400, target_size=32, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "tag", im_tag, out_dir, prefix)

    sprite_plan = [
        {"sprite": "hero", "anim": "pop_bounce", "cx0": 820, "cy0": 990, "w": 330, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "shield", "anim": "pop_bounce", "cx0": 590, "cy0": 980, "w": 230, "from_f": 0.08, "to_f": 1.0},
        {"sprite": "noise1", "anim": "sweep", "pts": [[190, 820], [450, 940], [220, 1140]], "w": 150, "from_f": 0.14, "to_f": 0.85},
        {"sprite": "tag", "anim": "slide_in", "cx0": 640, "cy0": 1410, "cx1": 640, "cy1": 1315, "w": 490, "from_f": 0.30, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "ring_pulse", "cx": 590, "cy": 980, "r": 165, "color": accent, "lw": 4, "from_f": 0.10, "to_f": 0.90},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_tether_break(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Figure pulls free from heavy anchor illusion toward glowing freedom."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 237))
    kws = scene.get("keywords") or ["Past"]
    sprites: dict[str, Any] = {}

    im_anc, danc = _make_sprite(240, 220)
    hand_rect(danc, 14, 14, 212, 192, seed=seed, lw=5, color=muted, fill=card_bg, r=24, shadow=True)
    draw_fitted_text(danc, str(kws[0]).upper(), 120, 110, max_w=180, target_size=34, family="noto", fill=muted, bold=True)
    _save_sprite(sprites, "anchor", im_anc, out_dir, prefix)

    im_h, dh = _make_sprite(310, 440)
    draw_stickman_figure(dh, 155, 80, scale=1.0, pose="walking", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 3)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    im_sun, dsun = _make_sprite(240, 320)
    hand_rect(dsun, 24, 24, 192, 272, seed=seed + 5, lw=5, color=accent, fill=soft_tint_bg(accent, 0.22, card_bg), r=20)
    draw_icon_sparkle(dsun, 120, 130, 56, color=accent, ink=ink)
    _save_sprite(sprites, "freedom", im_sun, out_dir, prefix)

    sprite_plan = [
        {"sprite": "anchor", "anim": "tilt_pivot", "cx0": 230, "cy0": 1120, "w": 220, "from_f": 0.0, "to_f": 1.0, "angles": [0.0, -0.14, -0.05], "anchor": [0.5, 0.85]},
        {"sprite": "freedom", "anim": "pop_bounce", "cx0": 1030, "cy0": 950, "w": 240, "from_f": 0.32, "to_f": 1.0},
        {"sprite": "hero", "anim": "walk_to", "cx0": 480, "cy0": 1010, "cx1": 900, "cy1": 990, "w": 285, "from_f": 0.0, "to_f": 1.0, "hops": 4},
    ]
    vector_plan: list[dict] = []
    return sprites, sprite_plan, vector_plan


def _choreo_mind_storm_calm(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Stormy overwhelm overhead dissolves into serene sun clarity."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 251))
    sprites: dict[str, Any] = {}

    im_s1, ds1 = _make_sprite(320, 450)
    draw_stickman_figure(ds1, 160, 82, scale=1.02, pose="anxious", accent_color=ACCENT_CORAL, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "anx", im_s1, out_dir, prefix)

    im_s2, ds2 = _make_sprite(320, 450)
    draw_stickman_figure(ds2, 160, 82, scale=1.02, pose="peaceful", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "calm", im_s2, out_dir, prefix)

    im_storm, dstm = _make_sprite(320, 180)
    draw_semantic_prop(dstm, "lightning", 110, 90, 48, accent=ACCENT_CORAL, ink=ink, card_bg=card_bg, seed=seed + 3)
    draw_semantic_prop(dstm, "lightning", 210, 90, 44, accent=muted, ink=ink, card_bg=card_bg, seed=seed + 4)
    _save_sprite(sprites, "storm", im_storm, out_dir, prefix)

    im_sun, dsun = _make_sprite(260, 260)
    hand_circle(dsun, 130, 130, 88, seed=seed + 6, lw=5, color=accent, fill=soft_tint_bg(accent, 0.25, card_bg))
    draw_icon_sparkle(dsun, 130, 130, 56, color=accent, ink=ink)
    _save_sprite(sprites, "sun", im_sun, out_dir, prefix)

    sprite_plan = [
        {"sprite": "storm", "anim": "crossfade", "cx0": 640, "cy0": 610, "w": 340, "from_f": 0.0, "to_f": 0.55, "a0": 1.0, "a1": 0.0},
        {"sprite": "anx", "anim": "crossfade", "cx0": 640, "cy0": 1030, "w": 330, "from_f": 0.0, "to_f": 0.52, "a0": 1.0, "a1": 0.0},
        {"sprite": "sun", "anim": "pop_bounce", "cx0": 640, "cy0": 610, "w": 270, "from_f": 0.42, "to_f": 1.0},
        {"sprite": "calm", "anim": "pop_bounce", "cx0": 640, "cy0": 1030, "w": 335, "from_f": 0.45, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "ring_pulse", "cx": 640, "cy": 610, "r": 165, "color": accent, "lw": 4, "from_f": 0.45, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_idea_spark_build(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Thinking figure + book/brain prop launching upward into bright insight sparks."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 263))
    prop_kind = str(scene.get("prop_kind", "book"))
    if prop_kind == "spark":
        prop_kind = "book"
    sprites: dict[str, Any] = {}

    im_h, dh = _make_sprite(320, 450)
    draw_stickman_figure(dh, 160, 82, scale=1.02, pose="pondering", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "hero", im_h, out_dir, prefix)

    im_bk, dbk = _make_sprite(260, 220)
    draw_semantic_prop(dbk, prop_kind, 130, 110, 82, accent=accent, ink=ink, card_bg=card_bg, seed=seed + 3)
    _save_sprite(sprites, "book", im_bk, out_dir, prefix)

    im_lb, dlb = _make_sprite(240, 240)
    draw_icon_lightbulb(dlb, 120, 120, accent=accent, ink=ink, card_bg=card_bg)
    _save_sprite(sprites, "bulb", im_lb, out_dir, prefix)

    sprite_plan = [
        {"sprite": "hero", "anim": "pop_bounce", "cx0": 360, "cy0": 1030, "w": 325, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "book", "anim": "slide_in", "cx0": 860, "cy0": 1220, "cx1": 840, "cy1": 1090, "w": 265, "from_f": 0.08, "to_f": 1.0},
        {"sprite": "bulb", "anim": "pop_bounce", "cx0": 840, "cy0": 720, "w": 245, "from_f": 0.28, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "arrow", "x": 500, "y": 820, "w": 230, "color": accent, "lw": 6, "from_f": 0.22, "to_f": 0.72},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_two_path_fork(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Choice fork: easy shortcut fades down vs steep peak path crowned with reward."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 277))
    sprites: dict[str, Any] = {}

    im_ez, dez = _make_sprite(340, 160)
    hand_rect(dez, 10, 10, 320, 140, seed=seed, lw=4, color=muted, fill=card_bg, r=22, shadow=True)
    draw_fitted_text(dez, scene.get("left_tag") or "COMFORT", 170, 80, max_w=290, target_size=34, family="noto", fill=muted, bold=True)
    _save_sprite(sprites, "easy", im_ez, out_dir, prefix)

    im_hd, dhd = _make_sprite(340, 160)
    hand_rect(dhd, 10, 10, 320, 140, seed=seed + 2, lw=5, color=accent, fill=soft_tint_bg(accent, 0.22, card_bg), r=22, shadow=True)
    draw_fitted_text(dhd, scene.get("right_tag") or "DISCIPLINE", 170, 80, max_w=290, target_size=34, family="noto", fill=accent, bold=True)
    _save_sprite(sprites, "hard", im_hd, out_dir, prefix)

    im_cr, dcr = _make_sprite(170, 140)
    draw_semantic_prop(dcr, "crown", 85, 75, 58, accent=ACCENT_GOLD, ink=ink, card_bg=card_bg, seed=seed + 4)
    _save_sprite(sprites, "crown", im_cr, out_dir, prefix)

    im_h, dh = _make_sprite(290, 420)
    draw_stickman_figure(dh, 145, 78, scale=0.96, pose="walking", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 5)
    _save_sprite(sprites, "walker", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "easy", "anim": "slide_in", "cx0": 320, "cy0": 1080, "cx1": 320, "cy1": 1240, "w": 340, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "hard", "anim": "slide_in", "cx0": 950, "cy0": 980, "cx1": 950, "cy1": 810, "w": 360, "from_f": 0.15, "to_f": 1.0},
        {"sprite": "crown", "anim": "pop_bounce", "cx0": 950, "cy0": 640, "w": 165, "from_f": 0.35, "to_f": 1.0},
        {"sprite": "walker", "anim": "walk_to", "cx0": 360, "cy0": 1000, "cx1": 740, "cy1": 860, "w": 270, "from_f": 0.0, "to_f": 1.0, "hops": 4},
    ]
    vector_plan = [
        {"kind": "line", "x": 450, "y": 1030, "w": 360, "points": [[0, 0], [360, -210]], "color": accent, "lw": 7, "from_f": 0.1, "to_f": 0.75},
    ]
    return sprites, sprite_plan, vector_plan


_CHOREO_GENERATORS = {
    "question_burst": _choreo_question_burst,
    "phone_trap": _choreo_phone_trap,
    "scale_tipping": _choreo_scale_tipping,
    "staircase_climb": _choreo_staircase_climb,
    "domino_ripple": _choreo_domino_ripple,
    "spotlight_shift": _choreo_spotlight_shift,
    "mirror_truth": _choreo_mirror_truth,
    "hourglass_sprint": _choreo_hourglass_sprint,
    "bridge_cross": _choreo_bridge_cross,
    "magnet_orbit": _choreo_magnet_orbit,
    "split_cards_slide": _choreo_split_cards_slide,
    "rocket_breakthrough": _choreo_rocket_breakthrough,
    "crowd_filter": _choreo_crowd_filter,
    "give_and_withdraw": _choreo_give_and_withdraw,
    "boundary_shield": _choreo_boundary_shield,
    "tether_break": _choreo_tether_break,
    "mind_storm_calm": _choreo_mind_storm_calm,
    "idea_spark_build": _choreo_idea_spark_build,
    "two_path_fork": _choreo_two_path_fork,
    "cta_celebration": _choreo_cta_celebration,
}


# ---------------------------------------------------------------------------
# Public Scene Illustrator Class
# ---------------------------------------------------------------------------

class CISSceneIllustrator:
    """Generates modular transparent animated sprite sets + composite preview PNGs (100% Free & Offline)."""

    def __init__(self, mode: str = "pil", aspect_ratio: str = "9:16") -> None:
        self.mode = mode
        self.aspect_ratio = aspect_ratio

    def illustrate(self, scene: dict, output_path: str) -> bool:
        out_p = Path(output_path)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        stem = out_p.stem
        sid = int(scene.get("scene_id", 1))
        prefix = f"s{sid:02d}"

        accent = safe_hex_color(scene.get("accent_color"), ACCENT_CORAL)
        choreo = str(scene.get("choreography") or scene.get("composition_type") or "question_burst")
        gen = _CHOREO_GENERATORS.get(choreo, _choreo_question_burst)

        sprites, sprite_plan, vector_plan = gen(scene, accent, out_p.parent, prefix)
        th = _theme_of(scene)

        # Optional local LCM DreamShaper illustrated scene backdrop
        if self.mode == "lcm" and choreo != "cta_celebration":
            try:
                from engine.lcm_image_engine import LCMImageEngine
                if LCMImageEngine.is_available():
                    if self.aspect_ratio == "16:9":
                        wash_w, wash_h = 1920, 1080
                    elif self.aspect_ratio == "1:1":
                        wash_w, wash_h = 1080, 1080
                    else:
                        wash_w, wash_h = CANVAS_W, CANVAS_H

                    is_dark = bool(th.get("is_dark", False))
                    pal_key = str(scene.get("palette_key", "")).lower()
                    if is_dark:
                        lcm_style = "cyberpunk" if ("neon" in pal_key or "blueprint" in pal_key) else "noir"
                    else:
                        lcm_style = "ghibli" if "sage" in pal_key else "storyteller"

                    narr_ctx = f"{scene.get('scene_title', '')}. {scene.get('narration', '')}".strip()
                    lcm_img = LCMImageEngine.render_background(
                        narration=narr_ctx,
                        width=wash_w,
                        height=wash_h,
                        style_name=lcm_style,
                        seed=int(scene.get("variant_seed", 42)),
                    )
                    if lcm_img is not None:
                        lcm_rgba = lcm_img.resize((wash_w, wash_h), Image.Resampling.LANCZOS).convert("RGBA")
                        # Soften bright highlights / darken shadows so foreground stickmen & typography pop cleanly
                        if is_dark:
                            scrim = Image.new("RGBA", (wash_w, wash_h), (10, 14, 22, 115))
                            lcm_toned = Image.alpha_composite(lcm_rgba, scrim)
                            alpha_val = 190
                        else:
                            paper_rgb = _hex_to_rgb(th.get("paper_bg", PAPER_BG))
                            scrim = Image.new("RGBA", (wash_w, wash_h), (*paper_rgb, 105))
                            lcm_toned = Image.alpha_composite(lcm_rgba, scrim)
                            alpha_val = 180
                        r_ch, g_ch, b_ch, _ = lcm_toned.split()
                        soft_alpha = Image.new("L", (wash_w, wash_h), alpha_val)
                        lcm_final = Image.merge("RGBA", (r_ch, g_ch, b_ch, soft_alpha))
                        lcm_path = str(out_p.parent / f"{stem}_lcm_wash.png")
                        lcm_final.save(lcm_path, "PNG")
                        sprites["lcm_wash"] = {"path": lcm_path, "w": wash_w, "h": wash_h}
                    else:
                        logger.warning("LCM DreamShaper returned None for scene %s (%s).", sid, lcm_style)
                else:
                    logger.warning("LCM DreamShaper requested but torch/diffusers are unavailable.")
            except Exception as exc:
                logger.warning("LCM backdrop generation exception on scene %s: %s", sid, exc)

        # Build composite fallback/preview PNG directly from sprites' final positions
        comp = Image.new("RGBA", (CANVAS_W, CANVAS_H), rgba(th["paper_bg"], 255))
        if "lcm_wash" in sprites:
            try:
                lw_img = Image.open(sprites["lcm_wash"]["path"]).convert("RGBA").resize(
                    (CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS
                )
                comp = Image.alpha_composite(comp, lw_img)
            except Exception:
                pass

        for sp in sprite_plan:
            name = sp.get("sprite")
            meta = sprites.get(name)
            if not meta:
                continue
            try:
                sp_img = Image.open(meta["path"]).convert("RGBA")
                # Place using final stage coords scaled from 1280 -> 1080
                scale_to_comp = CANVAS_W / 1280.0
                if "cx1" in sp:
                    cx, cy = sp["cx1"], sp["cy1"]
                elif "pts" in sp and sp["pts"]:
                    cx, cy = sp["pts"][-1][0], sp["pts"][-1][1]
                else:
                    cx, cy = sp.get("cx0", 640), sp.get("cy0", 960)
                tw = int(sp.get("w", meta["w"]) * scale_to_comp)
                th_px = max(1, int(tw * sp_img.height / max(1, sp_img.width)))
                resized = sp_img.resize((tw, th_px), Image.Resampling.LANCZOS)
                px = int(cx * scale_to_comp - tw / 2)
                py = int(cy * scale_to_comp - th_px / 2)
                comp.alpha_composite(resized, (max(0, min(CANVAS_W - 1, px)), max(0, min(CANVAS_H - 1, py))))
            except Exception:
                pass

        comp.save(output_path, "PNG")

        scene["_sprites"] = sprites
        scene["_sprite_plan"] = sprite_plan
        scene["_vector_plan"] = vector_plan
        logger.info(
            "Rendered [%s/%s/%s] %d animated sprites (accent=%s): %s",
            th["style"], choreo, scene.get("layout_mode"), len(sprites), accent, output_path
        )
        return True

    def illustrate_all(
        self,
        scenes: list[dict],
        output_dir: str,
        progress_callback=None,
    ) -> list[str]:
        paths: list[str] = []
        total = len(scenes)
        for i, sc in enumerate(scenes):
            sid = sc.get("scene_id", i + 1)
            title_slug = sc.get("scene_title", "scene").lower().replace(" ", "_")[:14]
            out = str(Path(output_dir) / f"scene{sid:02d}_{title_slug}.png")
            ok = self.illustrate(sc, out)
            paths.append(out if ok else "")
            if progress_callback:
                try:
                    progress_callback(i + 1, total)
                except Exception:
                    pass
        return paths
