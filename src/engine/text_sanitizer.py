# Created by Atharv Hatwar
"""
text_sanitizer.py - Visual Text Sanitizer for Stickman Studio.
==============================================================
Strictly isolates internal scene-generation instructions, metadata,
JSON, code, and prompt artifacts from on-screen visual elements:
  - Thinking bubbles
  - Speech bubbles
  - Phone messages & notifications
  - Badges, cards & typography banners

Guarantees that NO technical code, JSON, prompt directives, or malformed
strings ever render visually in exported videos.
"""

from __future__ import annotations

import ast
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Precise regex patterns indicating actual programming code syntax,
# avoiding false positives on natural English phrases ("Remember this...", "they return", "from him")
_CODE_PATTERNS = (
    re.compile(r"\bdef\s+[a-zA-Z_]\w*\s*\(", re.IGNORECASE),
    re.compile(r"\bclass\s+[A-Z]\w*\s*[:\(]", re.IGNORECASE),
    re.compile(r"\bimport\s+[a-zA-Z_]\w*", re.IGNORECASE),
    re.compile(r"\bfrom\s+[a-zA-Z_.]+\s+import\b", re.IGNORECASE),
    re.compile(r"\breturn\s+(?:None|True|False|0|\"|\'|\{|\[|[a-zA-Z_]\w*\()", re.IGNORECASE),
    re.compile(r"\bconst\s+[a-zA-Z_]\w*\s*=", re.IGNORECASE),
    re.compile(r"\blet\s+[a-zA-Z_]\w*\s*=", re.IGNORECASE),
    re.compile(r"\bvar\s+[a-zA-Z_]\w*\s*=", re.IGNORECASE),
    re.compile(r"\bfunction\s*[a-zA-Z_]*\s*\(", re.IGNORECASE),
    re.compile(r"\bthis\.[a-zA-Z_]\w*", re.IGNORECASE),
    re.compile(r"\bself\.[a-zA-Z_]\w*", re.IGNORECASE),
    re.compile(r"\bconsole\.log\s*\(", re.IGNORECASE),
    re.compile(r"\bprint\s*\([\"']", re.IGNORECASE),
    re.compile(r"==|===|!==|!=|=>|->|__init__", re.IGNORECASE),
    re.compile(r"\[object\s+Object\]", re.IGNORECASE),
)

# Internal generation instruction prefixes that should never render
_INSTRUCTION_PREFIXES = re.compile(
    r"^\s*(?:"
    r"thought|speech|dialogue|dialog|say|says|thinking|thinks|voiceover|narration|"
    r"visual|action|scene|camera|prompt|instruction|note|meta|json|response"
    r")\s*[:=\-–—]\s*",
    re.IGNORECASE,
)


