"""
json_repair.py - Utilities for extracting and repairing JSON from LLM outputs.
LLMs frequently emit JSON surrounded by markdown fences, trailing commas,
unquoted keys, or other minor syntax errors. This module handles all of that
without any third-party dependencies (stdlib only: json + re).
"""

import json
import re
from typing import Optional


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_json_from_text(text: str) -> Optional[str]:
    """
    Scan *text* for the first JSON array or object and return the raw
    substring.  Returns None when nothing JSON-like is found.

    Strategy (in priority order):
    1. Strip markdown code-fences and try the inner content.
    2. Find the first '[' or '{' and walk forward tracking bracket depth.
    3. Use a liberal regex heuristic as a last resort.
    """
    if not text:
        return None

    # 1. Markdown fence: ```json ... ``` or ``` ... ```
    fence_match = re.search(
        r"```(?:json)?\s*\n?([\s\S]*?)\n?```",
        text,
        re.IGNORECASE,
    )
    if fence_match:
        candidate = fence_match.group(1).strip()
        if _looks_like_json(candidate):
            return candidate

    # 2. Walk from the first structural character
    for start_char, end_char in (("[", "]"), ("{", "}")):
        pos = text.find(start_char)
        if pos == -1:
            continue
        extracted = _extract_balanced(text, pos, start_char, end_char)
        if extracted:
            return extracted

    # 3. Regex heuristic – grab everything between outer brackets
    for pattern in (r"(\[[\s\S]*\])", r"(\{[\s\S]*\})"):
        m = re.search(pattern, text)
        if m:
            return m.group(1)

    return None


def repair_json(json_str: str) -> str:
    """
    Attempt to fix common JSON errors produced by LLMs:
    - Trailing commas before ] or }
    - Single-quoted strings → double-quoted strings
    - Python-style True/False/None → true/false/null
    - Unquoted simple keys
    - Missing commas between objects in arrays (best-effort)
    - Control characters inside strings
    Returns the (possibly repaired) string; never raises.
    """
    if not json_str:
        return json_str

    s = json_str.strip()

    # Remove BOM / zero-width characters
    s = s.lstrip("\ufeff\u200b\u200c\u200d")

    # Python literals → JSON literals
    s = re.sub(r'\bTrue\b',  'true',  s)
    s = re.sub(r'\bFalse\b', 'false', s)
    s = re.sub(r'\bNone\b',  'null',  s)

    # Single-quoted strings → double-quoted (naïve but covers most cases)
    # Only replace when the quote is a string delimiter, not an apostrophe
    s = _single_to_double_quotes(s)

    # Trailing commas before closing brackets/braces: [1, 2, 3,]  or {...,}
    s = re.sub(r',\s*([\]}])', r'\1', s)

    # Unquoted keys: { key: "value" } → { "key": "value" }
    s = re.sub(r'(?<=[{,])\s*([A-Za-z_][A-Za-z0-9_]*)\s*:', r' "\1":', s)

    # Missing comma between consecutive objects in an array: }{ → },{
    s = re.sub(r'}\s*{', '},{', s)

    # Strip control characters that break JSON parsing
    s = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', s)

    return s


def parse_scene_json(text: str) -> list[dict]:
    """
    Full pipeline: extract JSON from raw LLM text → repair → parse → return
    a list of scene dicts.  Returns an empty list only when every strategy
    has been exhausted; never raises.
    """
    if not text:
        return []

    # --- Step 1: extract ---
    raw = extract_json_from_text(text)
    if raw is None:
        raw = text  # try the whole text as-is

    # --- Step 2: repair ---
    repaired = repair_json(raw)

    # --- Step 3: parse ---
    result = _try_parse(repaired)
    if result is not None:
        return _normalise_to_list(result)

    # --- Step 4: progressively trim and retry ---
    result = _try_parse_with_truncation(repaired)
    if result is not None:
        return _normalise_to_list(result)

    # --- Step 5: line-by-line object extraction ---
    objects = _extract_objects_line_by_line(text)
    if objects:
        return objects

    return []


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _looks_like_json(text: str) -> bool:
    """Quick check: does the text start with [ or {?"""
    s = text.strip()
    return bool(s) and s[0] in ("{", "[")


def _extract_balanced(
    text: str,
    start: int,
    open_char: str,
    close_char: str,
) -> Optional[str]:
    """
    Starting at *start* (which should be an *open_char*), scan forward
    tracking nesting depth and return the balanced substring on success.
    Handles string literals (skips brackets inside strings).
    """
    depth = 0
    in_string = False
    escape_next = False

    for i in range(start, len(text)):
        ch = text[i]

        if escape_next:
            escape_next = False
            continue

        if ch == "\\" and in_string:
            escape_next = True
            continue

        if ch == '"':
            in_string = not in_string
            continue

        if in_string:
            continue

        if ch == open_char:
            depth += 1
        elif ch == close_char:
            depth -= 1
            if depth == 0:
                return text[start : i + 1]

    return None


def _single_to_double_quotes(s: str) -> str:
    """
    Convert single-quoted JSON string values/keys to double-quoted ones.
    This is a best-effort transformation using a simple state machine.
    """
    result = []
    i = 0
    in_double = False

    while i < len(s):
        ch = s[i]

        if ch == '\\' and in_double:
            result.append(ch)
            i += 1
            if i < len(s):
                result.append(s[i])
                i += 1
            continue

        if ch == '"':
            in_double = not in_double
            result.append(ch)
            i += 1
            continue

        if ch == "'" and not in_double:
            # Find the matching closing single quote
            j = i + 1
            content = []
            while j < len(s):
                c = s[j]
                if c == '\\' and j + 1 < len(s):
                    content.append(c)
                    j += 1
                    content.append(s[j])
                    j += 1
                    continue
                if c == "'":
                    break
                # Escape double quotes found inside single-quoted string
                if c == '"':
                    content.append('\\"')
                else:
                    content.append(c)
                j += 1
            result.append('"')
            result.extend(content)
            result.append('"')
            i = j + 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _try_parse(json_str: str):
    """Return parsed object or None."""
    try:
        return json.loads(json_str)
    except (json.JSONDecodeError, ValueError):
        return None


def _try_parse_with_truncation(json_str: str):
    """
    Try to fix an array by removing the last (possibly malformed) element
    and closing the bracket. Useful when the LLM cuts off mid-object.
    """
    if not json_str.startswith("["):
        return None

    # Find last complete }, then close the array
    last_close = json_str.rfind("}")
    if last_close == -1:
        return None

    candidate = json_str[: last_close + 1] + "]"
    candidate = re.sub(r',\s*]', ']', candidate)  # trailing comma
    return _try_parse(candidate)


def _normalise_to_list(data) -> list[dict]:
    """Ensure the parsed data is a list of dicts."""
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]
    if isinstance(data, dict):
        # Maybe it's {"scenes": [...]}
        for key in ("scenes", "scene_list", "results", "data"):
            if key in data and isinstance(data[key], list):
                return [i for i in data[key] if isinstance(i, dict)]
        return [data]
    return []


def _extract_objects_line_by_line(text: str) -> list[dict]:
    """
    Last-resort: scan for substrings that look like individual JSON objects
    and collect any that parse successfully.
    """
    objects: list[dict] = []
    # Match anything between { and the next } that is at root level
    for match in re.finditer(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)?\}', text, re.DOTALL):
        candidate = repair_json(match.group(0))
        parsed = _try_parse(candidate)
        if isinstance(parsed, dict) and parsed:
            objects.append(parsed)
    return objects
