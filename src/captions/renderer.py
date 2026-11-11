"""
Caption Renderer - Auto-positioned, StylePack-aware synchronized subtitle overlays.
=================================================================================
Features:
- Smart "auto" default placement tuned to aspect ratio (9:16 Reels safe zone,
  16:9 widescreen lower-third, 1:1 square balanced stage) sitting cleanly below
  the stickman floor horizon (0.74 * H) and above social app chrome!
- Crisp native Pillow anti-aliased outlines (stroke_width / stroke_fill)
- Soft rounded contrast pills adapting cleanly to both bright white paper styles
  (A1/B1/B2/A2) and dark atmospheric styles (A6/B3/B4/A3)
- Synchronized word-highlight & karaoke color sweeps across 1-2 line chunks
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from PIL import Image, ImageChops, ImageDraw, ImageFont

from styles.style_packs import resolve_style_pack

logger = logging.getLogger(__name__)

_WINDOWS_FONT_CANDIDATES: list[tuple[str, str]] = [
    ("Arial Bold", "arialbd.ttf"),
    ("Segoe UI Bold", "segoeuib.ttf"),
    ("Calibri Bold", "calibrib.ttf"),
    ("Verdana Bold", "verdanab.ttf"),
    ("Trebuchet MS", "trebucbd.ttf"),
    ("Arial", "arial.ttf"),
    ("Segoe UI", "segoeui.ttf"),
    ("Calibri", "calibri.ttf"),
    ("Verdana", "verdana.ttf"),
    ("Tahoma", "tahoma.ttf"),
]

_WINDOWS_FONT_DIR = Path("C:/Windows/Fonts")


class CaptionRenderer:
    """Draws auto-positioned, crisp caption overlays onto PIL Image frames."""

    def __init__(
        self,
        width: int,
        height: int,
        style: str = "bold_social",
        font_size: int = 38,
        font_color: str = "#FFFFFF",
        bg_color: str = "#000000",
        highlight_color: str = "",
        position: str = "auto",
        font_name: str = "",
        style_id: str = "a1_classic_bw",
        style_variant: Optional[str] = None,
    ) -> None:
        self.width = width
        self.height = height
        self.style = style
        self.base_font_size = font_size
        self.position = position or "auto"  # "auto" | "bottom" | "top" | "center"
        self.style_id = style_id
        self.style_variant = style_variant

        pack, sp = resolve_style_pack(style_id, style_variant)
        self.sp = sp
        self.font_name = font_name or str(sp.get("caption_font", "Arial Bold"))
        self.font_color = font_color or str(sp.get("caption_text_color", "#FFFFFF"))
        self.bg_color = str(sp.get("caption_bg_color", bg_color or "#0F172A"))
        self.stroke_color = str(sp.get("caption_stroke_color", "#0F172A"))
        self.highlight_color = highlight_color or str(sp.get("caption_highlight_color", "#FFD700"))
        self.pill_alpha = int(sp.get("caption_pill_alpha", 190))

        self._font_cache: dict[int, ImageFont.FreeTypeFont | ImageFont.ImageFont] = {}

    # ------------------------------------------------------------------
    # Font Loading
    # ------------------------------------------------------------------

    def load_font(self, size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if size in self._font_cache:
            return self._font_cache[size]

        font: ImageFont.FreeTypeFont | ImageFont.ImageFont | None = None
        candidates = list(_WINDOWS_FONT_CANDIDATES)
        if self.font_name:
            preferred = [c for c in candidates if self.font_name.lower() in c[0].lower()]
            others = [c for c in candidates if c not in preferred]
            candidates = preferred + others

        for _name, filename in candidates:
            fp = _WINDOWS_FONT_DIR / filename
            if fp.exists():
                try:
                    font = ImageFont.truetype(str(fp), size)
                    break
                except OSError:
                    continue

        if font is None:
            font = ImageFont.load_default()
        self._font_cache[size] = font
        return font

    # ------------------------------------------------------------------
    # Main Render Entry Point
    # ------------------------------------------------------------------

    def render_caption(
        self,
        frame: Image.Image,
        caption_event: dict,
        current_time: float,
    ) -> Image.Image:
        start: float = float(caption_event.get("start", 0.0))
        end: float = float(caption_event.get("end", 0.0))
        style: str = str(caption_event.get("style", self.style))

        if style == "none" or caption_event.get("visible") is False:
            return frame
        if not (start <= current_time <= end):
            return frame

        frame = frame.copy()
        text: str = str(caption_event.get("text", "")).strip()
        if not text:
            return frame
        if caption_event.get("uppercase"):
            text = text.upper()

        font_scale: float = float(caption_event.get("font_scale", 1.0))
        # Auto-clamp font size smoothly to canvas aspect ratio so captions never balloon
        max_auto_size = max(16, int(min(self.width, self.height) * 0.068))
        font_size = max(12, min(int(self.base_font_size * font_scale), max_auto_size))
        font = self.load_font(font_size)

        safe_x1, safe_y1, safe_x2, safe_y2 = self.get_safe_area()
        max_width = int((safe_x2 - safe_x1) * 0.92)
        lines = self._wrap_text(text, font, max_width)

        if style == "word_highlight":
            return self._render_word_highlight(
                frame, caption_event, current_time, font, font_size,
                safe_x1, safe_x2, safe_y1, safe_y2, uppercase=False, with_pill=True
            )
        elif style == "karaoke":
            return self._render_karaoke(
                frame, caption_event, current_time, font, font_size,
                lines, safe_x1, safe_x2, safe_y1, safe_y2
            )
        elif style == "bold_social":
            return self._render_word_highlight(
                frame, caption_event, current_time, font, font_size,
                safe_x1, safe_x2, safe_y1, safe_y2, uppercase=True, with_pill=True
            )
        elif style == "minimal":
            return self._render_minimal(
                frame, lines, safe_x1, safe_x2, safe_y1, safe_y2, caption_event
            )
        else:
            return self._render_normal(
                frame, lines, font, font_size,
                safe_x1, safe_x2, safe_y1, safe_y2,
                caption_event,
            )

    # ------------------------------------------------------------------
    # Smart Vertical Placement Engine ("auto" + overrides)
    # ------------------------------------------------------------------

    def _compute_y_start(
        self,
        total_h: int,
        safe_y1: int,
        safe_y2: int,
        caption_event: dict,
    ) -> int:
        pos = self.position.lower()
        if pos == "top":
            # Avoid clipping top headline/status bar on B1/B5 or Reels top UI
            top_pad = int(self.height * 0.14) if self.sp.get("headline_banner") else safe_y1 + 12
            return max(safe_y1, top_pad)
        if pos == "center":
            return max(safe_y1, (self.height - total_h) // 2)
        if pos == "bottom":
            return max(safe_y1, safe_y2 - total_h - 14)

        # AUTO SMART SAFE POSITION:
        # Characters stand with feet at floor_y = 0.74 * H.
        # On 9:16 vertical, Instagram safe bottom is ~0.875 * H (leaving clean band 0.76..0.87 * H!).
        # Center vertically inside the free stage band between floor_y and safe_y2!
        floor_y = int(self.height * 0.745)
        band_top = floor_y + max(8, int(self.height * 0.015))
        band_bot = safe_y2
        if (band_bot - band_top) >= total_h + 10:
            # Sweet spot centered right below stickman feet and cleanly above UI chrome!
            return band_top + ((band_bot - band_top) - total_h) // 2
        # On narrow/short heights or CLOSE zoom shots, hug cleanly above safe_y2
        return max(safe_y1, safe_y2 - total_h - max(8, int(self.height * 0.015)))

    def _measure_lines_width(self, lines: list[str], font) -> int:
        max_w = 0
        for line in lines:
            try:
                w = int(font.getlength(line))
            except AttributeError:
                w = len(line) * 14
            max_w = max(max_w, w)
        return max_w

    def _draw_rounded_pill(
        self,
        frame: Image.Image,
        cx: int,
        y_start: int,
        block_w: int,
        total_h: int,
        alpha: Optional[int] = None,
    ) -> Image.Image:
        pad_x = max(16, int(self.width * 0.025))
        pad_y = max(8, int(self.height * 0.01))
        x1 = max(int(self.width * 0.04), cx - block_w // 2 - pad_x)
        x2 = min(int(self.width * 0.96), cx + block_w // 2 + pad_x)
        y1 = max(4, y_start - pad_y)
        y2 = min(self.height - 4, y_start + total_h + pad_y)

        ov = Image.new("RGBA", frame.size, (0, 0, 0, 0))
        d = ImageDraw.Draw(ov)
        bg_rgb = self._hex_to_rgb(self.bg_color)
        a = self.pill_alpha if alpha is None else alpha
        rad = max(10, min(20, (y2 - y1) // 3))
        d.rounded_rectangle([x1, y1, x2, y2], radius=rad, fill=(*bg_rgb, a))
        return Image.alpha_composite(frame.convert("RGBA"), ov).convert("RGB")

    # ------------------------------------------------------------------
    # Style-specific Renderers
    # ------------------------------------------------------------------

    def _render_normal(
        self,
        frame: Image.Image,
        lines: list[str],
        font,
        font_size: int,
        safe_x1: int,
        safe_x2: int,
        safe_y1: int,
        safe_y2: int,
        caption_event: dict,
    ) -> Image.Image:
        line_h = font_size + 8
        total_h = line_h * len(lines)
        y_start = self._compute_y_start(total_h, safe_y1, safe_y2, caption_event)
        cx = (safe_x1 + safe_x2) // 2
        block_w = self._measure_lines_width(lines, font)

        frame = self._draw_rounded_pill(frame, cx, y_start, block_w, total_h, alpha=self.pill_alpha)
        draw = ImageDraw.Draw(frame)

        for i, line in enumerate(lines):
            y = y_start + i * line_h + line_h // 2
            self._draw_text_with_outline(draw, line, cx, y, font, self.font_color, self.stroke_color, max(1, font_size // 16))
        return frame

    def _render_word_highlight(
        self,
        frame: Image.Image,
        caption_event: dict,
        current_time: float,
        font,
        font_size: int,
        safe_x1: int,
        safe_x2: int,
        safe_y1: int,
        safe_y2: int,
        uppercase: bool = False,
        with_pill: bool = True,
    ) -> Image.Image:
        words: list[dict] = caption_event.get("words", [])
        if not words:
            return frame

        active_idx = -1
        for idx, w in enumerate(words):
            if w["start"] <= current_time <= w["end"]:
                active_idx = idx
                break
        if active_idx == -1 and words:
            # Clamp slightly across word boundary gaps
            for idx, w in enumerate(words):
                if current_time >= w["start"]:
                    active_idx = idx

        display_words = [w["word"].upper() if uppercase else w["word"] for w in words]
        full_text = " ".join(display_words)
        render_size = min(int(font_size * (1.12 if uppercase else 1.0)), max(18, int(min(self.width, self.height) * 0.072)))
        render_font = self.load_font(render_size)

        max_width = int((safe_x2 - safe_x1) * 0.90)
        lines = self._wrap_text(full_text, render_font, max_width)
        line_h = render_size + 9
        total_h = line_h * len(lines)
        y_start = self._compute_y_start(total_h, safe_y1, safe_y2, caption_event)
        cx = (safe_x1 + safe_x2) // 2

        if with_pill:
            block_w = self._measure_lines_width(lines, render_font)
            frame = self._draw_rounded_pill(frame, cx, y_start, block_w, total_h, alpha=self.pill_alpha)

        draw = ImageDraw.Draw(frame)
        stroke_w = max(2, render_size // 12)

        for i, line in enumerate(lines):
            y = y_start + i * line_h + line_h // 2
            self._draw_text_with_outline(draw, line, cx, y, render_font, self.font_color, self.stroke_color, stroke_w)

        if active_idx >= 0:
            word_counter = 0
            for i, line in enumerate(lines):
                line_words = line.split()
                if word_counter <= active_idx < word_counter + len(line_words):
                    local_idx = active_idx - word_counter
                    prefix = " ".join(line_words[:local_idx])
                    active_word = line_words[local_idx]
                    try:
                        line_w = render_font.getlength(line)
                        prefix_w = render_font.getlength(prefix + " ") if prefix else 0.0
                        word_w = render_font.getlength(active_word)
                    except AttributeError:
                        line_w = len(line) * (render_size * 0.55)
                        prefix_w = len(prefix) * (render_size * 0.55)
                        word_w = len(active_word) * (render_size * 0.55)

                    line_left = cx - line_w / 2.0
                    word_cx = int(line_left + prefix_w + word_w / 2.0)
                    word_y = y_start + i * line_h + line_h // 2
                    self._draw_text_with_outline(
                        draw, active_word, word_cx, word_y, render_font,
                        self.highlight_color, self.stroke_color, stroke_w,
                    )
                    break
                word_counter += len(line_words)

        return frame

    def _render_karaoke(
        self,
        frame: Image.Image,
        caption_event: dict,
        current_time: float,
        font,
        font_size: int,
        lines: list[str],
        safe_x1: int,
        safe_x2: int,
        safe_y1: int,
        safe_y2: int,
    ) -> Image.Image:
        start = float(caption_event["start"])
        end = float(caption_event["end"])
        duration = max(0.001, end - start)
        progress = max(0.0, min(1.0, (current_time - start) / duration))

        line_h = font_size + 8
        total_h = line_h * len(lines)
        y_start = self._compute_y_start(total_h, safe_y1, safe_y2, caption_event)
        cx = (safe_x1 + safe_x2) // 2
        block_w = self._measure_lines_width(lines, font)

        frame = self._draw_rounded_pill(frame, cx, y_start, block_w, total_h, alpha=self.pill_alpha)
        draw = ImageDraw.Draw(frame)

        total_chars = sum(len(l) for l in lines) or 1
        chars_done = 0
        for i, line in enumerate(lines):
            y = y_start + i * line_h + line_h // 2
            try:
                line_w = int(font.getlength(line))
            except AttributeError:
                line_w = len(line) * (font_size // 2)
            line_x = cx - line_w // 2

            self._draw_text_with_outline(draw, line, cx, y, font, "#CBD5E1", self.stroke_color, max(1, font_size // 15))

            line_frac_start = chars_done / total_chars
            line_frac_end = (chars_done + len(line)) / total_chars
            chars_done += len(line)
            if progress > line_frac_start:
                local_p = min(1.0, (progress - line_frac_start) / max(0.001, line_frac_end - line_frac_start))
                swept_px = int(line_w * local_p)
                if swept_px > 0:
                    tmp = Image.new("RGBA", frame.size, (0, 0, 0, 0))
                    tmp_d = ImageDraw.Draw(tmp)
                    hl_rgb = self._hex_to_rgb(self.highlight_color)
                    st_rgb = self._hex_to_rgb(self.stroke_color)
                    tmp_d.text((cx, y), line, font=font, fill=(*hl_rgb, 255), stroke_width=max(1, font_size // 15), stroke_fill=(*st_rgb, 255), anchor="mm")
                    mask = Image.new("L", frame.size, 0)
                    md = ImageDraw.Draw(mask)
                    md.rectangle([line_x - 6, y - line_h // 2 - 4, line_x + swept_px + 2, y + line_h // 2 + 4], fill=255)
                    tmp.putalpha(ImageChops.multiply(tmp.getchannel("A"), mask))
                    frame = Image.alpha_composite(frame.convert("RGBA"), tmp).convert("RGB")
                    draw = ImageDraw.Draw(frame)

        return frame

    def _render_minimal(
        self,
        frame: Image.Image,
        lines: list[str],
        safe_x1: int,
        safe_x2: int,
        safe_y1: int,
        safe_y2: int,
        caption_event: dict,
    ) -> Image.Image:
        small_size = max(14, int(self.base_font_size * 0.78))
        small_font = self.load_font(small_size)
        line_h = small_size + 6
        total_h = line_h * len(lines)
        y_start = self._compute_y_start(total_h, safe_y1, safe_y2, caption_event)
        cx = (safe_x1 + safe_x2) // 2
        draw = ImageDraw.Draw(frame)
        for i, line in enumerate(lines):
            y = y_start + i * line_h + line_h // 2
            self._draw_text_with_outline(draw, line, cx, y, small_font, self.font_color, self.stroke_color, max(1, small_size // 14))
        return frame

    # ------------------------------------------------------------------
    # Clean Antialiased Text Primitives
    # ------------------------------------------------------------------

    def _draw_text_with_shadow(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font,
        color: str,
        shadow_color: str = "#000000",
        shadow_offset: int = 2,
    ) -> None:
        shadow_rgb = self._hex_to_rgb(shadow_color)
        text_rgb = self._hex_to_rgb(color)
        draw.text((x + shadow_offset, y + shadow_offset), text, font=font, fill=(*shadow_rgb, 180), anchor="mm")
        draw.text((x, y), text, font=font, fill=(*text_rgb, 255), anchor="mm")

    def _draw_text_with_outline(
        self,
        draw: ImageDraw.ImageDraw,
        text: str,
        x: int,
        y: int,
        font,
        color: str,
        outline_color: str,
        outline_width: int = 2,
    ) -> None:
        outline_rgb = self._hex_to_rgb(outline_color)
        text_rgb = self._hex_to_rgb(color)
        try:
            draw.text(
                (x, y),
                text,
                font=font,
                fill=(*text_rgb, 255),
                stroke_width=max(1, outline_width),
                stroke_fill=(*outline_rgb, 255),
                anchor="mm",
            )
        except TypeError:
            self._draw_text_with_shadow(draw, text, x, y, font, color, outline_color)

    def _wrap_text(self, text: str, font, max_width: int) -> list[str]:
        if not text:
            return []
        words = text.split()
        lines: list[str] = []
        cur: list[str] = []
        for word in words:
            test = " ".join(cur + [word])
            try:
                w = font.getlength(test)
            except AttributeError:
                w = len(test) * 12
            if w <= max_width or not cur:
                cur.append(word)
            else:
                lines.append(" ".join(cur))
                cur = [word]
        if cur:
            lines.append(" ".join(cur))
        return lines or [text]

    # ------------------------------------------------------------------
    # Safe Area Calculation per Aspect Ratio
    # ------------------------------------------------------------------

    def get_safe_area(self) -> tuple[int, int, int, int]:
        """
        Return Instagram/YouTube-safe (x1, y1, x2, y2):
        - Portrait 9:16 leaves ~13.5% bottom clear for Reels UI description/buttons
        - Landscape 16:9 / 1:1 leaves ~8.5% bottom clear
        """
        ratio = self.width / max(1, self.height)
        margin_h = int(self.width * 0.06)
        margin_top = int(self.height * (0.08 if ratio < 0.8 else 0.05))
        margin_bottom = int(self.height * (0.135 if ratio < 0.8 else 0.085))
        return margin_h, margin_top, self.width - margin_h, self.height - margin_bottom

    @staticmethod
    def _hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
        hex_color = hex_color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(c * 2 for c in hex_color)
        try:
            return int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        except (ValueError, IndexError):
            return (255, 255, 255)
