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

from engine.text_sanitizer import VisualTextSanitizer

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
    sanitized = VisualTextSanitizer.sanitize_label(text, default="")
    clean = " ".join((sanitized or "").split())
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
    is_female: bool = False,
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

    # Female Stickman: delicate curved cartoon eyelashes + stylish ponytail with ribbon!
    if is_female:
        for eye_x in (cx - int(9 * scale), cx + int(9 * scale)):
            lash_d = 1 if eye_x > cx else -1
            draw.line([(eye_x + lash_d * 4 * scale, eye_y - 2 * scale), (eye_x + lash_d * 10 * scale, eye_y - 6 * scale)], fill=ink, width=max(2, int(2.5 * scale)))
            draw.line([(eye_x + lash_d * 2 * scale, eye_y - 4 * scale), (eye_x + lash_d * 7 * scale, eye_y - 9 * scale)], fill=ink, width=max(2, int(2.2 * scale)))

        # Ponytail with ribbon
        tie_x, tie_y = cx - int(head_r * 0.75), cy - int(head_r * 0.25)
        draw.ellipse([tie_x - 5 * scale, tie_y - 5 * scale, tie_x + 5 * scale, tie_y + 5 * scale], fill=accent_color)
        pony_pts = [
            (tie_x, tie_y),
            (tie_x - int(24 * scale), tie_y + int(8 * scale)),
            (tie_x - int(38 * scale), tie_y + int(36 * scale)),
            (tie_x - int(30 * scale), tie_y + int(56 * scale)),
            (tie_x - int(18 * scale), tie_y + int(40 * scale)),
            (tie_x, tie_y + int(8 * scale)),
        ]
        draw.polygon(pony_pts, fill=ink)

    neck_y = cy + head_r
    torso_end_x = cx
    torso_bot_y = neck_y + torso_len

    if pose == "sprinting":
        torso_end_x = cx - int(28 * scale)
        torso_bot_y = neck_y + int(155 * scale)
        draw.arc([cx - 8, cy + 10, cx + 10, cy + 24], 0, 180, fill=ink, width=3)
        hand_line(draw, cx, neck_y, torso_end_x, torso_bot_y, seed=seed + 2, lw=lw, color=ink)

    if is_female:
        skirt_w = int(36 * scale)
        skirt_pts = [
            (cx - int(12 * scale), neck_y + int(45 * scale)),
            (cx + int(12 * scale), neck_y + int(45 * scale)),
            (cx + skirt_w, torso_bot_y + int(12 * scale)),
            (cx - skirt_w, torso_bot_y + int(12 * scale)),
        ]
        draw.polygon(skirt_pts, fill=accent_color, outline=ink, width=max(2, lw - 1))
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

    if is_female:
        skirt_w = int(36 * scale)
        skirt_pts = [
            (cx - int(12 * scale), neck_y + int(45 * scale)),
            (cx + int(12 * scale), neck_y + int(45 * scale)),
            (cx + skirt_w, torso_bot_y + int(12 * scale)),
            (cx - skirt_w, torso_bot_y + int(12 * scale)),
        ]
        draw.polygon(skirt_pts, fill=accent_color, outline=ink, width=max(2, lw - 1))

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
    """Draw clean anti-aliased vector props covering all 12 multi-domain niches."""
    pk = (prop_kind or "spark").lower()
    tint = soft_tint_bg(accent, 0.26, base_hex=card_bg)

    # 1. Wealth & Business
    if pk in ("coin", "money", "dollar", "wealth"):
        hand_circle(draw, cx, cy, r, seed=seed, lw=5, color=ink, fill=tint)
        hand_circle(draw, cx, cy, int(r * 0.72), seed=seed + 1, lw=3, color=accent)
        draw_fitted_text(draw, "$", cx, cy, max_w=int(r * 1.1), target_size=max(26, int(r * 0.9)), family="noto", fill=ink, bold=True)
        return
    if pk in ("bull", "crypto", "bitcoin", "stocks"):
        # Bullish candlestick chart + arrow
        bw, bh = int(r * 1.5), int(r * 1.2)
        hand_rect(draw, cx - bw // 2, cy - bh // 2, bw, bh, seed=seed, lw=4, color=ink, fill=card_bg, r=12)
        # Green & red candle bars
        c_w = bw // 5
        draw.line([cx - c_w * 1.5, cy + bh // 3, cx - c_w * 1.5, cy - bh // 3], fill=ink, width=2)
        draw.rectangle([cx - c_w * 1.8, cy - bh // 8, cx - c_w * 1.2, cy + bh // 6], fill=ACCENT_CORAL, outline=ink, width=2)
        draw.line([cx, cy + bh // 2.5, cx, cy - bh // 2.5], fill=ink, width=2)
        draw.rectangle([cx - c_w * 0.3, cy - bh // 3, cx + c_w * 0.3, cy + bh // 8], fill=ACCENT_GREEN, outline=ink, width=2)
        draw.line([cx + c_w * 1.5, cy + bh // 4, cx + c_w * 1.5, cy - bh // 2.2], fill=ink, width=2)
        draw.rectangle([cx + c_w * 1.2, cy - bh // 2.4, cx + c_w * 1.8, cy - bh // 8], fill=ACCENT_GREEN, outline=ink, width=2)
        return
    if pk in ("vault", "safe", "bank"):
        hw, hh = int(r * 1.2), int(r * 1.1)
        hand_rect(draw, cx - hw, cy - hh, hw * 2, hh * 2, seed=seed, lw=5, color=ink, fill=card_bg, r=16)
        hand_circle(draw, cx, cy, int(r * 0.55), seed=seed + 1, lw=4, color=ink, fill=tint)
        # Safe wheel spokes
        for ang in (0, 60, 120):
            rad = math.radians(ang)
            dx = int(math.cos(rad) * r * 0.45)
            dy = int(math.sin(rad) * r * 0.45)
            draw.line([cx - dx, cy - dy, cx + dx, cy + dy], fill=accent, width=4)
        return

    # 2. Tech & Code
    if pk in ("code", "terminal", "developer"):
        tw, th = int(r * 1.4), int(r * 1.0)
        hand_rect(draw, cx - tw // 2, cy - th // 2, tw, th, seed=seed, lw=4, color=ink, fill=card_bg, r=10)
        # Window bar dots
        draw.ellipse([cx - tw // 2 + 10, cy - th // 2 + 8, cx - tw // 2 + 18, cy - th // 2 + 16], fill=ACCENT_CORAL)
        draw.ellipse([cx - tw // 2 + 24, cy - th // 2 + 8, cx - tw // 2 + 32, cy - th // 2 + 16], fill=ACCENT_GOLD)
        draw.ellipse([cx - tw // 2 + 38, cy - th // 2 + 8, cx - tw // 2 + 46, cy - th // 2 + 16], fill=ACCENT_GREEN)
        # Code brackets </ >
        draw_fitted_text(draw, "</>", cx, cy + 6, max_w=tw - 20, target_size=max(22, int(r * 0.65)), family="noto", fill=accent, bold=True)
        return
    if pk in ("cpu", "chip", "processor", "ai"):
        cw = int(r * 1.2)
        hand_rect(draw, cx - cw // 2, cy - cw // 2, cw, cw, seed=seed, lw=4, color=ink, fill=tint, r=8)
        hand_rect(draw, cx - cw // 3, cy - cw // 3, cw * 2 // 3, cw * 2 // 3, seed=seed + 1, lw=3, color=accent, fill=card_bg, r=4)
        # Pins
        for d in (-cw // 3, 0, cw // 3):
            draw.line([cx + d, cy - cw // 2 - 8, cx + d, cy - cw // 2], fill=ink, width=3)
            draw.line([cx + d, cy + cw // 2, cx + d, cy + cw // 2 + 8], fill=ink, width=3)
            draw.line([cx - cw // 2 - 8, cy + d, cx - cw // 2, cy + d], fill=ink, width=3)
            draw.line([cx + cw // 2, cy + d, cx + cw // 2 + 8, cy + d], fill=ink, width=3)
        return

    # 3. Fitness & Health
    if pk in ("dumbbell", "gym", "barbell", "workout"):
        dw, dh = int(r * 1.6), int(r * 0.8)
        # Bar
        hand_line(draw, cx - dw // 2, cy, cx + dw // 2, cy, seed=seed, lw=6, color=ink)
        # Heavy plates
        hand_rect(draw, cx - dw // 2 - 14, cy - dh // 2, 14, dh, seed=seed + 1, lw=4, color=ink, fill=accent, r=4)
        hand_rect(draw, cx - dw // 2, cy - int(dh * 0.4), 10, int(dh * 0.8), seed=seed + 2, lw=3, color=ink, fill=tint, r=3)
        hand_rect(draw, cx + dw // 2 + 4, cy - dh // 2, 14, dh, seed=seed + 3, lw=4, color=ink, fill=accent, r=4)
        hand_rect(draw, cx + dw // 2 - 10, cy - int(dh * 0.4), 10, int(dh * 0.8), seed=seed + 4, lw=3, color=ink, fill=tint, r=3)
        return
    if pk in ("heart_pulse", "ecg", "cardio"):
        draw_icon_heart(draw, cx, cy, accent=accent, ink=ink, card_bg=card_bg)
        # ECG zig-zag overlay
        draw.line([cx - r // 2, cy, cx - r // 5, cy, cx - r // 10, cy - r // 3, cx + r // 10, cy + r // 3, cx + r // 5, cy, cx + r // 2, cy], fill=card_bg, width=4)
        return

    # 4. Science & Space
    if pk in ("atom", "quantum", "physics"):
        hand_circle(draw, cx, cy, int(r * 0.35), seed=seed, lw=4, color=ink, fill=accent)
        # Elliptical orbits
        draw.arc([cx - r, cy - int(r * 0.4), cx + r, cy + int(r * 0.4)], 0, 360, fill=ink, width=3)
        draw.arc([cx - int(r * 0.5), cy - r, cx + int(r * 0.5), cy + r], 0, 360, fill=accent, width=3)
        return
    if pk in ("rocket", "space", "launch"):
        # Sleek rocket
        draw.polygon([(cx, cy - r), (cx + int(r * 0.4), cy + int(r * 0.4)), (cx - int(r * 0.4), cy + int(r * 0.4))], fill=card_bg, outline=ink)
        hand_circle(draw, cx, cy - int(r * 0.1), int(r * 0.2), seed=seed, lw=3, color=ink, fill=tint)
        # Exhaust plume
        draw.polygon([(cx - int(r * 0.25), cy + int(r * 0.4)), (cx, cy + r), (cx + int(r * 0.25), cy + int(r * 0.4))], fill=ACCENT_CORAL)
        return
    if pk in ("dna", "helix", "gene"):
        # Vertical double helix
        for i in range(-4, 5):
            y_pos = cy + int(i * r * 0.22)
            shift = math.sin(i * 0.8) * r * 0.5
            draw.line([cx - int(shift), y_pos, cx + int(shift), y_pos], fill=accent, width=4)
            draw.ellipse([cx - int(shift) - 4, y_pos - 4, cx - int(shift) + 4, y_pos + 4], fill=ink)
            draw.ellipse([cx + int(shift) - 4, y_pos - 4, cx + int(shift) + 4, y_pos + 4], fill=ink)
        return

    # 5. Stoicism & History
    if pk in ("pillar", "column", "ancient"):
        pw, ph = int(r * 0.8), int(r * 1.5)
        # Capital top
        hand_rect(draw, cx - pw // 2 - 8, cy - ph // 2, pw + 16, 16, seed=seed, lw=4, color=ink, fill=tint, r=4)
        # Shaft
        hand_rect(draw, cx - pw // 2, cy - ph // 2 + 16, pw, ph - 32, seed=seed + 1, lw=4, color=ink, fill=card_bg, r=2)
        # Vertical fluting
        for dx in (-pw // 4, 0, pw // 4):
            draw.line([cx + dx, cy - ph // 2 + 20, cx + dx, cy + ph // 2 - 20], fill=ink, width=2)
        # Base bottom
        hand_rect(draw, cx - pw // 2 - 8, cy + ph // 2 - 16, pw + 16, 16, seed=seed + 2, lw=4, color=ink, fill=tint, r=4)
        return
    if pk in ("sword", "battle"):
        draw.line([cx, cy - r, cx, cy + int(r * 0.6)], fill=ink, width=6)
        draw.line([cx - int(r * 0.4), cy + int(r * 0.3), cx + int(r * 0.4), cy + int(r * 0.3)], fill=accent, width=5)
        hand_circle(draw, cx, cy + int(r * 0.75), int(r * 0.15), seed=seed, lw=3, color=ink, fill=tint)
        return
    if pk in ("scroll", "parchment"):
        sw, sh = int(r * 1.3), int(r * 1.0)
        hand_rect(draw, cx - sw // 2, cy - sh // 2, sw, sh, seed=seed, lw=4, color=ink, fill=card_bg, r=10)
        for dy in (-sh // 4, 0, sh // 4):
            hand_line(draw, cx - sw // 3, cy + dy, cx + sw // 3, cy + dy, seed=seed + dy, lw=3, color=ink)
        return

    # 6. Productivity & Everyday
    if pk in ("timer", "stopwatch"):
        hand_circle(draw, cx, cy, r, seed=seed, lw=5, color=ink, fill=card_bg)
        draw.pieslice([cx - r + 8, cy - r + 8, cx + r - 8, cy + r - 8], -90, 30, fill=tint, outline=accent, width=2)
        hand_line(draw, cx, cy, cx, cy - int(r * 0.65), seed=seed + 1, lw=5, color=accent)
        draw.line([cx, cy - r - 8, cx, cy - r], fill=ink, width=5)
        return
    if pk in ("target", "bullseye"):
        hand_circle(draw, cx, cy, r, seed=seed, lw=5, color=ink, fill=card_bg)
        hand_circle(draw, cx, cy, int(r * 0.65), seed=seed + 1, lw=4, color=accent, fill=tint)
        hand_circle(draw, cx, cy, int(r * 0.3), seed=seed + 2, lw=4, color=ink, fill=accent)
        return
    if pk in ("coffee", "caffeine"):
        cw, ch = int(r * 1.1), int(r * 1.2)
        hand_rect(draw, cx - cw // 2, cy - ch // 4, cw, ch * 3 // 4, seed=seed, lw=4, color=ink, fill=card_bg, r=8)
        # Handle
        draw.arc([cx + cw // 2 - 8, cy - ch // 8, cx + cw // 2 + 20, cy + ch // 3], -90, 90, fill=ink, width=4)
        # Steam waves
        for ox in (-cw // 4, 0, cw // 4):
            hand_curve(draw, [(cx + ox, cy - ch // 4 - 4), (cx + ox + 6, cy - ch // 4 - 18), (cx + ox - 4, cy - ch // 4 - 32)], seed=seed + ox, lw=3, color=accent)
        return
    if pk in ("battery", "energy", "charge"):
        bw, bh = int(r * 0.9), int(r * 1.5)
        hand_rect(draw, cx - bw // 2, cy - bh // 2 + 10, bw, bh - 10, seed=seed, lw=4, color=ink, fill=card_bg, r=10)
        hand_rect(draw, cx - bw // 4, cy - bh // 2, bw // 2, 10, seed=seed + 1, lw=3, color=ink, fill=tint, r=3)
        # Green charge fill
        fill_h = int((bh - 24) * 0.75)
        draw.rectangle([cx - bw // 2 + 6, cy + bh // 2 - 6 - fill_h, cx + bw // 2 - 6, cy + bh // 2 - 6], fill=ACCENT_GREEN)
        return
    if pk in ("iceberg", "depth"):
        # Waterline
        draw.line([cx - r * 1.2, cy, cx + r * 1.2, cy], fill=accent, width=4)
        # Tip
        draw.polygon([(cx - r // 3, cy), (cx, cy - r // 2), (cx + r // 3, cy)], fill=card_bg, outline=ink)
        # Massive submerged base
        draw.polygon([(cx - r // 3, cy), (cx + r // 3, cy), (cx + r * 0.9, cy + r * 0.9), (cx - r * 0.9, cy + r * 0.9)], fill=tint, outline=ink)
        return
    if pk in ("chess", "checkmate"):
        # Pawn / Queen crown
        pts = [(cx - r // 2, cy + r // 2), (cx - r // 3, cy - r // 4), (cx, cy - r // 2), (cx + r // 3, cy - r // 4), (cx + r // 2, cy + r // 2)]
        draw.polygon(pts, fill=card_bg, outline=ink)
        hand_circle(draw, cx, cy - r // 2 - 8, r // 4, seed=seed, lw=3, color=ink, fill=accent)
        return

    # Classical Props
    if pk == "heart":
        draw_icon_heart(draw, cx, cy, accent=accent, ink=ink, card_bg=card_bg)
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

    # Check 1,000+ procedural object engine
    try:
        from engine.procedural_object_engine import ProceduralObjectEngine
        drawn = ProceduralObjectEngine.draw_object(
            draw=draw,
            asset_name=pk,
            x=cx - r,
            y=cy - r,
            w=r * 2,
            h=r * 2,
            color=accent,
            ink=ink,
            line_width=4,
            seed=seed,
        )
        if drawn:
            return
    except Exception:
        pass

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


def _choreo_lighthouse_fog_beam(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Lighthouse beacon slicing through fog with alternating signals & overthinking stickman."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 301))
    sprites: dict[str, Any] = {}

    # Overthinking stickman gazing right
    im_h, dh = _make_sprite(300, 440)
    draw_stickman_figure(dh, 150, 80, scale=1.0, pose="anxious", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "seeker", im_h, out_dir, prefix)

    # Lighthouse tower
    im_lh, dlh = _make_sprite(220, 480)
    hand_rect(dlh, 30, 80, 160, 380, seed=seed + 1, lw=5, color=ink, fill=card_bg, r=10)
    # Lantern room at top
    hand_rect(dlh, 45, 20, 130, 60, seed=seed + 2, lw=4, color=accent, fill=soft_tint_bg(accent, 0.35, card_bg), r=8)
    _save_sprite(sprites, "lighthouse", im_lh, out_dir, prefix)

    # Beam bands
    im_beam, db = _make_sprite(520, 220)
    hand_rect(db, 10, 10, 500, 95, seed=seed + 3, lw=3, color=accent, fill=soft_tint_bg(accent, 0.22, card_bg), r=18)
    draw_fitted_text(db, "+ WARMTH (1 DAY)", 260, 58, max_w=460, target_size=30, family="noto", fill=accent, bold=True)
    hand_rect(db, 10, 115, 500, 95, seed=seed + 4, lw=3, color=muted, fill=card_bg, r=18)
    draw_fitted_text(db, "- SILENCE (5 DAYS)", 260, 162, max_w=460, target_size=30, family="noto", fill=muted, bold=True)
    _save_sprite(sprites, "beam_labels", im_beam, out_dir, prefix)

    sprite_plan = [
        {"sprite": "lighthouse", "anim": "pop_bounce", "cx0": 980, "cy0": 1000, "w": 220, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "beam_labels", "anim": "slide_in", "cx0": 600, "cy0": 900, "cx1": 600, "cy1": 950, "w": 520, "from_f": 0.10, "to_f": 1.0},
        {"sprite": "seeker", "anim": "pop_bounce", "cx0": 240, "cy0": 1050, "w": 300, "from_f": 0.0, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "x": 100, "y": 1280, "w": 880, "points": [[0, 0], [880, 0]], "color": ink, "lw": 4, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_dopamine_spike_chart(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Neuro-pathway comparison: steady affection vs unpredictable dopamine jackpot."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 311))
    sprites: dict[str, Any] = {}

    # Left card: Predictable
    im_c1, dc1 = _make_sprite(420, 360)
    hand_rect(dc1, 10, 10, 400, 340, seed=seed, lw=4, color=muted, fill=card_bg, r=20, shadow=True)
    draw_fitted_text(dc1, "PREDICTABLE AFFECTION", 210, 50, max_w=370, target_size=24, family="noto", fill=muted, bold=True)
    draw_fitted_text(dc1, "Safe, steady rhythm", 210, 95, max_w=360, target_size=20, family="noto", fill=muted)
    # Flat calm line
    dc1.line([(40, 220), (380, 220)], fill=rgba(muted, 200), width=4)
    draw_fitted_text(dc1, "Result: Safe (No Urgency)", 210, 290, max_w=360, target_size=18, family="noto", fill=muted)
    _save_sprite(sprites, "card_steady", im_c1, out_dir, prefix)

    # Right card: Intermittent Jackpot
    im_c2, dc2 = _make_sprite(420, 360)
    hand_rect(dc2, 10, 10, 400, 340, seed=seed + 1, lw=5, color=accent, fill=card_bg, r=20, shadow=True)
    draw_fitted_text(dc2, "INTERMITTENT SIGNALS", 210, 50, max_w=370, target_size=24, family="noto", fill=accent, bold=True)
    draw_fitted_text(dc2, "DOPAMINE JACKPOT!", 210, 95, max_w=360, target_size=22, family="noto", fill=accent, bold=True)
    # Spiky erratic wave
    spike_pts = [(40, 230), (100, 210), (160, 130), (220, 250), (280, 120), (340, 230), (380, 210)]
    dc2.line(spike_pts, fill=rgba(accent, 255), width=5)
    draw_fitted_text(dc2, "Result: Intense Cognitive Loop", 210, 290, max_w=360, target_size=18, family="noto", fill=accent)
    _save_sprite(sprites, "card_jackpot", im_c2, out_dir, prefix)

    # Central VS pill
    im_vs, dvs = _make_sprite(90, 90)
    dvs.ellipse([8, 8, 82, 82], fill=rgba(card_bg, 255), outline=rgba(ink, 255), width=3)
    draw_fitted_text(dvs, "VS", 45, 46, max_w=70, target_size=24, family="noto", fill=ink, bold=True)
    _save_sprite(sprites, "vs_badge", im_vs, out_dir, prefix)

    sprite_plan = [
        {"sprite": "card_steady", "anim": "slide_in", "cx0": 290, "cy0": 980, "cx1": 290, "cy1": 960, "w": 420, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "card_jackpot", "anim": "slide_in", "cx0": 790, "cy0": 980, "cx1": 790, "cy1": 960, "w": 420, "from_f": 0.12, "to_f": 1.0},
        {"sprite": "vs_badge", "anim": "pop_bounce", "cx0": 540, "cy0": 960, "w": 90, "from_f": 0.25, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_split_mirror_ideal(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Two-sided reality vs fantasy reflection with central mirror partition."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 325))
    sprites: dict[str, Any] = {}

    # Left: Cold Reality stickman
    im_r, dr = _make_sprite(300, 450)
    draw_stickman_figure(dr, 150, 80, scale=1.0, pose="anxious", accent_color=muted, ink=muted, head_fill=card_bg, seed=seed)
    _save_sprite(sprites, "figure_reality", im_r, out_dir, prefix)

    # Right: Warm Idealized Fantasy stickman with heart
    im_f, df = _make_sprite(300, 450)
    draw_stickman_figure(df, 150, 80, scale=1.02, pose="peaceful", accent_color=accent, ink=accent, head_fill=card_bg, seed=seed + 1)
    # Heart above head
    draw_icon_sparkle(df, 150, 36, 32, color=ACCENT_CORAL, ink=ACCENT_CORAL)
    _save_sprite(sprites, "figure_fantasy", im_f, out_dir, prefix)

    # Center mirror divider card
    im_m, dm = _make_sprite(110, 480)
    hand_rect(dm, 15, 15, 80, 450, seed=seed + 2, lw=4, color=ink, fill=card_bg, r=12)
    # Vertical text "MIRROR"
    letters = ["M", "I", "R", "R", "O", "R"]
    for i, lt in enumerate(letters):
        draw_fitted_text(dm, lt, 55, 60 + i * 65, max_w=40, target_size=28, family="noto", fill=ink, bold=True)
    _save_sprite(sprites, "mirror_frame", im_m, out_dir, prefix)

    sprite_plan = [
        {"sprite": "figure_reality", "anim": "slide_in", "cx0": 260, "cy0": 1020, "cx1": 270, "cy1": 1020, "w": 300, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "mirror_frame", "anim": "pop_bounce", "cx0": 540, "cy0": 1020, "w": 110, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "figure_fantasy", "anim": "slide_in", "cx0": 820, "cy0": 1020, "cx1": 810, "cy1": 1020, "w": 300, "from_f": 0.15, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_pedestal_bust_trap(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Sculpted bust of the past on elevated stone pedestal with heavy self-doubt anchor."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 337))
    sprites: dict[str, Any] = {}

    # Pedestal + Bust
    im_ped, dped = _make_sprite(380, 520)
    # Stone pedestal
    hand_rect(dped, 40, 200, 300, 300, seed=seed, lw=5, color=ink, fill=card_bg, r=16)
    draw_fitted_text(dped, "THE GHOST OF", 190, 270, max_w=270, target_size=22, family="noto", fill=muted, bold=True)
    draw_fitted_text(dped, "WHO THEY WERE", 190, 320, max_w=270, target_size=24, family="noto", fill=accent, bold=True)
    draw_fitted_text(dped, "AT THE BEGINNING", 190, 370, max_w=270, target_size=20, family="noto", fill=muted)
    # Sculpted bust on top
    dped.ellipse([140, 40, 240, 140], fill=rgba(card_bg, 255), outline=rgba(accent, 255), width=5)
    _save_sprite(sprites, "pedestal_bust", im_ped, out_dir, prefix)

    # Stickman kneeling / bowing with anchor
    im_h, dh = _make_sprite(320, 450)
    draw_stickman_figure(dh, 160, 80, scale=0.98, pose="anxious", accent_color=muted, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "seeker_anchor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "seeker_anchor", "anim": "pop_bounce", "cx0": 310, "cy0": 1040, "w": 320, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "pedestal_bust", "anim": "slide_in", "cx0": 780, "cy0": 1060, "cx1": 780, "cy1": 1000, "w": 380, "from_f": 0.12, "to_f": 1.0},
    ]
    vector_plan = [
        {"kind": "line", "x": 100, "y": 1280, "w": 880, "points": [[0, 0], [880, 0]], "color": ink, "lw": 4, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, vector_plan


def _choreo_protective_couple_shield(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Stickman couple encircled by protective glowing emerald shield with green check badge."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 349))
    sprites: dict[str, Any] = {}

    # Couple holding hands (Male Alex & Female Maya with ponytail)
    im_cp, dcp = _make_sprite(420, 460)
    draw_stickman_figure(dcp, 140, 80, scale=0.98, pose="peaceful", accent_color=ACCENT_GREEN, ink=ink, head_fill=card_bg, seed=seed, is_female=False)
    draw_stickman_figure(dcp, 280, 80, scale=0.98, pose="peaceful", accent_color=ACCENT_GREEN, ink=ink, head_fill=card_bg, seed=seed + 1, is_female=True)
    # Green heart connecting them
    draw_icon_sparkle(dcp, 210, 180, 44, color=ACCENT_GREEN, ink=ACCENT_GREEN)
    _save_sprite(sprites, "couple", im_cp, out_dir, prefix)

    # Protective aura shield
    im_sh, dsh = _make_sprite(520, 520)
    dsh.ellipse([20, 20, 500, 500], fill=rgba(soft_tint_bg(ACCENT_GREEN, 0.12, card_bg), 180), outline=rgba(ACCENT_GREEN, 240), width=6)
    _save_sprite(sprites, "shield_aura", im_sh, out_dir, prefix)

    # Top badges: Red X (Addiction) vs Green Check (Security)
    im_b1, db1 = _make_sprite(360, 100)
    hand_rect(db1, 10, 10, 340, 80, seed=seed + 3, lw=3, color=ACCENT_CORAL, fill=card_bg, r=16)
    draw_fitted_text(db1, "X  ADDICTION TO SCRAPS", 180, 50, max_w=310, target_size=24, family="noto", fill=ACCENT_CORAL, bold=True)
    _save_sprite(sprites, "badge_scraps", im_b1, out_dir, prefix)

    im_b2, db2 = _make_sprite(360, 100)
    hand_rect(db2, 10, 10, 340, 80, seed=seed + 4, lw=4, color=ACCENT_GREEN, fill=card_bg, r=16)
    draw_fitted_text(db2, "✓  REAL SECURITY", 180, 50, max_w=310, target_size=24, family="noto", fill=ACCENT_GREEN, bold=True)
    _save_sprite(sprites, "badge_security", im_b2, out_dir, prefix)

    sprite_plan = [
        {"sprite": "badge_scraps", "anim": "slide_in", "cx0": 300, "cy0": 680, "cx1": 300, "cy1": 720, "w": 360, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "badge_security", "anim": "slide_in", "cx0": 780, "cy0": 680, "cx1": 780, "cy1": 720, "w": 360, "from_f": 0.12, "to_f": 1.0},
        {"sprite": "shield_aura", "anim": "pop_bounce", "cx0": 540, "cy0": 1040, "w": 520, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "couple", "anim": "pop_bounce", "cx0": 540, "cy0": 1040, "w": 420, "from_f": 0.15, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


def _choreo_notification_fishhook(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Mobile notification card with curved fishing hook catching the emotional response."""
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 363))
    sprites: dict[str, Any] = {}

    # Whiplash Phase cards
    im_cards, dcd = _make_sprite(840, 220)
    # Phase 1: High
    hand_rect(dcd, 20, 20, 380, 180, seed=seed, lw=4, color=ACCENT_GREEN, fill=card_bg, r=18)
    draw_fitted_text(dcd, "PHASE 1: THE HIGH", 210, 60, max_w=340, target_size=24, family="noto", fill=ACCENT_GREEN, bold=True)
    draw_fitted_text(dcd, "Texting until 2:00 AM", 210, 110, max_w=340, target_size=22, family="noto", fill=ink)
    # Phase 2: Freeze
    hand_rect(dcd, 440, 20, 380, 180, seed=seed + 1, lw=4, color=ACCENT_CORAL, fill=card_bg, r=18)
    draw_fitted_text(dcd, "PHASE 2: DEEP FREEZE", 630, 60, max_w=340, target_size=24, family="noto", fill=ACCENT_CORAL, bold=True)
    draw_fitted_text(dcd, "Days of total silence", 630, 110, max_w=340, target_size=22, family="noto", fill=muted)
    _save_sprite(sprites, "phase_cards", im_cards, out_dir, prefix)

    # Stickman staring down at phone
    im_h, dh = _make_sprite(300, 440)
    draw_stickman_figure(dh, 150, 80, scale=1.0, pose="anxious", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 2)
    _save_sprite(sprites, "seeker_phone", im_h, out_dir, prefix)

    # Golden hooked text message: "Hey, I missed you..."
    im_hk, dhk = _make_sprite(520, 140)
    hand_rect(dhk, 15, 15, 490, 110, seed=seed + 3, lw=4, color=ACCENT_GOLD, fill=soft_tint_bg(ACCENT_GOLD, 0.25, card_bg), r=24)
    draw_fitted_text(dhk, '"Hey, I missed you..."', 260, 70, max_w=450, target_size=32, family="caveat", fill=ink, bold=True)
    _save_sprite(sprites, "hook_message", im_hk, out_dir, prefix)

    sprite_plan = [
        {"sprite": "phase_cards", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 720, "w": 840, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "seeker_phone", "anim": "pop_bounce", "cx0": 340, "cy0": 1080, "w": 300, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "hook_message", "anim": "slide_in", "cx0": 720, "cy0": 1150, "cx1": 720, "cy1": 1050, "w": 520, "from_f": 0.25, "to_f": 1.0},
    ]
    vector_plan = []
    return sprites, sprite_plan, vector_plan


# ---------------------------------------------------------------------------
# Universal Multi-Domain Choreography Generators (Atharv Hatwar)
# ---------------------------------------------------------------------------

def _choreo_crypto_market_rally(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg, muted = th["ink"], th["card_bg"], th["ink_muted"]
    seed = int(scene.get("variant_seed", 401))
    sprites: dict[str, Any] = {}

    # Market Rally Card with Green Candlestick Chart
    im_c, dc = _make_sprite(860, 420)
    hand_rect(dc, 20, 20, 820, 380, seed=seed, lw=4, color=ink, fill=card_bg, r=20)
    draw_fitted_text(dc, "MARKET SURGE: +480% GAIN", 430, 75, max_w=760, target_size=32, family="noto", fill=ACCENT_GREEN, bold=True)
    draw_semantic_prop(dc, "bull", 430, 230, 90, accent=ACCENT_GREEN, ink=ink, card_bg=card_bg, seed=seed)
    _save_sprite(sprites, "market_card", im_c, out_dir, prefix)

    # Celebrating Trader Stickman
    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="spotlight_crown", accent_color=ACCENT_GREEN, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "trader_actor", im_h, out_dir, prefix)

    # Gold Coins Badge
    im_coins, dcn = _make_sprite(420, 140)
    hand_rect(dcn, 10, 10, 400, 120, seed=seed + 2, lw=3, color=ACCENT_GOLD, fill=soft_tint_bg(ACCENT_GOLD, 0.25, card_bg), r=16)
    draw_semantic_prop(dcn, "coin", 80, 70, 36, accent=ACCENT_GOLD, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dcn, "CAPITAL COMPOUNDED", 250, 70, max_w=280, target_size=22, family="noto", fill=ink, bold=True)
    _save_sprite(sprites, "coins_badge", im_coins, out_dir, prefix)

    sprite_plan = [
        {"sprite": "market_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 720, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "trader_actor", "anim": "pop_bounce", "cx0": 340, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "coins_badge", "anim": "slide_in", "cx0": 740, "cy0": 1200, "cx1": 740, "cy1": 1120, "w": 420, "from_f": 0.2, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_terminal_code_deploy(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 402))
    sprites: dict[str, Any] = {}

    # Dark CLI Code Terminal Card
    im_t, dt = _make_sprite(880, 440)
    hand_rect(dt, 20, 20, 840, 400, seed=seed, lw=4, color="#10B981", fill="#0B131E", r=16)
    # Window Dots
    dt.ellipse([45, 45, 57, 57], fill="#EF4444")
    dt.ellipse([67, 45, 79, 57], fill="#F59E0B")
    dt.ellipse([89, 45, 101, 57], fill="#10B981")
    draw_fitted_text(dt, "dev_terminal: main.py", 440, 52, max_w=400, target_size=20, family="noto", fill="#64748B", bold=False)
    # Code syntax lines
    draw_fitted_text(dt, "def build_scalable_system(input_data):", 440, 130, max_w=760, target_size=26, family="noto", fill="#38BDF8", bold=True)
    draw_fitted_text(dt, "    architecture = optimize(input_data, concurrency=True)", 440, 185, max_w=760, target_size=22, family="noto", fill="#94A3B8")
    draw_fitted_text(dt, "    return ship_to_production(version='2.0')", 440, 240, max_w=760, target_size=22, family="noto", fill="#A78BFA")
    hand_rect(dt, 60, 310, 720, 70, seed=seed + 1, lw=2, color="#10B981", fill="#064E3B", r=10)
    draw_fitted_text(dt, "✓ 0 ERRORS • BUILD & DEPLOY SUCCESSFUL", 420, 345, max_w=680, target_size=24, family="noto", fill="#34D399", bold=True)
    _save_sprite(sprites, "code_terminal", im_t, out_dir, prefix)

    # Programmer Stickman at Work
    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pointing_cta", accent_color="#10B981", ink=ink, head_fill=card_bg, seed=seed + 2)
    _save_sprite(sprites, "coder_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "code_terminal", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 880, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "coder_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.1, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_dumbbell_gym_lift(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 403))
    sprites: dict[str, Any] = {}

    # Progressive Overload Meter Card
    im_c, dc = _make_sprite(860, 360)
    hand_rect(dc, 20, 20, 820, 320, seed=seed, lw=4, color=ink, fill=card_bg, r=20)
    draw_fitted_text(dc, "PROGRESSIVE OVERLOAD", 430, 70, max_w=760, target_size=32, family="noto", fill=ACCENT_CORAL, bold=True)
    draw_semantic_prop(dc, "dumbbell", 430, 190, 80, accent=ACCENT_CORAL, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dc, "Daily Resistance • Consistent Adaption", 430, 290, max_w=760, target_size=24, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "overload_card", im_c, out_dir, prefix)

    # Athlete Stickman
    im_h, dh = _make_sprite(340, 460)
    draw_stickman_figure(dh, 170, 80, scale=1.05, pose="climbing", accent_color=ACCENT_CORAL, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "athlete_actor", im_h, out_dir, prefix)

    # Health & Recovery Tag
    im_rec, dr = _make_sprite(420, 130)
    hand_rect(dr, 10, 10, 400, 110, seed=seed + 2, lw=3, color=ACCENT_GREEN, fill=soft_tint_bg(ACCENT_GREEN, 0.22, card_bg), r=16)
    draw_semantic_prop(dr, "heart_pulse", 70, 65, 34, accent=ACCENT_GREEN, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dr, "HYDRATION & REPAIR", 250, 65, max_w=280, target_size=22, family="noto", fill=ink, bold=True)
    _save_sprite(sprites, "recovery_tag", im_rec, out_dir, prefix)

    sprite_plan = [
        {"sprite": "overload_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "athlete_actor", "anim": "pop_bounce", "cx0": 340, "cy0": 1140, "w": 340, "from_f": 0.0, "to_f": 1.0},
        {"sprite": "recovery_tag", "anim": "slide_in", "cx0": 740, "cy0": 1200, "cx1": 740, "cy1": 1120, "w": 420, "from_f": 0.2, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_atom_quantum_orbit(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 404))
    sprites: dict[str, Any] = {}

    # Quantum Physics Orb Card
    im_a, da = _make_sprite(860, 420)
    hand_rect(da, 20, 20, 820, 380, seed=seed, lw=4, color="#38BDF8", fill=card_bg, r=20)
    draw_fitted_text(da, "SUBATOMIC SCALE & QUANTUM ENTANGLEMENT", 430, 75, max_w=780, target_size=28, family="noto", fill="#0284C7", bold=True)
    draw_semantic_prop(da, "atom", 430, 230, 100, accent="#38BDF8", ink=ink, card_bg=card_bg, seed=seed)
    _save_sprite(sprites, "quantum_card", im_a, out_dir, prefix)

    # Scientist Stickman
    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pondering", accent_color="#38BDF8", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "scientist_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "quantum_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 720, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "scientist_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_stoic_pillar_stand(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 405))
    sprites: dict[str, Any] = {}

    # Stoic Ancient Pillars Card
    im_p, dp = _make_sprite(860, 420)
    hand_rect(dp, 20, 20, 820, 380, seed=seed, lw=4, color=ink, fill=card_bg, r=18)
    draw_fitted_text(dp, "IMMOVABLE ROCK AGAINST THE STORM", 430, 70, max_w=760, target_size=30, family="noto", fill=ACCENT_GOLD, bold=True)
    draw_semantic_prop(dp, "pillar", 250, 240, 80, accent=ACCENT_GOLD, ink=ink, card_bg=card_bg, seed=seed)
    draw_semantic_prop(dp, "pillar", 610, 240, 80, accent=ACCENT_GOLD, ink=ink, card_bg=card_bg, seed=seed + 1)
    draw_fitted_text(dp, "Control Internal Response • Endure Outside Events", 430, 350, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "stoic_card", im_p, out_dir, prefix)

    # Peaceful Resolute Stickman
    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="peaceful", accent_color=ACCENT_GOLD, ink=ink, head_fill=card_bg, seed=seed + 2)
    _save_sprite(sprites, "stoic_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "stoic_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "stoic_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1140, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_compound_interest_snowball(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 406))
    sprites: dict[str, Any] = {}

    # Hockey stick compounding curve
    im_c, dc = _make_sprite(860, 400)
    hand_rect(dc, 20, 20, 820, 360, seed=seed, lw=4, color=ACCENT_GREEN, fill=card_bg, r=20)
    draw_fitted_text(dc, "THE EXPONENTIAL SNOWBALL CURVE", 430, 70, max_w=760, target_size=32, family="noto", fill=ACCENT_GREEN, bold=True)
    # Draw curve
    curve_pts = [(80, 300), (280, 290), (460, 260), (620, 180), (760, 110)]
    for i in range(len(curve_pts) - 1):
        dc.line([curve_pts[i], curve_pts[i + 1]], fill=ACCENT_GREEN, width=6)
    draw_fitted_text(dc, "Year 1-5: Boring Grind  →  Year 10+: Explosive Freedom", 430, 335, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "snowball_curve", im_c, out_dir, prefix)

    # Investor Stickman pushing boulder
    im_h, dh = _make_sprite(340, 440)
    draw_stickman_figure(dh, 170, 80, scale=1.0, pose="sprinting", accent_color=ACCENT_GREEN, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "snowball_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "snowball_curve", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "snowball_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 340, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_focus_pomodoro_timer(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 407))
    sprites: dict[str, Any] = {}

    # Giant Timer & Focus Dial
    im_t, dt = _make_sprite(860, 400)
    hand_rect(dt, 20, 20, 820, 360, seed=seed, lw=4, color=ACCENT_CORAL, fill=card_bg, r=20)
    draw_fitted_text(dt, "UNINTERRUPTED DEEP FOCUS (25 MIN)", 430, 70, max_w=760, target_size=30, family="noto", fill=ACCENT_CORAL, bold=True)
    draw_semantic_prop(dt, "timer", 430, 210, 85, accent=ACCENT_CORAL, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dt, "Phone Muted • Clutter Eliminated • Single-Tasking", 430, 330, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "pomodoro_card", im_t, out_dir, prefix)

    # Focused Stickman
    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="shielding", accent_color=ACCENT_CORAL, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "focus_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "pomodoro_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "focus_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_neural_net_synapse(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 408))
    sprites: dict[str, Any] = {}

    im_n, dn = _make_sprite(860, 420)
    hand_rect(dn, 20, 20, 820, 380, seed=seed, lw=4, color="#38BDF8", fill=card_bg, r=20)
    draw_fitted_text(dn, "NEURAL NETWORK & SYNAPSE ACCELERATION", 430, 70, max_w=760, target_size=28, family="noto", fill="#0284C7", bold=True)
    # Draw neural nodes & edges
    layers = [
        [(150, 160), (150, 240), (150, 320)],
        [(340, 180), (340, 260), (340, 340)],
        [(520, 180), (520, 260), (520, 340)],
        [(710, 210), (710, 290)],
    ]
    for li in range(len(layers) - 1):
        for p1 in layers[li]:
            for p2 in layers[li + 1]:
                dn.line([p1, p2], fill="#CBD5E1", width=2)
    for l in layers:
        for p in l:
            dn.ellipse([p[0] - 12, p[1] - 12, p[0] + 12, p[1] + 12], fill="#38BDF8", outline=ink, width=3)
    _save_sprite(sprites, "neural_graph", im_n, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pondering", accent_color="#38BDF8", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "ai_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "neural_graph", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "ai_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_iceberg_hidden_depth(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 409))
    sprites: dict[str, Any] = {}

    im_i, di = _make_sprite(860, 440)
    hand_rect(di, 20, 20, 820, 400, seed=seed, lw=4, color="#0284C7", fill=card_bg, r=20)
    draw_fitted_text(di, "THE ICEBERG OF MASTERY", 430, 65, max_w=760, target_size=32, family="noto", fill="#0284C7", bold=True)
    draw_semantic_prop(di, "iceberg", 430, 240, 100, accent="#0284C7", ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(di, "10% What People See: Glory  |  90% Unseen Work: Sweat & Solitude", 430, 375, max_w=760, target_size=20, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "iceberg_card", im_i, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pointing_cta", accent_color="#0284C7", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "observer_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "iceberg_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "observer_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_hamster_wheel_break(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 410))
    sprites: dict[str, Any] = {}

    im_w, dw = _make_sprite(860, 400)
    hand_rect(dw, 20, 20, 820, 360, seed=seed, lw=4, color=ACCENT_CORAL, fill=card_bg, r=20)
    draw_fitted_text(dw, "BREAKING OUT OF THE RAT RACE", 430, 65, max_w=760, target_size=32, family="noto", fill=ACCENT_CORAL, bold=True)
    # Large wheel outline
    hand_circle(dw, 430, 210, 85, seed=seed, lw=5, color=ink, fill=None)
    for ang in range(0, 360, 45):
        rad = math.radians(ang)
        dw.line([430, 210, 430 + int(math.cos(rad) * 85), 210 + int(math.sin(rad) * 85)], fill=accent, width=3)
    draw_fitted_text(dw, "Endless Cycle Ended  →  Ownership & Autonomy", 430, 340, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "wheel_card", im_w, out_dir, prefix)

    im_h, dh = _make_sprite(340, 440)
    draw_stickman_figure(dh, 170, 80, scale=1.0, pose="sprinting", accent_color=ACCENT_CORAL, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "leaper_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "wheel_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "leaper_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 340, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_chess_checkmate_move(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 411))
    sprites: dict[str, Any] = {}

    im_c, dc = _make_sprite(860, 400)
    hand_rect(dc, 20, 20, 820, 360, seed=seed, lw=4, color=ACCENT_GOLD, fill=card_bg, r=20)
    draw_fitted_text(dc, "GRANDMASTER STRATEGY: CHECKMATE", 430, 65, max_w=760, target_size=30, family="noto", fill=ACCENT_GOLD, bold=True)
    draw_semantic_prop(dc, "chess", 430, 200, 80, accent=ACCENT_GOLD, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dc, "Think Three Moves Ahead • Play the Long Game", 430, 335, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "chess_card", im_c, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="spotlight_crown", accent_color=ACCENT_GOLD, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "master_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "chess_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "master_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_battery_supercharge(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 412))
    sprites: dict[str, Any] = {}

    im_b, db = _make_sprite(860, 400)
    hand_rect(db, 20, 20, 820, 360, seed=seed, lw=4, color=ACCENT_GREEN, fill=card_bg, r=20)
    draw_fitted_text(db, "RECHARGING TO 100% PEAK POWER", 430, 65, max_w=760, target_size=32, family="noto", fill=ACCENT_GREEN, bold=True)
    draw_semantic_prop(db, "battery", 430, 200, 80, accent=ACCENT_GREEN, ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(db, "Full Physical & Mental Energy Restored", 430, 335, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "battery_card", im_b, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="climbing", accent_color=ACCENT_GREEN, ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "charged_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "battery_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "charged_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_rocket_launchpad_stage(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 413))
    sprites: dict[str, Any] = {}

    im_r, dr = _make_sprite(860, 420)
    hand_rect(dr, 20, 20, 820, 380, seed=seed, lw=4, color="#F59E0B", fill=card_bg, r=20)
    draw_fitted_text(dr, "LAUNCH SEQUENCE: REACHING ESCAPE VELOCITY", 430, 65, max_w=780, target_size=28, family="noto", fill="#D97706", bold=True)
    draw_semantic_prop(dr, "rocket", 430, 230, 95, accent="#F59E0B", ink=ink, card_bg=card_bg, seed=seed)
    _save_sprite(sprites, "rocket_card", im_r, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="spotlight_crown", accent_color="#F59E0B", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "commander_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "rocket_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "commander_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_scales_of_justice(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 414))
    sprites: dict[str, Any] = {}

    im_s, ds = _make_sprite(860, 400)
    hand_rect(ds, 20, 20, 820, 360, seed=seed, lw=4, color=ink, fill=card_bg, r=20)
    draw_fitted_text(ds, "SCALES OF TRUTH & REALITY", 430, 65, max_w=760, target_size=32, family="noto", fill=ACCENT_GOLD, bold=True)
    # Fulcrum and pans
    ds.line([430, 130, 430, 270], fill=ink, width=6)
    ds.line([250, 160, 610, 200], fill=accent, width=6)
    ds.polygon([(410, 310), (450, 310), (430, 270)], fill=ink)
    # Left pan (Truth - heavy)
    ds.line([250, 160, 220, 240], fill=ink, width=3)
    ds.line([250, 160, 280, 240], fill=ink, width=3)
    hand_rect(ds, 200, 240, 100, 20, seed=seed, lw=3, color=ink, fill=ACCENT_GREEN, r=6)
    draw_fitted_text(ds, "FACTS", 250, 250, max_w=80, target_size=18, family="noto", fill=WHITE, bold=True)
    # Right pan (Illusion - light)
    ds.line([610, 200, 580, 260], fill=ink, width=3)
    ds.line([610, 200, 640, 260], fill=ink, width=3)
    hand_rect(ds, 560, 260, 100, 20, seed=seed + 1, lw=3, color=ink, fill=ACCENT_CORAL, r=6)
    draw_fitted_text(ds, "NOISE", 610, 270, max_w=80, target_size=18, family="noto", fill=WHITE, bold=True)
    _save_sprite(sprites, "scales_card", im_s, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pointing_cta", accent_color=ACCENT_GOLD, ink=ink, head_fill=card_bg, seed=seed + 2)
    _save_sprite(sprites, "judge_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "scales_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "judge_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_puzzle_assembly(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 415))
    sprites: dict[str, Any] = {}

    im_p, dp = _make_sprite(860, 400)
    hand_rect(dp, 20, 20, 820, 360, seed=seed, lw=4, color="#1D70B8", fill=card_bg, r=20)
    draw_fitted_text(dp, "THE MISSING PIECE SNAPS INTO PLACE", 430, 65, max_w=760, target_size=30, family="noto", fill="#1D70B8", bold=True)
    # 2x2 Jigsaw Puzzle layout
    pw = 120
    for r_i in (0, 1):
        for c_i in (0, 1):
            px = 330 + c_i * (pw + 10)
            py = 140 + r_i * (pw + 10)
            is_gold = (r_i == 1 and c_i == 1)
            fill_c = ACCENT_GOLD if is_gold else soft_tint_bg(accent, 0.2, card_bg)
            hand_rect(dp, px, py, pw, pw, seed=seed + r_i * 2 + c_i, lw=3, color=ink, fill=fill_c, r=10)
    draw_fitted_text(dp, "Everything Connects • Complete Pattern Revealed", 430, 345, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "puzzle_card", im_p, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pondering", accent_color="#1D70B8", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "solver_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "puzzle_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "solver_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_radar_scanner_sweep(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 416))
    sprites: dict[str, Any] = {}

    im_r, dr = _make_sprite(860, 420)
    hand_rect(dr, 20, 20, 820, 380, seed=seed, lw=4, color="#10B981", fill="#0A1612", r=20)
    draw_fitted_text(dr, "HIGH-VALUE TARGET ACQUISITION", 430, 65, max_w=760, target_size=30, family="noto", fill="#10B981", bold=True)
    # Radar Grid
    rcx, rcy = 430, 230
    for rad in (40, 80, 120):
        dr.ellipse([rcx - rad, rcy - rad, rcx + rad, rcy + rad], outline="#10B981", width=2)
    dr.line([rcx - 130, rcy, rcx + 130, rcy], fill="#047857", width=2)
    dr.line([rcx, rcy - 130, rcx, rcy + 130], fill="#047857", width=2)
    # Sweep beam
    dr.pieslice([rcx - 120, rcy - 120, rcx + 120, rcy + 120], 30, 75, fill="#065F46", outline="#34D399", width=2)
    # Target Blip
    dr.ellipse([rcx + 60, rcy - 50, rcx + 72, rcy - 38], fill="#F59E0B")
    _save_sprite(sprites, "radar_screen", im_r, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pointing_cta", accent_color="#10B981", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "radar_operator", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "radar_screen", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "radar_operator", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_dna_evolution_spiral(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 417))
    sprites: dict[str, Any] = {}

    im_d, dd = _make_sprite(860, 400)
    hand_rect(dd, 20, 20, 820, 360, seed=seed, lw=4, color="#8B5CF6", fill=card_bg, r=20)
    draw_fitted_text(dd, "CELLULAR REPAIR & REWIRING", 430, 65, max_w=760, target_size=32, family="noto", fill="#8B5CF6", bold=True)
    draw_semantic_prop(dd, "dna", 430, 200, 85, accent="#8B5CF6", ink=ink, card_bg=card_bg, seed=seed)
    draw_fitted_text(dd, "Biological Adaptation at the Foundation", 430, 335, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "dna_card", im_d, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="peaceful", accent_color="#8B5CF6", ink=ink, head_fill=card_bg, seed=seed + 1)
    _save_sprite(sprites, "evolved_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "dna_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "evolved_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_eisenhower_grid_sort(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 418))
    sprites: dict[str, Any] = {}

    im_m, dm = _make_sprite(860, 420)
    hand_rect(dm, 20, 20, 820, 380, seed=seed, lw=4, color=ink, fill=card_bg, r=20)
    draw_fitted_text(dm, "EISENHOWER 4-QUADRANT MATRIX", 430, 60, max_w=760, target_size=28, family="noto", fill=accent, bold=True)
    # 4 Quadrants
    dm.line([430, 100, 430, 370], fill=ink, width=4)
    dm.line([50, 235, 810, 235], fill=ink, width=4)
    # Q1: Do First (Red)
    hand_rect(dm, 60, 110, 350, 110, seed=seed, lw=2, color=ACCENT_CORAL, fill=soft_tint_bg(ACCENT_CORAL, 0.15, card_bg), r=8)
    draw_fitted_text(dm, "1. DO FIRST (Urgent+Important)", 235, 165, max_w=330, target_size=20, family="noto", fill=ACCENT_CORAL, bold=True)
    # Q2: Schedule (Green)
    hand_rect(dm, 450, 110, 350, 110, seed=seed + 1, lw=2, color=ACCENT_GREEN, fill=soft_tint_bg(ACCENT_GREEN, 0.15, card_bg), r=8)
    draw_fitted_text(dm, "2. SCHEDULE (Not Urgent+Important)", 625, 165, max_w=330, target_size=20, family="noto", fill=ACCENT_GREEN, bold=True)
    # Q3: Delegate (Yellow)
    hand_rect(dm, 60, 250, 350, 110, seed=seed + 2, lw=2, color=ACCENT_GOLD, fill=soft_tint_bg(ACCENT_GOLD, 0.15, card_bg), r=8)
    draw_fitted_text(dm, "3. DELEGATE (Urgent+Not Important)", 235, 305, max_w=330, target_size=20, family="noto", fill=ACCENT_GOLD, bold=True)
    # Q4: Eliminate (Gray)
    hand_rect(dm, 450, 250, 350, 110, seed=seed + 3, lw=2, color="#64748B", fill=soft_tint_bg("#64748B", 0.15, card_bg), r=8)
    draw_fitted_text(dm, "4. ELIMINATE (Distractions)", 625, 305, max_w=330, target_size=20, family="noto", fill="#64748B", bold=True)
    _save_sprite(sprites, "matrix_card", im_m, out_dir, prefix)

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose="pointing_cta", accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 4)
    _save_sprite(sprites, "manager_actor", im_h, out_dir, prefix)

    sprite_plan = [
        {"sprite": "matrix_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "manager_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1150, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


def _choreo_dynamic_synthesizer(scene: dict, accent: str, out_dir: Path, prefix: str) -> tuple[dict, list[dict], list[dict]]:
    """Universal Dynamic Visual Synthesizer: Dynamically generates custom scenes matching ANY sentence."""
    th = _theme_of(scene)
    ink, card_bg = th["ink"], th["card_bg"]
    seed = int(scene.get("variant_seed", 500))
    sprites: dict[str, Any] = {}

    narration = str(scene.get("narration", "")).strip()
    headline = str(scene.get("scene_title", "CORE INSIGHT")).upper()
    prop_kind = str(scene.get("prop_kind", "spark")).lower()
    layout_mode = str(scene.get("layout_mode", "clean_stage"))

    is_fem = bool(scene.get("speaker") == 2 or str(scene.get("speaker_name", "")).lower() in ("maya", "female"))

    # Determine pose matched to semantic prop
    pose = "pondering"
    if prop_kind in ("bull", "coin", "crown", "chess"):
        pose = "spotlight_crown"
    elif prop_kind in ("dumbbell", "battery", "rocket"):
        pose = "climbing"
    elif prop_kind in ("code", "cpu", "radar"):
        pose = "pointing_cta"
    elif prop_kind in ("pillar", "sun", "dna"):
        pose = "peaceful"
    elif prop_kind in ("timer", "target"):
        pose = "shielding"

    im_h, dh = _make_sprite(320, 440)
    draw_stickman_figure(dh, 160, 80, scale=1.0, pose=pose, accent_color=accent, ink=ink, head_fill=card_bg, seed=seed + 1, is_female=is_fem)
    _save_sprite(sprites, "synth_actor", im_h, out_dir, prefix)

    if layout_mode == "clean_stage":
        # Clean Stage: Natural diorama without a heavy rectangular card box!
        im_p, dp = _make_sprite(360, 360)
        draw_semantic_prop(dp, prop_kind, 180, 180, 130, accent=accent, ink=ink, card_bg=card_bg, seed=seed)
        _save_sprite(sprites, "synth_prop", im_p, out_dir, prefix)

        sprite_plan = [
            {"sprite": "synth_actor", "anim": "walk_to", "cx0": 340, "cy0": 1150, "cx1": 390, "cy1": 1150, "w": 380, "from_f": 0.0, "to_f": 1.0, "hops": 1},
            {"sprite": "synth_prop", "anim": "pop_bounce", "cx0": 780, "cy0": 1050, "w": 340, "from_f": 0.15, "to_f": 1.0},
        ]
        return sprites, sprite_plan, []

    # Other layout modes: Graphic insight banner card
    im_c, dc = _make_sprite(860, 380)
    hand_rect(dc, 20, 20, 820, 340, seed=seed, lw=4, color=accent, fill=card_bg, r=20)
    draw_fitted_text(dc, headline, 430, 70, max_w=760, target_size=32, family="noto", fill=accent, bold=True)
    draw_semantic_prop(dc, prop_kind, 430, 205, 80, accent=accent, ink=ink, card_bg=card_bg, seed=seed)
    clean_sub = " ".join(narration.split()[:8])
    if len(narration.split()) > 8:
        clean_sub += "..."
    draw_fitted_text(dc, clean_sub, 430, 315, max_w=760, target_size=22, family="noto", fill=th["ink_muted"])
    _save_sprite(sprites, "synth_card", im_c, out_dir, prefix)

    sprite_plan = [
        {"sprite": "synth_card", "anim": "slide_in", "cx0": 540, "cy0": 680, "cx1": 540, "cy1": 710, "w": 860, "from_f": 0.05, "to_f": 1.0},
        {"sprite": "synth_actor", "anim": "pop_bounce", "cx0": 540, "cy0": 1160, "w": 320, "from_f": 0.0, "to_f": 1.0},
    ]
    return sprites, sprite_plan, []


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
    "lighthouse_fog_beam": _choreo_lighthouse_fog_beam,
    "dopamine_spike_chart": _choreo_dopamine_spike_chart,
    "split_mirror_ideal": _choreo_split_mirror_ideal,
    "pedestal_bust_trap": _choreo_pedestal_bust_trap,
    "protective_couple_shield": _choreo_protective_couple_shield,
    "notification_fishhook": _choreo_notification_fishhook,
    "crypto_market_rally": _choreo_crypto_market_rally,
    "terminal_code_deploy": _choreo_terminal_code_deploy,
    "dumbbell_gym_lift": _choreo_dumbbell_gym_lift,
    "atom_quantum_orbit": _choreo_atom_quantum_orbit,
    "stoic_pillar_stand": _choreo_stoic_pillar_stand,
    "compound_interest_snowball": _choreo_compound_interest_snowball,
    "focus_pomodoro_timer": _choreo_focus_pomodoro_timer,
    "neural_net_synapse": _choreo_neural_net_synapse,
    "iceberg_hidden_depth": _choreo_iceberg_hidden_depth,
    "hamster_wheel_break": _choreo_hamster_wheel_break,
    "chess_checkmate_move": _choreo_chess_checkmate_move,
    "battery_supercharge": _choreo_battery_supercharge,
    "rocket_launchpad_stage": _choreo_rocket_launchpad_stage,
    "scales_of_justice": _choreo_scales_of_justice,
    "puzzle_assembly": _choreo_puzzle_assembly,
    "radar_scanner_sweep": _choreo_radar_scanner_sweep,
    "dna_evolution_spiral": _choreo_dna_evolution_spiral,
    "eisenhower_grid_sort": _choreo_eisenhower_grid_sort,
    "dynamic_synthesizer": _choreo_dynamic_synthesizer,
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

    @classmethod
    def _enrich_scene_composite(
        cls,
        comp: Image.Image,
        scene: dict,
        th: dict,
        accent: str,
        vector_plan: list[dict],
        sprite_plan: list[dict],
        sprites: dict[str, Any],
        aspect_ratio: str = "9:16",
    ) -> Image.Image:
        """Composites dynamic topic-driven vector environment, semantic props, vectors & layout-tailored typography."""
        w, h = comp.size
        d = ImageDraw.Draw(comp)
        seed = int(scene.get("variant_seed", 42))
        floor_y = int(h * 0.74)
        narr = (str(scene.get("narration", "")) + " " + str(scene.get("scene_title", "")) + " " + str(scene.get("choreography", ""))).lower()
        layout_mode = str(scene.get("layout_mode", "clean_stage"))

        # 1. Synthesize Unique Thematic Vector Environment from narration via AIBackgroundEngine
        style_params = {
            "fg": th["ink"],
            "bg": th["paper_bg"],
            "accent": accent,
            "accent_secondary": th.get("accents", [accent, "#38BDF8"])[1 % len(th.get("accents", [accent, "#38BDF8"]))],
            "line_width": max(2, int(w / 360)),
        }
        sid = "b3_dark" if th.get("is_dark") else "b1_light"
        bg_rendered = False
        try:
            from engine.ai_background_engine import AIBackgroundEngine
            AIBackgroundEngine.render_ai_background(
                draw=d,
                narration=narr,
                scene_idx=int(scene.get("scene_id", 1)) - 1,
                w=w,
                h=h,
                floor_y=floor_y,
                style_params=style_params,
                style_id=sid,
            )
            bg_rendered = True
        except Exception as bg_err:
            logger.debug("AI background engine fallback: %s", bg_err)

        if not bg_rendered:
            hand_line(d, 40, floor_y, w - 40, floor_y, seed=seed, lw=4, color=th["ink_muted"])
            ground_wash = Image.new("RGBA", (w, h - floor_y), (*_hex_to_rgb(th["ink_faint"]), 16))
            comp.alpha_composite(ground_wash, (0, floor_y))

        # 2. Semantic Contextual Props via AssetLibrary & ProceduralObjectEngine (1,000+ Props)
        try:
            import re
            from animation.assets import AssetLibrary
            from engine.procedural_object_engine import ProceduralObjectEngine

            asset_lib = AssetLibrary({"accent": accent, "fg": th["ink"], "line_width": 4})
            words = set(re.findall(r"[a-z']+", narr))

            # Determine open side based on hero sprite placement
            hero_on_left = True
            for sp in sprite_plan:
                if sp.get("sprite") in ("hero", "synth_actor", "climber", "thinker"):
                    cx = sp.get("cx0", 350)
                    if cx > 550:
                        hero_on_left = False
                        break

            px_x = int(w * 0.70) if hero_on_left else int(w * 0.10)
            px_y = int(h * 0.28)

            prop_rendered = False
            # 2a. Check explicit prop planned by storyboard director
            planned_prop = str(scene.get("prop_kind", "")).strip().lower()
            if planned_prop and planned_prop not in ("spark", "none"):
                asset_lib.render_asset_aa(comp, planned_prop.upper(), px_x, px_y, int(w * 0.24), int(h * 0.20), color=accent)
                prop_rendered = True

            # 2b. Check 1,000+ procedural catalog aliases
            if not prop_rendered:
                for word in words:
                    if word in ProceduralObjectEngine.ALIASES:
                        asset_name = ProceduralObjectEngine.ALIASES[word]
                        if asset_name == "CAR":
                            asset_lib.render_asset_aa(comp, "CAR", int(w * 0.60), int(h * 0.60), int(w * 0.34), int(h * 0.16), color=accent)
                        elif asset_name == "TREE":
                            asset_lib.render_asset_aa(comp, "TREE", int(w * 0.05), int(h * 0.44), int(w * 0.26), int(h * 0.32), color=accent)
                        elif asset_name in ("COIN", "MONEY"):
                            asset_lib.render_asset_aa(comp, "COIN", int(w * 0.08), px_y, int(w * 0.18), int(h * 0.18), color=accent)
                            asset_lib.render_asset_aa(comp, "BAG", int(w * 0.72), px_y, int(w * 0.20), int(h * 0.20), color=accent)
                        else:
                            asset_lib.render_asset_aa(comp, asset_name, px_x, px_y, int(w * 0.24), int(h * 0.20), color=accent)
                        prop_rendered = True
                        break

            # 2c. Fallback: Check direct procedural asset names
            if not prop_rendered:
                for word in words:
                    if len(word) >= 4 and ProceduralObjectEngine.has_asset(word):
                        asset_lib.render_asset_aa(comp, word.upper(), px_x, px_y, int(w * 0.24), int(h * 0.20), color=accent)
                        prop_rendered = True
                        break
        except Exception as prop_err:
            logger.debug("Scene enrichment prop exception: %s", prop_err)

        # 3. Draw Hand-Drawn Vector Plan Elements
        scale_to_comp = w / 1280.0
        for vec in vector_plan:
            k = vec.get("kind")
            col = vec.get("color", th["ink"])
            lw = max(2, int(vec.get("lw", 4) * scale_to_comp))
            if k == "line":
                p1 = vec.get("p1", [0, 0])
                p2 = vec.get("p2", [w, 0])
                hand_line(d, p1[0] * scale_to_comp, p1[1] * scale_to_comp, p2[0] * scale_to_comp, p2[1] * scale_to_comp, lw=lw, color=col)
            elif k == "arrow":
                x, y, aw = vec.get("x", 0), vec.get("y", 0), vec.get("w", 100)
                sx, sy = x * scale_to_comp, y * scale_to_comp
                ex = (x + aw) * scale_to_comp
                hand_line(d, sx, sy, ex, sy, lw=lw, color=col)
                d.polygon([(ex, sy), (ex - 20, sy - 12), (ex - 20, sy + 12)], fill=col)

        # 4. Composite Sprites from sprite_plan
        for sp in sprite_plan:
            name = sp.get("sprite")
            meta = sprites.get(name)
            if not meta:
                continue
            try:
                sp_img = Image.open(meta["path"]).convert("RGBA")
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
                comp.alpha_composite(resized, (max(0, min(w - 1, px)), max(0, min(h - 1, py))))
            except Exception:
                pass

        # 5. Non-Repetitive Layout-Driven Typography & Callouts
        raw_title = str(scene.get("scene_title") or scene.get("beat_b_label") or "").strip().upper()

        if raw_title and len(raw_title) > 2:
            if layout_mode == "clean_stage":
                # Clean Stage: No top banner box! Pure visual diorama where characters & art breathe freely.
                pass
            elif layout_mode == "split_screen":
                # Split Screen: Subtle center comparison line with contrasting left/right topic badges
                hand_line(d, w // 2, int(h * 0.16), w // 2, floor_y - 20, seed=seed, lw=3, color=th["ink_faint"])
                left_lbl = str(scene.get("left_tag") or "BEFORE").upper()
                right_lbl = str(scene.get("right_tag") or "AFTER").upper()
                d.rounded_rectangle([int(w * 0.12), int(h * 0.08), int(w * 0.38), int(h * 0.08) + 52], radius=14, fill=th["card_bg"], outline=th["ink_muted"], width=2)
                draw_fitted_text(d, left_lbl, int(w * 0.25), int(h * 0.08) + 26, max_w=int(w * 0.24), target_size=24, family="noto", fill=th["ink"], bold=True)
                d.rounded_rectangle([int(w * 0.62), int(h * 0.08), int(w * 0.88), int(h * 0.08) + 52], radius=14, fill=th["card_bg"], outline=accent, width=2)
                draw_fitted_text(d, right_lbl, int(w * 0.75), int(h * 0.08) + 26, max_w=int(w * 0.24), target_size=24, family="noto", fill=accent, bold=True)
            elif layout_mode == "comic_beats":
                # Comic Beats: Speech/thought cloud above the action beat
                cb_w = min(int(w * 0.65), 580)
                cb_h = 68
                cx = (w - cb_w) // 2
                cy = int(h * 0.10)
                d.rounded_rectangle([cx, cy, cx + cb_w, cy + cb_h], radius=24, fill=th["card_bg"], outline=accent, width=3)
                d.polygon([(cx + cb_w // 2 - 12, cy + cb_h), (cx + cb_w // 2 + 12, cy + cb_h), (cx + cb_w // 2, cy + cb_h + 16)], fill=th["card_bg"], outline=accent)
                draw_fitted_text(d, f"💭 {raw_title}", cx + cb_w // 2, cy + cb_h // 2, max_w=cb_w - 40, target_size=28, family="caveat", fill=th["ink"], bold=True)
            elif layout_mode == "floating_callout":
                # Floating Callout: Lower-third pill leaving the entire upper screen completely open
                badge_w = min(int(w * 0.72), 620)
                badge_h = 60
                bx = (w - badge_w) // 2
                by = int(h * 0.78)
                d.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=30, fill=th["card_bg"], outline=accent, width=2)
                draw_fitted_text(d, f"✦  {raw_title}", bx + badge_w // 2, by + badge_h // 2, max_w=badge_w - 50, target_size=26, family="caveat", fill=accent, bold=True)
            elif layout_mode == "editorial_spread":
                # Editorial Spread: Minimalist unboxed typography in top corner
                draw_fitted_text(d, f"✦  {raw_title}", int(w * 0.45), int(h * 0.06), max_w=int(w * 0.75), target_size=32, family="caveat", fill=accent, bold=True)
            elif layout_mode == "big_typo_banner":
                # Big Typo Banner: Bold impact card reserved for major climactic takeaways
                badge_w = min(int(w * 0.82), 780)
                badge_h = 80
                bx = (w - badge_w) // 2
                by = int(h * 0.055)
                d.rounded_rectangle([bx + 4, by + 4, bx + badge_w + 4, by + badge_h + 4], radius=18, fill=(0, 0, 0, 35))
                d.rounded_rectangle([bx, by, bx + badge_w, by + badge_h], radius=18, fill=th["card_bg"], outline=accent, width=3)
                d.rounded_rectangle([bx, by, bx + 18, by + badge_h], radius=9, fill=accent)
                draw_fitted_text(d, f"✦  {raw_title}", bx + badge_w // 2 + 8, by + badge_h // 2, max_w=badge_w - 60, target_size=34, family="caveat", fill=th["ink"], bold=True)

        # 6. Dynamic Organic Particles Seeded Per-Scene
        rng = mulberry32(seed)
        particle_symbols = ["✦", "·", "✧", "°", "✦"]
        for p_idx in range(5):
            px = int(w * (0.10 + rng() * 0.80))
            py = int(h * (0.12 + rng() * 0.60))
            sym = particle_symbols[p_idx % len(particle_symbols)]
            col = accent if p_idx % 2 == 0 else th["ink_muted"]
            d.text((px, py), sym, fill=col, font=ImageFont.load_default(), anchor="mm")

        return comp

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

        # Contextual Semantic Procedural Prop from 1,025+ Object Catalog
        try:
            from engine.procedural_object_engine import ProceduralObjectEngine
            import re

            # Choreographies that already possess hand-crafted props or dual characters
            BUILTIN_FOCAL_CHOREOS = {
                "cta_celebration",
                "split_mirror_ideal",
                "two_path_fork",
                "phone_trap",
                "hourglass_sprint",
                "dumbbell_gym_lift",
                "terminal_code_deploy",
                "crypto_market_rally",
                "battery_supercharge",
                "rocket_launchpad_stage",
                "scales_of_justice",
                "pedestal_bust_trap",
                "bridge_cross",
                "boundary_shield",
                "tether_break",
                "give_and_withdraw",
                "scale_tipping",
                "chess_checkmate_move",
                "puzzle_assembly",
                "radar_scanner_sweep",
                "atom_quantum_orbit",
                "compound_interest_snowball",
                "focus_pomodoro_timer",
                "staircase_climb",
                "mirror_truth",
                "protective_couple_shield",
                "notification_fishhook",
                "crowd_filter",
                "split_cards_slide",
                "magnet_orbit",
            }

            is_cta = bool(scene.get("is_cta", False)) or choreo == "cta_celebration"

            # NEVER inject overlapping props onto CTA buttons or scenes with focal choreography
            if not is_cta and choreo not in BUILTIN_FOCAL_CHOREOS:
                seed = int(scene.get("variant_seed", 42))
                narr_text = (str(scene.get("narration", "")) + " " + str(scene.get("scene_title", ""))).lower()
                words = re.findall(r"[a-z']+", narr_text)

                detected_prop: Optional[str] = None
                planned = str(scene.get("prop_kind", "")).strip().lower()
                if planned and planned not in ("spark", "none", "arrow", "line"):
                    detected_prop = planned

                if not detected_prop:
                    for w in words:
                        if w in ProceduralObjectEngine.ALIASES:
                            detected_prop = ProceduralObjectEngine.ALIASES[w].lower()
                            break

                if not detected_prop:
                    for w in words:
                        if len(w) >= 4 and ProceduralObjectEngine.has_asset(w):
                            detected_prop = w.lower()
                            break

                # If we found a semantic prop and it's not already in sprite_plan
                if detected_prop and not any(detected_prop in sp.get("sprite", "").lower() for sp in sprite_plan):
                    prop_slug = re.sub(r"[^a-z0-9]+", "_", detected_prop).strip("_")
                    sp_name = f"prop_{prop_slug}"

                    prop_sz = 280
                    im_prop, d_prop = _make_sprite(prop_sz, prop_sz)
                    drawn = ProceduralObjectEngine.draw_object(
                        draw=d_prop,
                        asset_name=detected_prop,
                        x=20,
                        y=20,
                        w=prop_sz - 40,
                        h=prop_sz - 40,
                        color=accent,
                        ink=th["ink"],
                        line_width=4,
                        seed=seed + sid * 31,
                    )
                    if drawn:
                        # Collision detection test against existing sprites
                        candidate_slots = [(760, 1150), (320, 1150), (760, 950), (320, 950), (540, 750)]
                        safe_cx, safe_cy = None, None

                        for cand_cx, cand_cy in candidate_slots:
                            collides = False
                            for sp in sprite_plan:
                                s_name = sp.get("sprite", "")
                                sp_cx = sp.get("cx0", 0)
                                sp_cy = sp.get("cy0", 0)
                                sp_w = sp.get("w", 300)
                                sp_h = sprites.get(s_name, {}).get("h") if s_name in sprites else sp.get("h")
                                if sp_h is None:
                                    sp_h = 160 if ("pill" in s_name or "banner" in s_name) else min(sp_w, 360)
                                min_dist_x = (prop_sz + sp_w) * 0.38
                                min_dist_y = (prop_sz + sp_h) * 0.38
                                if abs(cand_cx - sp_cx) < min_dist_x and abs(cand_cy - sp_cy) < min_dist_y:
                                    collides = True
                                    break
                            if not collides:
                                safe_cx, safe_cy = cand_cx, cand_cy
                                break

                        if safe_cx is not None:
                            _save_sprite(sprites, sp_name, im_prop, out_p.parent, prefix)
                            sprite_plan.append({
                                "sprite": sp_name,
                                "anim": "pop_bounce",
                                "cx0": safe_cx,
                                "cy0": safe_cy,
                                "w": prop_sz,
                                "from_f": 0.12,
                                "to_f": 1.0,
                            })
        except Exception as prop_err:
            logger.debug("Failed to inject semantic procedural prop sprite: %s", prop_err)

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

        # Build rich, multi-layered cinematic illustrated composite
        comp = Image.new("RGBA", (CANVAS_W, CANVAS_H), rgba(th["paper_bg"], 255))
        if "lcm_wash" in sprites:
            try:
                lw_img = Image.open(sprites["lcm_wash"]["path"]).convert("RGBA").resize(
                    (CANVAS_W, CANVAS_H), Image.Resampling.LANCZOS
                )
                comp = Image.alpha_composite(comp, lw_img)
            except Exception:
                pass

        comp = self._enrich_scene_composite(
            comp=comp,
            scene=scene,
            th=th,
            accent=accent,
            vector_plan=vector_plan,
            sprite_plan=sprite_plan,
            sprites=sprites,
            aspect_ratio=self.aspect_ratio,
        )

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
