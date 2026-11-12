"""
Scene Composer - Converts scene JSON descriptions into crisp 2x-AA PIL RGBA frames.
Created by Atharv Hatwar.
Coordinates:
- 11 Style Packs (A1-A6 Director & B1-B5 Autopilot) + style variations
- 2x supersampled characters planted squarely on the ground horizon across 9:16, 16:9, 1:1
- 2x supersampled animated props & metaphors
- Style-native overlays (headline callouts, B5 recurring presenter PIP, CRT scanlines,
  A6 amber noir rim & blinds, A3 fire embers, A4 cozy dust motes, B4 storm rain & flash)
"""

from __future__ import annotations

import hashlib
import math
import random
import re
import textwrap
from typing import Any, Callable, Iterator, Optional

from PIL import Image, ImageDraw, ImageFilter, ImageFont

from .assets import AssetLibrary, _hex_to_rgba, _is_dark_hex, _load_ui_font
from .stickman import POSE_SEQUENCES, StickmanRenderer
from engine.scene_templates import normalize_scene_for_composer
from styles.style_packs import (
    resolve_style_pack,
    get_adaptive_style_for_scene,
    synthesize_auto_style_for_scene,
)


_CHARACTER_PALETTE = [
    "#FF6B35",
    "#4FC3F7",
    "#66BB6A",
    "#AB47BC",
    "#FF7043",
    "#26C6DA",
    "#D4E157",
    "#EC407A",
]

