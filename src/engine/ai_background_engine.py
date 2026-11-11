"""
AI Background Engine - Generates 100% Unique, Topic-Aligned Environments
========================================================================
Analyzes scene narration semantically and procedurally synthesizes completely
distinct, topic-tailored vector backgrounds: Space Cosmos, Forest Mountains,
City Skyline, Highway Road, Desert Pyramids, Underwater Ocean, Medieval Castle,
Classroom Chalkboard, Tech Server Room, Trading Finance, Hospital Clinic, etc.

Eliminates repetitive indoor room backgrounds completely.
Created by Atharv Hatwar.
"""

from __future__ import annotations

import hashlib
import math
import random
import re
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont


def _load_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    from pathlib import Path
    candidates = (
        ["C:/Windows/Fonts/segoeuib.ttf", "C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/calibrib.ttf"]
        if bold
        else ["C:/Windows/Fonts/segoeui.ttf", "C:/Windows/Fonts/arial.ttf"]
    )
    for fp in candidates:
        if Path(fp).exists():
            try:
                return ImageFont.truetype(fp, max(10, int(size)))
            except OSError:
                continue
    return ImageFont.load_default()


def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
    h = str(hex_str).strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))
    except Exception:
        return (24, 24, 27)


def _hex_to_rgba(hex_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    r, g, b = _hex_to_rgb(hex_str)
    return (r, g, b, alpha)


def _lighten(hex_color: str, factor: float = 0.3) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r + (255 - r) * factor)
    g = int(g + (255 - g) * factor)
    b = int(b + (255 - b) * factor)
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, factor: float = 0.3) -> str:
    r, g, b = _hex_to_rgb(hex_color)
    r = int(r * (1.0 - factor))
    g = int(g * (1.0 - factor))
    b = int(b * (1.0 - factor))
    return f"#{r:02x}{g:02x}{b:02x}"


