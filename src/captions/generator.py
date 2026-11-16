"""
Caption Generator - Creates synchronized, punchy multi-phrase caption events
from TTS audio timing data and narration scripts.
"""

from __future__ import annotations

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


class CaptionGenerator:
    """Generates synchronized caption events from scene narration and TTS timing."""

    VALID_STYLES = {"normal", "word_highlight", "karaoke", "bold_social", "minimal", "none"}

    def __init__(self) -> None:
        self._sentence_splitter = re.compile(
            r'(?<=[.!?])\s+(?=[A-Z"])|(?<=[.!?])$',
            re.MULTILINE,
        )

    def generate_captions(
        self,
        scenes: list[dict],
        sentence_audio: list[dict],
        style: str = "bold_social",
        max_words_per_caption: Optional[int] = None,
    ) -> list[dict]:
        """
        Generate caption events aligned to TTS audio timing.
        Longer sentences are automatically chunked into crisp 3-5 word rhythmic phrases
        so captions remain 1-2 ultra-readable lines and never obscure stickman action.
        """
        if style not in self.VALID_STYLES:
            logger.warning("Unknown caption style '%s'; falling back to 'bold_social'.", style)
            style = "bold_social"

        if style == "none":
            return []

        if max_words_per_caption is None:
            chunk_limit = 4 if style in ("bold_social", "word_highlight") else (6 if style == "karaoke" else 8)
        else:
            chunk_limit = max(2, int(max_words_per_caption))

        audio_queues: dict[str, list[dict]] = {}
        for entry in sentence_audio:
            key = self._normalize_text(entry.get("text", ""))
            audio_queues.setdefault(key, []).append(entry)

        caption_events: list[dict] = []

        for scene in scenes:
            narration: str = scene.get("narration", "").strip()
            if not narration:
                continue

            camera = str(scene.get("camera", "MEDIUM")).upper()
            sentences = self.split_into_sentences(narration)

            for sentence in sentences:
                sentence = sentence.strip()
                if not sentence:
                    continue

                key = self._normalize_text(sentence)
                queue = audio_queues.get(key)
                audio_entry = queue.pop(0) if queue else None

                if audio_entry:
                    start_time = float(audio_entry.get("start_time", 0.0))
                    duration = float(audio_entry.get("duration", 2.0))
                else:
                    start_time = float(scene.get("_scene_start_time", 0.0))
                    duration = max(1.0, len(sentence.split()) * 0.35)

                word_timings = self._estimate_word_timings(sentence, start_time, duration)
                if not word_timings:
                    continue

                # Chunk words into rhythmic phrases so captions never stack 4-5 lines tall
                chunks = self._chunk_words(word_timings, chunk_limit)
                for chunk_words in chunks:
                    c_start = chunk_words[0]["start"]
                    c_end = chunk_words[-1]["end"]
                    c_text = " ".join(w["word"] for w in chunk_words)
                    caption: dict = {
                        "text": c_text,
                        "start": c_start,
                        "end": c_end,
                        "style": style,
                        "words": chunk_words,
                        "scene_camera": camera,
                    }
                    caption_events.append(self.format_for_style(caption, style))

        caption_events.sort(key=lambda c: c["start"])
        return caption_events

    @staticmethod
    def _chunk_words(word_timings: list[dict], chunk_limit: int) -> list[list[dict]]:
        """Split timed words cleanly without leaving tiny 1-word orphans."""
        n = len(word_timings)
        if n <= chunk_limit:
            return [word_timings]

        chunks: list[list[dict]] = []
        i = 0
        while i < n:
            end_i = min(n, i + chunk_limit)
            # Avoid leaving a lone 1-word tail if possible
            if (n - end_i) == 1 and (end_i - i) > 2:
                end_i -= 1
            # Prefer natural punctuation break near end of chunk
            for k in range(i + 1, end_i):
                if word_timings[k - 1]["word"].endswith((",", ";", ":", "—", "-")):
                    if (k - i) >= 2:
                        end_i = k
                        break
            chunks.append(word_timings[i:end_i])
            i = end_i
        return chunks

    def split_into_sentences(self, text: str) -> list[str]:
        if not text:
            return []
        protected = text
        abbreviations = [
            "Mr.", "Mrs.", "Ms.", "Dr.", "Prof.", "Sr.", "Jr.",
            "vs.", "etc.", "i.e.", "e.g.", "approx.", "dept.", "est.",
            "vol.", "No.", "Fig.", "Jan.", "Feb.", "Mar.", "Apr.",
            "Jun.", "Jul.", "Aug.", "Sep.", "Oct.", "Nov.", "Dec.",
        ]
        placeholders: dict[str, str] = {}
        for i, abbr in enumerate(abbreviations):
            ph = f"__ABBR{i}__"
            placeholders[ph] = abbr
            protected = protected.replace(abbr, ph)
        protected = re.sub(r"\.{3,}", "__ELLIPSIS__", protected)

        raw_sentences = re.split(r"(?<=[.!?])\s+", protected)
        expanded: list[str] = []
        for s in raw_sentences:
            parts = [p.strip() for p in s.split("\n\n") if p.strip()]
            expanded.extend(parts if parts else [s])

        result: list[str] = []
        for s in expanded:
            restored = s
            for ph, original in placeholders.items():
                restored = restored.replace(ph, original)
            restored = restored.replace("__ELLIPSIS__", "...").strip()
            if restored:
                result.append(restored)
        return result

    def split_into_words(self, text: str) -> list[str]:
        if not text:
            return []
        return [w for w in text.split() if w]

    def _estimate_word_timings(
        self,
        sentence: str,
        start_time: float,
        duration: float,
    ) -> list[dict]:
        words = self.split_into_words(sentence)
        if not words:
            return []
        if duration <= 0:
            duration = max(0.5, len(words) * 0.3)

        weights = [max(1, len(re.sub(r"[^\w]", "", w))) for w in words]
        total_weight = sum(weights) or 1

        timings: list[dict] = []
        cursor = start_time
        for word, weight in zip(words, weights):
            wd = max(0.05, duration * (weight / total_weight))
            timings.append({
                "word": word,
                "start": round(cursor, 4),
                "end": round(cursor + wd, 4),
            })
            cursor += wd
        return timings

    def format_for_style(self, caption: dict, style: str) -> dict:
        caption = dict(caption)
        caption["style"] = style
        if style == "normal":
            caption["bg_alpha"] = 175
            caption["font_weight"] = "regular"
            caption["text_align"] = "center"
        elif style == "word_highlight":
            caption["bg_alpha"] = 150
            caption["font_weight"] = "bold"
            caption["text_align"] = "center"
            caption["highlight_current_word"] = True
        elif style == "karaoke":
            caption["bg_alpha"] = 185
            caption["font_weight"] = "bold"
            caption["text_align"] = "center"
            caption["color_sweep"] = True
        elif style == "bold_social":
            caption["bg_alpha"] = 170
            caption["font_weight"] = "bold"
            caption["text_align"] = "center"
            caption["stroke_width"] = 3
            caption["uppercase"] = True
        elif style == "minimal":
            caption["bg_alpha"] = 110
            caption["font_weight"] = "regular"
            caption["text_align"] = "center"
            caption["font_scale"] = 0.78
        elif style == "none":
            caption["visible"] = False
        return caption

    @staticmethod
    def _normalize_text(text: str) -> str:
        # Strip speaker labels e.g. "Male Voice:", "Alex:", "Speaker 1:"
        t = re.sub(
            r"^\s*(?:\*\*)?(?:\[)?(?:alex|maya|speaker\s*\d+|voice\s*\d+|male\s*voice|female\s*voice|male|female)(?:\])?(?:\s*\([^)]*\))?(?:\*\*)?\s*[:\-–—]\s*",
            "",
            text,
            flags=re.IGNORECASE,
        )
        t = re.sub(r"[^\w\s]", "", t.lower())
        return " ".join(t.split())
