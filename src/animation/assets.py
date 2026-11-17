"""
Asset & Scenery Engine - Rich procedural 2D illustration & prop library.
Supports all 11 Director & Autopilot Style Packs (A1-A6, B1-B5) offline:
- 2x LANCZOS-downsampled cached multi-layer backgrounds (zero-cost AA per frame)
- Tight-box 2x supersampled prop sprites (`render_asset_aa`) for razor-sharp vectors
- Animated props (flickering campfires, glowing bulbs, spinning clocks, growing charts,
  steaming coffee, holographic glass UI cards, swinging lanterns, puppet control strings)
"""

from __future__ import annotations

import hashlib
import math
import random
import textwrap
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageDraw, ImageFont

from engine.text_sanitizer import VisualTextSanitizer


# ---------------------------------------------------------------------------
# Colour & Texture Helpers
# ---------------------------------------------------------------------------

def _hex_to_rgba(hex_color: str, alpha: int = 255) -> tuple[int, int, int, int]:
    if not hex_color:
        return (0, 0, 0, alpha)
    h = hex_color.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha
    except Exception:
        return (0, 0, 0, alpha)


def _lighten(hex_color: str, amount: float = 0.3) -> str:
    r, g, b, _ = _hex_to_rgba(hex_color)
    r = int(min(255, r + (255 - r) * amount))
    g = int(min(255, g + (255 - g) * amount))
    b = int(min(255, b + (255 - b) * amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _darken(hex_color: str, amount: float = 0.3) -> str:
    r, g, b, _ = _hex_to_rgba(hex_color)
    r = int(r * (1 - amount))
    g = int(g * (1 - amount))
    b = int(b * (1 - amount))
    return f"#{r:02X}{g:02X}{b:02X}"


def _is_dark_hex(hex_color: str) -> bool:
    r, g, b, _ = _hex_to_rgba(hex_color)
    lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
    return lum < 128


def _load_ui_font(size: int, bold: bool = True) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
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


# ---------------------------------------------------------------------------
# Asset Library
# ---------------------------------------------------------------------------

class AssetLibrary:
    """Draws richly detailed, style-cohesive 2D vector props & environments."""

    _BG_CACHE: dict[tuple[str, int, int, str, str], Image.Image] = {}

    def __init__(self, style_params: dict[str, Any]) -> None:
        self.sp = style_params
        self.style_id = str(style_params.get("id", "a1_classic_bw"))
        self.variant = str(style_params.get("variant", "default"))

    # ------------------------------------------------------------------
    # 2x Supersampled Anti-Aliased Prop Entry Point
    # ------------------------------------------------------------------

    def render_asset_aa(
        self,
        base_img: Image.Image,
        asset_name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Optional[str] = None,
        t: float = 1.0,
    ) -> None:
        """Render prop at 2x resolution onto a tight sprite patch and composite with AA."""
        w = max(8, int(width))
        h = max(8, int(height))

        # Check if caller requested an AI sticker prop
        if asset_name.startswith("AI_") or asset_name.startswith("LCM_"):
            try:
                from engine.lcm_image_engine import LCMImageEngine
                clean_name = asset_name.replace("AI_", "").replace("LCM_", "").lower()
                ai_img = LCMImageEngine.render_object(clean_name, w, h)
                if ai_img is not None:
                    base_img.alpha_composite(ai_img, (int(x), int(y)))
                    return
            except Exception:
                pass

        pad = max(14, int(max(w, h) * 0.35))
        spr_w = w + pad * 2
        spr_h = h + pad * 2
        aa = 2

        hi = Image.new("RGBA", (spr_w * aa, spr_h * aa), (0, 0, 0, 0))
        hi_draw = ImageDraw.Draw(hi)

        saved_lw = self.sp.get("line_width", 4.0)
        self.sp["line_width"] = max(2, int(round(float(saved_lw) * aa * 0.72)))
        try:
            self.draw_asset(
                hi_draw,
                asset_name,
                pad * aa,
                pad * aa,
                w * aa,
                h * aa,
                color=color,
                t=t,
            )
        finally:
            self.sp["line_width"] = saved_lw

        lo = hi.resize((spr_w, spr_h), Image.Resampling.BICUBIC)
        base_img.alpha_composite(lo, (int(x - pad), int(y - pad)))

    def draw_asset(
        self,
        draw: ImageDraw.ImageDraw,
        asset_name: str,
        x: int,
        y: int,
        width: int,
        height: int,
        color: Optional[str] = None,
        t: float = 1.0,
    ) -> None:
        """Draw *asset_name* inside (x, y, x+width, y+height) at progress *t* in [0, 1]."""
        name = asset_name.upper()
        col = color or self.sp.get("accent", "#E94560")
        anim = max(0.0, min(1.0, t))

        dispatchers = {
            "HOUSE":           lambda d, _x, _y, _w, _h: self._draw_house(d, _x, _y, _w, _h),
            "BUILDING":        lambda d, _x, _y, _w, _h: self._draw_building(d, _x, _y, _w, _h),
            "OFFICE":          lambda d, _x, _y, _w, _h: self._draw_office(d, _x, _y, _w, _h),
            "PHONE":           lambda d, _x, _y, _w, _h: self._draw_phone(d, _x, _y, _w, _h, t=anim),
            "MONEY":           lambda d, _x, _y, _w, _h: self._draw_money(d, _x, _y, _w, _h),
            "COIN":            lambda d, _x, _y, _w, _h: self._draw_coin(d, _x, _y, _w, _h, t=anim),
            "CAR":             lambda d, _x, _y, _w, _h: self._draw_car(d, _x, _y, _w, _h),
            "TREE":            lambda d, _x, _y, _w, _h: self._draw_tree(d, _x, _y, _w, _h),
            "TABLE":           lambda d, _x, _y, _w, _h: self._draw_table(d, _x, _y, _w, _h),
            "CHAIR":           lambda d, _x, _y, _w, _h: self._draw_chair(d, _x, _y, _w, _h),
            "LAPTOP":          lambda d, _x, _y, _w, _h: self._draw_laptop(d, _x, _y, _w, _h),
            "GLASS_CARD":      lambda d, _x, _y, _w, _h: self._draw_glass_card(d, _x, _y, _w, _h, t=anim),
            "BOOK":            lambda d, _x, _y, _w, _h: self._draw_book(d, _x, _y, _w, _h),
            "SCROLL":          lambda d, _x, _y, _w, _h: self._draw_scroll(d, _x, _y, _w, _h),
            "CLOCK":           lambda d, _x, _y, _w, _h: self._draw_clock(d, _x, _y, _w, _h, t=anim),
            "LIGHTBULB":       lambda d, _x, _y, _w, _h: self._draw_lightbulb(d, _x, _y, _w, _h, t=anim),
            "HEART":           lambda d, _x, _y, _w, _h: self._draw_heart(d, _x, _y, _w, _h, t=anim),
            "STAR":            lambda d, _x, _y, _w, _h: self._draw_star(d, _x, _y, _w, _h),
            "BAG":             lambda d, _x, _y, _w, _h: self._draw_bag(d, _x, _y, _w, _h),
            "TROPHY":          lambda d, _x, _y, _w, _h: self._draw_trophy(d, _x, _y, _w, _h),
            "CROWN":           lambda d, _x, _y, _w, _h: self._draw_crown(d, _x, _y, _w, _h),
            "SIGN":            lambda d, _x, _y, _w, _h: self._draw_sign(d, _x, _y, _w, _h),
            "ENVELOPE":        lambda d, _x, _y, _w, _h: self._draw_envelope(d, _x, _y, _w, _h),
            "PLANT":           lambda d, _x, _y, _w, _h: self._draw_tree(d, _x, _y, _w, _h),
            "BED":             lambda d, _x, _y, _w, _h: self._draw_bed(d, _x, _y, _w, _h, t=anim),
            "NIGHTSTAND_CLOCK":lambda d, _x, _y, _w, _h: self._draw_nightstand_clock(d, _x, _y, _w, _h, t=anim),
            "THOUGHT_CLOUD":   lambda d, _x, _y, _w, _h: self._draw_thought_cloud(d, _x, _y, _w, _h, t=anim),
            "SPLIT_DIVIDER":   lambda d, _x, _y, _w, _h: self._draw_split_divider(d, _x, _y, _w, _h, t=anim),
            "FOLDER_DOCUMENT": lambda d, _x, _y, _w, _h: self._draw_folder_document(d, _x, _y, _w, _h, t=anim),
            "ALERT_STAMP":     lambda d, _x, _y, _w, _h: self._draw_alert_stamp(d, _x, _y, _w, _h, t=anim),
            "MEGAPHONE":       lambda d, _x, _y, _w, _h: self._draw_megaphone(d, _x, _y, _w, _h, t=anim),
            "CROWD_ROW":       lambda d, _x, _y, _w, _h: self._draw_crowd_row(d, _x, _y, _w, _h, t=anim),
            "DOODLE_ARROW":    lambda d, _x, _y, _w, _h: self._draw_doodle_arrow(d, _x, _y, _w, _h, t=anim),
            "DIYA":            lambda d, _x, _y, _w, _h: self._draw_diya(d, _x, _y, _w, _h, t=anim),
            "CAMPFIRE":        lambda d, _x, _y, _w, _h: self._draw_campfire(d, _x, _y, _w, _h, t=anim),
            "SPEAR":           lambda d, _x, _y, _w, _h: self._draw_spear(d, _x, _y, _w, _h),
            "CLUB":            lambda d, _x, _y, _w, _h: self._draw_spear(d, _x, _y, _w, _h),
            "COFFEE_CUP":      lambda d, _x, _y, _w, _h: self._draw_coffee_cup(d, _x, _y, _w, _h, t=anim),
            "LANTERN":         lambda d, _x, _y, _w, _h: self._draw_lantern(d, _x, _y, _w, _h, t=anim),
            "WARNING":         lambda d, _x, _y, _w, _h: self._draw_warning(d, _x, _y, _w, _h, col),
            "SOCIAL_MEDIA":    lambda d, _x, _y, _w, _h: self._draw_social_icons(d, _x, _y, _w, _h, t=anim),
            "SOCIAL":          lambda d, _x, _y, _w, _h: self._draw_social_icons(d, _x, _y, _w, _h, t=anim),
            "CONTROL_STRINGS": lambda d, _x, _y, _w, _h: self._draw_control_strings(d, _x, _y, _w, _h, t=anim),
            "CHAINS":          lambda d, _x, _y, _w, _h: self._draw_chains(d, _x, _y, _w, _h, t=anim),
            "SPEECH_BUBBLE":   lambda d, _x, _y, _w, _h: self._draw_speech_bubble(d, _x, _y, _w, _h),
            "THOUGHT_BUBBLE":  lambda d, _x, _y, _w, _h: self._draw_thought_bubble(d, _x, _y, _w, _h),
            "ARROW":           lambda d, _x, _y, _w, _h: self._draw_arrow(d, _x, _y + _h // 2, _x + int(_w * min(1.0, 0.25 + anim * 0.9)), _y + _h // 2, col),
            "QUESTION_MARK":   lambda d, _x, _y, _w, _h: self._draw_question_mark(d, _x, _y, min(_w, _h), col),
            "CHECK":           lambda d, _x, _y, _w, _h: self._draw_check_mark(d, _x, _y, min(_w, _h), col),
            "XMARK":           lambda d, _x, _y, _w, _h: self._draw_x_mark(d, _x, _y, min(_w, _h), col),
            "EXCLAMATION":     lambda d, _x, _y, _w, _h: self._draw_exclamation(d, _x, _y, min(_w, _h), col),
            "CHART":           lambda d, _x, _y, _w, _h: self._draw_bar_chart(d, _x, _y, _w, _h, [0.4, 0.7, 0.5, 0.9, 0.6], t=anim),
            "BAR_CHART":       lambda d, _x, _y, _w, _h: self._draw_bar_chart(d, _x, _y, _w, _h, [0.4, 0.7, 0.5, 0.9, 0.6], t=anim),
            "LINE_CHART":      lambda d, _x, _y, _w, _h: self._draw_line_chart(d, _x, _y, _w, _h, [0.2, 0.5, 0.4, 0.8, 0.7, 0.9], t=anim),
            "PIE_CHART":       lambda d, _x, _y, _w, _h: self._draw_pie_chart(d, _x + _w // 2, _y + _h // 2, min(_w, _h) // 2, [0.4, 0.3, 0.2, 0.1]),
            # Physical Metaphors (Created by Atharv Hatwar)
            "LEVER_BOULDER":   lambda d, _x, _y, _w, _h: self._draw_lever_boulder(d, _x, _y, _w, _h, t=anim),
            "ICEBERG":         lambda d, _x, _y, _w, _h: self._draw_iceberg(d, _x, _y, _w, _h, t=anim),
            "HAMSTER_WHEEL":   lambda d, _x, _y, _w, _h: self._draw_hamster_wheel(d, _x, _y, _w, _h, t=anim),
            "JUGGLING_BALLS":  lambda d, _x, _y, _w, _h: self._draw_juggling_balls(d, _x, _y, _w, _h, t=anim),
            "DOMINOES":        lambda d, _x, _y, _w, _h: self._draw_dominoes(d, _x, _y, _w, _h, t=anim),
            "BRICK_WALL":      lambda d, _x, _y, _w, _h: self._draw_brick_wall(d, _x, _y, _w, _h, t=anim),
            "CRACKED_WALL":    lambda d, _x, _y, _w, _h: self._draw_cracked_wall(d, _x, _y, _w, _h, t=anim),
            "BATTERY_DRAIN":   lambda d, _x, _y, _w, _h: self._draw_battery_drain(d, _x, _y, _w, _h, t=anim),
            "BALANCE_SCALE":   lambda d, _x, _y, _w, _h: self._draw_balance_scale(d, _x, _y, _w, _h, t=anim),
            "HOURGLASS":       lambda d, _x, _y, _w, _h: self._draw_hourglass(d, _x, _y, _w, _h, t=anim),
            "PODIUM":          lambda d, _x, _y, _w, _h: self._draw_podium(d, _x, _y, _w, _h, t=anim),
            "SHIELD":          lambda d, _x, _y, _w, _h: self._draw_shield(d, _x, _y, _w, _h, t=anim),
            "MAGNIFYING_GLASS": lambda d, _x, _y, _w, _h: self._draw_magnifying_glass(d, _x, _y, _w, _h, t=anim),
            # Animals & Advanced Storytelling Props (Created by Atharv Hatwar)
            "DOG":             lambda d, _x, _y, _w, _h: self._draw_dog(d, _x, _y, _w, _h, t=anim),
            "PUPPY":           lambda d, _x, _y, _w, _h: self._draw_dog(d, _x, _y, _w, _h, t=anim),
            "CAT":             lambda d, _x, _y, _w, _h: self._draw_cat(d, _x, _y, _w, _h, t=anim),
            "KITTEN":          lambda d, _x, _y, _w, _h: self._draw_cat(d, _x, _y, _w, _h, t=anim),
            "BIRD":            lambda d, _x, _y, _w, _h: self._draw_bird(d, _x, _y, _w, _h, t=anim),
            "HORSE":           lambda d, _x, _y, _w, _h: self._draw_horse(d, _x, _y, _w, _h, t=anim),
            "ROCKET":          lambda d, _x, _y, _w, _h: self._draw_rocket(d, _x, _y, _w, _h, t=anim),
            "BICYCLE":         lambda d, _x, _y, _w, _h: self._draw_bicycle(d, _x, _y, _w, _h, t=anim),
            "BIKE":            lambda d, _x, _y, _w, _h: self._draw_bicycle(d, _x, _y, _w, _h, t=anim),
            "TREASURE_CHEST":  lambda d, _x, _y, _w, _h: self._draw_treasure_chest(d, _x, _y, _w, _h, t=anim),
            "TREASURE":        lambda d, _x, _y, _w, _h: self._draw_treasure_chest(d, _x, _y, _w, _h, t=anim),
            "BRAIN":           lambda d, _x, _y, _w, _h: self._draw_brain(d, _x, _y, _w, _h, t=anim),
            # Advanced Psychological Metaphor Props (Created by Atharv Hatwar)
            "MOUSETRAP":              lambda d, _x, _y, _w, _h: self._draw_mousetrap(d, _x, _y, _w, _h, t=anim),
            "GLASS_JAR_PRISON":       lambda d, _x, _y, _w, _h: self._draw_glass_jar_prison(d, _x, _y, _w, _h, t=anim),
            "TETHER_THREAD":          lambda d, _x, _y, _w, _h: self._draw_tether_thread(d, _x, _y, _w, _h, t=anim),
            "PUPPET_STRINGS":         lambda d, _x, _y, _w, _h: self._draw_puppet_strings(d, _x, _y, _w, _h, t=anim),
            "SIGH_SHOCKWAVES":        lambda d, _x, _y, _w, _h: self._draw_sigh_shockwaves(d, _x, _y, _w, _h, t=anim),
            "DOORWAY_SUNLIGHT":       lambda d, _x, _y, _w, _h: self._draw_doorway_sunlight(d, _x, _y, _w, _h, t=anim),
            "NOTIFICATION_POPUP":     lambda d, _x, _y, _w, _h: self._draw_notification_popups(d, _x, _y, _w, _h, t=anim),
            "BREADCRUMB_TRAIL":       lambda d, _x, _y, _w, _h: self._draw_breadcrumb_trail(d, _x, _y, _w, _h, t=anim),
            "BROKEN_CROWN":           lambda d, _x, _y, _w, _h: self._draw_broken_crown(d, _x, _y, _w, _h, t=anim),
            "GIANT_CLOCK":            lambda d, _x, _y, _w, _h: self._draw_giant_clock(d, _x, _y, _w, _h, t=anim),
            "SNIPPED_THREAD_SUNRISE": lambda d, _x, _y, _w, _h: self._draw_snipped_thread_sunrise(d, _x, _y, _w, _h, t=anim),
            "CHASM_CRACK":            lambda d, _x, _y, _w, _h: self._draw_chasm_crack(d, _x, _y, _w, _h, t=anim),
            "EGO_TROPHY":             lambda d, _x, _y, _w, _h: self._draw_ego_trophy(d, _x, _y, _w, _h, t=anim),
            # Psychological Narrative & Relationship Assets (Atharv Hatwar)
            "MESSAGE_BUBBLE_INCOMING": lambda d, _x, _y, _w, _h: self._draw_message_bubble_incoming(d, _x, _y, _w, _h, t=anim),
            "MESSAGE_BUBBLES_STACK":   lambda d, _x, _y, _w, _h: self._draw_message_bubbles_stack(d, _x, _y, _w, _h, t=anim),
            "SHORT_REPLY_BUBBLE":      lambda d, _x, _y, _w, _h: self._draw_short_reply_bubble(d, _x, _y, _w, _h, t=anim),
            "MISSED_CALL_ICON":        lambda d, _x, _y, _w, _h: self._draw_missed_call_icon(d, _x, _y, _w, _h, t=anim),
            "LIGHTHOUSE_FOG_BEAM":     lambda d, _x, _y, _w, _h: self._draw_lighthouse_fog_beam(d, _x, _y, _w, _h, t=anim),
            "DOPAMINE_SPIKE_CHART":    lambda d, _x, _y, _w, _h: self._draw_dopamine_spike_chart(d, _x, _y, _w, _h, t=anim),
            "SPLIT_MIRROR_IDEAL":      lambda d, _x, _y, _w, _h: self._draw_split_mirror_ideal(d, _x, _y, _w, _h, t=anim),
            "PEDESTAL_BUST_TRAP":      lambda d, _x, _y, _w, _h: self._draw_pedestal_bust_trap(d, _x, _y, _w, _h, t=anim),
        }

        fn = dispatchers.get(name)
        if fn:
            fn(draw, x, y, width, height)
        else:
            try:
                from engine.procedural_object_engine import ProceduralObjectEngine
                ProceduralObjectEngine.draw_object(
                    draw=draw,
                    asset_name=name,
                    x=x,
                    y=y,
                    w=width,
                    h=height,
                    color=col,
                    ink=self._ink(),
                    line_width=int(self.sp.get("line_width", 3)),
                    t=anim,
                )
            except Exception:
                pass

    def _ink(self) -> str:
        fg = self.sp.get("fg", "#111111")
        if self.style_id in ("a6_amber_noir", "b4_survival_thriller") and _is_dark_hex(fg):
            return self.sp.get("accent", "#F59E0B")
        return fg

    # ------------------------------------------------------------------
    # Detailed Stylized Props
    # ------------------------------------------------------------------

    def _draw_house(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#FF6B35")
        acc2 = self.sp.get("accent_secondary", "#4FC3F7")
        lw = max(2, int(self.sp.get("line_width", 3)))

        roof_h = int(h * 0.36)
        body_y = y + roof_h
        body_h = h - roof_h

        # Soft shadow
        draw.rectangle([x + 6, body_y + 4, x + w + 6, y + h + 4], fill=(0, 0, 0, 35))
        # Roof overhang + chimney
        draw.rectangle([x + int(w * 0.68), y + int(roof_h * 0.15), x + int(w * 0.80), body_y], fill=_darken(acc, 0.25), outline=fg, width=lw)
        roof_pts = [(x - 6, body_y), (x + w // 2, y), (x + w + 6, body_y)]
        draw.polygon(roof_pts, fill=acc, outline=fg, width=lw)
        # Body
        wall_fill = _lighten(acc2, 0.75) if self.style_id != "a1_classic_bw" else self.sp.get("head_fill", "#FFFFFF")
        draw.rectangle([x, body_y, x + w, y + h], fill=wall_fill, outline=fg, width=lw)
        # Arched Door
        dw, dh = int(w * 0.22), int(body_h * 0.48)
        dx = x + (w - dw) // 2
        dy = y + h - dh
        draw.rounded_rectangle([dx, dy, dx + dw, y + h], radius=max(3, dw // 3), fill=_darken(acc, 0.15), outline=fg, width=lw)
        # Glowing windows
        ww = max(8, int(w * 0.2))
        for wx in [x + int(w * 0.12), x + w - int(w * 0.12) - ww]:
            wy = body_y + int(body_h * 0.16)
            draw.rectangle([wx, wy, wx + ww, wy + ww], fill="#FEF08A", outline=fg, width=lw)
            draw.line([(wx + ww // 2, wy), (wx + ww // 2, wy + ww)], fill=fg, width=max(1, lw // 2))
            draw.line([(wx, wy + ww // 2), (wx + ww, wy + ww // 2)], fill=fg, width=max(1, lw // 2))

    def _draw_building(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#3B82F6")
        lw = max(2, int(self.sp.get("line_width", 3)))
        fill_c = "#1E293B" if _is_dark_hex(self.sp.get("bg", "#FFFFFF")) else "#E2E8F0"
        draw.rounded_rectangle([x, y, x + w, y + h], radius=4, outline=fg, fill=fill_c, width=lw)
        rows, cols = 5, 3
        pw = max(5, w // (cols * 2 + 1))
        ph = max(5, h // (rows * 2 + 1))
        for r in range(rows):
            for c in range(cols):
                wx = x + (c * 2 + 1) * (w // (cols * 2 + 1))
                wy = y + (r * 2 + 1) * (h // (rows * 2 + 1))
                lit = (r + c) % 3 != 0
                wcol = "#FDE047" if lit else _lighten(acc, 0.4)
                draw.rectangle([wx, wy, wx + pw, wy + ph], fill=wcol, outline=fg, width=max(1, lw // 2))

    def _draw_office(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#06B6D4")
        lw = max(2, int(self.sp.get("line_width", 3)))
        draw.rounded_rectangle([x, y, x + w, y + h], radius=4, outline=fg, fill=_lighten(acc, 0.65), width=lw)
        rows = max(3, h // 22)
        for r in range(1, rows):
            yy = y + r * h // rows
            draw.line([(x, yy), (x + w, yy)], fill=fg, width=max(1, lw // 2))
        cols = max(2, w // 22)
        for c in range(1, cols):
            xx = x + c * w // cols
            draw.line([(xx, y), (xx, y + h)], fill=fg, width=max(1, lw // 2))
        dw = max(12, w // 4)
        draw.rectangle([x + (w - dw) // 2, y + h - h // 5, x + (w + dw) // 2, y + h], outline=fg, fill=acc, width=lw)

    def _draw_phone(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#06B6D4")
        lw = max(2, int(self.sp.get("line_width", 3)))
        r = max(5, w // 5)
        draw.rounded_rectangle([x, y, x + w, y + h], radius=r, outline=fg, fill="#0F172A", width=lw)
        m = max(3, w // 8)
        draw.rounded_rectangle([x + m, y + m * 2, x + w - m, y + h - m * 2], radius=max(2, r // 2), fill=acc, outline=fg, width=max(1, lw // 2))
        # Animated notification glow card on screen
        notif_y = y + m * 3 + int(math.sin(t * math.pi * 2) * (h * 0.04))
        draw.rounded_rectangle([x + m + 3, notif_y, x + w - m - 3, notif_y + max(6, h // 5)], radius=3, fill="#FFFFFF")
        # Speaker notch
        draw.line([(x + w // 2 - w // 7, y + m), (x + w // 2 + w // 7, y + m)], fill="#94A3B8", width=max(2, lw // 2))

    def _draw_money(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        y1 = y + h // 5
        y2 = y + h * 4 // 5
        draw.rounded_rectangle([x, y1, x + w, y2], radius=4, outline=fg, fill="#22C55E", width=lw)
        m = max(3, min(w, h) // 10)
        draw.rounded_rectangle([x + m, y1 + m, x + w - m, y2 - m], radius=2, outline="#DCFCE7", width=max(1, lw // 2))
        cx, cy = x + w // 2, y + h // 2
        cr = max(5, min(w, h) // 5)
        draw.ellipse([cx - cr, cy - cr, cx + cr, cy + cr], fill="#DCFCE7", outline=fg, width=max(1, lw // 2))
        font = _load_ui_font(max(12, int(cr * 1.4)), bold=True)
        draw.text((cx, cy), "$", fill="#14532D", font=font, anchor="mm")

    def _draw_coin(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        spin_w = max(w // 3, int(w * (0.55 + 0.45 * abs(math.cos(t * math.pi * 3)))))
        cx, cy = x + w // 2, y + h // 2
        r_y = h // 2
        r_x = spin_w // 2
        draw.ellipse([cx - r_x, cy - r_y, cx + r_x, cy + r_y], fill="#FACC15", outline=fg, width=lw)
        draw.ellipse([cx - int(r_x * 0.7), cy - int(r_y * 0.7), cx + int(r_x * 0.7), cy + int(r_y * 0.7)], outline="#CA8A04", width=max(1, lw // 2))

    def _draw_car(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#EF4444")
        lw = max(2, int(self.sp.get("line_width", 3)))
        body_y = y + int(h * 0.46)
        draw.rounded_rectangle([x, body_y, x + w, y + h - h // 8], radius=max(5, h // 6), outline=fg, fill=acc, width=lw)
        roof_pts = [
            (x + w // 5, body_y),
            (x + int(w * 0.30), y + h // 6),
            (x + int(w * 0.70), y + h // 6),
            (x + w * 4 // 5, body_y),
        ]
        draw.polygon(roof_pts, outline=fg, fill=_lighten(acc, 0.35), width=lw)
        # Windshield highlight
        draw.polygon([
            (x + w // 4 + 3, body_y - 2),
            (x + int(w * 0.32), y + h // 5 + 3),
            (x + w // 2 - 3, y + h // 5 + 3),
            (x + w // 2 - 3, body_y - 2),
        ], fill="#BAE6FD")
        wr = max(6, h // 5)
        for wx in (x + w // 4, x + w * 3 // 4):
            draw.ellipse([wx - wr, y + h - wr * 2, wx + wr, y + h], fill="#1E293B", outline=fg, width=lw)
            draw.ellipse([wx - wr // 2, y + h - wr * 3 // 2, wx + wr // 2, y + h - wr // 2], fill="#E2E8F0")

    def _draw_tree(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc2 = self.sp.get("accent_secondary", "#16A34A")
        leaf_c = "#22C55E" if self.style_id != "a6_amber_noir" else "#1E293B"
        lw = max(2, int(self.sp.get("line_width", 3)))
        trunk_w = max(7, w // 5)
        trunk_h = int(h * 0.38)
        tx = x + (w - trunk_w) // 2
        draw.rectangle([tx, y + h - trunk_h, tx + trunk_w, y + h], fill="#78350F", outline=fg, width=lw)
        cr = int(w * 0.38)
        cx, cy = x + w // 2, y + h - trunk_h - cr // 2
        for ox, oy, rr, c in [(-cr // 2, cr // 6, int(cr * 0.72), _darken(leaf_c, 0.15)), (cr // 2, cr // 6, int(cr * 0.72), _darken(leaf_c, 0.15)), (0, -cr // 4, cr, leaf_c)]:
            draw.ellipse([cx + ox - rr, cy + oy - rr, cx + ox + rr, cy + oy + rr], fill=c, outline=fg, width=lw)

    def _draw_table(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        if self.style_id == "a4_cozy_storytelling":
            # Round bistro cafe table with pedestal base + open notebook!
            top_ry = max(8, h // 5)
            cx = x + w // 2
            # Pedestal stem + tripod/base
            draw.line([(cx, y + top_ry), (cx, y + h)], fill="#475569", width=max(5, w // 12))
            draw.ellipse([cx - w // 4, y + h - max(6, h // 9), cx + w // 4, y + h], fill="#475569", outline=fg, width=max(1, lw // 2))
            # Soft sage-blue bistro tabletop ellipse
            draw.ellipse([x, y, x + w, y + top_ry * 2], fill="#94B0A7", outline=fg, width=lw)
            # Open white notebook in center of table
            nb_w, nb_h = int(w * 0.44), int(top_ry * 0.9)
            nx1, ny1 = cx - nb_w // 2, y + top_ry - nb_h // 2
            draw.polygon([(nx1, ny1), (nx1 + nb_w, ny1 - 2), (nx1 + nb_w + 5, ny1 + nb_h), (nx1 + 5, ny1 + nb_h + 2)], fill="#FFFDF7", outline=fg, width=max(1, lw // 2))
            draw.line([(cx, ny1), (cx + 3, ny1 + nb_h + 1)], fill="#64748B", width=max(1, lw // 3))
            return

        top_h = max(6, h // 5)
        leg_w = max(5, w // 11)
        draw.rounded_rectangle([x, y, x + w, y + top_h], radius=3, fill="#92400E", outline=fg, width=lw)
        for lx in [x + leg_w, x + w - leg_w * 2]:
            draw.rectangle([lx, y + top_h, lx + leg_w, y + h], fill="#78350F", outline=fg, width=lw)

    def _draw_chair(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        seat_y = y + h // 2
        seat_h = max(5, h // 8)
        leg_w = max(4, w // 8)
        draw.rectangle([x, y, x + leg_w, seat_y + seat_h], fill="#92400E", outline=fg, width=lw)
        draw.rounded_rectangle([x, seat_y, x + w * 3 // 4, seat_y + seat_h], radius=3, fill="#B45309", outline=fg, width=lw)
        for lx in [x + leg_w, x + w * 3 // 4 - leg_w]:
            draw.rectangle([lx, seat_y + seat_h, lx + leg_w, y + h], fill="#78350F", outline=fg, width=lw)

    def _draw_laptop(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#06B6D4")
        lw = max(2, int(self.sp.get("line_width", 3)))
        lid_h = int(h * 0.62)
        m = max(4, w // 12)
        draw.rounded_rectangle([x + m, y, x + w - m, y + lid_h], radius=4, outline=fg, fill="#0F172A", width=lw)
        draw.rectangle([x + m * 2, y + 5, x + w - m * 2, y + lid_h - 5], fill=acc)
        # Glow code lines
        for row in range(3):
            ly = y + 9 + row * max(4, (lid_h - 18) // 3)
            draw.line([(x + m * 2 + 4, ly), (x + w - m * 2 - (4 if row % 2 == 0 else w // 5), ly)], fill="#FFFFFF", width=max(2, lw // 2))
        draw.rounded_rectangle([x, y + lid_h, x + w, y + h], radius=3, outline=fg, fill="#94A3B8", width=lw)

    def _draw_glass_card(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Modern floating UI glass panel for A2 Modern Pop & B5 Explainer."""
        fg = self._ink()
        acc = self.sp.get("accent", "#06B6D4")
        acc2 = self.sp.get("accent_secondary", "#3B82F6")
        lw = max(2, int(self.sp.get("line_width", 3)))
        bob = int(math.sin(t * math.pi * 2) * (h * 0.04))
        yy = y + bob
        draw.rounded_rectangle([x + 4, yy + 6, x + w + 4, yy + h + 6], radius=10, fill=(15, 23, 42, 45))
        draw.rounded_rectangle([x, yy, x + w, yy + h], radius=10, fill=(255, 255, 255, 230), outline=acc, width=lw)
        # Window traffic dots
        r = max(3, min(w, h) // 18)
        for i, c in enumerate(("#EF4444", "#F59E0B", "#22C55E")):
            dx = x + 10 + i * (r * 3)
            dy = yy + 10
            draw.ellipse([dx - r, dy - r, dx + r, dy + r], fill=c)
        # Progress wave / mini bars
        self._draw_bar_chart(draw, x + int(w * 0.14), yy + int(h * 0.30), int(w * 0.72), int(h * 0.56), [0.35, 0.65, 0.5, 0.95], t=t)

    def _draw_book(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#F59E0B")
        lw = max(2, int(self.sp.get("line_width", 3)))
        spine_w = max(7, w // 6)
        draw.rounded_rectangle([x, y, x + w, y + h], radius=4, fill=acc, outline=fg, width=lw)
        draw.rectangle([x, y, x + spine_w, y + h], fill=_darken(acc, 0.3), outline=fg, width=lw)
        draw.rectangle([x + spine_w + 5, y + int(h * 0.2), x + w - 6, y + int(h * 0.45)], fill="#FFFBEB", outline=fg, width=max(1, lw // 2))

    def _draw_scroll(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        """Historical parchment scroll for A5 Historical Cartoon."""
        fg = self._ink()
        acc = self.sp.get("accent", "#B91C1C")
        lw = max(2, int(self.sp.get("line_width", 3)))
        m = max(5, h // 7)
        draw.rounded_rectangle([x + m, y + m, x + w - m, y + h - m], radius=3, fill="#FEF3C7", outline=fg, width=lw)
        # Rolled top & bottom cylinders
        draw.rounded_rectangle([x, y, x + w, y + m * 2], radius=m, fill="#FDE68A", outline=fg, width=lw)
        draw.rounded_rectangle([x, y + h - m * 2, x + w, y + h], radius=m, fill="#FDE68A", outline=fg, width=lw)
        # Ink text lines + wax seal
        for r in range(3):
            ly = y + m * 2 + 8 + r * max(6, (h - m * 4) // 4)
            draw.line([(x + m * 2, ly), (x + w - m * 2, ly)], fill="#78350F", width=max(2, lw // 2))
        sr = max(5, min(w, h) // 8)
        draw.ellipse([x + w - m * 2 - sr, y + h - m * 2 - sr, x + w - m * 2 + sr, y + h - m * 2 + sr], fill=acc, outline=fg, width=max(1, lw // 2))

    def _draw_campfire(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Crackling animated prehistoric campfire for A3 Prehistoric Cave."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx = x + w // 2
        base_y = y + int(h * 0.86)
        flicker = math.sin(t * math.pi * 8) * (w * 0.08)
        flicker2 = math.cos(t * math.pi * 10) * (h * 0.06)

        # Warm ambient fire glow
        draw.ellipse([x - w // 4, y - h // 6, x + w + w // 4, y + h], fill=(249, 115, 22, 48))

        # Outer orange flame
        draw.polygon([
            (cx - int(w * 0.34), base_y),
            (cx - int(w * 0.25), y + int(h * 0.38)),
            (cx + int(flicker), y + int(flicker2)),
            (cx + int(w * 0.28), y + int(h * 0.35)),
            (cx + int(w * 0.34), base_y),
        ], fill="#F97316", outline=fg, width=max(1, lw // 2))
        # Inner gold-yellow flame core
        draw.polygon([
            (cx - int(w * 0.18), base_y),
            (cx - int(w * 0.12), y + int(h * 0.52)),
            (cx - int(flicker * 0.6), y + int(h * 0.22 - flicker2 * 0.5)),
            (cx + int(w * 0.15), y + int(h * 0.50)),
            (cx + int(w * 0.18), base_y),
        ], fill="#FACC15")

        # Crossed charred logs
        log_h = max(6, h // 7)
        draw.line([(x + int(w * 0.1), base_y - 2), (x + int(w * 0.9), base_y + log_h)], fill="#5C3A21", width=log_h)
        draw.line([(x + int(w * 0.9), base_y - 2), (x + int(w * 0.1), base_y + log_h)], fill="#7C4D2B", width=log_h)

    def _draw_spear(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        """Primitive flint spear for A3 Prehistoric Cave."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        draw.line([(x + int(w * 0.15), y + h), (x + int(w * 0.80), y + int(h * 0.22))], fill="#78350F", width=max(4, lw))
        # Flint arrowhead
        tx, ty = x + int(w * 0.86), y + int(h * 0.12)
        draw.polygon([
            (tx, ty),
            (tx - int(w * 0.22), ty + int(h * 0.08)),
            (tx - int(w * 0.08), ty + int(h * 0.26)),
        ], fill="#94A3B8", outline=fg, width=max(1, lw // 2))

    def _draw_coffee_cup(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Warm steaming cup for A4 Cozy Storytelling."""
        fg = self._ink()
        acc = self.sp.get("accent", "#EA580C")
        lw = max(2, int(self.sp.get("line_width", 3)))
        cup_y = y + int(h * 0.34)
        cup_w = int(w * 0.72)
        # Rising gentle steam curls
        for idx in range(2):
            sx = x + cup_w // 3 + idx * (cup_w // 3)
            wave = math.sin(t * math.pi * 4 + idx) * (w * 0.06)
            draw.line([
                (sx, cup_y - 4),
                (sx + wave, cup_y - int(h * 0.16)),
                (sx - wave, y + 4),
            ], fill=(255, 255, 255, 190), width=max(2, lw // 2), joint="curve")
        # Handle + cup body
        draw.arc([x + cup_w - 6, cup_y + 6, x + w, y + h - 8], start=-90, end=90, fill=fg, width=lw)
        draw.rounded_rectangle([x, cup_y, x + cup_w, y + h], radius=max(5, cup_w // 5), fill="#FFFBEB", outline=fg, width=lw)
        draw.rectangle([x + 3, cup_y + int((h * 0.66) * 0.35), x + cup_w - 3, cup_y + int((h * 0.66) * 0.65)], fill=acc)

    def _draw_lantern(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Warm amber/yellow lantern for A6 Amber Noir / B4 Survival Thriller."""
        fg = self._ink()
        glow = "#F59E0B"
        lw = max(2, int(self.sp.get("line_width", 3)))
        pulse = 0.85 + 0.15 * math.sin(t * math.pi * 6)
        cx, cy = x + w // 2, y + int(h * 0.58)
        gr = int(max(w, h) * 0.65 * pulse)
        draw.ellipse([cx - gr, cy - gr, cx + gr, cy + gr], fill=(245, 158, 11, 55))
        draw.arc([x + w // 4, y, x + w * 3 // 4, y + h // 3], start=180, end=360, fill=fg, width=lw)
        draw.rounded_rectangle([x + w // 5, y + h // 4, x + w * 4 // 5, y + int(h * 0.88)], radius=5, fill="#FEF08A", outline=fg, width=lw)
        draw.rectangle([x + w // 8, y + int(h * 0.88), x + w * 7 // 8, y + h], fill="#1E293B", outline=fg, width=lw)

    def _draw_warning(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, color: str) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        pts = [(x + w // 2, y), (x + w, y + h), (x, y + h)]
        draw.polygon(pts, fill="#EF4444", outline=fg, width=lw)
        draw.line([(x + w // 2, y + int(h * 0.34)), (x + w // 2, y + int(h * 0.68))], fill="#FFFFFF", width=max(3, lw))
        r = max(2, lw // 2 + 1)
        cy = y + int(h * 0.82)
        draw.ellipse([x + w // 2 - r, cy - r, x + w // 2 + r, cy + r], fill="#FFFFFF")

    def _draw_clock(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.0) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#EF4444")
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FFFDF9", outline=fg, width=lw)
        for i in range(12):
            ang = math.radians(i * 30 - 90)
            ix, iy = cx + int((r - 4) * math.cos(ang)), cy + int((r - 4) * math.sin(ang))
            ox, oy = cx + int((r - 9) * math.cos(ang)), cy + int((r - 9) * math.sin(ang))
            draw.line([(ix, iy), (ox, oy)], fill=fg, width=max(1, lw // 2))
        for deg, ratio, col in [(300 + t * 90.0, 0.52, fg), (t * 720.0, 0.74, acc)]:
            ang = math.radians(deg - 90)
            draw.line([(cx, cy), (cx + int(r * ratio * math.cos(ang)), cy + int(r * ratio * math.sin(ang)))], fill=col, width=lw)

    def _draw_lightbulb(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        fg = self._ink()
        acc = "#FACC15"
        lw = max(2, int(self.sp.get("line_width", 3)))
        bulb_h = int(h * 0.65)
        cx, cy = x + w // 2, y + bulb_h // 2
        if t > 0.15:
            draw.ellipse([cx - int(w * 0.72), cy - int(bulb_h * 0.72), cx + int(w * 0.72), cy + int(bulb_h * 0.72)], fill=(250, 204, 21, 60))
            ray_pulse = 0.6 + 0.4 * abs(math.sin(t * math.pi * 4.0))
            for i in range(8):
                ang = math.radians(i * 45)
                r1, r2 = int(w * 0.58), int(w * (0.72 + 0.18 * ray_pulse))
                draw.line([
                    (cx + int(r1 * math.cos(ang)), cy + int(r1 * math.sin(ang))),
                    (cx + int(r2 * math.cos(ang)), cy + int(r2 * math.sin(ang))),
                ], fill=acc, width=max(2, lw))
        draw.ellipse([x, y, x + w, y + bulb_h], fill="#FEF08A", outline=fg, width=lw)
        bw = int(w * 0.48)
        bx = x + (w - bw) // 2
        for i in range(3):
            by = y + bulb_h + i * max(3, h // 10)
            draw.rectangle([bx, by, bx + bw, by + max(3, h // 10)], fill="#CBD5E1", outline=fg, width=max(1, lw // 2))
        draw.arc([x + w // 4, y + h // 8, x + w * 3 // 4, y + bulb_h * 2 // 3], start=200, end=260, fill="#FFFFFF", width=max(2, lw // 2))

    def _draw_heart(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        acc = self.sp.get("accent", "#F43F5E")
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx, cy = x + w // 2, y + h // 2
        pulse = 1.0 + 0.07 * math.sin(t * math.pi * 4)
        pts = []
        for deg in range(0, 360, 5):
            a = math.radians(deg)
            px = 16 * math.sin(a) ** 3
            py = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
            pts.append((cx + int(px * w * pulse / 34), cy + int(py * h * pulse / 26)))
        draw.polygon(pts, fill=acc, outline=fg, width=lw)

    def _draw_star(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        acc = "#FACC15"
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx, cy = x + w // 2, y + h // 2
        outer, inner = min(w, h) // 2, min(w, h) // 4
        pts = []
        for i in range(10):
            ang = math.radians(i * 36 - 90)
            r = outer if i % 2 == 0 else inner
            pts.append((cx + int(r * math.cos(ang)), cy + int(r * math.sin(ang))))
        draw.polygon(pts, fill=acc, outline=fg, width=lw)

    # ------------------------------------------------------------------
    # Speech & Thought Bubbles
    # ------------------------------------------------------------------

    def _draw_speech_bubble(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str = "",
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> None:
        head_dark = _is_dark_hex(self.sp.get("head_fill", "#FFFFFF"))
        dark_bubble = head_dark and _is_dark_hex(self.sp.get("bg", "#FFFFFF"))
        b_bg = "#1A1625" if dark_bubble else "#FFFDF8"
        b_fg = "#FFFFFF" if dark_bubble else "#111827"
        b_outline = self.sp.get("accent", "#F59E0B") if dark_bubble else "#18181B"
        lw = max(2, int(self.sp.get("line_width", 3)))
        r = max(10, min(w, h) // 5)
        bubble_h = max(14, h - h // 4)

        # Subtle drop shadow
        draw.rounded_rectangle([x + 3, y + 4, x + w + 3, y + bubble_h + 4], radius=r, fill=(0, 0, 0, 50))
        draw.rounded_rectangle([x, y, x + w, y + bubble_h], radius=r, fill=b_bg, outline=b_outline, width=lw)
        tail_pts = [(x + w // 3, y + bubble_h - 1), (x + w // 3 + w // 9, y + bubble_h - 1), (x + w // 4, y + h)]
        draw.polygon(tail_pts, fill=b_bg, outline=b_outline, width=lw)
        draw.line([(x + w // 3 + 2, y + bubble_h), (x + w // 3 + w // 9 - 2, y + bubble_h)], fill=b_bg, width=lw + 2)

        self._draw_fitted_bubble_text(draw, x, y, w, bubble_h, text, b_fg, kind="speech")

    def _draw_fitted_bubble_text(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        bubble_h: int,
        text: str,
        fg_col: str,
        kind: str = "speech",
    ) -> None:
        """Render perfectly fitted multi-line text that strictly never overflows bubble bounds."""
        clean_text = VisualTextSanitizer.sanitize_bubble_text(text, kind=kind)
        if not clean_text:
            return

        avail_w = max(30, int(w * 0.86))
        avail_h = max(16, int(bubble_h * 0.78))

        best_font = None
        best_lines: list[str] = [clean_text]
        font_sz = max(10, min(24, int(avail_h * 0.52)))

        while font_sz >= 9:
            curr_font = _load_ui_font(font_sz, bold=True)
            avg_cw = max(5.0, curr_font.getlength("m") * 0.72)
            wrap_chars = max(8, int(avail_w / avg_cw))
            cand_lines = textwrap.wrap(clean_text, width=wrap_chars) or [clean_text]

            max_lw = max((curr_font.getlength(ln) for ln in cand_lines), default=0)
            line_sp = int(font_sz * 1.22)
            total_th = len(cand_lines) * line_sp

            if max_lw <= avail_w and total_th <= avail_h:
                best_font = curr_font
                best_lines = cand_lines
                break
            font_sz -= 1

        if best_font is None:
            font_sz = 9
            best_font = _load_ui_font(font_sz, bold=True)
            avg_cw = max(5.0, best_font.getlength("m") * 0.72)
            wrap_chars = max(8, int(avail_w / avg_cw))
            best_lines = textwrap.wrap(clean_text, width=wrap_chars) or [clean_text]
            max_lines = max(1, avail_h // int(font_sz * 1.22))
            if len(best_lines) > max_lines:
                best_lines = best_lines[:max_lines]
                if len(best_lines[-1]) > 3:
                    best_lines[-1] = best_lines[-1][:-2] + "…"

        line_spacing = int(font_sz * 1.22)
        total_text_h = len(best_lines) * line_spacing
        start_y = y + max(3, (bubble_h - total_text_h) // 2 + font_sz // 2)
        cx = x + w // 2
        for i, line in enumerate(best_lines):
            ly = start_y + i * line_spacing
            draw.text((cx, ly), line, fill=fg_col, font=best_font, anchor="mm")

    def _draw_thought_bubble(
        self,
        draw: ImageDraw.ImageDraw,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str = "",
        font: Optional[ImageFont.FreeTypeFont] = None,
    ) -> None:
        head_dark = _is_dark_hex(self.sp.get("head_fill", "#FFFFFF"))
        dark_bubble = head_dark and _is_dark_hex(self.sp.get("bg", "#FFFFFF"))
        b_bg = "#1A1625" if dark_bubble else "#FFFDF8"
        b_fg = "#FFFFFF" if dark_bubble else "#111827"
        b_outline = self.sp.get("accent", "#F59E0B") if dark_bubble else "#18181B"
        lw = max(2, int(self.sp.get("line_width", 3)))
        bubble_h = max(14, h - h // 4)

        draw.rounded_rectangle([x + 3, y + 4, x + w + 3, y + bubble_h + 4], radius=max(10, min(w, h) // 4), fill=(0, 0, 0, 45))
        draw.rounded_rectangle([x, y, x + w, y + bubble_h], radius=max(10, min(w, h) // 4), fill=b_bg, outline=b_outline, width=lw)
        for cr, cx_off, cy_off in [(5, w // 3, bubble_h + h // 10), (7, w // 4, bubble_h + h // 4), (4, w // 5, bubble_h + h // 3)]:
            bcx, bcy = x + cx_off, y + cy_off
            draw.ellipse([bcx - cr, bcy - cr, bcx + cr, bcy + cr], fill=b_bg, outline=b_outline, width=max(1, lw // 2))
        self._draw_fitted_bubble_text(draw, x, y, w, bubble_h, text, b_fg, kind="thought")

    # ------------------------------------------------------------------
    # Data & Symbolic Graphics
    # ------------------------------------------------------------------

    def _draw_arrow(self, draw: ImageDraw.ImageDraw, x1: int, y1: int, x2: int, y2: int, color: str) -> None:
        lw = max(3, int(self.sp.get("line_width", 3)))
        draw.line([(x1, y1), (x2, y2)], fill=color, width=lw)
        angle = math.atan2(y2 - y1, x2 - x1)
        hl = max(12, lw * 3)
        for side in (0.45, -0.45):
            draw.line([(x2, y2), (x2 - int(hl * math.cos(angle - side)), y2 - int(hl * math.sin(angle - side)))], fill=color, width=lw)

    def _draw_check_mark(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str) -> None:
        lw = max(3, int(self.sp.get("line_width", 3)) + 1)
        c = "#22C55E" if color == "#111111" else color
        draw.line([(x + int(size * 0.12), y + int(size * 0.52)), (x + int(size * 0.42), y + int(size * 0.80)), (x + int(size * 0.88), y + int(size * 0.22))], fill=c, width=lw, joint="curve")

    def _draw_x_mark(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str) -> None:
        lw = max(3, int(self.sp.get("line_width", 3)) + 1)
        m = int(size * 0.14)
        draw.line([(x + m, y + m), (x + size - m, y + size - m)], fill=color, width=lw)
        draw.line([(x + size - m, y + m), (x + m, y + size - m)], fill=color, width=lw)

    def _draw_exclamation(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str) -> None:
        lw = max(3, int(self.sp.get("line_width", 3)))
        cx = x + size // 2
        draw.rounded_rectangle([cx - lw, y + int(size * 0.1), cx + lw, y + int(size * 0.64)], radius=lw, fill=color)
        dr = max(3, lw + 1)
        cy = y + int(size * 0.82)
        draw.ellipse([cx - dr, cy - dr, cx + dr, cy + dr], fill=color)

    def _draw_question_mark(self, draw: ImageDraw.ImageDraw, x: int, y: int, size: int, color: str) -> None:
        lw = max(3, int(self.sp.get("line_width", 3)) + 1)
        cx = x + size // 2
        r = max(6, size // 4)
        draw.arc([cx - r, y + int(size * 0.1), cx + r, y + int(size * 0.52)], start=180, end=45, fill=color, width=lw)
        draw.line([(cx, y + int(size * 0.46)), (cx, y + int(size * 0.66))], fill=color, width=lw)
        dr = max(3, lw // 2 + 1)
        draw.ellipse([cx - dr, y + int(size * 0.80) - dr, cx + dr, y + int(size * 0.80) + dr], fill=color)

    def _draw_bar_chart(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, values: list[float], t: float = 1.0) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#3B82F6")
        lw = max(2, int(self.sp.get("line_width", 3)))
        values = values[:5]
        n = len(values)
        mx = max(values) if values else 1.0
        bar_w = max(6, w // (n * 2 + 1))
        growth = min(1.0, max(0.08, t * 1.4))
        for i, v in enumerate(values):
            lg = max(0.05, min(1.0, (growth - i * 0.08) / 0.65))
            bh = max(3, int((v / mx) * (h - 12) * lg))
            bx = x + (i * 2 + 1) * (w // (n * 2 + 1))
            by = y + h - bh
            draw.rounded_rectangle([bx, by, bx + bar_w, y + h], radius=3, fill=_lighten(acc, i * 0.09), outline=fg, width=max(1, lw // 2))
        draw.line([(x, y), (x, y + h), (x + w, y + h)], fill=fg, width=lw)

    def _draw_line_chart(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, values: list[float], t: float = 1.0) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#06B6D4")
        lw = max(2, int(self.sp.get("line_width", 3)))
        if not values:
            return
        mx, mn = max(values), min(values)
        rng = max(mx - mn, 0.001)
        n = len(values)
        pts = [(x + (int(i * w / (n - 1)) if n > 1 else w // 2), y + h - int(((v - mn) / rng) * (h - 12)) - 6) for i, v in enumerate(values)]
        shown = pts[: max(2, int(math.ceil(len(pts) * min(1.0, t * 1.3))))]
        if len(shown) > 1:
            draw.line(shown, fill=acc, width=lw + 2, joint="curve")
        for px, py in shown:
            r = max(3, lw)
            draw.ellipse([px - r, py - r, px + r, py + r], fill="#FFFFFF", outline=acc, width=lw)
        draw.line([(x, y), (x, y + h), (x + w, y + h)], fill=fg, width=lw)

    def _draw_pie_chart(self, draw: ImageDraw.ImageDraw, cx: int, cy: int, radius: int, slices: list[float]) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#6366F1")
        acc2 = self.sp.get("accent_secondary", "#F59E0B")
        lw = max(2, int(self.sp.get("line_width", 3)))
        palette = [acc, acc2, _lighten(acc, 0.35), _darken(acc2, 0.25)]
        total = sum(slices[:4]) or 1.0
        start = -90.0
        for i, s in enumerate(slices[:4]):
            sweep = (s / total) * 360.0
            draw.pieslice([cx - radius, cy - radius, cx + radius, cy + radius], start=start, end=start + sweep, fill=palette[i % len(palette)], outline=fg, width=lw)
            start += sweep

    def _draw_bag(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#D97706")
        lw = max(2, int(self.sp.get("line_width", 3)))
        by = y + h // 4
        draw.rounded_rectangle([x, by, x + w, y + h], radius=max(5, w // 7), fill=acc, outline=fg, width=lw)
        draw.arc([x + w // 4, y, x + w * 3 // 4, by + h // 4], start=180, end=360, fill=fg, width=lw)

    def _draw_trophy(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        ch = int(h * 0.56)
        draw.polygon([(x + w // 6, y), (x + w * 5 // 6, y), (x + w * 2 // 3, y + ch), (x + w // 3, y + ch)], fill="#FACC15", outline=fg, width=lw)
        draw.line([(x + w // 2, y + ch), (x + w // 2, y + int(h * 0.85))], fill=fg, width=lw + 1)
        draw.rounded_rectangle([x + w // 4, y + int(h * 0.85), x + w * 3 // 4, y + h], radius=3, fill="#B45309", outline=fg, width=lw)

    def _draw_crown(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        pts = [(x, y + h), (x + w // 8, y + h // 4), (x + w * 3 // 8, y + h * 2 // 3), (x + w // 2, y + h // 8), (x + w * 5 // 8, y + h * 2 // 3), (x + w * 7 // 8, y + h // 4), (x + w, y + h)]
        draw.polygon(pts, fill="#FACC15", outline=fg, width=lw)

    def _draw_sign(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#F59E0B")
        lw = max(2, int(self.sp.get("line_width", 3)))
        bh = int(h * 0.56)
        draw.rounded_rectangle([x, y, x + w, y + bh], radius=4, fill=_lighten(acc, 0.5), outline=fg, width=lw)
        draw.line([(x + w // 2, y + bh), (x + w // 2, y + h)], fill=fg, width=lw + 1)

    def _draw_envelope(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int) -> None:
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        draw.rounded_rectangle([x, y + h // 6, x + w, y + h * 5 // 6], radius=4, fill="#FFFBEB", outline=fg, width=lw)
        draw.line([(x, y + h // 6), (x + w // 2, y + h // 2), (x + w, y + h // 6)], fill=fg, width=lw)

    def _draw_social_icons(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#E94560")
        acc2 = self.sp.get("accent_secondary", "#3B82F6")
        lw = max(2, int(self.sp.get("line_width", 3)))
        sz = max(18, min(w, h) // 2)
        bob1 = int(math.sin(t * math.pi * 4) * 7)
        bob2 = int(math.cos(t * math.pi * 4) * 7)
        draw.rounded_rectangle([x, y + bob1, x + sz, y + sz + bob1], radius=max(6, sz // 4), fill=acc, outline=fg, width=lw)
        self._draw_heart(draw, x + sz // 5, y + sz // 5 + bob1, sz * 3 // 5, sz * 3 // 5, t=t)
        bx, by = x + w - sz, y + h - sz + bob2
        draw.rounded_rectangle([bx, by, bx + sz, by + sz], radius=max(6, sz // 4), fill=acc2, outline=fg, width=lw)
        self._draw_star(draw, bx + sz // 5, by + sz // 5, sz * 3 // 5, sz * 3 // 5)

    def _draw_control_strings(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        acc = self.sp.get("accent", "#E94560")
        lw = max(2, int(self.sp.get("line_width", 3)))
        tilt = int(math.sin(t * math.pi * 3) * (h * 0.09))
        draw.line([(x + w // 5, y + tilt), (x + w * 4 // 5, y - tilt)], fill=acc, width=lw + 2)
        for idx, dx in enumerate((0.28, 0.50, 0.72)):
            sx = x + int(w * dx)
            sy = y + (tilt if idx == 0 else (-tilt if idx == 2 else 0))
            ex = sx + (w // 10 if dx < 0.5 else (-w // 10 if dx > 0.5 else 0))
            draw.line([(sx, sy), (ex, y + h)], fill=acc, width=max(2, lw // 2 + 1))

    def _draw_chains(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        fg = self._ink()
        acc = self.sp.get("accent", "#E94560")
        lw = max(2, int(self.sp.get("line_width", 3)))
        links = 4
        link_w = max(16, w // links)
        link_h = max(12, h // 3)
        cy = y + h // 2
        for i in range(links):
            lx = x + i * (link_w - 5)
            col = acc if i % 2 else fg
            draw.rounded_rectangle([lx, cy - link_h // 2, lx + link_w, cy + link_h // 2], radius=link_h // 2, outline=col, width=lw)

    # ------------------------------------------------------------------
    # Procedural Animals & Dynamic Story Props (Created by Atharv Hatwar)
    # ------------------------------------------------------------------

    def _draw_dog(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Procedural stickman-companion dog with wagging tail and floppy ears."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        acc = self.sp.get("accent", "#F59E0B")
        bx1, by1 = x + int(w * 0.20), y + int(h * 0.40)
        bx2, by2 = x + int(w * 0.70), y + int(h * 0.70)
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=max(6, int(h * 0.15)), fill=acc, outline=fg, width=lw)
        hx1, hy1 = x + int(w * 0.60), y + int(h * 0.20)
        hx2, hy2 = x + int(w * 0.95), y + int(h * 0.55)
        draw.rounded_rectangle([hx1, hy1, hx2, hy2], radius=max(6, int(h * 0.15)), fill=acc, outline=fg, width=lw)
        draw.polygon([(x + int(w * 0.68), y + int(h * 0.22)), (x + int(w * 0.60), y + int(h * 0.45)), (x + int(w * 0.76), y + int(h * 0.35))], fill=_darken(acc, 0.2), outline=fg)
        draw.ellipse([x + int(w * 0.80), y + int(h * 0.28), x + int(w * 0.84), y + int(h * 0.34)], fill=fg)
        draw.ellipse([x + int(w * 0.90), y + int(h * 0.38), x + int(w * 0.96), y + int(h * 0.44)], fill="#1E1E1E")
        draw.line([(x + int(w * 0.66), y + int(h * 0.45)), (x + int(w * 0.72), y + int(h * 0.55))], fill="#EF4444", width=max(3, lw + 1))
        draw.line([(x + int(w * 0.28), by2), (x + int(w * 0.28), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.38), by2), (x + int(w * 0.38), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.58), by2), (x + int(w * 0.58), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.68), by2), (x + int(w * 0.68), y + h)], fill=fg, width=lw)
        wag = math.sin(t * math.pi * 8.0) * 8
        draw.line([(bx1, by1 + 6), (x + int(w * 0.08), y + int(h * 0.25) + int(wag))], fill=fg, width=lw)

    def _draw_cat(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Procedural stickman-companion cat with pointy ears and arched tail."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        acc = self.sp.get("accent_secondary", "#38BDF8")
        bx1, by1 = x + int(w * 0.25), y + int(h * 0.45)
        bx2, by2 = x + int(w * 0.70), y + int(h * 0.72)
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=max(5, int(h * 0.12)), fill=acc, outline=fg, width=lw)
        hx, hy = x + int(w * 0.75), y + int(h * 0.38)
        hr = int(min(w, h) * 0.20)
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=acc, outline=fg, width=lw)
        draw.polygon([(hx - hr + 2, hy - hr + 4), (hx - hr + 4, hy - hr - 8), (hx, hy - hr + 3)], fill=_darken(acc, 0.2), outline=fg)
        draw.polygon([(hx, hy - hr + 3), (hx + hr - 4, hy - hr - 8), (hx + hr - 2, hy - hr + 4)], fill=_darken(acc, 0.2), outline=fg)
        draw.line([(hx + hr - 2, hy), (hx + hr + 12, hy - 4)], fill=fg, width=1)
        draw.line([(hx + hr - 2, hy + 3), (hx + hr + 12, hy + 5)], fill=fg, width=1)
        draw.ellipse([hx + 2, hy - 3, hx + 6, hy + 1], fill=fg)
        draw.line([(x + int(w * 0.32), by2), (x + int(w * 0.32), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.62), by2), (x + int(w * 0.62), y + h)], fill=fg, width=lw)
        twag = math.sin(t * math.pi * 4.0) * 6
        draw.arc([x + int(w * 0.05), y + int(h * 0.20) + int(twag), bx1 + 10, by2], start=160, end=320, fill=fg, width=lw)

    def _draw_bird(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Flying bird silhouette with flapping wings."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx, cy = x + w // 2, y + h // 2
        flap = math.sin(t * math.pi * 10.0) * (h * 0.32)
        draw.line([(cx - w // 2, cy - int(flap)), (cx, cy), (cx + w // 2, cy - int(flap))], fill=fg, width=lw)
        draw.ellipse([cx - 4, cy - 3, cx + 4, cy + 3], fill=fg)

    def _draw_horse(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Regal horse silhouette with mane and hooves."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        acc = self.sp.get("accent", "#8B5CF6")
        bx1, by1 = x + int(w * 0.22), y + int(h * 0.36)
        bx2, by2 = x + int(w * 0.72), y + int(h * 0.64)
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=10, fill=_lighten(acc, 0.4), outline=fg, width=lw)
        neck_pts = [
            (x + int(w * 0.65), by1),
            (x + int(w * 0.82), y + int(h * 0.12)),
            (x + int(w * 0.94), y + int(h * 0.24)),
            (x + int(w * 0.76), by2 - 4),
        ]
        draw.polygon(neck_pts, fill=_lighten(acc, 0.4), outline=fg, width=lw)
        draw.line([(x + int(w * 0.68), by1), (x + int(w * 0.80), y + int(h * 0.14))], fill=fg, width=lw + 2)
        draw.line([(x + int(w * 0.30), by2), (x + int(w * 0.28), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.42), by2), (x + int(w * 0.40), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.62), by2), (x + int(w * 0.62), y + h)], fill=fg, width=lw)
        draw.line([(x + int(w * 0.72), by2), (x + int(w * 0.74), y + h)], fill=fg, width=lw)

    def _draw_rocket(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Dynamic space rocket with flame thruster."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        cx = x + w // 2
        body_w = int(w * 0.45)
        body_pts = [
            (cx, y),
            (cx + body_w // 2, y + int(h * 0.30)),
            (cx + body_w // 2, y + int(h * 0.75)),
            (cx - body_w // 2, y + int(h * 0.75)),
            (cx - body_w // 2, y + int(h * 0.30)),
        ]
        draw.polygon(body_pts, fill="#F8FAFC", outline=fg, width=lw)
        pr = int(body_w * 0.26)
        draw.ellipse([cx - pr, y + int(h * 0.42) - pr, cx + pr, y + int(h * 0.42) + pr], fill="#38BDF8", outline=fg, width=lw)
        draw.polygon([(cx - body_w // 2, y + int(h * 0.55)), (x, y + int(h * 0.82)), (cx - body_w // 2, y + int(h * 0.75))], fill="#EF4444", outline=fg, width=lw)
        draw.polygon([(cx + body_w // 2, y + int(h * 0.55)), (x + w, y + int(h * 0.82)), (cx + body_w // 2, y + int(h * 0.75))], fill="#EF4444", outline=fg, width=lw)
        flame_len = int(h * 0.22) + int(math.sin(t * math.pi * 12.0) * (h * 0.08))
        draw.polygon([(cx - body_w // 3, y + int(h * 0.75)), (cx, y + int(h * 0.75) + flame_len), (cx + body_w // 3, y + int(h * 0.75))], fill="#F59E0B")
        draw.polygon([(cx - body_w // 5, y + int(h * 0.75)), (cx, y + int(h * 0.75) + int(flame_len * 0.65)), (cx + body_w // 5, y + int(h * 0.75))], fill="#FEF08A")

    def _draw_bicycle(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Procedural two-wheeled bicycle."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        acc = self.sp.get("accent", "#38BDF8")
        wr = int(h * 0.28)
        w1_cx, w1_cy = x + wr + 4, y + h - wr
        w2_cx, w2_cy = x + w - wr - 4, y + h - wr
        draw.ellipse([w1_cx - wr, w1_cy - wr, w1_cx + wr, w1_cy + wr], outline=fg, width=lw)
        draw.ellipse([w2_cx - wr, w2_cy - wr, w2_cx + wr, w2_cy + wr], outline=fg, width=lw)
        crank_x, crank_y = (w1_cx + w2_cx) // 2, w1_cy
        seat_x, seat_y = crank_x - int(w * 0.08), y + int(h * 0.42)
        bars_x, bars_y = crank_x + int(w * 0.16), y + int(h * 0.32)
        draw.line([(w1_cx, w1_cy), (seat_x, seat_y), (crank_x, crank_y), (w1_cx, w1_cy)], fill=acc, width=lw)
        draw.line([(seat_x, seat_y), (bars_x, bars_y), (crank_x, crank_y)], fill=acc, width=lw)
        draw.line([(bars_x, bars_y), (w2_cx, w2_cy)], fill=acc, width=lw)
        draw.line([(bars_x - 8, bars_y - 4), (bars_x + 8, bars_y - 4)], fill=fg, width=lw + 1)
        draw.line([(seat_x - 10, seat_y), (seat_x + 8, seat_y)], fill=fg, width=lw + 1)

    def _draw_treasure_chest(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Wooden pirate/wealth treasure chest brimming with gold coins."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        by = y + int(h * 0.45)
        draw.rounded_rectangle([x, by, x + w, y + h], radius=6, fill="#78350F", outline=fg, width=lw)
        draw.chord([x, y + int(h * 0.15), x + w, by + int(h * 0.20)], start=180, end=360, fill="#92400E", outline=fg, width=lw)
        for i in range(12):
            gx = x + int(w * 0.15) + (i * 11) % int(w * 0.70)
            gy = by - 8 + (i % 3) * 6
            draw.ellipse([gx - 5, gy - 4, gx + 5, gy + 4], fill="#FACC15", outline="#CA8A04", width=1)
        lx = x + w // 2
        draw.rectangle([lx - 5, by - 4, lx + 5, by + 12], fill="#FACC15", outline=fg, width=lw)

    def _draw_brain(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 0.5) -> None:
        """Stylized neural brain with glowing synapses."""
        fg = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3)))
        acc = self.sp.get("accent", "#EC4899")
        cx, cy = x + w // 2, y + h // 2
        r_w, r_h = int(w * 0.40), int(h * 0.42)
        draw.ellipse([cx - r_w - 4, cy - r_h, cx - 2, cy + r_h], fill=_lighten(acc, 0.4), outline=fg, width=lw)
        draw.ellipse([cx + 2, cy - r_h, cx + r_w + 4, cy + r_h], fill=_lighten(acc, 0.4), outline=fg, width=lw)
        draw.arc([cx - r_w, cy - int(r_h * 0.5), cx - 6, cy + int(r_h * 0.2)], start=120, end=300, fill=fg, width=max(1, lw - 1))
        draw.arc([cx + 6, cy - int(r_h * 0.5), cx + r_w, cy + int(r_h * 0.2)], start=240, end=60, fill=fg, width=max(1, lw - 1))

    # ------------------------------------------------------------------
    # Rich 2x-AA Style-Cohesive Backgrounds (Cached per Style+Variant+Loc)
    # ------------------------------------------------------------------

    @staticmethod
    def get_cached_background(
        bg_name: str,
        width: int,
        height: int,
        style_params: dict[str, Any],
        style: str = "",
        scene: Optional[dict[str, Any]] = None,
    ) -> Image.Image:
        """Render background ONCE at 2x resolution and LANCZOS downsample cleanly.
        Supports both LCM DreamShaper AI concept art and procedural AI backgrounds.
        Created by Atharv Hatwar.
        """
        sid = str(style or style_params.get("id", "a1_classic_bw"))
        var = str(style_params.get("variant", "default"))
        narr = str(scene.get("narration", "")).strip() if scene else ""
        sc_id = int(scene.get("id", 0)) if scene else 0
        use_lcm = bool(style_params.get("use_lcm") or (scene and scene.get("use_lcm")))
        narr_hash = hashlib.md5(narr.encode("utf-8")).hexdigest()[:8] if narr else ""
        bg_hex = str(style_params.get("bg", ""))
        key = (bg_name.upper(), width, height, sid, var, bg_hex, sc_id, narr_hash, use_lcm)
        cached = AssetLibrary._BG_CACHE.get(key)
        if cached is not None:
            return cached

        # 1. Attempt LCM DreamShaper AI generation if requested
        if use_lcm and narr:
            try:
                from engine.lcm_image_engine import LCMImageEngine
                lcm_bg = LCMImageEngine.render_background(
                    narration=narr,
                    width=width,
                    height=height,
                    style_name=sid,
                    seed=int(narr_hash, 16) if narr_hash else None,
                )
                if lcm_bg is not None:
                    if len(AssetLibrary._BG_CACHE) > 24:
                        AssetLibrary._BG_CACHE.clear()
                    AssetLibrary._BG_CACHE[key] = lcm_bg
                    return lcm_bg
            except Exception:
                pass

        aa = 2 if max(width, height) <= 1320 else 1
        hi_w, hi_h = width * aa, height * aa
        hi_img = Image.new("RGBA", (hi_w, hi_h), _hex_to_rgba(style_params.get("bg", "#FFFFFF")))
        hi_draw = ImageDraw.Draw(hi_img)

        AssetLibrary._render_style_background(hi_draw, bg_name.upper(), hi_w, hi_h, style_params, sid, scene=scene)

        if aa > 1:
            img = hi_img.resize((width, height), Image.Resampling.LANCZOS)
        else:
            img = hi_img

        # Optional deterministic organic paper grain
        grain = float(style_params.get("paper_grain", 0.0))
        if grain > 0.01:
            img = AssetLibrary._apply_paper_grain(img, grain)

        if len(AssetLibrary._BG_CACHE) > 24:
            AssetLibrary._BG_CACHE.clear()
        AssetLibrary._BG_CACHE[key] = img
        return img

    @staticmethod
    def _apply_paper_grain(img: Image.Image, strength: float) -> Image.Image:
        w, h = img.size
        tile = Image.new("RGBA", (128, 128), (0, 0, 0, 0))
        tdraw = ImageDraw.Draw(tile)
        rng = random.Random(1042)
        n_specks = int(320 * strength)
        for _ in range(n_specks):
            x, y = rng.randint(0, 127), rng.randint(0, 127)
            dark = rng.choice([(110, 95, 75, int(28 * strength)), (255, 250, 240, int(24 * strength))])
            tdraw.point((x, y), fill=dark)
        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        for ty in range(0, h, 128):
            for tx in range(0, w, 128):
                overlay.paste(tile, (tx, ty))
        return Image.alpha_composite(img.convert("RGBA"), overlay)

    @staticmethod
    def _grad(draw: ImageDraw.ImageDraw, w: int, h: int, top: str, bottom: str) -> None:
        tr, tg, tb, _ = _hex_to_rgba(top)
        br, bg, bb, _ = _hex_to_rgba(bottom)
        step = max(1, h // 180)
        for y in range(0, h, step):
            t = y / max(h - 1, 1)
            r = int(tr + (br - tr) * t)
            g = int(tg + (bg - tg) * t)
            b = int(tb + (bb - tb) * t)
            draw.rectangle([0, y, w, min(h, y + step)], fill=(r, g, b, 255))

    @staticmethod
    def _render_style_background(
        draw: ImageDraw.ImageDraw,
        bg_name: str,
        w: int,
        h: int,
        sp: dict[str, Any],
        sid: str,
        scene: Optional[dict[str, Any]] = None,
    ) -> None:
        floor_y = int(h * 0.74)
        narr = str(scene.get("narration", "")).strip() if scene else ""
        scene_idx = int(scene.get("id", 1)) - 1 if scene else 0

        # Intelligent AI Background Synthesis per scene narration
        if narr and sid != "a3_prehistoric_cave":
            try:
                from engine.ai_background_engine import AIBackgroundEngine
                AIBackgroundEngine.render_ai_background(
                    draw=draw,
                    narration=narr,
                    scene_idx=scene_idx,
                    w=w,
                    h=h,
                    floor_y=floor_y,
                    style_params=sp,
                    style_id=sid,
                )
                return
            except Exception as exc:
                pass
        bg = sp.get("bg", "#FFFFFF")
        bg2 = sp.get("bg_secondary", "#E2E8F0")
        fg = sp.get("fg", "#111111")
        acc = sp.get("accent", "#E94560")
        acc2 = sp.get("accent_secondary", "#3B82F6")
        lw = max(2, int(float(sp.get("line_width", 4)) * (w / 720.0)))
        floor_y = int(h * 0.74)

        # Dispatch dedicated art direction per StylePack!
        if sid == "a1_classic_bw":
            var = str(sp.get("variant", "black_on_white"))
            if var == "spotlight_chaos":
                # Pitch-black canvas + tangled glowing violet chaotic scribbles + crisp white spotlight orb!
                AssetLibrary._grad(draw, w, h, "#050508", "#120B24")
                rng = random.Random(77)
                for i in range(95):
                    pts = [(rng.randint(-w // 8, int(w * 1.12)), rng.randint(-h // 8, int(h * 1.12)))]
                    for _ in range(rng.randint(3, 7)):
                        nx = pts[-1][0] + rng.randint(-w // 4, w // 4)
                        ny = pts[-1][1] + rng.randint(-h // 5, h // 5)
                        pts.append((nx, ny))
                    v_col = (124, 58, 237, 170) if i % 3 else (167, 139, 250, 125)
                    draw.line(pts, fill=v_col, width=max(2, lw // 2 + (i % 2)), joint="curve")
                # Bright white spotlight circle + trailing glowing thought orbs (matches reference!)
                cx_s, cy_s = int(w * 0.42), int(h * 0.48)
                rad = int(min(w, h) * 0.36)
                draw.ellipse([cx_s - rad - 10, cy_s - rad - 10, cx_s + rad + 10, cy_s + rad + 10], fill=(167, 139, 250, 65))
                draw.ellipse([cx_s - rad, cy_s - rad, cx_s + rad, cy_s + rad], fill="#FFFFFF", outline="#111111", width=max(2, lw // 2))
                for ox_f, oy_f, or_f in [(0.74, 0.25, 0.036), (0.81, 0.21, 0.020)]:
                    ocx, ocy = int(w * ox_f), int(h * oy_f)
                    orad = max(6, int(min(w, h) * or_f))
                    draw.ellipse([ocx - orad, ocy - orad, ocx + orad, ocy + orad], fill="#FFFFFF")
                draw.line([(cx_s - int(rad * 0.72), floor_y), (cx_s + int(rad * 0.72), floor_y)], fill=(17, 17, 17, 85), width=max(2, lw // 3))
            elif var == "white_on_black":
                AssetLibrary._grad(draw, w, h, "#09090E", "#181326")
                rng = random.Random(42)
                for _ in range(42):
                    x0, y0 = rng.randint(0, w), rng.randint(0, h)
                    x1, y1 = x0 + rng.randint(-w // 4, w // 4), y0 + rng.randint(-h // 5, h // 5)
                    draw.line([(x0, y0), (x1, y1)], fill=(91, 33, 182, 85), width=max(2, lw // 2))
                cx_s, cy_s = w // 2, int(h * 0.48)
                rad = int(min(w, h) * 0.35)
                draw.ellipse([cx_s - rad, cy_s - rad, cx_s + rad, cy_s + rad], fill=(56, 189, 248, 32), outline=(56, 189, 248, 120), width=max(2, lw // 2))
                draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=max(2, lw // 2))
                AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, fg, acc, outline_only=True, lw=lw)
            else:
                AssetLibrary._grad(draw, w, h, bg, bg2)
                cx_s, cy_s = w // 2, int(h * 0.48)
                rad = int(min(w, h) * 0.34)
                draw.ellipse([cx_s - rad, cy_s - rad, cx_s + rad, cy_s + rad], fill=_hex_to_rgba(acc, 24), outline=_hex_to_rgba(fg, 45), width=max(2, lw // 2))
                # Subtle radial comic speed focus rays in background
                for deg in range(0, 360, 20):
                    a = math.radians(deg)
                    r0, r1 = rad * 1.12, max(w, h) * 0.78
                    draw.line([(cx_s + int(r0 * math.cos(a)), cy_s + int(r0 * math.sin(a))), (cx_s + int(r1 * math.cos(a)), cy_s + int(r1 * math.sin(a)))], fill=(15, 23, 42, 18), width=max(1, lw // 3))
                draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=max(2, lw // 2))
                AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, fg, acc, outline_only=True, lw=lw)

        elif sid == "a2_modern_pop":
            # Crisp 3D perspective studio gallery room (receding left/right walls + foreshortened floor grid + white 3D plinth)
            var = str(sp.get("variant", "minimal_tech"))
            AssetLibrary._grad(draw, w, h, bg, bg2)
            # Soft depth perspective studio side walls
            wall_l_x = int(w * 0.24)
            wall_r_x = int(w * 0.78)
            wall_top = int(h * 0.16)
            wall_bot = floor_y
            draw.polygon([(0, 0), (wall_l_x, wall_top), (wall_l_x, wall_bot), (0, floor_y + int(h * 0.04))], fill=_darken(bg, 0.04))
            draw.polygon([(w, 0), (wall_r_x, wall_top), (wall_r_x, wall_bot), (w, floor_y + int(h * 0.04))], fill=_darken(bg, 0.05))
            # Soft minimalist white architectural plinth/step on lower right (matches reference!)
            draw.polygon([
                (int(w * 0.76), int(h * 0.56)),
                (w, int(h * 0.50)),
                (w, h),
                (int(w * 0.76), int(h * 0.84)),
            ], fill="#E2E8F0", outline="#CBD5E1", width=max(1, lw // 2))
            draw.polygon([
                (int(w * 0.76), int(h * 0.56)),
                (w, int(h * 0.50)),
                (w, int(h * 0.60)),
                (int(w * 0.88), int(h * 0.63)),
            ], fill="#F8FAFC")

            # Clean 3D perspective tiled floor (radial rays + horizontal foreshortened tiles!)
            draw.rectangle([0, floor_y, w, h], fill=_darken(bg, 0.02))
            tile_col = _hex_to_rgba(acc2 if var == "minimal_tech" else fg, 34)
            draw.line([(0, floor_y), (w, floor_y)], fill=acc if var == "colorful_story" else "#CBD5E1", width=max(2, lw // 2))
            for i in range(-8, 9):
                tx_top = int(w * 0.5 + i * w * 0.065)
                tx_bot = int(w * 0.5 + i * w * 0.165)
                draw.line([(tx_top, floor_y), (tx_bot, h)], fill=tile_col, width=max(1, lw // 3))
            # Foreshortened horizontal floor tile lines
            floor_h = h - floor_y
            for frac in (0.08, 0.19, 0.34, 0.54, 0.78):
                fy_row = floor_y + int(floor_h * frac)
                draw.line([(0, fy_row), (w, fy_row)], fill=tile_col, width=max(1, lw // 3))
            # Subtle wall glow accent only in colorful_story or secondary background cues
            if var == "colorful_story":
                draw.rounded_rectangle([int(w * 0.06), int(h * 0.12), int(w * 0.30), int(h * 0.22)], radius=12, fill=_hex_to_rgba(acc, 28), outline=_hex_to_rgba(acc, 95), width=max(2, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, acc2, acc, outline_only=False, lw=lw, soft=True)

        elif sid == "a3_prehistoric_cave":
            # Authentic Prehistoric Cavern: warm ochre rock chamber on left + cave wall art + dark cave mouth arch on right!
            AssetLibrary._grad(draw, w, h, "#70492B", "#C99E67")
            # Warm illuminated inner sandstone rock wall (left & center)
            draw.ellipse([-int(w * 0.12), int(h * 0.06), int(w * 0.72), int(h * 0.86)], fill="#D5AB75")
            draw.ellipse([-int(w * 0.04), int(h * 0.14), int(w * 0.62), int(h * 0.80)], fill="#E2BC8A")
            # Deep dark arched cave mouth tunnel opening on right!
            draw.chord([int(w * 0.56), int(h * 0.22), int(w * 1.12), floor_y + int(h * 0.38)], start=180, end=360, fill="#3D2616", outline="#24150B", width=max(2, lw // 2))
            draw.chord([int(w * 0.62), int(h * 0.27), int(w * 1.06), floor_y + int(h * 0.32)], start=180, end=360, fill="#190E08")
            # Jagged rocky cavern ceiling border + stalactites
            ceiling_pts = [(0, 0), (w, 0), (w, int(h * 0.12))]
            for rx_f, ry_f in [(0.88, 0.18), (0.74, 0.11), (0.58, 0.19), (0.44, 0.12), (0.28, 0.21), (0.14, 0.14), (0.0, 0.20)]:
                ceiling_pts.append((int(w * rx_f), int(h * ry_f)))
            draw.polygon(ceiling_pts, fill="#4E311D", outline="#26160C", width=max(2, lw // 2))

            # Textured prehistoric dirt & stone floor
            draw.polygon([(0, floor_y), (w, floor_y - int(h * 0.015)), (w, h), (0, h)], fill="#6B4426", outline="#26160C", width=lw)
            for px, py, pr in [(0.16, 0.80, 12), (0.34, 0.86, 16), (0.68, 0.79, 14), (0.85, 0.84, 18), (0.52, 0.82, 10)]:
                draw.ellipse([int(w * px) - pr, int(h * py) - pr // 2, int(w * px) + pr, int(h * py) + pr // 2], fill="#51311A", outline="#29170B", width=1)

            # Detailed ochre cave wall art: woolly mammoth & stick hunter strokes on sandstone wall
            wall_col = "#7C2D12"
            mx, my = int(w * 0.22), int(h * 0.30)
            mw_p, mh_p = max(40, int(w * 0.14)), max(26, int(h * 0.065))
            draw.arc([mx, my, mx + mw_p, my + mh_p], start=170, end=360, fill=wall_col, width=max(2, lw // 2))
            draw.arc([mx, my + mh_p // 3, mx + mw_p, my + mh_p], start=0, end=180, fill=wall_col, width=max(2, lw // 3))
            draw.arc([mx - int(mw_p * 0.35), my + 2, mx + int(mw_p * 0.12), my + int(mh_p * 1.15)], start=160, end=330, fill=wall_col, width=max(2, lw // 2))
            for lx_f in (0.18, 0.35, 0.65, 0.82):
                draw.line([(mx + int(mw_p * lx_f), my + mh_p), (mx + int(mw_p * lx_f), my + mh_p + max(10, int(h * 0.025)))], fill=wall_col, width=max(2, lw // 2))
            hx_c, hy_c = mx - int(mw_p * 0.45), my + int(mh_p * 0.4)
            draw.ellipse([hx_c - 6, hy_c - 12, hx_c + 6, hy_c], outline=wall_col, width=max(2, lw // 3))
            draw.line([(hx_c, hy_c), (hx_c, hy_c + 18)], fill=wall_col, width=max(2, lw // 3))
            draw.line([(hx_c - 10, hy_c + 8), (hx_c + 14, hy_c - 6)], fill=wall_col, width=max(2, lw // 3))

        elif sid == "a4_cozy_storytelling":
            # Sunlit slice-of-life European cafe street OR golden-hour cozy room/park/station
            if bg_name in ("CAFE", "STREET"):
                AssetLibrary._grad(draw, w, h, "#DCE6E8", "#F7E7CE")
                # Soft distant sunlit buildings & leafy pastel trees down street
                draw.rectangle([0, floor_y, w, h], fill="#D8D2C5")
                draw.line([(0, floor_y), (w, floor_y)], fill="#8C8275", width=max(2, lw // 2))
                # Perspective street curb line receding to right
                draw.line([(int(w * 0.35), floor_y), (w, floor_y + int(h * 0.09))], fill="#A89F91", width=max(2, lw // 2))
                # Sunlit leafy park trees along the street (right side depth)
                for tx_f, tr_f, shade in [(0.74, 0.10, "#B7C9A8"), (0.90, 0.14, "#9EB88C")]:
                    tx, tr = int(w * tx_f), int(min(w, h) * tr_f)
                    draw.rectangle([tx - max(4, tr // 7), floor_y - int(tr * 2.2), tx + max(4, tr // 7), floor_y], fill="#8B7355")
                    draw.ellipse([tx - tr, floor_y - int(tr * 2.8), tx + tr, floor_y - int(tr * 1.1)], fill=shade)
                # Classic streetlamp silhouette cleanly tucked along sidewalk background
                slx = int(w * 0.78)
                draw.line([(slx, int(h * 0.38)), (slx, floor_y)], fill="#64748B", width=max(3, lw // 2))
                draw.ellipse([slx - 7, int(h * 0.35), slx + 7, int(h * 0.39)], fill="#FEF3C7", outline="#64748B", width=max(1, lw // 3))
                # Cozy outdoor European cafe facade on LEFT!
                caf_w = int(w * 0.42)
                draw.polygon([(0, int(h * 0.08)), (caf_w, int(h * 0.20)), (caf_w, floor_y), (0, floor_y)], fill="#8E9B9D", outline="#475569", width=max(2, lw // 2))
                # Glass storefront paned windows + warm amber interior glow
                draw.polygon([(int(w * 0.04), int(h * 0.24)), (int(w * 0.36), int(h * 0.30)), (int(w * 0.36), floor_y - int(h * 0.06)), (int(w * 0.04), floor_y - int(h * 0.06))], fill="#CBD5E1", outline="#334155", width=max(2, lw // 2))
                draw.line([(int(w * 0.20), int(h * 0.27)), (int(w * 0.20), floor_y - int(h * 0.06))], fill="#334155", width=max(2, lw // 2))
                draw.line([(int(w * 0.04), int(h * 0.48)), (int(w * 0.36), int(h * 0.49))], fill="#334155", width=max(2, lw // 2))
                # Cute cafe striped awning above window
                draw.polygon([(0, int(h * 0.16)), (int(w * 0.44), int(h * 0.25)), (int(w * 0.40), int(h * 0.30)), (0, int(h * 0.22))], fill="#D97706", outline="#78350F", width=max(2, lw // 2))
            elif bg_name in ("PARK", "STATION"):
                AssetLibrary._grad(draw, w, h, "#FDBA74", "#FEF3C7")
                draw.ellipse([int(w * 0.68), int(h * 0.14), int(w * 0.86), int(h * 0.14) + int(w * 0.18)], fill="#FFF7ED")
                draw.chord([-w // 6, floor_y - int(h * 0.16), int(w * 0.7), floor_y + int(h * 0.2)], start=180, end=360, fill="#86EFAC")
                draw.chord([int(w * 0.35), floor_y - int(h * 0.12), int(w * 1.15), floor_y + int(h * 0.2)], start=180, end=360, fill="#4ADE80")
                draw.rectangle([0, floor_y, w, h], fill="#D6BFA9" if bg_name != "PARK" else "#65A30D")
                draw.line([(0, floor_y), (w, floor_y)], fill="#57534E", width=max(2, lw // 2))
                if bg_name == "STATION":
                    draw.rectangle([int(w * 0.08), int(h * 0.30), int(w * 0.92), int(h * 0.34)], fill="#78350F")
                    draw.line([(int(w * 0.14), int(h * 0.34)), (int(w * 0.14), floor_y)], fill="#78350F", width=lw)
                    draw.line([(int(w * 0.86), int(h * 0.34)), (int(w * 0.86), floor_y)], fill="#78350F", width=lw)
            else:
                # Warm cozy room with sunlit paned window + light beam + hardwood floor
                AssetLibrary._grad(draw, w, h, "#FDE68A", "#FED7AA")
                draw.rectangle([0, floor_y, w, h], fill="#B47B56")
                draw.line([(0, floor_y), (w, floor_y)], fill="#5C3A21", width=lw)
                for px in range(0, w, max(60, w // 7)):
                    draw.line([(px, floor_y), (px - w // 12, h)], fill="#9A623F", width=max(1, lw // 3))
                wx, wy, ww, wh = int(w * 0.62), int(h * 0.14), int(w * 0.28), int(h * 0.24)
                draw.polygon([(wx, wy + wh), (wx + ww, wy + wh), (wx + ww + int(w * 0.08), floor_y + 20), (wx - int(w * 0.18), floor_y + 20)], fill=(255, 251, 235, 70))
                draw.rectangle([wx, wy, wx + ww, wy + wh], fill="#FFFBEB", outline="#78350F", width=lw)
                draw.line([(wx + ww // 2, wy), (wx + ww // 2, wy + wh)], fill="#78350F", width=max(2, lw // 2))
                draw.line([(wx, wy + wh // 2), (wx + ww, wy + wh // 2)], fill="#78350F", width=max(2, lw // 2))

        elif sid == "a5_historical_cartoon":
            if bg_name == "LIBRARY":
                # Classical marble pillars & archival parchment room
                AssetLibrary._grad(draw, w, h, "#F5ECD7", "#E6D5B8")
                draw.rectangle([0, floor_y, w, h], fill="#C7B299")
                draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)
                for px in (int(w * 0.09), int(w * 0.85)):
                    pw = max(24, int(w * 0.07))
                    draw.rectangle([px - pw // 2, int(h * 0.22), px + pw // 2, floor_y], fill="#EFE6D5", outline=fg, width=max(2, lw // 2))
                    draw.rectangle([px - int(pw * 0.7), int(h * 0.20), px + int(pw * 0.7), int(h * 0.23)], fill="#E2CEAE", outline=fg, width=max(2, lw // 2))
                    draw.rectangle([px - int(pw * 0.7), floor_y - int(h * 0.03), px + int(pw * 0.7), floor_y], fill="#E2CEAE", outline=fg, width=max(2, lw // 2))
            else:
                # Classic Medieval Stone Fortress Grand Hall with battlements & banner (no pagoda/temple)
                AssetLibrary._grad(draw, w, h, "#1E293B", "#334155")
                # Heavy stone wall masonry
                draw.rectangle([0, 0, w, floor_y], fill="#475569")
                for r in range(0, floor_y, 32):
                    draw.line([(0, r), (w, r)], fill="#1E293B", width=1)
                    off = (r // 32) % 2 * 35
                    for c in range(off, w, 70):
                        draw.line([(c, r), (c, r + 32)], fill="#1E293B", width=1)
                # Stone battlements crenels at top
                for c in range(0, w, 55):
                    draw.rectangle([c, 0, c + 30, 24], fill="#334155", outline=fg, width=1)
                # Royal crimson banner
                bx = int(w * 0.18)
                draw.polygon([(bx, int(h * 0.14)), (bx + 40, int(h * 0.14)), (bx + 40, int(h * 0.42)), (bx + 20, int(h * 0.35)), (bx, int(h * 0.42))], fill="#DC2626", outline=fg, width=1)
                # Wall torch with warm glow
                tx, ty = int(w * 0.82), int(h * 0.30)
                draw.rectangle([tx - 4, ty, tx + 4, ty + 26], fill="#78350F")
                draw.polygon([(tx, ty - 16), (tx + 10, ty + 2), (tx - 10, ty + 2)], fill="#F59E0B")
                draw.ellipse([tx - 28, ty - 28, tx + 28, ty + 16], fill=(245, 158, 11, 35))
                # Cobblestone fortress floor
                draw.rectangle([0, floor_y, w, h], fill="#334155")
                draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=lw)

        elif sid == "a6_amber_noir":
            # Deep plum-obsidian twilight sky + glowing amber city skyline + wet reflections + Venetian blinds
            AssetLibrary._grad(draw, w, h, "#090712", "#22122C")
            # Warm glowing full moon / amber mist behind city
            mx, my, mr = int(w * 0.72), int(h * 0.22), int(min(w, h) * 0.09)
            draw.ellipse([mx - mr * 2, my - mr * 2, mx + mr * 2, my + mr * 2], fill=(245, 158, 11, 22))
            draw.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill="#FCD34D")
            # Dark layered cityscape with glowing amber windows
            for i, (bx_r, bh_r, bw_r) in enumerate([(0.0, 0.36, 0.16), (0.14, 0.46, 0.15), (0.28, 0.30, 0.18), (0.45, 0.40, 0.14), (0.58, 0.26, 0.16), (0.73, 0.44, 0.14), (0.85, 0.34, 0.16)]):
                bx, bw = int(w * bx_r), int(w * bw_r)
                by = floor_y - int(h * bh_r)
                draw.rectangle([bx, by, bx + bw, floor_y], fill="#0F0B18", outline="#2E1B3B", width=1)
                for wr in range(3):
                    for wc in range(2):
                        if (i + wr + wc) % 2 == 0:
                            wx = bx + int(bw * 0.2) + wc * int(bw * 0.4)
                            wy = by + int(h * 0.04) + wr * int(h * 0.06)
                            if wy + 12 < floor_y:
                                draw.rectangle([wx, wy, wx + max(6, bw // 6), wy + max(8, h // 45)], fill="#F59E0B")
            # Wet street + amber spotlight reflection on ground
            draw.rectangle([0, floor_y, w, h], fill="#0B0914")
            draw.line([(0, floor_y), (w, floor_y)], fill="#F59E0B", width=max(2, lw // 2))
            draw.polygon([(int(w * 0.2), 0), (int(w * 0.48), 0), (int(w * 0.85), floor_y), (int(w * 0.12), floor_y)], fill=(245, 158, 11, 22))

        elif sid == "b1_minimal_line_art":
            AssetLibrary._grad(draw, w, h, "#FCFBF7", "#F2EFE6")
            draw.line([(int(w * 0.05), floor_y), (int(w * 0.95), floor_y)], fill=fg, width=max(2, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, "#94A3B8", acc, outline_only=True, lw=lw)

        elif sid == "b2_colorful_hand_drawn":
            AssetLibrary._grad(draw, w, h, "#FCF8EB", "#F5ECD4")
            # Soft watercolor pastel wash shapes
            draw.ellipse([int(w * 0.06), int(h * 0.12), int(w * 0.45), int(h * 0.36)], fill=(186, 230, 253, 95))
            draw.ellipse([int(w * 0.56), int(h * 0.22), int(w * 0.94), int(h * 0.46)], fill=(253, 186, 116, 85))
            draw.ellipse([int(w * 0.18), floor_y - int(h * 0.10), int(w * 0.85), floor_y + int(h * 0.14)], fill=(167, 243, 208, 110))
            draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=max(3, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, fg, acc, outline_only=False, lw=lw, soft=True)

        elif sid == "b3_retro_tv":
            AssetLibrary._grad(draw, w, h, "#050A0E", "#0C1821")
            # CRT phosphor glow oval in center
            cx, cy = w // 2, h // 2
            for i in range(6, 0, -1):
                rx, ry = int(w * 0.46 * i / 6), int(h * 0.42 * i / 6)
                draw.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], fill=(16, 48, 56, 35))
            draw.line([(0, floor_y), (w, floor_y)], fill="#2DD4BF", width=max(2, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, "#134E4A", acc, outline_only=True, lw=lw)

        elif sid == "b4_survival_thriller":
            # Dramatic dark storm sky + sharp flashlight spotlight cone + jagged mountain/forest silhouettes
            AssetLibrary._grad(draw, w, h, "#060912", "#172338")
            # Jagged storm peaks & dark trees in midground
            peaks = [(0, floor_y), (int(w * 0.18), int(h * 0.45)), (int(w * 0.36), floor_y - int(h * 0.12)), (int(w * 0.54), int(h * 0.42)), (int(w * 0.74), floor_y - int(h * 0.10)), (int(w * 0.90), int(h * 0.48)), (w, floor_y)]
            draw.polygon(peaks + [(w, h), (0, h)], fill="#0B1120")
            # Stark flashlight / spotlight cone highlighting hero zone
            draw.polygon([(int(w * 0.08), int(h * 0.12)), (int(w * 0.34), 0), (int(w * 0.76), floor_y), (int(w * 0.24), floor_y)], fill=(148, 163, 184, 30))
            draw.rectangle([0, floor_y, w, h], fill="#04060D")
            draw.line([(0, floor_y), (w, floor_y)], fill="#475569", width=max(2, lw // 2))

        elif sid == "b5_character_explainer":
            AssetLibrary._grad(draw, w, h, "#FCF9F2", "#EFE8D6")
            # Subtle dot-matrix notebook grid
            dot_c = "#CBD5E1"
            step = max(36, w // 14)
            for gx in range(step, w, step):
                for gy in range(step, floor_y, step):
                    draw.ellipse([gx - 2, gy - 2, gx + 2, gy + 2], fill=dot_c)
            draw.rectangle([0, floor_y, w, h], fill="#E2D7C1")
            draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=max(2, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, "#64748B", acc, outline_only=True, lw=lw)

        else:
            AssetLibrary._grad(draw, w, h, bg, bg2)
            draw.line([(0, floor_y), (w, floor_y)], fill=fg, width=max(2, lw // 2))
            AssetLibrary._add_location_silhouettes(draw, bg_name, w, h, floor_y, fg, acc, outline_only=True, lw=lw)

    @staticmethod
    def _add_location_silhouettes(
        draw: ImageDraw.ImageDraw,
        bg_name: str,
        w: int,
        h: int,
        floor_y: int,
        line_col: str,
        acc: str,
        outline_only: bool = True,
        lw: int = 3,
        soft: bool = False,
    ) -> None:
        """
        Draw rich, authentic architectural & environmental silhouettes for ALL backgrounds.
        Created by Atharv Hatwar.
        """
        stroke = _hex_to_rgba(line_col, 95 if soft else 170)
        fill_c = _hex_to_rgba(line_col, 16) if not outline_only else None
        accent_c = _hex_to_rgba(acc, 160)
        accent_fill = _hex_to_rgba(acc, 32)
        base_lw = max(2, lw // 2)

        if bg_name == "OFFICE":
            # 1. Whiteboard on left with diagram and flowchart arrows
            bx, by, bw, bh = int(w * 0.08), int(h * 0.16), int(w * 0.36), int(h * 0.28)
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=fill_c, outline=stroke, width=base_lw)
            # Whiteboard stand legs
            draw.line([(bx + int(bw * 0.2), by + bh), (bx + int(bw * 0.1), floor_y)], fill=stroke, width=max(1, base_lw - 1))
            draw.line([(bx + int(bw * 0.8), by + bh), (bx + int(bw * 0.9), floor_y)], fill=stroke, width=max(1, base_lw - 1))
            # Brainstorm graph & nodes inside whiteboard
            draw.line([(bx + 20, by + bh - 24), (bx + bw - 20, by + bh - 24)], fill=stroke, width=1)
            draw.line([(bx + 20, by + 24), (bx + 20, by + bh - 24)], fill=stroke, width=1)
            # Growth curve
            draw.line([(bx + 28, by + bh - 32), (bx + int(bw * 0.45), by + int(bh * 0.55)), (bx + bw - 32, by + 34)], fill=accent_c, width=base_lw)
            draw.ellipse([bx + bw - 36, by + 30, bx + bw - 26, by + 40], fill=acc)

            # 2. Wall clock at top center
            cx_ck, cy_ck, r_ck = int(w * 0.52), int(h * 0.13), max(12, int(w * 0.038))
            draw.ellipse([cx_ck - r_ck, cy_ck - r_ck, cx_ck + r_ck, cy_ck + r_ck], fill=fill_c, outline=stroke, width=base_lw)
            draw.line([(cx_ck, cy_ck), (cx_ck, cy_ck - r_ck + 4)], fill=stroke, width=max(1, base_lw - 1))
            draw.line([(cx_ck, cy_ck), (cx_ck + r_ck - 6, cy_ck)], fill=stroke, width=max(1, base_lw - 1))

            # 3. Large paned office window on right with blinds & skyline view
            wx, wy, ww, wh = int(w * 0.65), int(h * 0.14), int(w * 0.28), int(h * 0.34)
            draw.rounded_rectangle([wx, wy, wx + ww, wy + wh], radius=6, fill=fill_c, outline=stroke, width=base_lw)
            # Window mullions
            draw.line([(wx + ww // 2, wy), (wx + ww // 2, wy + wh)], fill=stroke, width=max(1, base_lw - 1))
            draw.line([(wx, wy + wh // 2), (wx + ww, wy + wh // 2)], fill=stroke, width=max(1, base_lw - 1))
            # Blinds lines
            for bly in range(wy + 14, wy + wh, max(12, wh // 6)):
                draw.line([(wx + 4, bly), (wx + ww - 4, bly)], fill=_hex_to_rgba(line_col, 55), width=1)

            # 4. Potted fiddle-leaf plant in corner floor
            px, py = int(w * 0.04), floor_y
            pw_pot = max(18, int(w * 0.045))
            draw.polygon([(px, py), (px + pw_pot, py), (px + int(pw_pot * 0.85), py - int(h * 0.07)), (px + int(pw_pot * 0.15), py - int(h * 0.07))], fill=fill_c, outline=stroke, width=base_lw)
            # Leaves
            pot_top_y = py - int(h * 0.07)
            for lx_off, ly_off in [(-12, -26), (pw_pot // 2, -38), (pw_pot + 10, -22)]:
                draw.ellipse([px + lx_off - 8, pot_top_y + ly_off - 12, px + lx_off + 14, pot_top_y + ly_off + 8], fill=accent_fill, outline=stroke, width=max(1, base_lw - 1))

        elif bg_name == "HOME":
            # 1. Framed wall pictures
            fx1, fy1, fw1, fh1 = int(w * 0.10), int(h * 0.16), int(w * 0.22), int(h * 0.18)
            draw.rectangle([fx1, fy1, fx1 + fw1, fy1 + fh1], fill=fill_c, outline=stroke, width=base_lw)
            # Mountain and sun art inside frame
            draw.polygon([(fx1 + 10, fy1 + fh1 - 8), (fx1 + int(fw1 * 0.45), fy1 + 18), (fx1 + int(fw1 * 0.75), fy1 + fh1 - 8)], fill=accent_fill, outline=stroke, width=1)
            draw.ellipse([fx1 + fw1 - 28, fy1 + 12, fx1 + fw1 - 14, fy1 + 26], fill=acc)

            # Framed picture 2
            fx2, fy2, fw2, fh2 = int(w * 0.36), int(h * 0.14), int(w * 0.15), int(h * 0.22)
            draw.rectangle([fx2, fy2, fx2 + fw2, fy2 + fh2], fill=fill_c, outline=stroke, width=base_lw)
            draw.ellipse([fx2 + int(fw2 * 0.25), fy2 + int(fh2 * 0.2), fx2 + int(fw2 * 0.75), fy2 + int(fh2 * 0.8)], fill=fill_c, outline=stroke, width=1)

            # 2. Modern wall bookshelf on right
            bx, by, bw, bh = int(w * 0.62), int(h * 0.16), int(w * 0.30), int(h * 0.28)
            draw.rectangle([bx, by, bx + bw, by + bh], fill=fill_c, outline=stroke, width=base_lw)
            draw.line([(bx, by + bh // 2), (bx + bw, by + bh // 2)], fill=stroke, width=base_lw)
            # Book spines on shelves
            for sx in range(bx + 8, bx + bw - 16, 14):
                draw.rectangle([sx, by + 8, sx + 9, by + bh // 2 - 2], fill=accent_fill, outline=stroke, width=1)
            for sx in range(bx + 12, bx + bw - 20, 16):
                draw.rectangle([sx, by + bh // 2 + 6, sx + 10, by + bh - 2], fill=fill_c, outline=stroke, width=1)

            # 3. Floor lamp on right
            lx, ly = int(w * 0.94), floor_y
            draw.line([(lx, ly), (lx, ly - int(h * 0.38))], fill=stroke, width=base_lw)
            # Lamp base
            draw.ellipse([lx - 16, ly - 4, lx + 16, ly + 2], fill=stroke)
            # Lamp shade
            sy = ly - int(h * 0.38)
            draw.polygon([(lx - 18, sy), (lx + 18, sy), (lx + 28, sy + int(h * 0.08)), (lx - 28, sy + int(h * 0.08))], fill=accent_fill, outline=stroke, width=base_lw)
            # Warm conical light beam onto floor
            draw.polygon([(lx - 24, sy + int(h * 0.08)), (lx + 24, sy + int(h * 0.08)), (lx + 65, floor_y), (lx - 65, floor_y)], fill=(254, 240, 138, 28))

            # 4. Soft oval rug on floor
            rw, rh = int(w * 0.52), int(h * 0.08)
            rx = int(w * 0.24)
            draw.ellipse([rx, floor_y - 2, rx + rw, floor_y + rh], outline=stroke, width=max(1, base_lw - 1))

        elif bg_name in ("BEDROOM", "BEDROOM_RETREAT"):
            # Cozy bedroom: bed with pillows + nightstand lamp + wall art
            bx1, by1 = int(w * 0.08), floor_y - int(h * 0.22)
            bw_b, bh_b = int(w * 0.44), int(h * 0.22)
            draw.rounded_rectangle([bx1, by1, bx1 + bw_b, floor_y], radius=6, fill=fill_c, outline=stroke, width=base_lw)
            # Headboard
            draw.rounded_rectangle([bx1, by1 - int(h * 0.10), bx1 + 18, floor_y], radius=3, fill=accent_fill, outline=stroke, width=base_lw)
            # Pillows
            draw.ellipse([bx1 + 24, by1 - 18, bx1 + int(w * 0.16), by1 + 6], fill=fill_c, outline=stroke, width=1)
            # Nightstand with lamp
            ns_x = bx1 + bw_b + 12
            ns_w = int(w * 0.12)
            draw.rectangle([ns_x, floor_y - int(h * 0.14), ns_x + ns_w, floor_y], fill=fill_c, outline=stroke, width=base_lw)
            lx = ns_x + ns_w // 2
            ly = floor_y - int(h * 0.14)
            draw.line([(lx, ly), (lx, ly - 18)], fill=stroke, width=base_lw)
            draw.polygon([(lx - 12, ly - 18), (lx + 12, ly - 18), (lx + 8, ly - 32), (lx - 8, ly - 32)], fill=accent_fill, outline=stroke, width=base_lw)
            # Rug on floor
            draw.ellipse([int(w * 0.15), floor_y + 4, int(w * 0.85), floor_y + int(h * 0.09)], outline=stroke, width=1)

        elif bg_name in ("GALLERY", "GALLERY_REFLECT"):
            # Art studio gallery: downward spotlight cone + large framed mirror
            draw.polygon([(w // 2 - 25, 0), (w // 2 + 25, 0), (int(w * 0.82), floor_y), (int(w * 0.18), floor_y)], fill=(255, 255, 255, 20))
            # Large floor mirror on right
            mx1, my1 = int(w * 0.68), int(h * 0.16)
            mw_m, mh_m = int(w * 0.22), int(h * 0.50)
            draw.rounded_rectangle([mx1, my1, mx1 + mw_m, my1 + mh_m], radius=6, fill=fill_c, outline=stroke, width=base_lw + 1)
            draw.line([(mx1 + 8, my1 + 12), (mx1 + mw_m - 8, my1 + int(mh_m * 0.35))], fill=accent_c, width=1)
            # Picture frame on left
            draw.rectangle([int(w * 0.10), int(h * 0.20), int(w * 0.32), int(h * 0.40)], fill=fill_c, outline=stroke, width=base_lw)
            draw.ellipse([int(w * 0.21) - 14, int(h * 0.30) - 14, int(w * 0.21) + 14, int(h * 0.30) + 14], fill=accent_fill, outline=stroke, width=1)

        elif bg_name == "CAFE":
            # 1. Three hanging modern pendant lamps from ceiling
            for idx, lx_f in enumerate((0.18, 0.50, 0.82)):
                lx = int(w * lx_f)
                cord_len = int(h * (0.18 + 0.04 * (idx % 2)))
                draw.line([(lx, 0), (lx, cord_len)], fill=stroke, width=max(1, base_lw - 1))
                # Pendant shade
                draw.polygon([(lx - 14, cord_len + 12), (lx + 14, cord_len + 12), (lx + 8, cord_len), (lx - 8, cord_len)], fill=fill_c, outline=stroke, width=base_lw)
                # Glowing bulb
                draw.ellipse([lx - 6, cord_len + 10, lx + 6, cord_len + 22], fill=acc)
                # Soft amber glow cone
                draw.polygon([(lx - 12, cord_len + 14), (lx + 12, cord_len + 14), (lx + 36, floor_y - int(h * 0.1)), (lx - 36, floor_y - int(h * 0.1))], fill=(251, 191, 36, 18))

            # 2. Cafe chalkboard menu on left
            bx, by, bw, bh = int(w * 0.08), int(h * 0.24), int(w * 0.32), int(h * 0.30)
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=fill_c, outline=stroke, width=base_lw)
            # Coffee cup doodle
            cx, cy = bx + bw // 2, by + 28
            draw.rectangle([cx - 14, cy - 8, cx + 14, cy + 10], outline=stroke, width=1)
            draw.arc([cx + 12, cy - 4, cx + 22, cy + 6], start=270, end=90, fill=stroke, width=1)
            # Menu price chalk lines
            for ly in (by + 48, by + 64, by + 80):
                draw.line([(bx + 20, ly), (bx + bw - 20, ly)], fill=stroke, width=1)

            # 3. Brick accent lines on right wall
            for r in range(4):
                ry = int(h * 0.22) + r * 22
                draw.line([(int(w * 0.72), ry), (w, ry)], fill=_hex_to_rgba(line_col, 45), width=1)

        elif bg_name == "CLASSROOM":
            # 1. Large blackboard
            bx, by, bw, bh = int(w * 0.06), int(h * 0.14), int(w * 0.58), int(h * 0.34)
            draw.rounded_rectangle([bx, by, bx + bw, by + bh], radius=8, fill=fill_c, outline=stroke, width=base_lw)
            # Chalk tray at bottom
            draw.rectangle([bx - 6, by + bh, bx + bw + 6, by + bh + 6], fill=stroke)
            # Diagrams inside blackboard
            # Math equation
            font_chalk = _load_ui_font(max(13, int(w * 0.024)), bold=True)
            draw.text((bx + 22, by + 18), "E = mc²", fill=accent_c, font=font_chalk)
            # Upward trending chart
            draw.line([(bx + 24, by + bh - 24), (bx + int(bw * 0.44), by + bh - 24)], fill=stroke, width=1)
            draw.line([(bx + 28, by + bh - 28), (bx + int(bw * 0.24), by + int(bh * 0.65)), (bx + int(bw * 0.40), by + 36)], fill=stroke, width=base_lw)
            # Geometric triangle
            tx = bx + int(bw * 0.64)
            draw.polygon([(tx, by + 26), (tx - 28, by + bh - 28), (tx + 28, by + bh - 28)], outline=stroke, width=1)

            # 2. Wall clock above board
            draw.ellipse([bx + bw // 2 - 16, by - 38, bx + bw // 2 + 16, by - 6], fill=fill_c, outline=stroke, width=base_lw)
            draw.line([(bx + bw // 2, by - 22), (bx + bw // 2, by - 32)], fill=stroke, width=1)
            draw.line([(bx + bw // 2, by - 22), (bx + bw // 2 + 8, by - 22)], fill=stroke, width=1)

            # 3. Teacher's lectern / podium on right
            lx, ly = int(w * 0.78), floor_y
            pw = max(34, int(w * 0.10))
            ph = int(h * 0.26)
            draw.polygon([(lx, ly), (lx + pw, ly), (lx + int(pw * 0.9), ly - ph), (lx + int(pw * 0.1), ly - ph)], fill=fill_c, outline=stroke, width=base_lw)
            # Slanted book rest on top
            draw.polygon([(lx - 6, ly - ph), (lx + pw + 6, ly - ph), (lx + pw + 2, ly - ph - 12), (lx - 8, ly - ph - 6)], fill=fill_c, outline=stroke, width=base_lw)

        elif bg_name == "LIBRARY":
            # Multi-tier grand wooden bookshelves spanning walls
            for side_x, side_w in [(int(w * 0.04), int(w * 0.38)), (int(w * 0.60), int(w * 0.36))]:
                draw.rectangle([side_x, int(h * 0.10), side_x + side_w, floor_y], fill=fill_c, outline=stroke, width=base_lw)
                # Shelves
                n_shelves = 4
                sh_gap = (floor_y - int(h * 0.10)) // n_shelves
                for s in range(n_shelves):
                    sy = int(h * 0.10) + s * sh_gap
                    draw.line([(side_x, sy), (side_x + side_w, sy)], fill=stroke, width=base_lw)
                    # Books on shelf
                    bx = side_x + 8
                    while bx < side_x + side_w - 18:
                        bk_w = 12 + (bx * 7 % 10)
                        bk_h = sh_gap - 8 - (bx * 3 % 14)
                        col = accent_fill if (bx % 3 == 0) else fill_c
                        draw.rectangle([bx, sy + sh_gap - bk_h - 2, bx + bk_w, sy + sh_gap - 2], fill=col, outline=stroke, width=1)
                        bx += bk_w + 3
            # Angled rolling library ladder on left shelf
            lad_x = int(w * 0.32)
            draw.line([(lad_x - 18, int(h * 0.12)), (lad_x - 38, floor_y)], fill=stroke, width=base_lw)
            draw.line([(lad_x + 6, int(h * 0.12)), (lad_x - 14, floor_y)], fill=stroke, width=base_lw)
            for r_step in range(6):
                ry = int(h * 0.18) + r_step * int(h * 0.08)
                draw.line([(lad_x - 18 - r_step * 3, ry), (lad_x + 6 - r_step * 3, ry)], fill=stroke, width=1)

        elif bg_name in ("STREET", "CITY"):
            # Layered city skyline with lit windows
            for i, (bx_r, bh_r, bw_r) in enumerate([
                (0.04, 0.34, 0.18), (0.24, 0.44, 0.16), (0.42, 0.28, 0.20),
                (0.64, 0.42, 0.16), (0.82, 0.32, 0.16)
            ]):
                bx = int(w * bx_r)
                bw = int(w * bw_r)
                by = floor_y - int(h * bh_r)
                draw.rectangle([bx, by, bx + bw, floor_y], fill=fill_c, outline=stroke, width=base_lw)
                # Antenna on taller buildings
                if bh_r > 0.40:
                    draw.line([(bx + bw // 2, by), (bx + bw // 2, by - 24)], fill=stroke, width=1)
                    draw.ellipse([bx + bw // 2 - 3, by - 28, bx + bw // 2 + 3, by - 22], fill=acc)
                # Window grid
                win_w, win_h = max(6, bw // 6), max(8, int(h * 0.024))
                for wr in range(int((floor_y - by) / (win_h + 12))):
                    for wc in range(2):
                        wx = bx + int(bw * 0.22) + wc * int(bw * 0.44)
                        wy = by + 16 + wr * (win_h + 12)
                        if wy + win_h < floor_y - 8:
                            w_fill = accent_fill if ((i + wr + wc) % 3 == 0) else None
                            draw.rectangle([wx, wy, wx + win_w, wy + win_h], fill=w_fill, outline=stroke, width=1)

            # Classic streetlamp on right
            slx = int(w * 0.86)
            sly = floor_y - int(h * 0.36)
            draw.line([(slx, sly), (slx, floor_y)], fill=stroke, width=base_lw)
            draw.ellipse([slx - 12, floor_y - 4, slx + 12, floor_y + 2], fill=stroke)
            # Lamp top lantern
            draw.polygon([(slx - 14, sly), (slx + 14, sly), (slx + 10, sly - 22), (slx - 10, sly - 22)], fill=fill_c, outline=stroke, width=base_lw)
            draw.ellipse([slx - 6, sly - 16, slx + 6, sly - 4], fill=acc)
            # Light cone
            draw.polygon([(slx - 10, sly), (slx + 10, sly), (slx + 48, floor_y), (slx - 48, floor_y)], fill=(254, 240, 138, 22))

            # Sidewalk curb and dashed road marking
            draw.line([(0, floor_y + 12), (w, floor_y + 12)], fill=stroke, width=1)
            for d_x in range(16, w, 56):
                draw.line([(d_x, floor_y + int((h - floor_y) * 0.6)), (d_x + 32, floor_y + int((h - floor_y) * 0.6))], fill=_hex_to_rgba(line_col, 85), width=max(2, base_lw))

        elif bg_name == "PARK":
            # 1. Distant rolling hill
            draw.chord([-int(w * 0.15), floor_y - int(h * 0.18), int(w * 0.75), floor_y + int(h * 0.2)], start=180, end=360, fill=fill_c, outline=stroke, width=base_lw)
            # Midground hill
            draw.chord([int(w * 0.35), floor_y - int(h * 0.14), int(w * 1.15), floor_y + int(h * 0.2)], start=180, end=360, fill=fill_c, outline=stroke, width=base_lw)

            # 2. Majestic leafy park tree on left
            tx, ty = int(w * 0.16), floor_y
            tr_h = int(h * 0.38)
            draw.line([(tx, ty), (tx, ty - tr_h)], fill=stroke, width=max(3, base_lw + 2))
            draw.line([(tx, ty - int(tr_h * 0.6)), (tx - 24, ty - int(tr_h * 0.85))], fill=stroke, width=base_lw)
            draw.line([(tx, ty - int(tr_h * 0.6)), (tx + 24, ty - int(tr_h * 0.85))], fill=stroke, width=base_lw)
            # Leaf crown puffs
            crown_y = ty - tr_h
            for cx_o, cy_o, cr in [(-24, 0, 36), (24, -8, 38), (0, -32, 44), (-12, -18, 40)]:
                draw.ellipse([tx + cx_o - cr, crown_y + cy_o - cr, tx + cx_o + cr, crown_y + cy_o + cr], fill=accent_fill, outline=stroke, width=base_lw)

            # 3. Wooden park bench on right
            bx, by = int(w * 0.74), floor_y
            bw_b = max(42, int(w * 0.12))
            draw.line([(bx, by - 18), (bx + bw_b, by - 18)], fill=stroke, width=max(2, base_lw))
            draw.line([(bx + 4, by - 32), (bx + bw_b - 4, by - 32)], fill=stroke, width=max(2, base_lw))
            draw.line([(bx + 8, by), (bx + 8, by - 32)], fill=stroke, width=base_lw)
            draw.line([(bx + bw_b - 8, by), (bx + bw_b - 8, by - 32)], fill=stroke, width=base_lw)

            # 4. Flying birds in sky
            for bird_x, bird_y in [(int(w * 0.54), int(h * 0.18)), (int(w * 0.62), int(h * 0.14)), (int(w * 0.70), int(h * 0.20))]:
                draw.arc([bird_x - 14, bird_y - 8, bird_x, bird_y + 4], start=180, end=360, fill=stroke, width=base_lw)
                draw.arc([bird_x, bird_y - 8, bird_x + 14, bird_y + 4], start=180, end=360, fill=stroke, width=base_lw)

        elif bg_name == "MOUNTAIN":
            # Majestic mountain peaks with snowcaps
            peaks = [
                (-int(w * 0.1), floor_y),
                (int(w * 0.22), int(h * 0.28)),
                (int(w * 0.44), floor_y - int(h * 0.16)),
                (int(w * 0.68), int(h * 0.22)),
                (int(w * 0.88), floor_y - int(h * 0.12)),
                (int(w * 1.1), floor_y)
            ]
            draw.polygon(peaks, fill=fill_c, outline=stroke, width=base_lw)
            # Snowcaps on peaks
            # Peak 1 snowcap
            p1_top = (int(w * 0.22), int(h * 0.28))
            draw.polygon([
                p1_top,
                (p1_top[0] - 28, p1_top[1] + 42),
                (p1_top[0] - 12, p1_top[1] + 34),
                (p1_top[0] + 10, p1_top[1] + 44),
                (p1_top[0] + 32, p1_top[1] + 38)
            ], fill=accent_fill, outline=stroke, width=1)
            # Peak 2 snowcap
            p2_top = (int(w * 0.68), int(h * 0.22))
            draw.polygon([
                p2_top,
                (p2_top[0] - 36, p2_top[1] + 52),
                (p2_top[0] - 10, p2_top[1] + 42),
                (p2_top[0] + 16, p2_top[1] + 56),
                (p2_top[0] + 42, p2_top[1] + 48)
            ], fill=accent_fill, outline=stroke, width=1)
            # Pine trees along foothills
            for px in (int(w * 0.08), int(w * 0.38), int(w * 0.84)):
                draw.polygon([(px, floor_y), (px - 14, floor_y), (px, floor_y - 36), (px + 14, floor_y)], fill=stroke)

        elif bg_name == "STAGE":
            # Theatrical stage with heavy parted side curtains + overhead spotlights
            curt_w = int(w * 0.16)
            # Left curtain with drapery swags
            draw.polygon([(0, 0), (curt_w, 0), (int(curt_w * 0.6), floor_y), (0, floor_y)], fill=fill_c, outline=stroke, width=base_lw)
            draw.arc([-curt_w, 0, curt_w * 2, int(h * 0.24)], start=0, end=90, fill=stroke, width=base_lw)
            # Right curtain
            draw.polygon([(w, 0), (w - curt_w, 0), (w - int(curt_w * 0.6), floor_y), (w, floor_y)], fill=fill_c, outline=stroke, width=base_lw)
            draw.arc([w - curt_w * 2, 0, w + curt_w, int(h * 0.24)], start=90, end=180, fill=stroke, width=base_lw)
            # Top valance scallop
            for vx in range(0, w, max(40, w // 8)):
                draw.arc([vx, -18, vx + max(40, w // 8), 24], start=0, end=180, fill=stroke, width=base_lw)

            # Overhead spotlight cones casting pools on stage floor
            sp1_x, sp2_x = int(w * 0.35), int(w * 0.65)
            draw.polygon([(sp1_x - 12, 0), (sp1_x + 12, 0), (int(w * 0.46), floor_y), (int(w * 0.24), floor_y)], fill=(254, 240, 138, 22))
            draw.polygon([(sp2_x - 12, 0), (sp2_x + 12, 0), (int(w * 0.76), floor_y), (int(w * 0.54), floor_y)], fill=(254, 240, 138, 22))
            draw.ellipse([int(w * 0.24), floor_y - 6, int(w * 0.46), floor_y + 12], fill=(254, 240, 138, 32))
            draw.ellipse([int(w * 0.54), floor_y - 6, int(w * 0.76), floor_y + 12], fill=(254, 240, 138, 32))

            # Perspective stage floorboards
            for sx in range(int(w * 0.1), int(w * 0.9), max(30, w // 10)):
                draw.line([(sx, floor_y), (sx + int((sx - w // 2) * 0.35), h)], fill=_hex_to_rgba(line_col, 50), width=1)

        elif bg_name == "SPLIT_COMPARISON":
            # Dynamic dual comparison split-screen: left vs right contrast!
            mid_x = w // 2
            # Vertical center dividing dashed line
            for dy in range(int(h * 0.08), floor_y, 18):
                draw.line([(mid_x, dy), (mid_x, dy + 10)], fill=stroke, width=base_lw)

            # Left side: Warning/Challenge tone & red circle X badge
            draw.rectangle([0, 0, mid_x, floor_y], fill=(239, 68, 68, 14))
            badge1_x, badge1_y = int(w * 0.25), int(h * 0.16)
            br_sz = max(18, int(w * 0.045))
            draw.ellipse([badge1_x - br_sz, badge1_y - br_sz, badge1_x + br_sz, badge1_y + br_sz], fill="#EF4444", outline="#B91C1C", width=base_lw)
            # White X mark inside
            draw.line([(badge1_x - 8, badge1_y - 8), (badge1_x + 8, badge1_y + 8)], fill="#FFFFFF", width=3)
            draw.line([(badge1_x + 8, badge1_y - 8), (badge1_x - 8, badge1_y + 8)], fill="#FFFFFF", width=3)

            # Right side: Solution/Growth tone & green circle Checkmark badge
            draw.rectangle([mid_x, 0, w, floor_y], fill=(16, 185, 129, 14))
            badge2_x, badge2_y = int(w * 0.75), int(h * 0.16)
            draw.ellipse([badge2_x - br_sz, badge2_y - br_sz, badge2_x + br_sz, badge2_y + br_sz], fill="#10B981", outline="#047857", width=base_lw)
            # White checkmark inside
            draw.line([(badge2_x - 8, badge2_y), (badge2_x - 2, badge2_y + 8), (badge2_x + 9, badge2_y - 7)], fill="#FFFFFF", width=3)

        elif bg_name in ("ABSTRACT", "STUDIO"):
            # High-tech dynamic infographic & geometric studio layout
            # Isometric dot matrix
            step = max(34, w // 15)
            for gx in range(step, w, step):
                for gy in range(step, floor_y, step):
                    draw.ellipse([gx - 1, gy - 1, gx + 1, gy + 1], fill=_hex_to_rgba(line_col, 40))

            # Floating frosted translucent graphic cards
            # Card 1 on left
            c1_x, c1_y, c1_w, c1_h = int(w * 0.08), int(h * 0.18), int(w * 0.32), int(h * 0.24)
            draw.rounded_rectangle([c1_x, c1_y, c1_x + c1_w, c1_y + c1_h], radius=10, fill=fill_c, outline=stroke, width=base_lw)
            draw.line([(c1_x + 14, c1_y + 22), (c1_x + c1_w - 14, c1_y + 22)], fill=accent_c, width=base_lw)
            draw.line([(c1_x + 14, c1_y + 36), (c1_x + int(c1_w * 0.65), c1_y + 36)], fill=stroke, width=1)
            draw.line([(c1_x + 14, c1_y + 50), (c1_x + int(c1_w * 0.8), c1_y + 50)], fill=stroke, width=1)

            # Circular metric ring on right
            m_cx, m_cy = int(w * 0.82), int(h * 0.28)
            mr = max(24, int(w * 0.07))
            draw.ellipse([m_cx - mr, m_cy - mr, m_cx + mr, m_cy + mr], fill=fill_c, outline=_hex_to_rgba(line_col, 50), width=base_lw)
            draw.arc([m_cx - mr, m_cy - mr, m_cx + mr, m_cy + mr], start=-90, end=150, fill=acc, width=max(3, base_lw + 2))
            draw.text((m_cx, m_cy), "85%", fill=line_col, font=_load_ui_font(max(11, mr // 2), bold=True), anchor="mm")

        elif bg_name == "BEACH":
            # Ocean horizon + wave lines + tropical palm tree on left
            ocean_y = int(h * 0.52)
            draw.line([(0, ocean_y), (w, ocean_y)], fill=stroke, width=base_lw)
            for wy in range(ocean_y + 18, floor_y, 22):
                draw.arc([int(w * 0.2), wy, int(w * 0.5), wy + 14], start=180, end=360, fill=stroke, width=1)
                draw.arc([int(w * 0.55), wy + 8, int(w * 0.85), wy + 22], start=180, end=360, fill=stroke, width=1)
            # Palm tree
            px, py = int(w * 0.12), floor_y
            draw.arc([px - 40, py - int(h * 0.44), px + 40, py + 20], start=180, end=270, fill=stroke, width=max(3, base_lw + 1))
            # Fronds
            top_px = px
            top_py = py - int(h * 0.38)
            for ang in (-60, -20, 20, 60, 100):
                rad = math.radians(ang)
                fx = top_px + int(50 * math.cos(rad))
                fy = top_py - int(32 * math.sin(rad))
                draw.line([(top_px, top_py), (fx, fy)], fill=accent_c, width=base_lw)

        elif bg_name == "HOSPITAL":
            # Medical cross emblem + heart rate monitor ECG pulse line
            draw.rectangle([int(w * 0.12), int(h * 0.16), int(w * 0.42), int(h * 0.36)], fill=fill_c, outline=stroke, width=base_lw)
            # Cross
            cross_x, cross_y = int(w * 0.27), int(h * 0.26)
            draw.rectangle([cross_x - 6, cross_y - 20, cross_x + 6, cross_y + 20], fill="#EF4444")
            draw.rectangle([cross_x - 20, cross_y - 6, cross_x + 20, cross_y + 6], fill="#EF4444")
            # ECG pulse line on right
            ecg_y = int(h * 0.28)
            pts = [
                (int(w * 0.54), ecg_y), (int(w * 0.64), ecg_y),
                (int(w * 0.67), ecg_y - 32), (int(w * 0.70), ecg_y + 36),
                (int(w * 0.73), ecg_y - 14), (int(w * 0.76), ecg_y),
                (int(w * 0.90), ecg_y)
            ]
            draw.line(pts, fill="#10B981", width=base_lw)

        elif bg_name == "SHOP":
            # Storefront counter + awning + cash register silhouette
            aw_w = max(40, w // 8)
            for ax in range(0, w, aw_w):
                draw.polygon([(ax, 0), (ax + aw_w, 0), (ax + aw_w - 6, int(h * 0.12)), (ax - 6, int(h * 0.12))], fill=accent_fill if (ax // aw_w) % 2 == 0 else fill_c, outline=stroke, width=1)
            # Counter
            draw.rectangle([int(w * 0.08), floor_y - int(h * 0.24), int(w * 0.46), floor_y], fill=fill_c, outline=stroke, width=base_lw)
            # Cash register
            rx, ry = int(w * 0.22), floor_y - int(h * 0.24)
            draw.polygon([(rx, ry), (rx + 36, ry), (rx + 28, ry - 22), (rx + 4, ry - 22)], fill=stroke)
            draw.rectangle([rx + 8, ry - 34, rx + 24, ry - 22], fill=fill_c, outline=stroke, width=1)

        elif bg_name == "FACTORY":
            # Industrial saw-tooth factory roof + smokestacks + gears
            roof_pts = [(0, floor_y)]
            for sx in range(0, w, max(60, w // 5)):
                roof_pts.extend([(sx, floor_y - int(h * 0.22)), (sx + max(60, w // 5), floor_y - int(h * 0.36))])
            roof_pts.append((w, floor_y))
            draw.polygon(roof_pts, fill=fill_c, outline=stroke, width=base_lw)
            # Smokestack
            draw.polygon([(int(w * 0.75), floor_y - int(h * 0.34)), (int(w * 0.81), floor_y - int(h * 0.34)), (int(w * 0.80), int(h * 0.12)), (int(w * 0.76), int(h * 0.12))], fill=fill_c, outline=stroke, width=base_lw)
            # Smoke puff cloud
            draw.ellipse([int(w * 0.74), int(h * 0.04), int(w * 0.84), int(h * 0.12)], fill=accent_fill, outline=stroke, width=1)

        elif bg_name == "STATION":
            # Train platform canopy + track rails
            draw.rectangle([int(w * 0.06), int(h * 0.16), int(w * 0.94), int(h * 0.22)], fill=fill_c, outline=stroke, width=base_lw)
            # Support pillars
            for px in (int(w * 0.15), int(w * 0.50), int(w * 0.85)):
                draw.line([(px, int(h * 0.22)), (px, floor_y)], fill=stroke, width=base_lw)
            # Hanging station clock
            draw.ellipse([int(w * 0.47), int(h * 0.22), int(w * 0.53), int(h * 0.32)], fill=fill_c, outline=stroke, width=base_lw)
            # Rails on floor
            draw.line([(0, floor_y + 16), (w, floor_y + 16)], fill=stroke, width=base_lw)
            draw.line([(0, floor_y + 36), (w, floor_y + 36)], fill=stroke, width=base_lw)
            for tx in range(12, w, 32):
                draw.line([(tx, floor_y + 12), (tx, floor_y + 40)], fill=stroke, width=1)

    # ------------------------------------------------------------------
    # Physical Metaphors Drawing Implementations (Created by Atharv Hatwar)
    # ------------------------------------------------------------------

    def _draw_lever_boulder(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Fulcrum triangle at 35% from left
        fx, fy = x + int(w * 0.35), y + int(h * 0.85)
        tri_w = int(w * 0.14)
        draw.polygon([(fx, fy - int(h * 0.22)), (fx - tri_w // 2, fy), (fx + tri_w // 2, fy)], fill=_hex_to_rgba(ink, 40), outline=ink, width=lw)
        # Wooden beam pivoting on fulcrum
        tilt = -0.15 + 0.12 * math.sin(t * math.pi * 2)
        bx1 = x + int(w * 0.05)
        by1 = fy - int(h * 0.22) + int(w * 0.3 * math.sin(tilt))
        bx2 = x + int(w * 0.95)
        by2 = fy - int(h * 0.22) - int(w * 0.6 * math.sin(tilt))
        draw.line([(bx1, by1), (bx2, by2)], fill=ink, width=max(3, lw + 2))
        # Giant stone boulder resting on right beam end
        rx = bx2 - int(w * 0.12)
        ry = by2 - int(h * 0.32)
        br = int(min(w, h) * 0.30)
        draw.ellipse([rx - br, ry - br, rx + br, ry + br], fill=_hex_to_rgba("#78716C", 75), outline=ink, width=lw)

    def _draw_iceberg(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        water_y = y + int(h * 0.36)
        # Small tip above water
        tip_pts = [(x + int(w * 0.48), y + int(h * 0.08)), (x + int(w * 0.38), water_y), (x + int(w * 0.60), water_y)]
        draw.polygon(tip_pts, fill=_hex_to_rgba("#E0F2FE", 180), outline=ink, width=lw)
        # Massive underwater mountain
        base_pts = [
            (x + int(w * 0.38), water_y),
            (x + int(w * 0.10), y + int(h * 0.75)),
            (x + int(w * 0.30), y + int(h * 0.95)),
            (x + int(w * 0.75), y + int(h * 0.92)),
            (x + int(w * 0.90), y + int(h * 0.65)),
            (x + int(w * 0.60), water_y),
        ]
        draw.polygon(base_pts, fill=_hex_to_rgba("#38BDF8", 65), outline=_hex_to_rgba(ink, 150), width=lw)
        # Waterline wave
        draw.line([(x, water_y), (x + w, water_y)], fill="#0284C7", width=max(2, lw + 1))

    def _draw_hamster_wheel(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        cx, cy = x + w // 2, y + int(h * 0.46)
        r = int(min(w, h) * 0.42)
        # Stand base
        draw.line([(cx, cy), (x + int(w * 0.2), y + h - lw)], fill=ink, width=lw)
        draw.line([(cx, cy), (x + int(w * 0.8), y + h - lw)], fill=ink, width=lw)
        draw.line([(x + int(w * 0.15), y + h - lw), (x + int(w * 0.85), y + h - lw)], fill=ink, width=lw)
        # Circular outer rim
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], outline=ink, width=lw)
        # Rotating spokes
        rot = t * math.pi * 4
        for i in range(6):
            ang = rot + i * (math.pi / 3)
            sx = cx + int(r * math.cos(ang))
            sy = cy + int(r * math.sin(ang))
            draw.line([(cx, cy), (sx, sy)], fill=_hex_to_rgba(ink, 120), width=max(1, lw - 1))

    def _draw_juggling_balls(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        colors = ["#EF4444", "#3B82F6", "#10B981", "#F59E0B"]
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        br = max(7, int(min(w, h) * 0.10))
        for i, col in enumerate(colors):
            phase = (t * 2.0 + i * 0.25) % 1.0
            bx = x + int(w * (0.15 + 0.70 * phase))
            by = y + int(h * 0.85 - math.sin(phase * math.pi) * h * 0.75)
            draw.ellipse([bx - br, by - br, bx + br, by + br], fill=col, outline=self._ink(), width=lw)

    def _draw_dominoes(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        n_dominoes = 5
        dw = int(w * 0.09)
        dh = int(h * 0.60)
        base_y = y + int(h * 0.90)
        for i in range(n_dominoes):
            dx = x + int(w * (0.12 + i * 0.18))
            # First dominoes tip forward
            tip = min(1.0, max(0.0, (t * 2.5 - i * 0.35)))
            angle = tip * 0.45
            x_top = dx + int(dh * math.sin(angle))
            y_top = base_y - int(dh * math.cos(angle))
            draw.line([(dx, base_y), (x_top, y_top)], fill=ink, width=max(3, dw))
            draw.ellipse([x_top - dw // 2, y_top - dw // 2, x_top + dw // 2, y_top + dw // 2], fill=ink)

    def _draw_brick_wall(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 2.5)))
        rows = 4
        cols = 4
        rw = w / cols
        rh = h / rows
        for r in range(rows):
            for c in range(cols):
                shift = (rw * 0.5) if (r % 2 == 1) else 0.0
                bx1 = int(x + c * rw + shift)
                by1 = int(y + r * rh)
                bx2 = int(bx1 + rw - 3)
                by2 = int(by1 + rh - 3)
                if bx2 > x + w:
                    continue
                draw.rectangle([bx1, by1, bx2, by2], fill=_hex_to_rgba("#D97706", 80), outline=ink, width=lw)

    def _draw_cracked_wall(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        draw.rectangle([x, y, x + w, y + h], fill=_hex_to_rgba("#78716C", 45), outline=ink, width=lw)
        # Jagged lightning crack through center
        cx = x + w // 2
        pts = [(cx, y), (cx - int(w * 0.08), y + int(h * 0.25)), (cx + int(w * 0.10), y + int(h * 0.50)), (cx - int(w * 0.06), y + int(h * 0.75)), (cx + int(w * 0.04), y + h)]
        draw.line(pts, fill="#FBBF24", width=max(3, lw + 1))
        # Golden rays bursting outward
        for li in range(5):
            ray_y = y + int(h * (0.2 + li * 0.15))
            draw.line([(cx, ray_y), (cx + int(w * 0.28), ray_y - int(h * 0.08))], fill=_hex_to_rgba("#F59E0B", 140), width=max(1, lw - 1))

    def _draw_battery_drain(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        bw = int(w * 0.85)
        bh = int(h * 0.65)
        by = y + int(h * 0.18)
        # Outer chassis
        draw.rounded_rectangle([x, by, x + bw, by + bh], radius=6, outline=ink, width=lw)
        # Positive terminal knob
        tw = int(w * 0.08)
        th = int(bh * 0.40)
        draw.rounded_rectangle([x + bw, by + (bh - th) // 2, x + bw + tw, by + (bh + th) // 2], radius=2, fill=ink)
        # Blinking 1% red battery level
        lvl_w = max(4, int(bw * max(0.08, 0.35 - t * 0.28)))
        blink = (int(t * 12) % 2 == 0)
        col = "#EF4444" if blink else "#B91C1C"
        draw.rectangle([x + lw + 2, by + lw + 2, x + lw + lvl_w, by + bh - lw - 2], fill=col)

    def _draw_balance_scale(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        cx = x + w // 2
        # Vertical pillar
        draw.line([(cx, y + int(h * 0.12)), (cx, y + int(h * 0.88))], fill=ink, width=lw + 1)
        # Base
        draw.line([(cx - int(w * 0.25), y + int(h * 0.88)), (cx + int(w * 0.25), y + int(h * 0.88))], fill=ink, width=lw + 2)
        # Tipping balance beam
        tilt = math.sin(t * math.pi * 2) * int(h * 0.10)
        draw.line([(x + int(w * 0.15), y + int(h * 0.22) + tilt), (x + int(w * 0.85), y + int(h * 0.22) - tilt)], fill=ink, width=lw)
        # Left and right pans
        pw = int(w * 0.18)
        draw.arc([x + int(w * 0.15) - pw // 2, y + int(h * 0.45) + tilt, x + int(w * 0.15) + pw // 2, y + int(h * 0.55) + tilt], start=0, end=180, fill=ink, width=lw)
        draw.arc([x + int(w * 0.85) - pw // 2, y + int(h * 0.45) - tilt, x + int(w * 0.85) + pw // 2, y + int(h * 0.55) - tilt], start=0, end=180, fill=ink, width=lw)

    def _draw_hourglass(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Top and bottom caps
        draw.line([(x + int(w * 0.15), y), (x + int(w * 0.85), y)], fill=ink, width=lw + 1)
        draw.line([(x + int(w * 0.15), y + h), (x + int(w * 0.85), y + h)], fill=ink, width=lw + 1)
        # Glass bulbs meeting in narrow neck
        cx = x + w // 2
        cy = y + h // 2
        neck = int(w * 0.08)
        draw.polygon([(x + int(w * 0.18), y), (x + int(w * 0.82), y), (cx + neck, cy), (cx - neck, cy)], fill=_hex_to_rgba("#FBBF24", 45), outline=ink, width=lw)
        draw.polygon([(cx - neck, cy), (cx + neck, cy), (x + int(w * 0.82), y + h), (x + int(w * 0.18), y + h)], fill=_hex_to_rgba("#FBBF24", 95), outline=ink, width=lw)

    def _draw_podium(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        pw = w // 3
        base_y = y + h
        # #2 (Left)
        draw.rectangle([x, base_y - int(h * 0.60), x + pw, base_y], fill=_hex_to_rgba("#94A3B8", 65), outline=ink, width=lw)
        # #1 (Center - Tallest)
        draw.rectangle([x + pw, base_y - int(h * 0.90), x + pw * 2, base_y], fill=_hex_to_rgba("#F59E0B", 85), outline=ink, width=lw)
        # #3 (Right)
        draw.rectangle([x + pw * 2, base_y - int(h * 0.45), x + w, base_y], fill=_hex_to_rgba("#D97706", 65), outline=ink, width=lw)

    def _draw_shield(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        cx = x + w // 2
        pts = [(x + int(w * 0.15), y + int(h * 0.12)), (x + int(w * 0.85), y + int(h * 0.12)), (x + int(w * 0.85), y + int(h * 0.60)), (cx, y + int(h * 0.95)), (x + int(w * 0.15), y + int(h * 0.60))]
        draw.polygon(pts, fill=_hex_to_rgba("#3B82F6", 65), outline=ink, width=lw)
        # Cross emblem
        draw.line([(cx, y + int(h * 0.25)), (cx, y + int(h * 0.70))], fill="#FFFFFF", width=max(2, lw))
        draw.line([(cx - int(w * 0.20), y + int(h * 0.40)), (cx + int(w * 0.20), y + int(h * 0.40))], fill="#FFFFFF", width=max(2, lw))

    def _draw_magnifying_glass(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        r = int(min(w, h) * 0.32)
        cx = x + int(w * 0.42)
        cy = y + int(h * 0.42)
        # Glass lens with reflection
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=_hex_to_rgba("#E0F2FE", 140), outline=ink, width=lw)
        draw.arc([cx - r + 3, cy - r + 3, cx + r - 3, cy + r - 3], start=210, end=300, fill="#FFFFFF", width=max(2, lw))
        # Handle extending diagonally down-right
        hx1 = cx + int(r * 0.7)
        hy1 = cy + int(r * 0.7)
        hx2 = x + int(w * 0.90)
        hy2 = y + int(h * 0.90)
        draw.line([(hx1, hy1), (hx2, hy2)], fill=ink, width=max(4, lw + 2))

    def _draw_bed(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        hb_w = max(10, int(w * 0.08))
        draw.rounded_rectangle([x, y + int(h * 0.15), x + hb_w, y + h], radius=4, fill=_hex_to_rgba("#78350F", 180), outline=ink, width=lw)
        mat_y = y + int(h * 0.52)
        draw.rounded_rectangle([x + hb_w, mat_y, x + w - int(w * 0.05), y + int(h * 0.85)], radius=8, fill=_hex_to_rgba("#F8FAFC", 240), outline=ink, width=lw)
        draw.rectangle([x + hb_w, y + int(h * 0.82), x + w - int(w * 0.05), y + int(h * 0.88)], fill=_hex_to_rgba("#92400E", 200), outline=ink, width=lw)
        leg_w = max(6, int(w * 0.05))
        draw.rectangle([x + w - int(w * 0.05) - leg_w, y + int(h * 0.88), x + w - int(w * 0.05), y + h], fill=_hex_to_rgba("#78350F", 220), outline=ink, width=lw)
        pil_w = int(w * 0.22)
        pil_h = int(h * 0.18)
        draw.rounded_rectangle([x + hb_w + 6, mat_y - int(pil_h * 0.5), x + hb_w + 6 + pil_w, mat_y + int(pil_h * 0.5)], radius=12, fill="#FFFFFF", outline=ink, width=max(2, lw - 1))
        bl_x = x + hb_w + int(w * 0.24)
        draw.rounded_rectangle([bl_x, mat_y + 4, x + w - int(w * 0.05), y + int(h * 0.84)], radius=6, fill=_hex_to_rgba("#3B82F6", 180), outline=ink, width=lw)
        draw.rounded_rectangle([bl_x - 4, mat_y + 2, bl_x + int(w * 0.08), y + int(h * 0.84)], radius=4, fill=_hex_to_rgba("#60A5FA", 220), outline=ink, width=max(1, lw - 1))

    def _draw_nightstand_clock(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        draw.rounded_rectangle([x + int(w * 0.15), y + int(h * 0.40), x + int(w * 0.85), y + int(h * 0.95)], radius=6, fill=_hex_to_rgba("#A16207", 180), outline=ink, width=lw)
        draw.line([(x + int(w * 0.20), y + int(h * 0.65)), (x + int(w * 0.80), y + int(h * 0.65))], fill=ink, width=lw)
        draw.ellipse([x + int(w * 0.50) - 4, y + int(h * 0.52) - 4, x + int(w * 0.50) + 4, y + int(h * 0.52) + 4], fill=ink)
        draw.line([(x + int(w * 0.22), y + int(h * 0.95)), (x + int(w * 0.22), y + h)], fill=ink, width=lw + 1)
        draw.line([(x + int(w * 0.78), y + int(h * 0.95)), (x + int(w * 0.78), y + h)], fill=ink, width=lw + 1)
        clk_w = int(w * 0.50)
        clk_h = int(h * 0.25)
        clk_x = x + int(w * 0.25)
        clk_y = y + int(h * 0.15)
        draw.rounded_rectangle([clk_x, clk_y, clk_x + clk_w, clk_y + clk_h], radius=5, fill=_hex_to_rgba("#0F172A", 240), outline=ink, width=lw)
        fnt = _load_ui_font(max(10, int(clk_h * 0.65)), bold=True)
        draw.text((clk_x + clk_w // 2, clk_y + clk_h // 2), "11:47", fill="#EF4444", font=fnt, anchor="mm")

    def _draw_thought_cloud(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        w = max(40, w)
        h = max(30, h)
        draw.ellipse([x + int(w * 0.12), y + int(h * 0.90), max(x + int(w * 0.12) + 4, x + int(w * 0.18)), y + h], fill=_hex_to_rgba("#F1F5F9", 220), outline=ink, width=max(1, lw - 1))
        draw.ellipse([x + int(w * 0.20), y + int(h * 0.78), max(x + int(w * 0.20) + 6, x + int(w * 0.28)), max(y + int(h * 0.78) + 6, y + int(h * 0.88))], fill=_hex_to_rgba("#F1F5F9", 220), outline=ink, width=max(1, lw - 1))
        cw = max(30, int(w * 0.85))
        ch = max(20, int(h * 0.75))
        cx0 = x + int(w * 0.10)
        cy0 = y
        pad_x = min(8, cw // 4)
        pad_y = min(8, ch // 4)
        rx0 = cx0 + pad_x
        ry0 = cy0 + pad_y
        rx1 = max(rx0 + 10, cx0 + cw - pad_x)
        ry1 = max(ry0 + 10, cy0 + ch - pad_y)
        rad = max(4, min(18, (rx1 - rx0) // 3, (ry1 - ry0) // 3))
        draw.rounded_rectangle([rx0, ry0, rx1, ry1], radius=rad, fill=_hex_to_rgba("#F8FAFC", 235), outline=ink, width=lw)
        lobes = [
            (cx0 + int(cw * 0.25), cy0 + 8, max(8, int(cw * 0.22))),
            (cx0 + int(cw * 0.50), cy0 + 4, max(10, int(cw * 0.26))),
            (cx0 + int(cw * 0.75), cy0 + 10, max(8, int(cw * 0.20))),
            (cx0 + int(cw * 0.15), cy0 + int(ch * 0.50), max(8, int(cw * 0.20))),
            (cx0 + int(cw * 0.85), cy0 + int(ch * 0.50), max(8, int(cw * 0.20))),
        ]
        for lx, ly, lr in lobes:
            draw.ellipse([lx - lr // 2, ly - lr // 2, lx + lr // 2, ly + lr // 2], fill=_hex_to_rgba("#F8FAFC", 235))
            draw.arc([lx - lr // 2, ly - lr // 2, lx + lr // 2, ly + lr // 2], start=180, end=360, fill=ink, width=lw)
        fnt = _load_ui_font(max(10, int(ch * 0.24)), bold=True)
        draw.text((cx0 + cw // 2, cy0 + ch // 2), "MEMORY", fill=_hex_to_rgba("#64748B", 200), font=fnt, anchor="mm")

    def _draw_split_divider(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        cx = x + w // 2
        draw.line([(cx, y), (cx, y + h)], fill=ink, width=lw)
        bw = max(36, int(w * 0.35))
        bh = max(24, int(h * 0.16))
        cy = y + h // 2
        draw.rounded_rectangle([cx - bw // 2, cy - bh // 2, cx + bw // 2, cy + bh // 2], radius=10, fill=_hex_to_rgba("#1E293B", 230), outline="#38BDF8", width=max(1, lw - 1))
        fnt = _load_ui_font(max(10, int(bh * 0.55)), bold=True)
        draw.text((cx, cy), "VS", fill="#FFFFFF", font=fnt, anchor="mm")

    def _draw_folder_document(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        draw.rounded_rectangle([x + int(w * 0.08), y + int(h * 0.18), x + int(w * 0.42), y + int(h * 0.35)], radius=6, fill=_hex_to_rgba("#D97706", 210), outline=ink, width=lw)
        draw.rounded_rectangle([x + int(w * 0.05), y + int(h * 0.28), x + int(w * 0.95), y + int(h * 0.92)], radius=8, fill=_hex_to_rgba("#F59E0B", 210), outline=ink, width=lw)
        doc_y = y + int(h * 0.10 * (1.0 - t * 0.4))
        draw.rounded_rectangle([x + int(w * 0.14), doc_y, x + int(w * 0.86), y + int(h * 0.85)], radius=4, fill="#FFFFFF", outline=ink, width=max(1, lw - 1))
        draw.rectangle([x + int(w * 0.20), doc_y + int(h * 0.08), x + int(w * 0.80), doc_y + int(h * 0.20)], fill=_hex_to_rgba("#EF4444", 40), outline="#EF4444", width=1)
        fnt = _load_ui_font(max(9, int(h * 0.09)), bold=True)
        draw.text((x + w // 2, doc_y + int(h * 0.14)), "SECRET FILE", fill="#EF4444", font=fnt, anchor="mm")
        for ly in (0.28, 0.38, 0.48):
            draw.line([(x + int(w * 0.22), doc_y + int(h * ly)), (x + int(w * 0.78), doc_y + int(h * ly))], fill=_hex_to_rgba("#94A3B8", 160), width=max(1, lw - 1))

    def _draw_alert_stamp(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        cx = x + w // 2
        cy = y + h // 2
        for ring_r in (int(min(w, h) * 0.45), int(min(w, h) * 0.38)):
            draw.ellipse([cx - ring_r, cy - ring_r, cx + ring_r, cy + ring_r], outline=_hex_to_rgba("#EF4444", int(80 * (1.0 - t * 0.3))), width=max(1, lw - 1))
        sw = int(w * 0.75)
        sh = int(h * 0.42)
        draw.rounded_rectangle([cx - sw // 2, cy - sh // 2, cx + sw // 2, cy + sh // 2], radius=6, fill=_hex_to_rgba("#FEE2E2", 230), outline="#DC2626", width=lw + 1)
        draw.rectangle([cx - sw // 2 + 3, cy - sh // 2 + 3, cx + sw // 2 - 3, cy + sh // 2 - 3], outline="#DC2626", width=1)
        fnt = _load_ui_font(max(11, int(sh * 0.45)), bold=True)
        draw.text((cx, cy), "URGENT!", fill="#DC2626", font=fnt, anchor="mm")

    def _draw_megaphone(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        pts = [
            (x + int(w * 0.22), y + int(h * 0.38)),
            (x + int(w * 0.70), y + int(h * 0.15)),
            (x + int(w * 0.70), y + int(h * 0.85)),
            (x + int(w * 0.22), y + int(h * 0.62)),
        ]
        draw.polygon(pts, fill=_hex_to_rgba("#F59E0B", 220), outline=ink, width=lw)
        draw.rounded_rectangle([x + int(w * 0.12), y + int(h * 0.35), x + int(w * 0.24), y + int(h * 0.65)], radius=4, fill=_hex_to_rgba("#475569", 220), outline=ink, width=lw)
        draw.polygon([(x + int(w * 0.28), y + int(h * 0.60)), (x + int(w * 0.36), y + int(h * 0.60)), (x + int(w * 0.34), y + int(h * 0.90)), (x + int(w * 0.26), y + int(h * 0.88))], fill=ink)
        for idx, dist in enumerate((0.78, 0.88, 0.98)):
            wave_w = int(w * dist)
            draw.arc([wave_w - 8, y + int(h * (0.25 - idx * 0.05)), wave_w + 12, y + int(h * (0.75 + idx * 0.05))], start=300, end=420, fill="#EF4444", width=max(1, lw - 1))

    def _draw_crowd_row(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        lw = max(1, int(self.sp.get("line_width", 2.5)))
        count = 5
        slot_w = w / count
        head_r = max(4, int(slot_w * 0.16))
        for i in range(count):
            fx = int(x + slot_w * (i + 0.5))
            fy = y + int(h * 0.35)
            is_accent = (i != 4)
            col = "#06B6D4" if is_accent else "#EF4444"
            draw.ellipse([fx - head_r, fy - head_r, fx + head_r, fy + head_r], fill="#FFFFFF", outline=col, width=lw)
            neck_y = fy + head_r
            hip_y = neck_y + int(h * 0.28)
            draw.line([(fx, neck_y), (fx, hip_y)], fill=col, width=lw)
            draw.line([(fx - int(slot_w * 0.20), neck_y + 6), (fx + int(slot_w * 0.20), neck_y + 6)], fill=col, width=lw)
            draw.line([(fx, hip_y), (fx - int(slot_w * 0.16), y + int(h * 0.90))], fill=col, width=lw)
            draw.line([(fx, hip_y), (fx + int(slot_w * 0.16), y + int(h * 0.90))], fill=col, width=lw)

    def _draw_doodle_arrow(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        pts = [
            (x + int(w * 0.10), y + int(h * 0.70)),
            (x + int(w * 0.35), y + int(h * 0.25)),
            (x + int(w * 0.75), y + int(h * 0.30)),
            (x + int(w * 0.88), y + int(h * 0.50)),
        ]
        col = self.sp.get("accent", "#38BDF8")
        draw.line(pts, fill=col, width=lw, joint="curve")
        ax, ay = pts[-1]
        draw.polygon([(ax, ay), (ax - 12, ay - 8), (ax - 8, ay + 10)], fill=col)

    def _draw_diya(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        draw.arc([x + int(w * 0.15), y + int(h * 0.40), x + int(w * 0.85), y + int(h * 0.90)], start=0, end=180, fill=_hex_to_rgba("#B45309", 230), width=lw + 2)
        draw.line([(x + int(w * 0.15), y + int(h * 0.65)), (x + int(w * 0.85), y + int(h * 0.65))], fill=ink, width=lw)
        flicker = math.sin(t * math.pi * 6.0) * 2.0
        fx = x + int(w * 0.50)
        fy = y + int(h * 0.52)
        fw = int(w * 0.15)
        fh = int(h * 0.35 + flicker)
        draw.ellipse([fx - fw * 2, fy - fh - 10, fx + fw * 2, fy + 10], fill=_hex_to_rgba("#F59E0B", 45))
        draw.polygon([(fx, fy - fh), (fx + fw, fy - int(fh * 0.3)), (fx, fy), (fx - fw, fy - int(fh * 0.3))], fill="#F59E0B")
        draw.polygon([(fx, fy - int(fh * 0.7)), (fx + int(fw * 0.5), fy - int(fh * 0.2)), (fx, fy), (fx - int(fw * 0.5), fy - int(fh * 0.2))], fill="#FEF08A")

    # ------------------------------------------------------------------
    # Advanced Psychological & Storytelling Metaphors (Atharv Hatwar)
    # ------------------------------------------------------------------

    def _draw_mousetrap(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Wooden base block
        base_y = y + int(h * 0.68)
        draw.rounded_rectangle([x, base_y, x + w, y + h], radius=6, fill=_hex_to_rgba("#F1F5F9", 250), outline=ink, width=lw)
        draw.line([(x + 10, base_y + int((y + h - base_y) * 0.45)), (x + w - 10, base_y + int((y + h - base_y) * 0.45))], fill=_hex_to_rgba(ink, 40), width=1)
        # Coiled metal spring in center
        cx = x + w // 2
        draw.arc([cx - 16, base_y - 8, cx + 16, base_y + 14], start=0, end=360, fill=ink, width=lw)
        # Cocked snap bar angled up menacingly
        draw.line([(cx, base_y), (x + int(w * 0.84), y + int(h * 0.14))], fill=ink, width=lw + 2)
        # Bait plate: Smartphone with glowing heart
        bx1, by1 = x + int(w * 0.18), base_y - int(h * 0.22)
        bx2, by2 = x + int(w * 0.42), base_y
        draw.rounded_rectangle([bx1, by1, bx2, by2], radius=4, fill="#FFFFFF", outline=ink, width=lw)
        # Heart on bait screen
        hx = (bx1 + bx2) // 2
        hy = (by1 + by2) // 2
        hr = max(3, int((bx2 - bx1) * 0.22))
        draw.ellipse([hx - hr * 2, hy - hr * 2, hx + hr * 2, hy + hr * 2], fill=_hex_to_rgba(acc, 50))
        draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=acc)

    def _draw_glass_jar_prison(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # High shelf
        sy = y + int(h * 0.80)
        draw.rectangle([x, sy, x + w, sy + int(h * 0.08)], fill=_hex_to_rgba("#475569", 230), outline=ink, width=lw)
        # Shelf brackets underneath
        draw.line([(x + int(w * 0.25), sy + int(h * 0.08)), (x + int(w * 0.25), y + h)], fill=ink, width=lw)
        draw.line([(x + int(w * 0.75), sy + int(h * 0.08)), (x + int(w * 0.75), y + h)], fill=ink, width=lw)
        # Glass jar body
        jx1, jy1 = x + int(w * 0.18), y + int(h * 0.12)
        jx2, jy2 = x + int(w * 0.82), sy
        draw.rounded_rectangle([jx1, jy1, jx2, jy2], radius=16, fill=_hex_to_rgba("#E0F2FE", 55), outline=ink, width=lw)
        # Glass reflection shine
        draw.arc([jx1 + 8, jy1 + 10, jx1 + 35, jy2 - 12], start=90, end=270, fill="#FFFFFF", width=max(2, lw - 1))
        # Jar screw lid
        draw.rounded_rectangle([x + int(w * 0.25), y + int(h * 0.05), x + int(w * 0.75), jy1], radius=4, fill=acc, outline=ink, width=lw)
        # Stickman curled inside the jar
        cx = (jx1 + jx2) // 2
        cy = (jy1 + jy2) // 2
        draw.ellipse([cx - 10, cy - 14, cx + 10, cy + 6], fill="#FFFFFF", outline=ink, width=lw)
        draw.line([(cx, cy + 6), (cx - 4, cy + 24)], fill=ink, width=lw)
        draw.line([(cx - 4, cy + 24), (cx + 8, cy + 18)], fill=ink, width=lw)
        draw.line([(cx + 8, cy + 18), (cx + 10, cy + 30)], fill=ink, width=lw)

    def _draw_tether_thread(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        mid_y = y + h // 2
        # Outer glow
        draw.line([(x, mid_y), (x + w, mid_y)], fill=_hex_to_rgba(acc, 50), width=lw * 3)
        # Core taut thread
        draw.line([(x, mid_y), (x + w, mid_y)], fill=acc, width=lw)
        # Strain tension markers
        draw.line([(x + 25, mid_y - 6), (x + 35, mid_y + 6)], fill=acc, width=2)
        draw.line([(x + w - 35, mid_y - 6), (x + w - 25, mid_y + 6)], fill=acc, width=2)

    def _draw_puppet_strings(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Overhead wooden cross controller
        top_y = y + int(h * 0.08)
        draw.line([(x + int(w * 0.15), top_y), (x + int(w * 0.85), top_y)], fill=ink, width=lw + 2)
        draw.line([(x + w // 2, y), (x + w // 2, top_y + 12)], fill=ink, width=lw + 2)
        # Crimson puppet strings
        for px in (0.22, 0.42, 0.58, 0.78):
            sx = x + int(w * px)
            draw.line([(sx, top_y), (sx, y + int(h * 0.95))], fill=acc, width=lw)

    def _draw_sigh_shockwaves(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Expanding acoustic concentric arcs
        for f in (0.35, 0.65, 0.95):
            box = [x, y, x + int(w * f), y + int(h * f)]
            draw.arc(box, start=305, end=55, fill=acc, width=lw)

    def _draw_doorway_sunlight(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Door frame
        dx1, dy1 = x + int(w * 0.20), y + int(h * 0.12)
        dx2, dy2 = x + int(w * 0.80), y + h
        draw.rectangle([dx1, dy1, dx2, dy2], fill="#FFFFFF", outline=ink, width=lw)
        # Radiant sunbeams
        for a in (-0.25, -0.08, 0.08, 0.25):
            draw.line([(x + w // 2, dy1 + 20), (int(x + w // 2 + a * w * 2.2), dy2)], fill=_hex_to_rgba("#FBBF24", 85), width=max(2, lw - 1))
        # EXIT sign above door
        draw.rounded_rectangle([x + int(w * 0.32), y, x + int(w * 0.68), dy1 - 4], radius=3, fill=ink)
        fnt = _load_ui_font(max(9, int(h * 0.08)), bold=True)
        draw.text((x + w // 2, (y + dy1 - 4) // 2), "EXIT", fill="#FFFFFF", font=fnt, anchor="mm")

    def _draw_notification_popups(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Floating message card
        card_h = int(h * 0.72)
        draw.rounded_rectangle([x, y, x + w, y + card_h], radius=10, fill="#FFFFFF", outline=ink, width=lw)
        # Red circular heart badge
        bx, by = x + 12, y + 12
        bw = min(30, int(card_h * 0.45))
        draw.ellipse([bx, by, bx + bw, by + bw], fill=acc)
        # Subtext lines
        fnt = _load_ui_font(max(10, int(card_h * 0.22)), bold=True)
        draw.text((bx + bw + 10, y + int(card_h * 0.30)), "Story Reply", fill=ink, font=fnt, anchor="lm")
        fnt2 = _load_ui_font(max(9, int(card_h * 0.18)), bold=False)
        draw.text((bx + bw + 10, y + int(card_h * 0.65)), "how have you been? 🥺", fill=_hex_to_rgba(ink, 160), font=fnt2, anchor="lm")

    def _draw_breadcrumb_trail(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        acc = self.sp.get("accent", "#E03E36")
        cy = y + h // 2
        for i in range(5):
            bx = x + int(w * (i + 1) / 6)
            draw.ellipse([bx - 10, cy - 10, bx + 10, cy + 10], fill=_hex_to_rgba(acc, 45))
            draw.ellipse([bx - 5, cy - 5, bx + 5, cy + 5], fill=acc)

    def _draw_broken_crown(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Regal crown base and 3 peaks
        pts = [
            (x + int(w * 0.12), y + int(h * 0.82)),
            (x + int(w * 0.88), y + int(h * 0.82)),
            (x + w, y + int(h * 0.25)),
            (x + int(w * 0.68), y + int(h * 0.50)),
            (x + w // 2, y + int(h * 0.15)),
            (x + int(w * 0.32), y + int(h * 0.50)),
            (x, y + int(h * 0.25)),
        ]
        draw.polygon(pts, fill=_hex_to_rgba("#F59E0B", 95), outline=ink, width=lw)
        # Jagged fracture crack
        draw.line([(x + w // 2, y + int(h * 0.15)), (x + int(w * 0.44), y + int(h * 0.48)), (x + int(w * 0.54), y + int(h * 0.82))], fill=acc, width=lw + 1)

    def _draw_giant_clock(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Clock face
        draw.ellipse([x, y, x + w, y + h], fill="#FFFFFF", outline=ink, width=lw + 1)
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2
        # Tick marks
        for a_deg in (0, 30, 60, 90, 120, 150, 180, 210, 240, 270, 300, 330):
            ang = math.radians(a_deg)
            tx1 = cx + math.cos(ang) * (r - 14)
            ty1 = cy + math.sin(ang) * (r - 14)
            tx2 = cx + math.cos(ang) * (r - 4)
            ty2 = cy + math.sin(ang) * (r - 4)
            draw.line([(tx1, ty1), (tx2, ty2)], fill=ink, width=2)
        # Hands: Minute hand up, Hour hand in red
        draw.line([(cx, cy), (cx, cy - int(r * 0.65))], fill=ink, width=lw + 1)
        draw.line([(cx, cy), (cx + int(r * 0.45), cy + int(r * 0.25))], fill=acc, width=lw + 2)

    def _draw_snipped_thread_sunrise(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Radiant rising sun on horizon
        sun_box = [x + int(w * 0.15), y + int(h * 0.35), x + int(w * 0.85), y + h + int(h * 0.35)]
        draw.pieslice(sun_box, start=180, end=360, fill=_hex_to_rgba("#FBBF24", 160), outline=ink, width=lw)
        # Rising rays
        cx = x + w // 2
        cy = y + int(h * 0.70)
        for a_deg in (200, 230, 270, 310, 340):
            ang = math.radians(a_deg)
            rx = cx + math.cos(ang) * (w * 0.45)
            ry = cy + math.sin(ang) * (h * 0.45)
            draw.line([(cx, cy), (rx, ry)], fill=_hex_to_rgba("#FBBF24", 90), width=lw)
        # Snipped red thread ends on ground
        draw.line([(x + int(w * 0.1), y + int(h * 0.85)), (x + int(w * 0.35), y + int(h * 0.88))], fill=acc, width=lw + 1)
        draw.line([(x + int(w * 0.65), y + int(h * 0.88)), (x + int(w * 0.9), y + int(h * 0.85))], fill=acc, width=lw + 1)
        # Cut indicator
        fnt = _load_ui_font(max(10, int(h * 0.12)), bold=True)
        draw.text((cx, y + int(h * 0.85)), "*SNIP*", fill=acc, font=fnt, anchor="mm")

    def _draw_chasm_crack(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.5)))
        # Jagged canyon split
        pts = [
            (x + int(w * 0.45), y),
            (x + int(w * 0.55), y),
            (x + int(w * 0.65), y + int(h * 0.4)),
            (x + int(w * 0.58), y + h),
            (x + int(w * 0.42), y + h),
            (x + int(w * 0.48), y + int(h * 0.5)),
        ]
        draw.polygon(pts, fill=_hex_to_rgba(ink, 40), outline=ink, width=lw)

    def _draw_ego_trophy(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#E03E36")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Pedestal
        draw.rectangle([x + int(w * 0.2), y + int(h * 0.75), x + int(w * 0.8), y + h], fill=_hex_to_rgba("#94A3B8", 120), outline=ink, width=lw)
        # Trophy cup
        tx1, ty1 = x + int(w * 0.28), y + int(h * 0.2)
        tx2, ty2 = x + int(w * 0.72), y + int(h * 0.6)
        draw.arc([tx1, ty1, tx2, ty2 + int(h * 0.1)], start=0, end=180, fill=_hex_to_rgba("#F59E0B", 180), width=lw + 1)
        # Red heart on trophy
        cx = x + w // 2
        cy = y + int(h * 0.45)
        draw.ellipse([cx - 8, cy - 8, cx + 8, cy + 8], fill=acc)

    def _draw_message_bubble_incoming(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#38BDF8")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        pop = min(1.0, t * 1.4)
        bw, bh = int(w * pop), int(h * pop)
        draw.rounded_rectangle([x, y, x + bw, y + bh], radius=max(6, bh // 4), fill="#E0F2FE", outline=ink, width=lw)
        # Text simulation line inside
        line_w = int(bw * 0.65)
        draw.line([(x + int(bw * 0.18), y + bh // 2), (x + int(bw * 0.18) + line_w, y + bh // 2)], fill=acc, width=max(2, lw))
        # Tail on left
        tail_pts = [(x, y + int(bh * 0.6)), (x - max(6, int(w * 0.08)), y + int(bh * 0.8)), (x + max(4, int(w * 0.05)), y + int(bh * 0.8))]
        draw.polygon(tail_pts, fill="#E0F2FE", outline=ink)

    def _draw_message_bubbles_stack(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        sub_h = h // 3
        self._draw_message_bubble_incoming(draw, x, y, int(w * 0.85), sub_h - 4, t=t)
        self._draw_message_bubble_incoming(draw, x + int(w * 0.1), y + sub_h, int(w * 0.9), sub_h - 4, t=t)
        self._draw_message_bubble_incoming(draw, x, y + sub_h * 2, w, sub_h - 4, t=t)

    def _draw_short_reply_bubble(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 2.5)))
        bw = max(24, int(w * 0.45))
        bh = max(18, int(h * 0.55))
        draw.rounded_rectangle([x + w - bw, y, x + w, y + bh], radius=max(4, bh // 4), fill="#F1F5F9", outline=ink, width=lw)
        # Dot dot or single character line
        draw.ellipse([x + w - bw + 8, y + bh // 2 - 2, x + w - bw + 12, y + bh // 2 + 2], fill=ink)
        draw.ellipse([x + w - bw + 16, y + bh // 2 - 2, x + w - bw + 20, y + bh // 2 + 2], fill=ink)

    def _draw_missed_call_icon(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = "#EF4444"
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        cx, cy = x + w // 2, y + h // 2
        r = min(w, h) // 2
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill="#FEE2E2", outline=ink, width=lw)
        # Diagonal missed arrow
        draw.line([(cx + int(r * 0.35), cy - int(r * 0.35)), (cx - int(r * 0.35), cy + int(r * 0.35))], fill=ink, width=lw + 1)
        draw.polygon([(cx - int(r * 0.35), cy + int(r * 0.35)), (cx - int(r * 0.35), cy + int(r * 0.05)), (cx - int(r * 0.05), cy + int(r * 0.35))], fill=ink)

    def _draw_lighthouse_fog_beam(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#FBBF24")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Lighthouse tower
        bx, by = x + int(w * 0.15), y + h
        tx, ty = x + int(w * 0.22), y + int(h * 0.35)
        pts = [(bx - int(w * 0.08), by), (bx + int(w * 0.08), by), (tx + int(w * 0.05), ty), (tx - int(w * 0.05), ty)]
        draw.polygon(pts, fill="#F8FAFC", outline=ink, width=lw)
        # Lantern room
        draw.rectangle([tx - int(w * 0.06), ty - int(h * 0.12), tx + int(w * 0.06), ty], fill="#FEF08A", outline=ink, width=lw)
        # Radiant sweeping beam cutting through darkness
        beam_pulse = 0.85 + 0.15 * math.sin(t * 6.0)
        beam_pts = [
            (tx + int(w * 0.06), ty - int(h * 0.06)),
            (x + w, y + int(h * 0.05)),
            (x + w, y + int(h * 0.65)),
        ]
        draw.polygon(beam_pts, fill=_hex_to_rgba(acc, int(85 * beam_pulse)))

    def _draw_dopamine_spike_chart(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        acc = self.sp.get("accent", "#10B981")
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Baseline axis
        draw.line([(x, y + int(h * 0.8)), (x + w, y + int(h * 0.8))], fill=ink, width=lw)
        # Waveform with intermittent massive spike!
        pts = [
            (x, y + int(h * 0.78)),
            (x + int(w * 0.2), y + int(h * 0.75)),
            (x + int(w * 0.35), y + int(h * 0.77)),
            (x + int(w * 0.5), y + int(h * 0.15)),  # SPIKE!
            (x + int(w * 0.62), y + int(h * 0.76)),
            (x + int(w * 0.8), y + int(h * 0.74)),
            (x + w, y + int(h * 0.78)),
        ]
        draw.line(pts, fill=acc, width=lw + 1, joint="curve")
        # Star at top of spike
        sx, sy = x + int(w * 0.5), y + int(h * 0.15)
        draw.ellipse([sx - 8, sy - 8, sx + 8, sy + 8], fill="#FBBF24", outline=ink, width=lw)

    def _draw_split_mirror_ideal(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        cx, cy = x + w // 2, y + h // 2
        rw, rh = int(w * 0.38), int(h * 0.44)
        # Mirror frame
        draw.ellipse([cx - rw, cy - rh, cx + rw, cy + rh], fill="#F8FAFC", outline=ink, width=lw + 1)
        # Split line down center
        draw.line([(cx, cy - rh), (cx, cy + rh)], fill=ink, width=lw)
        # Left side: warm reflection glow
        draw.chord([cx - rw, cy - rh, cx + rw, cy + rh], start=90, end=270, fill=_hex_to_rgba("#FEF08A", 70))
        # Right side: cold darker reality
        draw.chord([cx - rw, cy - rh, cx + rw, cy + rh], start=270, end=90, fill=_hex_to_rgba("#94A3B8", 90))

    def _draw_pedestal_bust_trap(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, t: float = 1.0) -> None:
        ink = self._ink()
        lw = max(2, int(self.sp.get("line_width", 3.0)))
        # Pedestal base
        px1, py1 = x + int(w * 0.25), y + int(h * 0.62)
        px2, py2 = x + int(w * 0.75), y + h
        draw.rectangle([px1, py1, px2, py2], fill="#E2E8F0", outline=ink, width=lw)
        # Bust head on pedestal
        bx, by = x + w // 2, y + int(h * 0.35)
        br = int(min(w, h) * 0.18)
        draw.ellipse([bx - br, by - br, bx + br, by + br], fill="#FFFFFF", outline=ink, width=lw)
        # Bust shoulders
        draw.arc([bx - int(br * 1.5), by, bx + int(br * 1.5), py1], start=180, end=360, fill="#FFFFFF", width=lw)

    @staticmethod
    def _bg_abstract(draw: ImageDraw.ImageDraw, w: int, h: int, sp: dict) -> None:
        AssetLibrary._render_style_background(draw, "ABSTRACT", w, h, sp, str(sp.get("id", "a1_classic_bw")))

    @staticmethod
    def draw_background(draw: ImageDraw.ImageDraw, bg_name: str, width: int, height: int, style_params: dict, style: str = "") -> None:
        AssetLibrary._render_style_background(draw, bg_name.upper(), width, height, style_params, style or str(style_params.get("id", "a1_classic_bw")))