class AIBackgroundEngine:
    """
    Topic-specific procedural AI background generator.
    Completely replaces repetitive room templates with 12+ real scenic environments.
    Created by Atharv Hatwar.
    """

    @classmethod
    def render_ai_background(
        cls,
        draw: ImageDraw.ImageDraw,
        narration: str,
        scene_idx: int,
        w: int,
        h: int,
        floor_y: int,
        style_params: dict[str, Any],
        style_id: str = "s1_rsa_whiteboard",
    ) -> None:
        """Synthesize a unique, topic-aligned background tailored to this sentence."""
        text = narration.lower().strip()
        fg = style_params.get("fg", "#111111")
        acc = style_params.get("accent", "#E94560")
        acc2 = style_params.get("accent_secondary", "#38BDF8")
        lw = max(2, int(float(style_params.get("line_width", 3.5)) * (w / 720.0)))

        seed_int = int(hashlib.md5(f"{text}:{scene_idx}:{style_id}".encode("utf-8")).hexdigest()[:8], 16)
        rng = random.Random(seed_int)

        theme = cls._detect_theme(text)

        dispatchers = {
            "SPACE_COSMOS":          cls._render_space_cosmos,
            "NATURE_FOREST":         cls._render_nature_forest,
            "CITY_SKYLINE":          cls._render_city_skyline,
            "HIGHWAY_ROAD":          cls._render_highway_road,
            "OCEAN_WATER":           cls._render_ocean_water,
            "DESERT_PYRAMIDS":       cls._render_desert_pyramids,
            "MEDIEVAL_CASTLE":       cls._render_medieval_castle,
            "CLASSROOM_CHALKBOARD":  cls._render_classroom_chalkboard,
            "HOSPITAL_CLINIC":       cls._render_hospital_clinic,
            "TECH_CYBER_SERVER":     cls._render_tech_cyber_server,
            "TRADING_FINANCE":       cls._render_trading_finance,
            "COZY_LIBRARY":          cls._render_cozy_library,
            "BEDROOM_RETREAT":       cls._render_bedroom_retreat,
            "GALLERY_REFLECT":       cls._render_gallery_reflect,
            "MODERN_OFFICE":         cls._render_modern_office,
            "FITNESS_GYM":           cls._render_fitness_gym,
            "CONTRAST_SPLIT":        cls._render_contrast_split,
            "MODERN_STUDIO":         cls._render_modern_studio,
        }

        fn = dispatchers.get(theme, cls._render_modern_studio)
        fn(draw, text, w, h, floor_y, style_params, style_id, fg, acc, acc2, lw, rng)

    @classmethod
    def _detect_theme(cls, text: str) -> str:
        """Accurately classify narration into a dedicated environment."""
        if any(w in text for w in ("comfort", "lazy", "bed", "sleep", "tired", "morning", "habit", "routine", "stay", "couch", "relax", "zone", "destroy", "stuck", "comfort zone")):
            return "BEDROOM_RETREAT"
        elif any(w in text for w in ("pretend", "mirror", "mask", "who you are", "identity", "reflection", "look in", "truth", "realize", "self", "mind", "person", "inside", "shadow", "ego")):
            return "GALLERY_REFLECT"
        elif any(w in text for w in ("gym", "workout", "exercise", "strength", "body", "physical", "train", "sweat", "lift", "fitness", "discipline")):
            return "FITNESS_GYM"
        elif any(w in text for w in ("work", "career", "job", "business", "hustle", "desk", "build", "focus", "goal", "success", "future", "ambition")):
            return "MODERN_OFFICE"
        elif any(w in text for w in ("space", "galaxy", "planet", "star", "universe", "rocket", "astronaut", "alien", "orbit", "cosmos", "moon", "mars")):
            return "SPACE_COSMOS"
        elif any(w in text for w in ("nature", "forest", "tree", "mountain", "river", "hike", "wood", "wild", "animal", "dog", "cat", "horse", "bird", "park", "grass", "hill", "breathe")):
            return "NATURE_FOREST"
        elif any(w in text for w in ("car", "highway", "road", "drive", "traffic", "speed", "vehicle", "travel", "engine", "asphalt", "lane", "ride")):
            return "HIGHWAY_ROAD"
        elif any(w in text for w in ("ocean", "sea", "water", "beach", "swim", "fish", "deep", "island", "wave", "coral", "lake", "submerged")):
            return "OCEAN_WATER"
        elif any(w in text for w in ("desert", "sand", "pyramid", "egypt", "dune", "heat", "ancient", "camel", "sahara")):
            return "DESERT_PYRAMIDS"
        elif any(w in text for w in ("castle", "fortress", "king", "kingdom", "sword", "knight", "battle", "empire", "throne", "medieval", "stone wall")):
            return "MEDIEVAL_CASTLE"
        elif any(w in text for w in ("school", "class", "classroom", "student", "teacher", "lecture", "math", "exam", "lesson", "study", "algebra", "academic")):
            return "CLASSROOM_CHALKBOARD"
        elif any(w in text for w in ("hospital", "doctor", "medicine", "health", "sick", "patient", "nurse", "cure", "clinic", "surgery", "vital", "disease")):
            return "HOSPITAL_CLINIC"
        elif any(w in text for w in ("tech", "code", "coding", "software", "ai", "developer", "computer", "server", "algorithm", "digital", "data", "bot", "program", "stack")):
            return "TECH_CYBER_SERVER"
        elif any(w in text for w in ("money", "finance", "wealth", "trading", "stock", "crypto", "dollar", "asset", "rich", "invest", "cash", "millionaire", "roi", "dividend", "passive income")):
            return "TRADING_FINANCE"
        elif any(w in text for w in ("book", "library", "read", "story", "tale", "wisdom", "history", "novel", "legend", "chapter", "scroll")):
            return "COZY_LIBRARY"
        elif any(w in text for w in ("city", "urban", "skyline", "downtown", "building", "skyscraper", "society", "crowd", "street")):
            return "CITY_SKYLINE"
        elif any(w in text for w in ("instead", "versus", "vs", "opposite", "difference", "compare", "contrast", "two paths", "choice")):
            return "CONTRAST_SPLIT"
        return "MODERN_STUDIO"

    # ------------------------------------------------------------------
    # Thematic Environment Renderers
    # ------------------------------------------------------------------

    @classmethod
    def _render_space_cosmos(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Deep cosmic sky with twinkling stars, glowing moon/ringed planet, and lunar surface."""
        # Sky: Dark space gradient
        cls._grad(draw, w, h, "#030712", "#0F172A")
        # Distant nebula clouds
        for _ in range(3):
            nx, ny = rng.randint(0, w), rng.randint(0, int(h * 0.6))
            nr = rng.randint(int(w * 0.25), int(w * 0.50))
            draw.ellipse([nx - nr, ny - nr, nx + nr, ny + nr], fill=(139, 92, 246, 20))

        # Stars
        for _ in range(60):
            sx, sy = rng.randint(0, w), rng.randint(0, int(h * 0.70))
            sz = rng.choice([1, 2, 2, 3])
            star_col = rng.choice(["#FFFFFF", "#BAE6FD", "#FEF08A"])
            draw.ellipse([sx, sy, sx + sz, sy + sz], fill=star_col)

        # Giant Glowing Moon or Ringed Saturn
        cx, cy = int(w * 0.75), int(h * 0.22)
        rad = int(min(w, h) * 0.14)
        draw.ellipse([cx - rad - 8, cy - rad - 8, cx + rad + 8, cy + rad + 8], fill=(56, 189, 248, 30))
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill="#FEF08A", outline="#FACC15", width=lw)
        # Ring arc
        draw.arc([cx - int(rad * 1.8), cy - int(rad * 0.4), cx + int(rad * 1.8), cy + int(rad * 0.4)], start=0, end=360, fill="#38BDF8", width=max(2, lw))

        # Lunar crater ground
        draw.rectangle([0, floor_y, w, h], fill="#1E293B")
        draw.line([(0, floor_y), (w, floor_y)], fill="#94A3B8", width=lw)
        for _ in range(8):
            cx_c = rng.randint(20, w - 20)
            cy_c = rng.randint(floor_y + 12, h - 12)
            cr_c = rng.randint(10, 28)
            draw.ellipse([cx_c - cr_c, cy_c - cr_c // 2, cx_c + cr_c, cy_c + cr_c // 2], fill="#0F172A", outline="#475569", width=1)

    @classmethod
    def _render_nature_forest(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Vibrant outdoor mountain landscape with layered pine trees, rolling hills, and sky."""
        # Sky
        cls._grad(draw, w, floor_y, "#BAE6FD", "#E0F2FE")
        # Golden Sun
        draw.ellipse([int(w * 0.80) - 24, int(h * 0.12) - 24, int(w * 0.80) + 24, int(h * 0.12) + 24], fill="#FACC15")
        # Soft clouds
        for cx_cl, cy_cl in [(int(w * 0.25), int(h * 0.14)), (int(w * 0.55), int(h * 0.18))]:
            draw.ellipse([cx_cl - 40, cy_cl - 15, cx_cl + 40, cy_cl + 15], fill="#FFFFFF")
            draw.ellipse([cx_cl - 20, cy_cl - 25, cx_cl + 20, cy_cl + 15], fill="#FFFFFF")

        # Distant mountain peaks
        mount_pts = [
            (0, floor_y),
            (int(w * 0.18), int(h * 0.32)),
            (int(w * 0.42), int(h * 0.48)),
            (int(w * 0.68), int(h * 0.28)),
            (int(w * 0.90), int(h * 0.44)),
            (w, floor_y),
        ]
        draw.polygon(mount_pts, fill="#94A3B8", outline=fg, width=1)

        # Midground Pine Trees
        for i in range(12):
            tx = int(w * (i / 11.0)) + rng.randint(-15, 15)
            th = rng.randint(int(h * 0.16), int(h * 0.26))
            ty = floor_y - th
            tw = int(th * 0.42)
            pts = [(tx, ty), (tx + tw // 2, floor_y), (tx - tw // 2, floor_y)]
            draw.polygon(pts, fill="#15803D", outline=fg, width=1)

        # Grassy terrain floor
        draw.rectangle([0, floor_y, w, h], fill="#166534")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)
        for i in range(15):
            gx = rng.randint(10, w - 10)
            gy = rng.randint(floor_y + 10, h - 10)
            draw.line([(gx, gy), (gx - 3, gy - 8)], fill="#22C55E", width=2)
            draw.line([(gx, gy), (gx + 3, gy - 9)], fill="#22C55E", width=2)

    @classmethod
    def _render_city_skyline(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Towering modern skyscrapers at dusk with illuminated windows and asphalt street."""
        cls._grad(draw, w, floor_y, "#0F172A", "#1E293B")
        # Moon
        draw.ellipse([int(w * 0.20) - 16, int(h * 0.12) - 16, int(w * 0.20) + 16, int(h * 0.12) + 16], fill="#F8FAFC")

        # Skyscrapers
        n_bldgs = 8
        bw = w // n_bldgs
        for b in range(n_bldgs):
            bh_b = rng.randint(int(h * 0.32), int(h * 0.58))
            bx = b * bw
            by = floor_y - bh_b
            b_col = "#1E293B" if b % 2 == 0 else "#0F172A"
            draw.rectangle([bx, by, bx + bw, floor_y], fill=b_col, outline=fg, width=max(1, lw // 2))
            # Glowing windows
            for wr in range(by + 12, floor_y - 12, 18):
                for wc in range(bx + 6, bx + bw - 6, 12):
                    if (wr + wc) % 3 != 0:
                        draw.rectangle([wc, wr, wc + 6, wr + 8], fill="#FDE047")

        # Asphalt street floor with yellow road markings
        draw.rectangle([0, floor_y, w, h], fill="#18181B")
        draw.line([(0, floor_y), (w, floor_y)], fill="#71717A", width=lw)
        road_mid = (floor_y + h) // 2
        for rx in range(10, w, 40):
            draw.line([(rx, road_mid), (rx + 22, road_mid)], fill="#FACC15", width=max(2, lw))

    @classmethod
    def _render_highway_road(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Perspective highway vanishing into horizon with sunset sky."""
        cls._grad(draw, w, floor_y, "#F97316", "#FEF08A")
        # Mountain silhouette on horizon
        draw.polygon([(0, floor_y), (int(w * 0.3), int(h * 0.48)), (int(w * 0.6), int(h * 0.44)), (w, floor_y)], fill="#475569")
        # Converging perspective road
        road_pts = [(int(w * 0.46), floor_y), (int(w * 0.54), floor_y), (w + 40, h), (-40, h)]
        draw.polygon(road_pts, fill="#27272A", outline=fg, width=lw)
        # Center dashed yellow line converging
        for frac in (0.05, 0.20, 0.40, 0.65, 0.90):
            y_dash = floor_y + int((h - floor_y) * frac)
            w_dash = max(2, int(4 * frac * 2.5))
            draw.line([(w // 2, y_dash), (w // 2, y_dash + int(15 * frac + 3))], fill="#FACC15", width=w_dash)

    @classmethod
    def _render_ocean_water(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Undersea ocean depth with filtering sunbeams, coral floor, and bubbles."""
        cls._grad(draw, w, h, "#0284C7", "#082F49")
        # Sunbeams filtering down from surface
        for deg in (-25, -10, 5, 20):
            draw.polygon([(w // 2 + deg * 15, 0), (w // 2 + deg * 25, 0), (w // 2 + deg * 40, h), (w // 2 + deg * 30, h)], fill=(255, 255, 255, 22))
        # Floating bubbles
        for _ in range(16):
            bx, by = rng.randint(20, w - 20), rng.randint(20, floor_y - 20)
            br = rng.randint(3, 9)
            draw.ellipse([bx - br, by - br, bx + br, by + br], outline="#E0F2FE", width=1)
        # Sandy sea bottom + coral silhouettes
        draw.rectangle([0, floor_y, w, h], fill="#CA8A04")
        draw.line([(0, floor_y), (w, floor_y)], fill="#854D0E", width=lw)
        for i in range(8):
            cx_c = rng.randint(15, w - 15)
            draw.line([(cx_c, floor_y), (cx_c - 6, floor_y - 25)], fill="#EF4444", width=3)
            draw.line([(cx_c, floor_y), (cx_c + 8, floor_y - 20)], fill="#F97316", width=3)

    @classmethod
    def _render_desert_pyramids(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Blazing sun, sand dunes, and monumental stone pyramids."""
        cls._grad(draw, w, floor_y, "#F59E0B", "#FEF3C7")
        # Blazing Sun
        draw.ellipse([int(w * 0.78) - 30, int(h * 0.15) - 30, int(w * 0.78) + 30, int(h * 0.15) + 30], fill="#F97316")
        # Great Pyramid Silhouette
        pyr_base = floor_y
        px, pw_pyr, ph_pyr = int(w * 0.36), int(w * 0.44), int(h * 0.36)
        draw.polygon([(px, pyr_base - ph_pyr), (px + pw_pyr // 2, pyr_base), (px - pw_pyr // 2, pyr_base)], fill="#D97706", outline=fg, width=lw)
        draw.polygon([(px, pyr_base - ph_pyr), (px + pw_pyr // 2, pyr_base), (px + 10, pyr_base)], fill="#B45309")
        # Second smaller pyramid
        draw.polygon([(int(w * 0.72), pyr_base - int(ph_pyr * 0.6)), (int(w * 0.85), pyr_base), (int(w * 0.59), pyr_base)], fill="#D97706", outline=fg, width=lw)
        # Undulating sand dunes floor
        draw.rectangle([0, floor_y, w, h], fill="#FBBF24")
        draw.line([(0, floor_y), (w, floor_y)], fill="#B45309", width=lw)

    @classmethod
    def _render_medieval_castle(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Heavy stone castle parapet, battlements, torch sconces, and medieval banner."""
        cls._grad(draw, w, floor_y, "#1E293B", "#334155")
        # Castle stone blocks
        draw.rectangle([0, 0, w, floor_y], fill="#475569")
        for r in range(0, floor_y, 28):
            draw.line([(0, r), (w, r)], fill="#1E293B", width=1)
            off = (r // 28) % 2 * 30
            for c in range(off, w, 60):
                draw.line([(c, r), (c, r + 28)], fill="#1E293B", width=1)
        # Battlements crenels at top
        for c in range(0, w, 50):
            draw.rectangle([c, 0, c + 25, 20], fill="#334155", outline=fg, width=1)
        # Flickering wall torch
        tx, ty = int(w * 0.82), int(h * 0.32)
        draw.rectangle([tx - 4, ty, tx + 4, ty + 24], fill="#78350F")
        draw.polygon([(tx, ty - 14), (tx + 8, ty + 2), (tx - 8, ty + 2)], fill="#F59E0B")
        # Flag banner
        bx = int(w * 0.18)
        draw.polygon([(bx, int(h * 0.15)), (bx + 35, int(h * 0.15)), (bx + 35, int(h * 0.40)), (bx + 17, int(h * 0.34)), (bx, int(h * 0.40))], fill="#DC2626", outline=fg, width=1)
        # Cobblestone floor
        draw.rectangle([0, floor_y, w, h], fill="#334155")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _render_classroom_chalkboard(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Grand academic chalkboard covered in mathematical formulas, diagrams, and chalk ledge."""
        cls._grad(draw, w, floor_y, "#1E293B", "#0F172A")
        # Chalkboard frame
        cb_m = max(16, int(w * 0.05))
        cb_x1, cb_y1 = cb_m, int(h * 0.08)
        cb_x2, cb_y2 = w - cb_m, floor_y - 12
        draw.rounded_rectangle([cb_x1, cb_y1, cb_x2, cb_y2], radius=8, fill="#19231E", outline="#78350F", width=max(4, lw + 2))
        # Chalk formulas and diagrams
        f_font = _load_font(max(10, int(w * 0.024)), bold=True)
        draw.text((cb_x1 + 25, cb_y1 + 25), "f(x) = ∫ e^(-x²) dx", fill="#F8FAFC", font=f_font)
        draw.text((cb_x1 + 25, cb_y1 + 55), "E = mc²   Δx · Δp ≥ ℏ/2", fill="#86EFAC", font=f_font)
        # Chalk coordinate axis graph
        gx, gy = cb_x2 - 120, cb_y1 + 35
        draw.line([(gx, gy + 70), (gx + 90, gy + 70)], fill="#F8FAFC", width=2)
        draw.line([(gx, gy + 70), (gx, gy)], fill="#F8FAFC", width=2)
        draw.arc([gx, gy, gx + 90, gy + 80], start=180, end=270, fill="#38BDF8", width=2)
        # Wooden classroom floor
        draw.rectangle([0, floor_y, w, h], fill="#78350F")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _render_hospital_clinic(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Clinical hospital operating room with ECG heart monitor and sterile wall tiles."""
        cls._grad(draw, w, floor_y, "#F0FDF4", "#E0F2FE")
        # White clinical wall tile grid
        for r in range(0, floor_y, 35):
            draw.line([(0, r), (w, r)], fill="#CBD5E1", width=1)
        # Medical Cross Sign
        cx, cy = int(w * 0.20), int(h * 0.22)
        draw.rectangle([cx - 5, cy - 16, cx + 5, cy + 16], fill="#EF4444")
        draw.rectangle([cx - 16, cy - 5, cx + 16, cy + 5], fill="#EF4444")
        # Heart Rate ECG Monitor Display
        mx, my = int(w * 0.65), int(h * 0.16)
        mw, mh = int(w * 0.28), int(h * 0.22)
        draw.rounded_rectangle([mx, my, mx + mw, my + mh], radius=6, fill="#0F172A", outline=fg, width=lw)
        # Glowing green ECG pulse line
        draw.line([
            (mx + 10, my + mh // 2),
            (mx + int(mw * 0.35), my + mh // 2),
            (mx + int(mw * 0.45), my + 14),
            (mx + int(mw * 0.55), my + mh - 14),
            (mx + int(mw * 0.65), my + mh // 2),
            (mx + mw - 10, my + mh // 2),
        ], fill="#22C55E", width=max(2, lw))
        draw.text((mx + 12, my + 8), "72 BPM  PULSE", fill="#22C55E", font=_load_font(max(9, int(w * 0.018)), bold=True))
        # Sterile tile floor
        draw.rectangle([0, floor_y, w, h], fill="#E2E8F0")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _render_tech_cyber_server(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """High-tech datacenter server racks with blinking LED arrays and neon grid reflections."""
        cls._grad(draw, w, h, "#090D16", "#030712")
        # Server Racks in background
        n_racks = 5
        rw = w // n_racks
        for i in range(n_racks):
            rx = i * rw + 10
            draw.rectangle([rx, 30, rx + rw - 20, floor_y], fill="#0F172A", outline="#00F0FF", width=1)
            # Server unit shelves with blinking status LEDs
            for sy in range(45, floor_y - 20, 24):
                draw.line([(rx + 5, sy), (rx + rw - 25, sy)], fill="#1E293B", width=1)
                for led in range(4):
                    l_col = "#22C55E" if (i + sy + led) % 3 != 0 else "#EF4444"
                    draw.ellipse([rx + 8 + led * 8, sy - 8, rx + 12 + led * 8, sy - 4], fill=l_col)
        # Perspective digital grid floor
        draw.rectangle([0, floor_y, w, h], fill="#050508")
        draw.line([(0, floor_y), (w, floor_y)], fill="#00F0FF", width=max(2, lw))
        for x_step in range(0, w, 40):
            draw.line([(x_step, floor_y), (int(w * 0.5 + (x_step - w * 0.5) * 1.8), h)], fill=(0, 240, 255, 60), width=1)

    @classmethod
    def _render_trading_finance(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Wall of financial trading screens with candlestick charts, ticker ribbon, and skyscraper view."""
        cls._grad(draw, w, floor_y, "#090A0F", "#1A150A")
        # Large Wall Display Monitor
        mw, mh = int(w * 0.84), int(h * 0.36)
        mx, my = (w - mw) // 2, int(h * 0.12)
        draw.rounded_rectangle([mx, my, mx + mw, my + mh], radius=8, fill="#0F172A", outline="#F59E0B", width=lw)
        # Candlestick bars
        for i in range(8):
            cx_b = mx + 30 + i * (mw // 10)
            h_b = 20 + i * 10
            cy_b = my + mh - 35 - h_b
            is_green = i % 3 != 0
            b_col = "#10B981" if is_green else "#EF4444"
            draw.line([(cx_b + 5, cy_b - 8), (cx_b + 5, cy_b + h_b + 8)], fill=b_col, width=1)
            draw.rectangle([cx_b, cy_b, cx_b + 10, cy_b + h_b], fill=b_col)
        # Green exponential curve
        draw.line([(mx + 20, my + mh - 30), (mx + mw - 30, my + 30)], fill="#10B981", width=max(2, lw + 1))
        draw.text((mx + 24, my + 14), "ASSET COMPOUND INDEX  +420% ▲", fill="#10B981", font=_load_font(max(10, int(w * 0.024)), bold=True))
        # Sleek marble floor
        draw.rectangle([0, floor_y, w, h], fill="#1C1917")
        draw.line([(0, floor_y), (w, floor_y)], fill="#F59E0B", width=lw)

    @classmethod
    def _render_cozy_library(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Warm mahogany floor-to-ceiling bookshelves lined with colorful book spines."""
        cls._grad(draw, w, floor_y, "#292524", "#44403C")
        # Bookshelves
        n_shelves = 4
        sh_h = floor_y // n_shelves
        book_colors = ["#DC2626", "#D97706", "#059669", "#2563EB", "#7C3AED", "#B45309"]
        for s in range(n_shelves):
            sy = s * sh_h
            draw.line([(0, sy + sh_h), (w, sy + sh_h)], fill="#78350F", width=max(3, lw + 1))
            # Books on this shelf
            bx = 20
            while bx < w - 30:
                bw_book = rng.randint(12, 24)
                bh_book = rng.randint(sh_h - 22, sh_h - 6)
                draw.rectangle([bx, sy + sh_h - bh_book, bx + bw_book, sy + sh_h], fill=rng.choice(book_colors), outline=fg, width=1)
                bx += bw_book + 3
        # Polished hardwood floor
        draw.rectangle([0, floor_y, w, h], fill="#78350F")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _render_bedroom_retreat(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Cozy modern bedroom with unmade bed, warm nightstand lamp, and morning window."""
        cls._grad(draw, w, floor_y, "#2D2438", "#4A3B5C")
        # Window with morning light sneaking through blinds on right
        win_x, win_y, win_w, win_h = int(w * 0.65), int(h * 0.12), int(w * 0.28), int(h * 0.32)
        draw.rectangle([win_x, win_y, win_x + win_w, win_y + win_h], fill="#FEF3C7", outline=fg, width=max(2, lw))
        for by in range(win_y + 16, win_y + win_h, 18):
            draw.line([(win_x, by), (win_x + win_w, by)], fill="#CBD5E1", width=1)
        # Cozy Wooden Bed Frame with Headboard on left
        bed_x1 = int(w * 0.06)
        bed_x2 = int(w * 0.52)
        bed_y1 = floor_y - int(h * 0.26)
        bed_y2 = floor_y
        # Headboard
        draw.rounded_rectangle([bed_x1, bed_y1 - int(h * 0.12), bed_x1 + max(16, int(w * 0.04)), bed_y2], radius=4, fill="#78350F", outline=fg, width=max(1, lw // 2))
        # Mattress and blanket
        draw.rounded_rectangle([bed_x1 + 10, bed_y1, bed_x2, bed_y2 - 6], radius=6, fill="#E2E8F0", outline=fg, width=max(1, lw // 2))
        draw.rounded_rectangle([bed_x1 + int((bed_x2 - bed_x1) * 0.32), bed_y1, bed_x2, bed_y2 - 6], radius=4, fill="#D97706", outline=fg, width=max(1, lw // 2))
        # Two Fluffy Pillows
        pw, ph = max(24, int(w * 0.09)), max(16, int(h * 0.06))
        draw.ellipse([bed_x1 + 16, bed_y1 - ph + 4, bed_x1 + 16 + pw, bed_y1 + 4], fill="#FFFFFF", outline=fg, width=1)
        # Nightstand table with warm table lamp
        ns_x = bed_x2 + 10
        ns_w = max(28, int(w * 0.10))
        ns_h = int(h * 0.16)
        draw.rectangle([ns_x, floor_y - ns_h, ns_x + ns_w, floor_y], fill="#78350F", outline=fg, width=max(1, lw // 2))
        # Lamp base and warm cone of light
        lx = ns_x + ns_w // 2
        ly = floor_y - ns_h
        draw.line([(lx, ly), (lx, ly - 22)], fill=fg, width=max(2, lw // 2))
        draw.polygon([(lx - 16, ly - 22), (lx + 16, ly - 22), (lx + 10, ly - 38), (lx - 10, ly - 38)], fill="#FDE68A", outline=fg, width=1)
        # Warm ambient lamp glow
        draw.ellipse([lx - 35, ly - 45, lx + 35, ly + 25], fill=(253, 230, 138, 25))
        # Soft bedroom rug on hardwood floor
        draw.rectangle([0, floor_y, w, h], fill="#1E1B2E")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)
        draw.ellipse([int(w * 0.15), floor_y + 8, int(w * 0.85), h - 8], fill="#3B2D54", outline=fg, width=1)

    @classmethod
    def _render_gallery_reflect(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Minimalist studio gallery with dramatic downward spotlight beam and reflective mirror."""
        cls._grad(draw, w, floor_y, "#0F172A", "#1E293B")
        # Dramatic downward spotlight cone from ceiling
        spot_top = w // 2
        draw.polygon([(spot_top - 30, 0), (spot_top + 30, 0), (spot_top + int(w * 0.38), floor_y), (spot_top - int(w * 0.38), floor_y)], fill=(255, 255, 255, 18))
        draw.ellipse([spot_top - int(w * 0.35), floor_y - 20, spot_top + int(w * 0.35), floor_y + 20], fill=(255, 255, 255, 30))
        # Tall Full-Length Floor Mirror on right side
        mx1, my1 = int(w * 0.68), int(h * 0.14)
        mw_m, mh_m = int(w * 0.22), int(h * 0.54)
        draw.rounded_rectangle([mx1, my1, mx1 + mw_m, my1 + mh_m], radius=8, fill="#F8FAFC", outline=fg, width=max(3, lw + 1))
        # Soft reflective surface sheen
        draw.line([(mx1 + 12, my1 + 16), (mx1 + mw_m - 12, my1 + int(mh_m * 0.40))], fill=_hex_to_rgba("#38BDF8", 80), width=2)
        draw.line([(mx1 + 12, my1 + int(mh_m * 0.50)), (mx1 + mw_m - 12, my1 + int(mh_m * 0.85))], fill=_hex_to_rgba("#38BDF8", 50), width=2)
        # Modern art picture frame on left wall
        ax1, ay1 = int(w * 0.08), int(h * 0.18)
        aw_m, ah_m = int(w * 0.24), int(h * 0.22)
        draw.rectangle([ax1, ay1, ax1 + aw_m, ay1 + ah_m], fill="#1E293B", outline=acc, width=max(2, lw // 2))
        draw.ellipse([ax1 + aw_m // 2 - 18, ay1 + ah_m // 2 - 18, ax1 + aw_m // 2 + 18, ay1 + ah_m // 2 + 18], fill=acc)
        # Polished gallery floor with reflection lines
        draw.rectangle([0, floor_y, w, h], fill="#090D16")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)
        for rx in range(int(w * 0.1), w, max(40, w // 8)):
            draw.line([(rx, floor_y), (rx - 25, h)], fill=(255, 255, 255, 15), width=1)

    @classmethod
    def _render_modern_office(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Executive skyscraper office overlooking night city skyline with modern desk and laptop."""
        cls._grad(draw, w, floor_y, "#0F172A", "#1E293B")
        # Panoramic window showing night city skyline
        win_y = int(h * 0.10)
        draw.rectangle([int(w * 0.05), win_y, int(w * 0.95), floor_y - 10], fill="#020617")
        # City skyscraper silhouettes through window
        for sx in range(int(w * 0.08), int(w * 0.92), max(30, int(w * 0.09))):
            sh = rng.randint(int(h * 0.15), int(h * 0.32))
            draw.rectangle([sx, floor_y - 10 - sh, sx + max(22, int(w * 0.08)), floor_y - 10], fill="#1E293B")
            # Window lights
            for ly_row in range(floor_y - 10 - sh + 8, floor_y - 18, 14):
                draw.rectangle([sx + 5, ly_row, sx + 10, ly_row + 5], fill=rng.choice(["#FDE047", "#67E8F9", "#CBD5E1", "#1E293B"]))
        # Office wooden work desk on left
        dk_x1 = int(w * 0.08)
        dk_w = int(w * 0.48)
        dk_y = floor_y - int(h * 0.18)
        draw.rectangle([dk_x1, dk_y, dk_x1 + dk_w, dk_y + 12], fill="#9A3412", outline=fg, width=max(2, lw // 2))
        draw.line([(dk_x1 + 16, dk_y + 12), (dk_x1 + 16, floor_y)], fill=fg, width=max(2, lw // 2))
        draw.line([(dk_x1 + dk_w - 16, dk_y + 12), (dk_x1 + dk_w - 16, floor_y)], fill=fg, width=max(2, lw // 2))
        # Desktop monitor on desk
        mx = dk_x1 + int(dk_w * 0.45)
        my = dk_y - int(h * 0.14)
        mw_mon = max(40, int(w * 0.18))
        mh_mon = max(24, int(h * 0.11))
        draw.rectangle([mx, my, mx + mw_mon, my + mh_mon], fill="#1E293B", outline=fg, width=max(1, lw // 2))
        draw.rectangle([mx + 3, my + 3, mx + mw_mon - 3, my + mh_mon - 3], fill="#38BDF8")
        draw.line([(mx + mw_mon // 2, my + mh_mon), (mx + mw_mon // 2, dk_y)], fill=fg, width=max(2, lw // 2))
        # Potted desk succulent plant
        px = dk_x1 + 24
        draw.polygon([(px - 8, dk_y), (px + 8, dk_y), (px + 6, dk_y - 14), (px - 6, dk_y - 14)], fill="#78350F")
        draw.ellipse([px - 8, dk_y - 24, px + 8, dk_y - 12], fill="#10B981")
        # Polished floor
        draw.rectangle([0, floor_y, w, h], fill="#1C1917")
        draw.line([(0, floor_y), (w, floor_y)], fill=acc, width=lw)

    @classmethod
    def _render_fitness_gym(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Modern athletic fitness studio with dumbbell weight rack and mirrored walls."""
        cls._grad(draw, w, floor_y, "#18181B", "#27272A")
        # Mirrored back wall panels
        draw.rectangle([int(w * 0.05), int(h * 0.12), int(w * 0.95), floor_y - 8], fill="#3F3F46", outline=fg, width=max(2, lw // 2))
        draw.line([(w // 2, int(h * 0.12)), (w // 2, floor_y - 8)], fill=fg, width=max(1, lw // 2))
        # Neon horizontal motivational stripe
        draw.line([(int(w * 0.05), int(h * 0.18)), (int(w * 0.95), int(h * 0.18))], fill="#EF4444", width=3)
        # Dumbbell weight rack on left
        rk_x = int(w * 0.08)
        rk_w = max(50, int(w * 0.28))
        rk_y = floor_y - int(h * 0.18)
        draw.line([(rk_x, rk_y), (rk_x + rk_w, rk_y)], fill="#71717A", width=max(3, lw))
        draw.line([(rk_x + 10, rk_y + int(h * 0.08)), (rk_x + rk_w - 10, rk_y + int(h * 0.08))], fill="#71717A", width=max(3, lw))
        draw.line([(rk_x + 8, rk_y), (rk_x, floor_y)], fill=fg, width=max(2, lw // 2))
        draw.line([(rk_x + rk_w - 8, rk_y), (rk_x + rk_w, floor_y)], fill=fg, width=max(2, lw // 2))
        # Dumbbells on rack
        for dx in range(rk_x + 12, rk_x + rk_w - 14, 20):
            draw.line([(dx, rk_y - 4), (dx + 12, rk_y - 4)], fill="#A1A1AA", width=2)
            draw.ellipse([dx - 2, rk_y - 8, dx + 2, rk_y], fill="#18181B")
            draw.ellipse([dx + 10, rk_y - 8, dx + 14, rk_y], fill="#18181B")
        # Heavy-duty rubber athletic floor with grid lines
        draw.rectangle([0, floor_y, w, h], fill="#09090B")
        draw.line([(0, floor_y), (w, floor_y)], fill="#EF4444", width=lw)
        for gx in range(0, w, max(40, w // 8)):
            draw.line([(gx, floor_y), (gx, h)], fill="#27272A", width=1)

    @classmethod
    def _render_contrast_split(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Dynamic vertical split comparison screen: wrong path (left) vs optimal path (right)."""
        mid_x = w // 2
        # Left negative side (Crimson Red)
        draw.rectangle([0, 0, mid_x, floor_y], fill=(239, 68, 68, 25))
        draw.ellipse([int(w * 0.25) - 20, int(h * 0.16) - 20, int(w * 0.25) + 20, int(h * 0.16) + 20], fill="#EF4444")
        draw.line([(int(w * 0.25) - 8, int(h * 0.16) - 8), (int(w * 0.25) + 8, int(h * 0.16) + 8)], fill="#FFFFFF", width=3)
        draw.line([(int(w * 0.25) + 8, int(h * 0.16) - 8), (int(w * 0.25) - 8, int(h * 0.16) + 8)], fill="#FFFFFF", width=3)
        # Right positive side (Emerald Green)
        draw.rectangle([mid_x, 0, w, floor_y], fill=(16, 185, 129, 25))
        draw.ellipse([int(w * 0.75) - 20, int(h * 0.16) - 20, int(w * 0.75) + 20, int(h * 0.16) + 20], fill="#10B981")
        draw.line([(int(w * 0.75) - 9, int(h * 0.16)), (int(w * 0.75) - 2, int(h * 0.16) + 8), (int(w * 0.75) + 9, int(h * 0.16) - 7)], fill="#FFFFFF", width=3)
        # Dividing center laser line
        draw.line([(mid_x, 0), (mid_x, h)], fill=fg, width=max(3, lw + 1))
        # Floor
        draw.rectangle([0, floor_y, w, h], fill="#1E293B")
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _render_modern_studio(cls, draw, text, w, h, floor_y, sp, sid, fg, acc, acc2, lw, rng):
        """Clean minimalist presentation studio with atmospheric lighting focus."""
        bg = sp.get("bg", "#FFFFFF")
        bg2 = sp.get("bg_secondary", "#E2E8F0")
        cls._grad(draw, w, floor_y, bg, bg2)
        # Center ambient halo
        cx, cy = w // 2, int(h * 0.44)
        rad = int(min(w, h) * 0.35)
        r, g, b = _hex_to_rgb(acc)
        draw.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], fill=(r, g, b, 24), outline=(r, g, b, 60), width=max(1, lw // 2))
        # Clean floor
        draw.rectangle([0, floor_y, w, h], fill=_darken(bg, 0.05))
        draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

    @classmethod
    def _grad(cls, draw: ImageDraw.ImageDraw, w: int, h: int, top: str, bottom: str) -> None:
        tr, tg, tb = _hex_to_rgb(top)
        br, bg, bb = _hex_to_rgb(bottom)
        step = max(1, h // 120)
        for y in range(0, h, step):
            t = y / max(h - 1, 1)
            r = int(tr + (br - tr) * t)
            g = int(tg + (bg - tg) * t)
            b = int(tb + (bb - tb) * t)
            draw.rectangle([0, y, w, min(h, y + step)], fill=(r, g, b, 255))