class VisualTextSanitizer:
    """Sanitizes and validates all text intended for visual rendering."""

    @classmethod
    def sanitize_bubble_text(
        cls,
        raw_text: Any,
        kind: str = "thought",
        default_fallback: str = "",
    ) -> str:
        """
        Sanitize text intended for a speech or thought bubble.
        Ensures output is clean, natural human dialogue or thought.
        Returns '' if the text is invalid, technical code, or empty.
        """
        if raw_text is None:
            return default_fallback

        # 1. Unpack structured data (dict / list / JSON)
        text = cls._extract_text_from_structure(raw_text, prefer_key=kind)
        if not text:
            return default_fallback

        # 2. Strip Markdown code fences and JSON wrappers
        text = cls._strip_markdown_and_wrappers(text)

        # 3. Strip HTML / XML tags (<thought>...</thought>)
        text = re.sub(r"<[^>]+>", " ", text)

        # 4. Strip bracketed instructions ([Visual: ...], [Action: ...])
        text = re.sub(r"\[[^\]]*\]", " ", text)
        text = re.sub(r"\([^)]*camera[^)]*\)", " ", text, flags=re.IGNORECASE)
        text = re.sub(r"\([^)]*visual[^)]*\)", " ", text, flags=re.IGNORECASE)

        # 5. Strip instruction prefixes ('thought: ...', 'speech: ...')
        text = _INSTRUCTION_PREFIXES.sub("", text).strip()

        # 6. Unescape escaped characters
        text = text.replace('\\"', '"').replace("\\'", "'").replace("\\n", " ").replace("\\t", " ")

        # 7. Strip surrounding quotes if wrapped
        text = text.strip()
        if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
            text = text[1:-1].strip()

        # 8. Check for raw code or programming syntax using precise patterns
        if any(pat.search(text) for pat in _CODE_PATTERNS):
            logger.warning("VisualTextSanitizer: Rejected programming code in %s bubble: '%s'", kind, text[:40])
            return default_fallback

        # If text contains raw braces or brackets, it's malformed JSON/code
        if ("{" in text and "}" in text) or ("[" in text and "]" in text):
            logger.warning("VisualTextSanitizer: Rejected bracketed syntax in %s bubble: '%s'", kind, text[:40])
            return default_fallback

        # 9. Clean excessive whitespace
        text = " ".join(text.split()).strip()

        # 10. Length and legibility bounds for bubbles (1 to 10 words, max 65 chars)
        if len(text) > 75:
            # Shorten to the first natural phrase
            words = text.split()
            if len(words) > 10:
                text = " ".join(words[:10])
                if not text.endswith((".", "?", "!")):
                    text += "..."

        if not text:
            return default_fallback
        if len(text) == 1 and text not in "$?!%€£0123456789+*#@&":
            return default_fallback

        return text

    @classmethod
    def sanitize_label(cls, raw_label: Any, default: str = "") -> str:
        """Sanitize a card label, badge, or notification string."""
        if raw_label is None:
            return default
        s = str(raw_label).strip()
        if not s:
            return default
        # Allow short symbols directly
        if s in ("$", "?", "!", "%", "VS", "</>", "+", "-", "*"):
            return s
        clean = cls.sanitize_bubble_text(raw_label, kind="label", default_fallback=default)
        # Remove any lingering quotes
        clean = re.sub(r'["\']', '', clean).strip()
        # Ensure it's not an internal identifier like "DOMINO_RIPPLE"
        if clean.isupper() and "_" in clean:
            clean = clean.replace("_", " ").title()
        return clean or default

    @classmethod
    def _extract_text_from_structure(cls, raw: Any, prefer_key: str = "thought") -> str:
        """Extract user-facing text from dict, list, or JSON string."""
        if isinstance(raw, dict):
            # Check specific keys in priority order
            keys = [prefer_key, "text", "speech", "thought", "dialogue", "content", "message", "label"]
            for k in keys:
                if k in raw and isinstance(raw[k], str) and raw[k].strip():
                    return raw[k].strip()
            # If no known key, search string values
            for v in raw.values():
                if isinstance(v, str) and len(v.strip()) > 1:
                    return v.strip()
            return ""

        if isinstance(raw, list):
            for item in raw:
                extracted = cls._extract_text_from_structure(item, prefer_key)
                if extracted:
                    return extracted
            return ""

        s = str(raw).strip()

        # Check if the string itself is stringified JSON: e.g. '{"thought": "Why me?"}'
        if (s.startswith("{") and s.endswith("}")) or (s.startswith("[") and s.endswith("]")):
            try:
                parsed = json.loads(s)
                return cls._extract_text_from_structure(parsed, prefer_key)
            except Exception:
                pass
            try:
                parsed = ast.literal_eval(s)
                return cls._extract_text_from_structure(parsed, prefer_key)
            except Exception:
                pass

            # Regex fallback to extract inner string from {"thought": "..."}
            m = re.search(r'["\'](?:thought|speech|dialogue|text|message)["\']\s*:\s*["\']([^"\']+)["\']', s, re.IGNORECASE)
            if m:
                return m.group(1).strip()

        return s

    @classmethod
    def _strip_markdown_and_wrappers(cls, text: str) -> str:
        """Strip markdown code fences and backticks."""
        # Strip ```json ... ``` or ``` ... ```
        text = re.sub(r"```(?:json|python|html|js)?\s*", "", text, flags=re.IGNORECASE)
        text = text.replace("```", "").replace("`", "")
        return text.strip()