_HEADLINE_STOPWORDS = {
    "the", "and", "that", "this", "with", "from", "your", "into", "when", "what",
    "have", "will", "about", "just", "they", "them", "than", "then", "very", "more",
    "most", "some", "been", "were", "their", "there", "which", "would", "could",
    "first", "glance", "surface", "looks", "like", "every", "picture", "everybody",
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _extract_headline(scene: dict[str, Any]) -> str:
    """Intrusive top headline banners disabled permanently per user directive."""
    return ""


class SceneComposer:
    """Renders scene dicts into anti-aliased, style-authentic PIL RGBA frames."""

    def __init__(
        self,
        style: str,
        width: int,
        height: int,
        fps: int = 24,
        style_variant: Optional[str] = None,
        use_lcm: bool = False,
    ) -> None:
        self.style = style
        self.style_variant = style_variant
        self.width = width
        self.height = height
        self.fps = fps
        self.use_lcm = use_lcm

        self.pack, self.sp = resolve_style_pack(style, style_variant)
        if use_lcm:
            self.sp["use_lcm"] = True
        self.renderer = StickmanRenderer(self.pack.id, variant=self.sp.get("variant"))
        self.assets = AssetLibrary(self.sp)
        self._scanline_cache: Optional[Image.Image] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compose_scene(self, scene: dict, duration: float) -> list[Image.Image]:
        return list(self.compose_scene_stream(scene, duration))

    def compose_scene_stream(self, scene: dict, duration: float) -> Iterator[Image.Image]:
        """Stream frames in O(1) memory with style-coherent scenery, actors & FX."""
        # Dynamic Auto / Chameleon Adaptive: synthesize or select bespoke per-scene style
        if self.style in ("auto", "s14_chameleon_adaptive"):
            narr = str(scene.get("narration", ""))
            emo = str(scene.get("emotion", ""))
            act = str(scene.get("action", ""))
            if not act and scene.get("characters"):
                act = str(scene["characters"][0].get("action", ""))
            if self.style == "auto":
                scene_pack, scene_sp = synthesize_auto_style_for_scene(
                    narration=narr,
                    emotion=emo,
                    action=act,
                    scene_idx=int(scene.get("id", 1)) - 1,
                    topic=str(scene.get("topic", "")),
                    variant=str(self.style_variant or "smart_mix"),
                )
            else:
                scene_style_id = get_adaptive_style_for_scene(narr, emo, act)
                scene_pack, scene_sp = resolve_style_pack(scene_style_id)
            if self.use_lcm:
                scene_sp["use_lcm"] = True
            self.pack = scene_pack
            self.sp = scene_sp
            self.renderer = StickmanRenderer(scene_pack.id, variant=scene_sp.get("variant"))
            self.renderer.params = dict(scene_sp)
            self.assets = AssetLibrary(scene_sp)

        scene = normalize_scene_for_composer(scene, style_id=self.pack.id)
        n_frames = max(1, int(round(duration * self.fps)))
        res_scale = max(0.5, min(self.width, self.height) / 540.0)
        floor_y = int(self.height * 0.74)

        bg_name = str(scene.get("background", self.sp.get("default_background", "ABSTRACT"))).upper()
        characters = scene.get("characters", [])
        effects = [str(e).upper() for e in scene.get("effects", [])]
        trans_in = str(scene.get("transition_in", scene.get("transition", self.sp.get("preferred_transition", "FADE")))).upper()
        trans_out = str(scene.get("transition_out", "CUT")).upper()
        camera = str(scene.get("camera", self.sp.get("preferred_camera", "MEDIUM"))).upper()

        # Precompute planted scales & hip Y so feet always rest cleanly on floor_y
        is_portrait = self.height > self.width * 1.1
        portrait_mult = (1.42 if len(characters) <= 1 else 1.20) if is_portrait else (1.14 if len(characters) <= 1 else 1.02)
        max_char_h = self.height * (0.54 if is_portrait else 0.60)
        char_scales: list[float] = []
        char_hips_y: list[float] = []
        for c in characters:
            raw_sc = float(c.get("scale", 1.42)) * res_scale * portrait_mult
            # Ensure character head doesn't exceed upper safe area on landscape 16:9
            if 135 * raw_sc > max_char_h:
                raw_sc = max(0.55, max_char_h / 135.0)
            y_frac = float(c.get("y", 0.62))
            act_c = str(c.get("action", "STAND")).upper()
            foot_off = 42.0 if act_c in ("SIT", "READ", "WRITE") else 56.0
            if 0.50 <= y_frac <= 0.72:
                hip_y = float(floor_y) - foot_off * raw_sc
            else:
                hip_y = y_frac * self.height
            char_scales.append(raw_sc)
            char_hips_y.append(hip_y)

        char_configs = self._build_char_configs(characters, n_frames, char_hips_y, res_scale=res_scale)
        base_bg = AssetLibrary.get_cached_background(
            bg_name, self.width, self.height, self.sp, style=self.pack.id, scene=scene
        )

        # Style-aware transition durations (slower/softer for A4 Cozy Storytelling)
        trans_sec = 0.45 if self.sp.get("motion_feel") == "gentle_slow" else 0.30
        n_trans_in = min(n_frames // 3, max(1, int(trans_sec * self.fps))) if trans_in != "CUT" else 0
        n_trans_out = min(n_frames // 3, max(1, int(trans_sec * self.fps))) if trans_out != "CUT" else 0
        headline_text = _extract_headline(scene) if self.sp.get("headline_banner") else ""
        scene_id = int(scene.get("id", 1))
        has_sitting_actor = any(str(c.get("action", "")).upper() in ("SIT", "READ", "WRITE") for c in characters)

        for f in range(n_frames):
            t = f / max(n_frames - 1, 1)
            time_sec = f / float(max(1, self.fps))
            img = base_bg.copy()

            # 1. Animated scene props / metaphors behind characters (2x AA)
            fg_furniture, primary_prop_center = self._draw_scene_objects_aa(
                img, scene, self.width, self.height, t=t, floor_y=floor_y,
                defer_foreground=has_sitting_actor,
            )

            # Precompute animated joints per character
            char_joints_list = []
            for idx_c, (char, cfg) in enumerate(zip(characters, char_configs)):
                px, py = cfg["positions"][f]
                action = str(char.get("action", "STAND")).upper()
                facing = char.get("facing", "right")
                scale = char_scales[idx_c]
                joints = self.renderer.get_animated_joints(
                    action=action,
                    t_norm=t,
                    time_sec=time_sec,
                    scale=scale,
                    facing=facing,
                )
                char_joints_list.append((px, py, scale, facing, joints))

            # 2. Characters (2x supersampled sprite AA, style outfits & expressions)
            for idx_c, (char, (px, py, scale, facing, joints)) in enumerate(zip(characters, char_joints_list)):
                act_u = str(char.get("action", "STAND")).upper()
                if act_u in ("SIT", "READ", "WRITE") and self.pack.id != "a3_prehistoric_cave":
                    # Auto-support any sitting character with a crisp chair right under hips (except stone-age cave floor)
                    cw = max(36, int(38 * scale))
                    ch = max(46, int(60 * scale))
                    cx_ch = int(px - (cw * 0.56 if facing == "right" else cw * 0.24))
                    cy_ch = int(floor_y - ch + int(2 * scale))
                    self.assets.render_asset_aa(img, "CHAIR", cx_ch, cy_ch, cw, ch, t=t)

                col = char.get("color") or self._get_character_color(char.get("id", f"P{idx_c}"), idx_c)
                base_emo = str(char.get("emotion") or scene.get("emotion") or "NEUTRAL").upper()
                # Dynamic in-scene emotional beat transition:
                # Reactions snap in at beat t >= 0.28 (anticipation -> shock/cringe/happy)
                if base_emo in ("SURPRISED", "SHOCKED", "CRINGE", "DISGUST") and t < 0.28:
                    emo = "CALM" if "BED" in act_u or act_u == "STAND" else "NEUTRAL"
                elif base_emo in ("HAPPY", "EXCITED") and t < 0.20:
                    emo = "NEUTRAL"
                else:
                    emo = base_emo

                acc = char.get("accessory")
                talk = bool(char.get("speaking", idx_c == 0 and len(characters) == 1))

                # Gaze tracking: Partner's head in dialogue, or focal prop center in solitary scenes
                if len(char_joints_list) > 1:
                    partner_idx = 1 if idx_c == 0 else 0
                    partner_px, partner_py, _, _, _ = char_joints_list[partner_idx]
                    gaze_tgt = (float(partner_px), float(partner_py) - 52.0 * scale)
                elif primary_prop_center is not None:
                    gaze_tgt = primary_prop_center
                else:
                    gaze_tgt = None

                self.renderer.render_character_on_frame(
                    img,
                    int(px),
                    int(py),
                    pose=act_u,
                    scale=scale,
                    facing=facing,
                    color_override=col,
                    emotion_override=emo,
                    joints_override=joints,
                    time_sec=time_sec,
                    speaking=talk,
                    accessory=acc,
                    outfit_override=char.get("outfit"),
                    char_index=idx_c,
                    gaze_target=gaze_tgt,
                )

                # Held object attached cleanly to active hand + arc transfer for GIVE->RECEIVE
                held = char.get("held_object", "")
                if not held:
                    if any(k in act_u for k in ("PHONE", "SCROLL_PHONE")):
                        held = "PHONE"
                    elif act_u == "COUNT_MONEY":
                        held = "MONEY"
                if held:
                    hx, hy = self.renderer.get_hand_position(
                        int(px), int(py), scale=scale, facing=facing, hand="right", joints_override=joints
                    )
                    if str(char.get("action", "")).upper() == "GIVE" and len(char_joints_list) > 1 and idx_c == 0:
                        rx_p, ry_p, r_sc, r_fac, r_j = char_joints_list[1]
                        rhx, rhy = self.renderer.get_hand_position(
                            int(rx_p), int(ry_p), scale=r_sc, facing=r_fac, hand="right", joints_override=r_j
                        )
                        pass_t = max(0.0, min(1.0, (t - 0.25) / 0.45))
                        ease_p = self._ease_in_out(pass_t)
                        hx = int(_lerp(hx, rhx, ease_p * 0.72))
                        hy = int(_lerp(hy, rhy, ease_p * 0.72) - math.sin(ease_p * math.pi) * 20 * res_scale)
                    obj_sz = int(38 * scale)
                    held_u = str(held).upper()
                    if held_u == "PHONE":
                        ow_h, oh_h = int(obj_sz * 0.60), int(obj_sz * 1.05)
                    elif held_u == "MONEY":
                        ow_h, oh_h = int(obj_sz * 1.35), int(obj_sz * 0.80)
                    elif held_u in ("SPEAR", "CLUB"):
                        ow_h, oh_h = int(obj_sz * 1.45), int(obj_sz * 1.45)
                    else:
                        ow_h, oh_h = obj_sz, obj_sz
                    self.assets.render_asset_aa(
                        img, held_u,
                        hx - ow_h // 2, hy - oh_h // 2,
                        ow_h, oh_h, t=t,
                    )

                # Foreground table + coffee cup right in front of sitting character for natural depth!
                if idx_c == len(characters) - 1 and fg_furniture:
                    for asset, ox, oy, ow, oh, color in fg_furniture:
                        self.assets.render_asset_aa(img, asset, ox, oy, ow, oh, color, t=t)

                # Contextual Speech & Thought Bubbles (smooth spring pop-in, text readable once open)
                pop = min(1.0, t / 0.16) if t < 0.16 else 1.0
                pop_ease = 1.0 - (1.0 - pop) ** 3

                speech = str(char.get("speech", "")).strip()
                if speech and pop_ease > 0.20:
                    lines = textwrap.wrap(speech, width=20)
                    max_len = max(len(ln) for ln in lines) if lines else 1
                    bw = max(int(150 * res_scale), int(min((max_len * 13 + 52) * res_scale, self.width * 0.58) * pop_ease))
                    bh = max(int(54 * res_scale), int(max((len(lines) * 26 + 42) * res_scale, self.height // 9) * pop_ease))
                    bx = max(16, min(int(px) - bw // 2, self.width - bw - 16))
                    by = max(16, min(int(py) - int(116 * scale) - bh, self.height - bh - 16))
                    bubble_key = "SPEECH_BUBBLE"
                    self._render_bubble_aa(img, bubble_key, bx, by, bw, bh, speech if pop_ease > 0.45 else "")

                thought = str(char.get("thought", "")).strip()
                if thought and pop_ease > 0.20:
                    lines = textwrap.wrap(thought, width=20)
                    max_len = max(len(ln) for ln in lines) if lines else 1
                    bw = max(int(150 * res_scale), int(min((max_len * 13 + 52) * res_scale, self.width * 0.58) * pop_ease))
                    bh = max(int(54 * res_scale), int(max((len(lines) * 26 + 42) * res_scale, self.height // 9) * pop_ease))

                    thought_img = None
                    if getattr(self, "use_lcm", False):
                        try:
                            from engine.lcm_image_engine import LCMImageEngine
                            tw = max(96, bw - 24)
                            th = max(64, int(bh * 0.70) - 16)
                            thought_img = LCMImageEngine.render_thought_illustration(thought, width=tw, height=th)
                            if thought_img is not None:
                                bh = max(bh, int(140 * res_scale * pop_ease))
                        except Exception:
                            pass

                    bx = max(16, min(int(px) - bw // 2, self.width - bw - 16))
                    by = max(16, min(int(py) - int(116 * scale) - bh, self.height - bh - 16))
                    self._render_bubble_aa(
                        img, "THOUGHT_BUBBLE", bx, by, bw, bh,
                        text=thought if (thought_img is None and pop_ease > 0.45) else "",
                        thought_img=thought_img if pop_ease > 0.45 else None
                    )

            # 3. Camera motion (dynamic zoom/pan with subtle breathing drift on MEDIUM)
            img = self._apply_camera(img, camera, t)

            # 4. Style-native dynamic atmosphere + lighting overlays (A3, A4, A6, B3, B4)
            img = self._apply_style_atmosphere(img, time_sec, t, scene_id)

            # 5. Atmosphere and Lighting Overlays (clean, uncluttered - top headline banners disabled)
            if self.sp.get("presenter_pip"):
                self._draw_presenter_pip(img, time_sec, scene.get("emotion", "HAPPY"))

            # 6. Extra scene effects (Cinematic overlays)
            for eff in effects:
                img = self._add_emphasis_effect(img, eff, t=t, f=f)

            # Punchy White Flash Jump-Cut at start of scene
            if f < 3 and scene_id > 1 and ("FLASH_CUT" in effects or trans_in == "SNAP_CUT"):
                flash_a = int(90 * (1.0 - f / 3.0))
                flash_ov = Image.new("RGBA", (self.width, self.height), (255, 255, 255, flash_a))
                img.alpha_composite(flash_ov)

            # 7. Streaming transitions
            if n_trans_in and f < n_trans_in:
                img = self._apply_single_transition(img, trans_in, f / n_trans_in, at_start=True, frame_idx=f)
            elif n_trans_out and f >= n_frames - n_trans_out:
                rem = (n_frames - 1 - f) / n_trans_out
                img = self._apply_single_transition(img, trans_out, rem, at_start=False, frame_idx=f)

            yield img

    # ------------------------------------------------------------------
    # 2x AA Prop & Bubble Helpers
    # ------------------------------------------------------------------

    def _draw_scene_objects_aa(
        self,
        img: Image.Image,
        scene: dict,
        width: int,
        height: int,
        t: float = 0.0,
        floor_y: Optional[int] = None,
        defer_foreground: bool = False,
    ) -> tuple[list[tuple[str, int, int, int, int, Any]], Optional[tuple[float, float]]]:
        """Render scene props anchored cleanly onto floor_y / tabletops; return (deferred, primary_prop_center)."""
        base_dim = min(width, height)
        if floor_y is None:
            floor_y = int(height * 0.74)

        _GROUND_PROPS = {
            "CAMPFIRE", "TABLE", "CHAIR", "TREE", "HOUSE", "CAR",
            "DOG", "PUPPY", "CAT", "KITTEN", "HORSE", "BICYCLE", "BIKE",
            "TREASURE_CHEST", "TREASURE", "ROCKET", "HAMSTER_WHEEL",
            "DOMINOES", "BRICK_WALL", "CRACKED_WALL", "PODIUM", "BALANCE_SCALE",
            "BED", "NIGHTSTAND_CLOCK", "DIYA", "CROWD_ROW"
        }
        _TABLETOP_PROPS = {"COFFEE_CUP", "LAPTOP", "BOOK", "BRAIN", "HOURGLASS"}

        # Detect grounded table top Y if scene contains a TABLE so cups/laptops rest squarely on top!
        table_top_y: Optional[int] = None
        for obj in scene.get("objects", []):
            if str(obj.get("asset", "")).upper() == "TABLE":
                th = max(44, int(float(obj.get("height", 0.15)) * base_dim * (1.28 if height > width * 1.1 else 1.0)))
                table_top_y = floor_y - th
                break

        deferred: list[tuple[str, int, int, int, int, Any]] = []
        primary_prop_center: Optional[tuple[float, float]] = None
        size_boost = 1.25 if height > width * 1.1 else 1.05

        for idx, obj in enumerate(scene.get("objects", [])):
            asset = str(obj.get("asset", "")).upper()
            x_frac = float(obj.get("x", 0.5))
            y_frac = float(obj.get("y", 0.5))
            motion = str(obj.get("motion", "")).upper()

            # Dynamic spring overshoot scale with staggered pop-ups!
            stagger = idx * 0.08
            pop_t = max(0.0, min(1.0, (t - stagger) / 0.20))
            pop_mult = self._spring_pop(pop_t) if pop_t > 0 else 0.0
            if pop_mult <= 0.02:
                continue

            if motion == "FLOAT_UP":
                y_frac -= 0.055 * t
            elif motion == "PASS_RIGHT":
                x_frac += 0.14 * self._ease_in_out(t)
            elif motion == "PASS_LEFT":
                x_frac -= 0.14 * self._ease_in_out(t)
            elif asset not in _GROUND_PROPS and asset not in _TABLETOP_PROPS:
                y_frac += 0.012 * math.sin(t * math.pi * 2.2 + idx * 1.5)

            raw_w = max(32, int(float(obj.get("width", 0.14)) * base_dim * size_boost))
            raw_h = max(32, int(float(obj.get("height", 0.14)) * base_dim * size_boost))
            if asset == "COFFEE_CUP":
                raw_w = min(raw_w, max(24, int(base_dim * 0.088)))
                raw_h = min(raw_h, max(24, int(base_dim * 0.084)))

            ow = max(8, int(raw_w * pop_mult))
            oh = max(8, int(raw_h * pop_mult))
            ox = int(x_frac * width - ow / 2.0)

            if asset in _GROUND_PROPS and y_frac >= 0.45:
                oy = floor_y - oh + max(2, int(oh * 0.06))
            elif asset in _TABLETOP_PROPS and table_top_y is not None and y_frac >= 0.42:
                oy = table_top_y - oh + max(4, int(oh * 0.20))
            else:
                oy = int(y_frac * height - oh / 2.0)

            # Strict bounds clamping to prevent any cut-off / clipped objects
            margin = max(16, int(base_dim * 0.02))
            ox = max(margin, min(ox, width - ow - margin))
            if asset not in _GROUND_PROPS:
                oy = max(margin, min(oy, height - oh - margin))
            else:
                oy = min(oy, height - oh - 8)

            if primary_prop_center is None and asset not in ("TABLE", "CHAIR", "WALL", "BRICK_WALL", "SPLIT_DIVIDER"):
                primary_prop_center = (float(ox + ow / 2.0), float(oy + oh / 2.0))

            color = obj.get("color")
            if defer_foreground and (asset == "TABLE" or (asset in _TABLETOP_PROPS and table_top_y is not None)):
                deferred.append((asset, ox, oy, ow, oh, color))
            else:
                self.assets.render_asset_aa(img, asset, ox, oy, ow, oh, color, t=t)

        return deferred, primary_prop_center

    def _render_bubble_aa(
        self,
        base_img: Image.Image,
        kind: str,
        x: int,
        y: int,
        w: int,
        h: int,
        text: str,
        thought_img: Optional[Image.Image] = None,
    ) -> None:
        pad = 14
        aa = 2
        spr = Image.new("RGBA", ((w + pad * 2) * aa, (h + pad * 2) * aa), (0, 0, 0, 0))
        d = ImageDraw.Draw(spr)
        saved_lw = self.sp.get("line_width", 3.5)
        self.sp["line_width"] = max(2, int(round(float(saved_lw) * aa * 0.72)))
        try:
            if kind == "THOUGHT_BUBBLE":
                self.assets._draw_thought_bubble(d, pad * aa, pad * aa, w * aa, h * aa, text=text)
            else:
                self.assets._draw_speech_bubble(d, pad * aa, pad * aa, w * aa, h * aa, text=text)
        finally:
            self.sp["line_width"] = saved_lw
        lo = spr.resize((w + pad * 2, h + pad * 2), Image.Resampling.BICUBIC)
        if thought_img is not None:
            # Composite vignette neatly inside the bubble body
            tw = max(16, w - 24)
            th = max(16, int(h * 0.68) - 16)
            fit_thumb = thought_img.resize((tw, th), Image.Resampling.LANCZOS)
            lo.alpha_composite(fit_thumb, (pad + 12, pad + 8))
        base_img.alpha_composite(lo, (x - pad, y - pad))

    # ------------------------------------------------------------------
    # Style-Specific Atmosphere, Lighting & Composition Overlays
    # ------------------------------------------------------------------

    def _apply_style_atmosphere(
        self,
        frame: Image.Image,
        time_sec: float,
        t: float,
        scene_id: int,
    ) -> Image.Image:
        sid = self.pack.id
        w, h = frame.size

        if sid == "a3_prehistoric_cave":
            # Rising campfire spark embers
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for i in range(10):
                ex = int(w * (0.25 + 0.50 * ((i * 37 % 100) / 100.0)) + math.sin(time_sec * 3 + i) * 14)
                ey = int(h * 0.75 - ((time_sec * 55 + i * 73) % (h * 0.45)))
                er = max(2, min(w, h) // 180)
                d.ellipse([ex - er, ey - er, ex + er, ey + er], fill=(251, 146, 60, 175))
            frame = Image.alpha_composite(frame.convert("RGBA"), ov)

        elif sid == "a4_cozy_storytelling":
            # Soft warm drifting sunlight dust motes
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            for i in range(14):
                mx = int((w * ((i * 71) % 100) / 100.0 + math.sin(time_sec * 0.9 + i) * 18) % w)
                my = int((h * ((i * 43) % 80) / 100.0 - time_sec * 14) % int(h * 0.75))
                mr = max(2, min(w, h) // 190)
                d.ellipse([mx - mr, my - mr, mx + mr, my + mr], fill=(255, 251, 235, 110))
            frame = Image.alpha_composite(frame.convert("RGBA"), ov)

        elif sid == "a6_amber_noir":
            # Diagonal Venetian blind shadow slats + warm amber edge glow
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            step = max(24, h // 18)
            for sy in range(0, int(h * 0.58), step):
                d.polygon([(0, sy), (w, sy + int(h * 0.09)), (w, sy + int(h * 0.09) + step // 3), (0, sy + step // 3)], fill=(8, 6, 16, 42))
            frame = Image.alpha_composite(frame.convert("RGBA"), ov)

        elif sid == "b3_retro_tv":
            # Crisp CRT horizontal scanlines + glossy rounded TV corner bezel + CH indicator
            if self._scanline_cache is None or self._scanline_cache.size != (w, h):
                sl = Image.new("RGBA", (w, h), (0, 0, 0, 0))
                sd = ImageDraw.Draw(sl)
                gap = max(3, h // 220)
                for yy in range(0, h, gap * 2):
                    sd.line([(0, yy), (w, yy)], fill=(0, 0, 0, 58), width=max(1, gap // 2))
                # Corner CRT phosphor shadow frame
                bw = max(6, min(w, h) // 65)
                sd.rounded_rectangle([bw, bw, w - bw, h - bw], radius=max(18, min(w, h) // 14), outline=(0, 0, 0, 170), width=bw * 2)
                self._scanline_cache = sl
            frame = Image.alpha_composite(frame.convert("RGBA"), self._scanline_cache)
            # Subtle CRT green/cyan corner channel stamp
            if (int(time_sec * 2) % 2) == 0 or True:
                cd = ImageDraw.Draw(frame)
                ch_font = _load_ui_font(max(12, min(w, h) // 36), bold=True)
                cd.text((int(w * 0.08), int(h * 0.07)), f"CH {scene_id:02d}", fill=(45, 212, 191, 210), font=ch_font)

        elif sid == "b4_survival_thriller":
            # Diagonal driving storm rain streaks + occasional lightning pulse
            ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
            d = ImageDraw.Draw(ov)
            rain_speed = time_sec * 420.0
            for i in range(28):
                rx = int(((i * 97 + rain_speed * 0.35) % (w + 40)) - 20)
                ry = int(((i * 131 + rain_speed) % (h + 60)) - 30)
                d.line([(rx, ry), (rx - 8, ry + 26)], fill=(148, 163, 184, 85), width=max(1, min(w, h) // 360))
            # Dramatic distant lightning flash beat early in scene
            if 0.08 < t < 0.14 or 0.62 < t < 0.66:
                d.rectangle([0, 0, w, h], fill=(226, 232, 240, 38))
            frame = Image.alpha_composite(frame.convert("RGBA"), ov)

        vignette_s = float(self.sp.get("vignette_strength", 0.0))
        if vignette_s > 0.05:
            frame = self._add_vignette(frame, vignette_s)
        return frame

    def _draw_headline_banner(self, frame: Image.Image, text: str, t: float) -> None:
        """Purposeful editorial headline strip for B1 Minimal Line Art & B5 Explainer."""
        w, h = frame.size
        ease = min(1.0, t / 0.18)
        ease = 1.0 - (1.0 - ease) ** 3
        if ease < 0.1 or not text:
            return
        font = _load_ui_font(max(15, min(w, h) // 24), bold=True)
        draw = ImageDraw.Draw(frame)
        try:
            tw = int(font.getlength(text))
        except Exception:
            tw = len(text) * 12
        pw = min(int(w * 0.84), tw + 36)
        ph = max(32, min(w, h) // 13)
        px = (w - pw) // 2
        py = int(h * 0.075 - (1.0 - ease) * 18)
        acc = self.sp.get("accent", "#6366F1")
        fg = self.sp.get("fg", "#18181B")
        draw.rounded_rectangle([px + 3, py + 3, px + pw + 3, py + ph + 3], radius=8, fill=(0, 0, 0, 32))
        draw.rounded_rectangle([px, py, px + pw, py + ph], radius=8, fill="#FFFFFF", outline=fg, width=max(2, min(w, h) // 260))
        # Accent left bar indicator
        draw.rounded_rectangle([px, py, px + max(7, pw // 28), py + ph], radius=4, fill=acc)
        draw.text((px + pw // 2 + 4, py + ph // 2), text, fill=fg, font=font, anchor="mm")

    def _draw_presenter_pip(self, frame: Image.Image, time_sec: float, emotion: str) -> None:
        """Draw recurring charismatic glasses+bowtie Presenter host in framed corner box (B5)."""
        w, h = frame.size
        box_sz = max(78, int(min(w, h) * 0.19))
        mx = int(w * 0.05)
        my = int(h * 0.145)  # Safe below top headline/status bar, completely clear of bottom captions!

        pip = Image.new("RGBA", (box_sz, box_sz), (255, 255, 255, 0))
        d = ImageDraw.Draw(pip)
        acc = self.sp.get("accent", "#6366F1")
        fg = self.sp.get("fg", "#1E293B")
        d.rounded_rectangle([0, 0, box_sz - 1, box_sz - 1], radius=14, fill="#EEF2FF", outline=acc, width=max(2, box_sz // 28))

        # Render recurring presenter inside the PIP card using 2x sprite AA
        sc = box_sz / 145.0
        self.renderer.render_character_on_frame(
            pip,
            box_sz // 2,
            int(box_sz * 0.86),
            pose="PRESENT",
            scale=sc,
            facing="right",
            color_override=fg,
            emotion_override=emotion or "HAPPY",
            time_sec=time_sec,
            speaking=True,
            outfit_override="presenter_suit",
            accessory="glasses_bowtie",
            char_index=0,
        )
        # "HOST" mini pill tag
        tag_font = _load_ui_font(max(9, box_sz // 9), bold=True)
        d.rounded_rectangle([6, 6, max(40, int(box_sz * 0.42)), max(18, int(box_sz * 0.18))], radius=5, fill=acc)
        d.text((6 + max(34, int(box_sz * 0.36)) // 2, 6 + max(12, int(box_sz * 0.12)) // 2), "HOST", fill="#FFFFFF", font=tag_font, anchor="mm")
        frame.alpha_composite(pip, (mx, my))

    @staticmethod
    def _spring_pop(t_norm: float) -> float:
        """Damped harmonic spring overshoot: 0 -> 1.16 -> 0.96 -> 1.0."""
        if t_norm <= 0.0:
            return 0.0
        if t_norm >= 1.0:
            return 1.0
        return 1.0 - math.exp(-t_norm * 7.2) * math.cos(t_norm * math.pi * 3.2)

    def _draw_kinetic_editor_badge(self, frame: Image.Image, badge: dict[str, Any], t: float, scene_id: int) -> None:
        """Render high-end Ali Abdaal / Vox kinetic motion graphic callout badge.
        Created by Atharv Hatwar.
        """
        w, h = frame.size
        # Pop in between t = 0.08 and t = 0.35
        if t < 0.08:
            return
        pop_t = min(1.0, (t - 0.08) / 0.20)
        scale = self._spring_pop(pop_t)
        if scale <= 0.05:
            return

        icon = str(badge.get("icon", "💡"))
        title = str(badge.get("title", "KEY TAKEAWAY")).upper()
        tagline = str(badge.get("tagline", "")).upper()
        acc = str(badge.get("accent", "#38BDF8"))

        title_font = _load_ui_font(max(13, int(min(w, h) * 0.024 * scale)), bold=True)
        tag_font = _load_ui_font(max(10, int(min(w, h) * 0.016 * scale)), bold=False)

        try:
            tw = int(title_font.getlength(title))
            gw = int(tag_font.getlength(tagline)) if tagline else 0
        except Exception:
            tw = len(title) * 10
            gw = len(tagline) * 7
        content_w = max(tw, gw)

        bw = max(int(w * 0.42), min(int(w * 0.86), int((content_w + 92) * scale)))
        bh = max(38, int(h * 0.068 * scale))
        cx = w // 2
        # Subtle floating bobbing
        float_y = math.sin(t * math.pi * 2.0) * 3.5
        cy = int(h * 0.125 + float_y)
        bx1 = cx - bw // 2
        by1 = cy - bh // 2
        bx2 = bx1 + bw
        by2 = by1 + bh

        overlay = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(overlay)

        # 1. Soft drop shadow
        d.rounded_rectangle([bx1 + 4, by1 + 4, bx2 + 4, by2 + 4], radius=12, fill=(0, 0, 0, 75))
        # 2. Sleek dark frosted glass chassis
        d.rounded_rectangle([bx1, by1, bx2, by2], radius=12, fill=(15, 23, 42, 235), outline=acc, width=2)

        # 3. Left glowing icon pill
        icon_w = int(bh * 0.76)
        ix = bx1 + 10
        iy = by1 + (bh - icon_w) // 2
        d.rounded_rectangle([ix, iy, ix + icon_w, iy + icon_w], radius=8, fill=acc)
        icon_font = _load_ui_font(max(12, int(icon_w * 0.58)), bold=True)
        d.text((ix + icon_w // 2, iy + icon_w // 2), icon, fill="#FFFFFF", font=icon_font, anchor="mm")

        # 4. Kinetic Typography
        text_x = ix + icon_w + 14
        if tagline:
            d.text((text_x, by1 + int(bh * 0.32)), title, fill="#FFFFFF", font=title_font, anchor="lm")
            d.text((text_x, by1 + int(bh * 0.72)), tagline, fill=acc, font=tag_font, anchor="lm")
        else:
            d.text((text_x, cy), title, fill="#FFFFFF", font=title_font, anchor="lm")

        # 5. Shimmer sweep line
        if 0.20 <= t <= 0.65:
            shimmer_frac = (t - 0.20) / 0.45
            sx = int(bx1 + (bw + 40) * shimmer_frac)
            if bx1 + 6 <= sx <= bx2 - 6:
                d.line([(sx, by1 + 2), (sx + 8, by2 - 2)], fill=(255, 255, 255, 80), width=3)

        frame.alpha_composite(overlay)

    def _draw_speed_lines(self, frame: Image.Image, t: float = 0.5) -> Image.Image:
        """Dynamic action speed lines radiating inward."""
        w, h = frame.size
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        cx, cy = w // 2, int(h * 0.55)
        rng = random.Random(int(t * 14.0) + 42)
        n_lines = 24
        line_col = (15, 23, 42, 60) if not _is_dark_hex(self.sp.get("bg", "#FFFFFF")) else (255, 255, 255, 55)
        for i in range(n_lines):
            ang = (i / n_lines) * 2.0 * math.pi + rng.uniform(-0.06, 0.06)
            outer_dist = max(w, h) * 0.72
            inner_dist = min(w, h) * rng.uniform(0.28, 0.44)
            x1 = cx + math.cos(ang) * outer_dist
            y1 = cy + math.sin(ang) * outer_dist
            x2 = cx + math.cos(ang) * inner_dist
            y2 = cy + math.sin(ang) * inner_dist
            d.line([(int(x1), int(y1)), (int(x2), int(y2))], fill=line_col, width=max(1, int(w * 0.003)))
        return Image.alpha_composite(frame.convert("RGBA"), ov)

    def _draw_sparkle_particles(self, frame: Image.Image, t: float = 0.5, gold: bool = False) -> Image.Image:
        """Floating sparkling dust motes and 4-point diamond stars."""
        w, h = frame.size
        ov = Image.new("RGBA", (w, h), (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        n_sparks = 14
        p_col = (245, 158, 11) if gold else (56, 189, 248)
        for i in range(n_sparks):
            seed_i = i * 137
            bx = (seed_i * 97) % w
            base_y = (seed_i * 71) % int(h * 0.72)
            py = int((base_y - t * 80.0) % int(h * 0.72))
            alpha = int(max(0.0, math.sin((t * 2.5 + i * 0.4) * math.pi)) * 170)
            sz = 4 + (i % 5)
            d.line([(bx - sz, py), (bx + sz, py)], fill=(*p_col, alpha), width=2)
            d.line([(bx, py - sz), (bx, py + sz)], fill=(*p_col, alpha), width=2)
            d.ellipse([bx - 1, py - 1, bx + 1, py + 1], fill=(255, 255, 255, alpha))
        return Image.alpha_composite(frame.convert("RGBA"), ov)

    # ------------------------------------------------------------------
    # Camera & Transitions
    # ------------------------------------------------------------------

    def _apply_camera(self, frame: Image.Image, camera: str, t: float) -> Image.Image:
        """Apply dynamic camera framing: punch-in, camera shake, slow zoom, pans, dynamic angles."""
        if camera in ("STATIC",):
            return frame

        cx_frac, cy_frac = 0.50, 0.51
        shake_x, shake_y = 0.0, 0.0
        rot_angle = 0.0

        if camera in ("PUNCH_IN", "SNAP_ZOOM"):
            punch_t = min(1.0, max(0.0, (t - 0.04) / 0.18))
            ease_punch = 1.0 - (1.0 - punch_t) ** 3
            zoom = 1.0 + 0.28 * ease_punch
            cx_frac, cy_frac = 0.50, 0.52
            rot_angle = math.sin(punch_t * math.pi) * 1.5

        elif camera in ("DYNAMIC_CUT", "MULTI_BEAT"):
            if t < 0.28:
                zoom = 1.02
                cx_frac, cy_frac = 0.50, 0.51
            else:
                punch_t = min(1.0, max(0.0, (t - 0.28) / 0.16))
                ease_punch = 1.0 - (1.0 - punch_t) ** 3
                zoom = 1.02 + 0.25 * ease_punch
                cx_frac, cy_frac = 0.50, 0.52
                rot_angle = math.sin(punch_t * math.pi) * 1.2

        elif camera in ("OBJECT_FOCUS", "SHOW_OBJECT"):
            zoom = 1.04 + 0.20 * self._ease_in_out(t)
            cx_frac = 0.50 + 0.10 * self._ease_in_out(t)
            cy_frac = 0.51 - 0.04 * self._ease_in_out(t)

        elif camera == "CAMERA_SHAKE":
            decay = math.exp(-t * 9.5)
            shake_amp = 18.0 * decay
            shake_x = math.sin(t * math.pi * 32.0) * shake_amp
            shake_y = math.cos(t * math.pi * 26.0) * shake_amp * 0.7
            zoom = 1.10 + 0.03 * math.sin(t * math.pi * 2)
            cx_frac, cy_frac = 0.50, 0.52
            rot_angle = math.sin(t * math.pi * 16.0) * (2.2 * decay)

        elif camera in ("SLOW_ZOOM_IN", "ZOOM_IN"):
            zoom = 1.0 + 0.22 * self._ease_in_out(t)
            cx_frac, cy_frac = 0.50, 0.51

        elif camera in ("SLOW_ZOOM_OUT", "ZOOM_OUT"):
            zoom = 1.25 - 0.22 * self._ease_in_out(t)
            cx_frac, cy_frac = 0.50, 0.51

        elif camera == "PAN_LEFT":
            zoom = 1.15
            cx_frac = 0.58 - 0.16 * self._ease_in_out(t)
            cy_frac = 0.51
            rot_angle = -1.2 * math.sin(t * math.pi)

        elif camera == "PAN_RIGHT":
            zoom = 1.15
            cx_frac = 0.42 + 0.16 * self._ease_in_out(t)
            cy_frac = 0.51
            rot_angle = 1.2 * math.sin(t * math.pi)

        elif camera in ("CLOSE", "DUTCH_ANGLE"):
            zoom = 1.35 + 0.06 * self._ease_in_out(t)
            cx_frac, cy_frac = 0.50, 0.48
            rot_angle = -2.0 + 1.2 * self._ease_in_out(t)

        elif camera == "WIDE":
            zoom = 1.04 - 0.04 * self._ease_in_out(t)
            cx_frac, cy_frac = 0.50, 0.50

        else:  # MEDIUM
            zoom = 1.0 + 0.10 * self._ease_in_out(t)
            cx_frac, cy_frac = 0.50, 0.51

        if zoom <= 1.004 and abs(shake_x) < 0.5 and abs(shake_y) < 0.5 and abs(rot_angle) < 0.2:
            return frame

        crop_w = max(64, int(self.width / zoom))
        crop_h = max(64, int(self.height / zoom))
        x1 = max(0, min(self.width - crop_w, int(self.width * cx_frac - crop_w / 2 + shake_x)))
        y1 = max(0, min(self.height - crop_h, int(self.height * cy_frac - crop_h / 2 + shake_y)))
        cropped = frame.crop((x1, y1, x1 + crop_w, y1 + crop_h))

        # Dynamic angle rotation for lively professional camera cuts
        if abs(rot_angle) >= 0.2:
            cropped = cropped.rotate(rot_angle, resample=Image.Resampling.BILINEAR, expand=False)

        return cropped.resize((self.width, self.height), Image.Resampling.BILINEAR)

    def _apply_single_transition(
        self,
        frame: Image.Image,
        transition: str,
        progress: float,
        at_start: bool = True,
        frame_idx: int = 0,
    ) -> Image.Image:
        t = max(0.0, min(1.0, progress))
        bg_rgba = _hex_to_rgba(self.sp.get("bg", "#000000"))

        if transition == "FADE":
            alpha = int((1.0 - t) * 235)
            overlay = Image.new("RGBA", frame.size, (bg_rgba[0], bg_rgba[1], bg_rgba[2], alpha))
            return Image.alpha_composite(frame.convert("RGBA"), overlay)
        elif transition == "VHS_GLITCH":
            # Analog retro channel horizontal jitter + tracking bar
            res = frame.copy()
            strip_h = max(14, self.height // 18)
            band_y = int(((frame_idx * 97) % max(1, self.height - strip_h)))
            band = res.crop((0, band_y, self.width, band_y + strip_h))
            shift = int((1.0 - t) * 48) * (1 if frame_idx % 2 == 0 else -1)
            res.paste(band, (shift, band_y))
            ov = Image.new("RGBA", frame.size, (45, 212, 191, int((1.0 - t) * 70)))
            return Image.alpha_composite(res.convert("RGBA"), ov)
        elif transition in ("SLIDE_LEFT", "SLIDE_RIGHT"):
            direction = 1 if transition == "SLIDE_LEFT" else -1
            offset = int((1.0 - t) * self.width * 0.42) * (direction if at_start else -direction)
            canvas = Image.new("RGBA", (self.width, self.height), bg_rgba)
            canvas.paste(frame, (offset, 0))
            return canvas
        elif transition in ("ZOOM_IN", "ZOOM_OUT"):
            scale = max(0.76, 0.76 + 0.24 * t)
            nw, nh = max(1, int(self.width * scale)), max(1, int(self.height * scale))
            small = frame.resize((nw, nh), Image.Resampling.BILINEAR)
            canvas = Image.new("RGBA", (self.width, self.height), bg_rgba)
            canvas.paste(small, ((self.width - nw) // 2, (self.height - nh) // 2))
            return canvas
        return frame

    # ------------------------------------------------------------------
    # Character config builder & colors
    # ------------------------------------------------------------------

    def _build_char_configs(
        self,
        characters: list[dict],
        n_frames: int,
        hips_y: list[float],
        res_scale: float = 1.0,
    ) -> list[dict]:
        """
        Build frame-by-frame positions and dynamic acting postures.
        Created by Atharv Hatwar.
        """
        configs = []
        feel = self.sp.get("motion_feel", "smooth")
        overshoot = float(self.sp.get("ease_overshoot", 0.0)) * 0.4
        pose_hold = max(3, self.fps // 6)
        n_chars = max(1, len(characters))

        for idx, char in enumerate(characters):
            action = str(char.get("action", "STAND")).upper()
            seq = POSE_SEQUENCES.get(action, ["STAND"])
            start_x = float(char.get("start_x", 0.5)) * self.width
            end_x = float(char.get("end_x", char.get("start_x", 0.5))) * self.width
            cy = hips_y[idx] if idx < len(hips_y) else float(char.get("y", 0.62)) * self.height
            is_locomotion = any(k in action for k in ("WALK", "RUN", "SNEAK", "JUMP"))
            facing_dir = 1 if char.get("facing", "right") == "right" else -1
            is_speaking = bool(char.get("speaking", idx == 0 and n_chars == 1))

            positions = []
            poses = []
            for f in range(n_frames):
                t = f / max(n_frames - 1, 1)
                eased = self._ease_in_out(t)

                jump_offset = 0.0
                if "JUMP" in action:
                    jump_offset = -abs(math.sin(t * math.pi)) * (65.0 * res_scale)
                elif action in ("CELEBRATE", "TRIUMPH_FIST"):
                    jump_offset = -abs(math.sin(t * math.pi * 2.0)) * (32.0 * res_scale)

                # Organic breathing and natural weight shifts
                sway_hz = 1.6 if feel == "gentle_slow" else 2.2
                breath_bob = math.cos(t * math.pi * sway_hz * 1.5 + idx) * (2.2 * res_scale)

                if start_x != end_x:
                    if feel in ("snappy_pop", "bouncy_sketch"):
                        eased = min(1.04, eased + math.sin(eased * math.pi) * overshoot)
                    px = _lerp(start_x, end_x, eased)
                    py = cy + jump_offset + breath_bob
                else:
                    weight_shift = math.sin(t * math.pi * sway_hz + idx * 2.1) * (14.0 * res_scale) * facing_dir
                    delivery_lean = math.sin(t * math.pi) * (22.0 * res_scale) * facing_dir if is_speaking else 0.0
                    px = start_x + weight_shift + delivery_lean
                    py = cy + jump_offset + breath_bob

                positions.append((px, py))

                # Natural narrative acting timeline (eliminates the rapid 4-frame jitter loop)
                if is_locomotion:
                    # Natural rhythmic locomotion cadence (~2.5 steps per second)
                    step_cadence = max(4, int(self.fps * 0.22))
                    poses.append(seq[(f // step_cadence) % len(seq)])
                elif action in ("TYPING_LAPTOP", "COUNT_MONEY", "FIGHT"):
                    # Quick alternating hand/tool cycles
                    cycle_cadence = max(3, int(self.fps * 0.16))
                    poses.append(seq[(f // cycle_cadence) % len(seq)])
                elif len(seq) == 1:
                    poses.append(seq[0])
                elif len(seq) == 2:
                    # Stand & breathe: slow natural cycle
                    breath_cadence = max(12, int(self.fps * 1.4))
                    poses.append(seq[(f // breath_cadence) % len(seq)])
                else:
                    # Expressive 3-phase narrative acting:
                    # Phase 1 (0-18%): Anticipation / Step-in
                    # Phase 2 (18-72%): Primary expressive delivery hold
                    # Phase 3 (72-88%): Accent gesture emphasis
                    # Phase 4 (88-100%): Resolve settle
                    if t < 0.18:
                        poses.append(seq[0])
                    elif t < 0.72:
                        poses.append(seq[1] if len(seq) > 1 else seq[0])
                    elif t < 0.88:
                        poses.append(seq[2] if len(seq) > 2 else seq[-1])
                    else:
                        poses.append(seq[-1])

            configs.append({"positions": positions, "poses": poses})
        return configs

    @staticmethod
    def _ease_in_out(t: float) -> float:
        return t * t * (3.0 - 2.0 * t)

    def _get_character_color(self, character_id: str, idx: int = 0) -> str:
        pal = self.sp.get("character_palette") or [self.sp.get("fg", "#111111")]
        if idx < len(pal):
            return pal[idx]
        cid = character_id.upper()
        if cid.endswith(("B", "2")) and len(pal) > 1:
            return pal[1]
        if cid.endswith(("C", "3")) and len(pal) > 2:
            return pal[2]
        return pal[0]

    # ------------------------------------------------------------------
    # Vignette & Emphasis Effects
    # ------------------------------------------------------------------

    _VIGNETTE_CACHE: dict[tuple[int, int, int], Image.Image] = {}

    @staticmethod
    def _add_vignette(frame: Image.Image, strength: float = 0.45) -> Image.Image:
        w, h = frame.size
        max_alpha = int(min(185, 195 * strength))
        key = (w, h, max_alpha)
        vignette = SceneComposer._VIGNETTE_CACHE.get(key)
        if vignette is None:
            # Silky radial elliptical vignette free of rectangular banding
            gw, gh = 96, max(96, int(96 * h / max(1, w)))
            low_v = Image.new("RGBA", (gw, gh), (0, 0, 0, max_alpha))
            ld = ImageDraw.Draw(low_v)
            ld.ellipse([int(gw * 0.10), int(gh * 0.10), int(gw * 0.90), int(gh * 0.90)], fill=(0, 0, 0, 0))
            low_v = low_v.filter(ImageFilter.GaussianBlur(radius=14))
            vignette = low_v.resize((w, h), Image.Resampling.BICUBIC)
            if len(SceneComposer._VIGNETTE_CACHE) > 16:
                SceneComposer._VIGNETTE_CACHE.clear()
            SceneComposer._VIGNETTE_CACHE[key] = vignette
        return Image.alpha_composite(frame.convert("RGBA"), vignette)

    def _add_emphasis_effect(self, frame: Image.Image, effect: str, t: float = 0.5, f: int = 0) -> Image.Image:
        if effect == "VIGNETTE":
            return self._add_vignette(frame, 0.48)
        elif effect == "SPEED_LINES":
            return self._draw_speed_lines(frame, t=t)
        elif effect in ("SPARKLES", "GOLD_SPARKLES"):
            return self._draw_sparkle_particles(frame, t=t, gold=(effect == "GOLD_SPARKLES"))
        elif effect == "BLUR":
            return frame.filter(ImageFilter.GaussianBlur(radius=2))
        elif effect == "SHARPEN":
            return frame.filter(ImageFilter.SHARPEN)
        elif effect == "DESATURATE":
            gray = frame.convert("L").convert("RGBA")
            return Image.blend(frame.convert("RGBA"), gray, alpha=0.5)
        elif effect == "WARM":
            r, g, b, a = frame.convert("RGBA").split()
            r = r.point(lambda p: min(255, p + 12))
            b = b.point(lambda p: max(0, p - 8))
            return Image.merge("RGBA", (r, g, b, a))
        elif effect == "COOL":
            r, g, b, a = frame.convert("RGBA").split()
            b = b.point(lambda p: min(255, p + 12))
            r = r.point(lambda p: max(0, p - 8))
            return Image.merge("RGBA", (r, g, b, a))
        return frame


def render_all_scenes(
    scenes: list[dict],
    style: str,
    width: int,
    height: int,
    fps: int,
    progress_callback: Optional[Callable[[float, str], None]] = None,
    style_variant: Optional[str] = None,
) -> list[Image.Image]:
    composer = SceneComposer(style, width, height, fps, style_variant=style_variant)
    all_frames: list[Image.Image] = []
    total = len(scenes)

    for idx, scene in enumerate(scenes):
        duration = float(scene.get("duration", 3.0))
        if progress_callback:
            progress_callback(idx / total, f"Rendering scene {idx + 1}/{total}…")
        try:
            all_frames.extend(composer.compose_scene(scene, duration))
        except Exception as exc:
            blank = Image.new("RGBA", (width, height), color=(30, 30, 30, 255))
            draw = ImageDraw.Draw(blank)
            draw.text((10, 10), f"[Scene {idx + 1} error: {exc}]", fill="#FF6B35")
            all_frames.append(blank)

    if progress_callback:
        progress_callback(1.0, "All scenes rendered.")
    return all_frames
