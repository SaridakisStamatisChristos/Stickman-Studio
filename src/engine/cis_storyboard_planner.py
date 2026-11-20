# Created by Atharv Hatwar
"""
cis_storyboard_planner.py - Script-Driven Visual Director & Storyboard Planner for CIS mode.

Instead of stamping a single static page template across all videos, this planner
builds a complete per-script Director Blueprint choosing:
  1. Visual World / Render Style (B1 Sketchbook Ink, B2 Warm Editorial Cream,
     or B3 Obsidian Dark Chalkboard + Neon Vectors) matched to the script's mood
     or user override.
  2. Per-shot Layout Architecture (clean_stage, big_typo_banner, split_screen,
     comic_beats, floating_callout, editorial_spread) so consecutive scenes never
     repeat the same fixed header/card frame.
  3. Per-shot Kinetic Choreography (14 distinct multi-sprite & vector animation
     engines: scale_tipping, staircase_climb, domino_ripple, spotlight_shift,
     mirror_truth, phone_trap, question_burst, hourglass_sprint, bridge_cross,
     magnet_orbit, split_cards_slide, rocket_breakthrough, crowd_filter,
     cta_celebration) driven directly by the narration semantics and script hash.

100% Free, Local & Offline.
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)

VISUAL_STYLES = ["B1", "B2", "B3"]

LAYOUT_MODES = [
    "clean_stage",
    "big_typo_banner",
    "split_screen",
    "comic_beats",
    "floating_callout",
    "editorial_spread",
]

CHOREOGRAPHY_TYPES = [
    "question_burst",
    "phone_trap",
    "scale_tipping",
    "staircase_climb",
    "domino_ripple",
    "spotlight_shift",
    "mirror_truth",
    "hourglass_sprint",
    "bridge_cross",
    "magnet_orbit",
    "split_cards_slide",
    "rocket_breakthrough",
    "crowd_filter",
    "give_and_withdraw",
    "boundary_shield",
    "tether_break",
    "mind_storm_calm",
    "idea_spark_build",
    "two_path_fork",
    "lighthouse_fog_beam",
    "dopamine_spike_chart",
    "split_mirror_ideal",
    "pedestal_bust_trap",
    "protective_couple_shield",
    "notification_fishhook",
    "crypto_market_rally",
    "terminal_code_deploy",
    "dumbbell_gym_lift",
    "atom_quantum_orbit",
    "stoic_pillar_stand",
    "compound_interest_snowball",
    "focus_pomodoro_timer",
    "neural_net_synapse",
    "iceberg_hidden_depth",
    "hamster_wheel_break",
    "chess_checkmate_move",
    "battery_supercharge",
    "rocket_launchpad_stage",
    "scales_of_justice",
    "puzzle_assembly",
    "radar_scanner_sweep",
    "dna_evolution_spiral",
    "eisenhower_grid_sort",
    "dynamic_synthesizer",
    "cta_celebration",
]

MOTION_PRESETS = [
    "dolly_in_smooth",
    "pan_right_glide",
    "crane_up_rise",
    "dolly_out_wide",
    "pan_left_glide",
    "tilt_drift",
    "pulse_beat",
]

# Theme palettes per render style (B1 / B2 = light ink-on-paper, B3 = dark obsidian chalk)
STYLE_THEMES: dict[str, dict[str, Any]] = {
    "B1": {
        "style": "B1",
        "is_dark": False,
        "paper_bg": "#FAF8F3",
        "card_bg": "#FFFFFF",
        "ink": "#191916",
        "ink_muted": "#4E5358",
        "ink_faint": "#8A9096",
        "accents": ["#E63946", "#1D70B8", "#D97706", "#2A9D8F"],
        "wash_tints": {
            "psychology": "#F3F6FA",
            "growth_discipline": "#FCF7EE",
            "social_contrast": "#FAF3F2",
            "story_wisdom": "#F1F8F6",
        },
    },
    "B2": {
        "style": "B2",
        "is_dark": False,
        "paper_bg": "#F4F0E5",
        "card_bg": "#FCF9F0",
        "ink": "#25231E",
        "ink_muted": "#59544B",
        "ink_faint": "#8C867B",
        "accents": ["#C84B31", "#2B5B84", "#B7791F", "#2F6F5E"],
        "wash_tints": {
            "psychology": "#F0ECE1",
            "growth_discipline": "#F6EFE0",
            "social_contrast": "#F3EAE4",
            "story_wisdom": "#ECF2EC",
        },
    },
    "B3": {
        "style": "B3",
        "is_dark": True,
        "paper_bg": "#111316",
        "card_bg": "#1B1F26",
        "ink": "#F1F5F9",
        "ink_muted": "#CBD5E1",
        "ink_faint": "#64748B",
        "accents": ["#38BDF8", "#FB7185", "#FBBF24", "#34D399"],
        "wash_tints": {
            "psychology": "#101622",
            "growth_discipline": "#14181F",
            "social_contrast": "#1A1318",
            "story_wisdom": "#101A19",
        },
    },
}

ACCENT_COLORS = ["#E63946", "#1D70B8", "#D97706", "#2A9D8F"]

PROFILE_PREFERRED_STYLES: dict[str, list[str]] = {
    "tech_software": ["B3", "B1", "B2"],
    "fitness_discipline": ["B3", "B1", "B2"],
    "finance_crypto": ["B3", "B1", "B2"],
    "space_science": ["B3", "B1", "B2"],
    "nature_adventure": ["B2", "B1", "B3"],
    "education_learning": ["B1", "B3", "B2"],
    "history_epic": ["B2", "B3", "B1"],
    "relationships_dating": ["B3", "B1", "B2"],
    "stoic_wisdom": ["B3", "B2", "B1"],
    "psychology": ["B3", "B1", "B2"],
    "growth_discipline": ["B1", "B3", "B2"],
    "social_contrast": ["B2", "B1", "B3"],
    "story_wisdom": ["B3", "B2", "B1"],
}

# Bespoke per-shot studio themes used when visual_style == "auto" so ONE video mixes styles + creates custom palettes!
AUTO_SHOT_PALETTES: dict[str, dict[str, Any]] = {
    "sketch_paper": {
        "style": "B3",
        "bg_mode": "paper_grid",
        "is_dark": False,
        "paper_bg": "#FAF8F3",
        "card_bg": "#FFFFFF",
        "ink": "#191916",
        "ink_muted": "#4B5563",
        "ink_faint": "#9CA3AF",
        "accents": ["#E63946", "#1D70B8", "#D97706", "#0D9488"],
    },
    "obsidian_neon": {
        "style": "B3",
        "bg_mode": "dark_radial",
        "is_dark": True,
        "paper_bg": "#111316",
        "card_bg": "#1B2029",
        "ink": "#F8FAFC",
        "ink_muted": "#CBD5E1",
        "ink_faint": "#64748B",
        "accents": ["#38BDF8", "#FB7185", "#FBBF24", "#34D399"],
    },
    "warm_kraft": {
        "style": "B3",
        "bg_mode": "warm_paper",
        "is_dark": False,
        "paper_bg": "#F3ECE0",
        "card_bg": "#FBF8F1",
        "ink": "#25211A",
        "ink_muted": "#5C5447",
        "ink_faint": "#9C9283",
        "accents": ["#C84B31", "#2B5B84", "#B7791F", "#2F6F5E"],
    },
    "blueprint_indigo": {
        "style": "B3",
        "bg_mode": "blueprint_grid",
        "is_dark": True,
        "paper_bg": "#0C182D",
        "card_bg": "#142442",
        "ink": "#E0F2FE",
        "ink_muted": "#93C5FD",
        "ink_faint": "#475569",
        "accents": ["#22D3EE", "#FBBF24", "#A78BFA", "#34D399"],
    },
    "sage_calm": {
        "style": "B3",
        "bg_mode": "warm_paper",
        "is_dark": False,
        "paper_bg": "#ECF3EE",
        "card_bg": "#F7FBF8",
        "ink": "#16241B",
        "ink_muted": "#445D4E",
        "ink_faint": "#88A092",
        "accents": ["#0F766E", "#EA580C", "#2563EB", "#D97706"],
    },
    "velvet_charcoal": {
        "style": "B3",
        "bg_mode": "dark_radial",
        "is_dark": True,
        "paper_bg": "#171422",
        "card_bg": "#231E33",
        "ink": "#F5F3FF",
        "ink_muted": "#C4B5FD",
        "ink_faint": "#6D28D9",
        "accents": ["#C084FC", "#F472B6", "#38BDF8", "#FBBF24"],
    },
}

_STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "if", "in", "on", "at", "to", "for",
    "of", "with", "by", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "can", "it", "its", "this", "that", "these",
    "those", "they", "them", "their", "you", "your", "we", "our", "he", "she",
    "him", "her", "his", "hers", "just", "only", "very", "really", "when",
    "then", "than", "so", "not", "no", "yes", "all", "some", "any", "much",
    "many", "more", "most", "here", "there", "what", "why", "how", "who",
    "where", "which", "about", "into", "from", "up", "down", "out", "over",
    "even", "also", "ever", "never", "always", "something", "someone", "anyone",
    "people", "person", "thing", "things", "way", "make", "makes", "get", "gets",
    "while", "until", "since", "though", "although", "unless", "during", "around",
    "between", "through", "without", "because", "another", "each", "every", "one",
    "two", "three", "small", "big", "little", "whole", "keeps", "keep", "look",
    "looks", "away", "back", "still", "even", "now", "today",
}


def script_fingerprint_seed(script: str, topic: str = "") -> int:
    """Deterministic seed per script+topic so every reel gets a unique director blueprint."""
    raw = f"{topic.strip().lower()}::{script.strip().lower()[:400]}".encode("utf-8", errors="ignore")
    return int.from_bytes(hashlib.blake2b(raw, digest_size=4).digest(), "big")


def classify_video_profile(script: str, topic: str = "") -> str:
    """Classify the reel's narrative genre from its script and topic with multi-domain intelligence."""
    text = f"{topic} {script}".lower()
    words = set(re.findall(r"[a-z']+", text))

    genre_rules = {
        "tech_software": (
            ("code", "coding", "software", "tech", "technology", "developer", "programmer", "server", "algorithm", "digital", "data", "bot", "python", "ai", "deploy", "terminal", "stack", "bug"),
            ("software engineer", "lines of code", "write code", "cloud server")
        ),
        "fitness_discipline": (
            ("gym", "workout", "exercise", "strength", "weights", "dumbbells", "barbell", "sweat", "lift", "lifting", "fitness", "muscle", "train", "body"),
            ("working out", "lift weights", "hit the gym", "physical fitness")
        ),
        "finance_crypto": (
            ("money", "finance", "wealth", "trading", "stock", "stocks", "crypto", "bitcoin", "dollar", "invest", "investing", "profit", "cash", "millionaire", "roi", "candlestick"),
            ("stock market", "compound interest", "passive income", "make money")
        ),
        "space_science": (
            ("space", "cosmos", "galaxy", "planet", "planets", "universe", "rocket", "astronaut", "orbit", "quantum", "physics", "atom", "stars", "gravity", "alien"),
            ("deep space", "outer space", "night sky", "solar system")
        ),
        "nature_adventure": (
            ("nature", "forest", "tree", "trees", "mountain", "mountains", "river", "hike", "hiking", "woods", "wild", "animal", "ocean", "sea", "desert", "explore"),
            ("deep forest", "mountain range", "outdoor adventure")
        ),
        "education_learning": (
            ("school", "class", "classroom", "student", "teacher", "lecture", "math", "exam", "lesson", "study", "studying", "book", "read", "reading", "learn", "skill"),
            ("learn a skill", "reading books", "study habits")
        ),
        "history_epic": (
            ("castle", "fortress", "king", "queen", "kingdom", "empire", "medieval", "battle", "war", "throne", "knights", "ancient", "emperor"),
            ("ancient history", "stone castle", "throne room")
        ),
        "relationships_dating": (
            ("text", "texting", "message", "reply", "replies", "call", "dating", "mixed", "ghost", "crush", "love", "partner", "attention", "special", "distant"),
            ("mixed signals", "texting you", "stopped replying", "calls disappear")
        ),
        "stoic_wisdom": (
            ("stoic", "calm", "peace", "boundary", "boundaries", "detach", "detachment", "patience", "silence", "quiet", "breathe", "unbothered", "inner peace"),
            ("protect your peace", "set a boundary", "walk away", "inner calm")
        ),
        "psychology": (
            ("brain", "mind", "narcissist", "embarrass", "awkward", "overthink", "overthinking", "guilt", "manipulat", "ignore", "behavior", "feeling", "emotion", "ego", "shadow"),
            ("human psychology", "human behavior", "psychological trick", "in your mind")
        ),
        "growth_discipline": (
            ("discipline", "habit", "habits", "routine", "compound", "brick", "focus", "consistency", "daily", "progress", "success", "work", "climb", "build", "goal"),
            ("daily habit", "compound effect", "build discipline")
        ),
        "social_contrast": (
            ("society", "trap", "double standard", "cruel", "truth", "reality", "versus", "vs", "myth", "crowd", "illusion", "fake", "comparison", "judge"),
            ("most people", "double standard", "harsh reality")
        ),
    }

    scores = {k: 0 for k in genre_rules}
    for prof, (kw_list, phrases) in genre_rules.items():
        for phrase in phrases:
            if phrase in text:
                scores[prof] += 5
        for kw in kw_list:
            if kw in words:
                scores[prof] += 3 if kw in (topic or "").lower() else 2

    best_prof, best_score = max(scores.items(), key=lambda item: item[1])
    if best_score > 0:
        return best_prof

    profiles = list(genre_rules.keys())
    return profiles[script_fingerprint_seed(script, topic) % len(profiles)]


def choose_visual_style(requested_style: Optional[str], profile: str, seed: int) -> str:
    """
    Pick explicit B1/B2/B3 or 'AUTO_MIX' (uses B3 flexible compositor while mixing
    light paper, dark obsidian, blueprint, and custom themes per scene).
    """
    if isinstance(requested_style, str):
        rs = requested_style.strip().upper()
        if rs in VISUAL_STYLES:
            return rs
        if rs in ("AUTO", "AUTO_MIX", "MIX", ""):
            return "AUTO_MIX"
    return "AUTO_MIX"


def _choose_shot_theme(
    visual_style: str,
    narration: str,
    choreo: str,
    idx: int,
    seed: int,
    prev_palette_key: str = "",
) -> tuple[str, str, dict[str, Any]]:
    """Return (render_style, palette_key, theme_dict) matched cleanly to shot emotion."""
    if visual_style in VISUAL_STYLES:
        return visual_style, visual_style, dict(STYLE_THEMES[visual_style])

    # AUTO_MIX: match canvas world to sentence meaning + vary cleanly per shot
    low = (narration or "").lower()
    if choreo in ("mind_storm_calm", "bridge_cross") or any(w in low for w in ("calm", "peace", "heal", "gentle", "breathe", "morning")):
        pref = ["sage_calm", "warm_kraft", "sketch_paper"]
    elif choreo in ("staircase_climb", "idea_spark_build", "hourglass_sprint") or any(w in low for w in ("plan", "build", "learn", "habit", "system", "code", "work", "step", "book")):
        pref = ["blueprint_indigo", "sketch_paper", "obsidian_neon"]
    elif choreo in ("mirror_truth", "phone_trap", "tether_break", "question_burst") or any(w in low for w in ("night", "secret", "fear", "overthink", "dark", "illusion", "doubt", "trap")):
        pref = ["obsidian_neon", "velvet_charcoal", "sketch_paper"]
    elif choreo in ("give_and_withdraw", "crowd_filter", "split_cards_slide", "boundary_shield"):
        pref = ["warm_kraft", "velvet_charcoal", "sketch_paper"]
    else:
        pref = list(AUTO_SHOT_PALETTES.keys())

    # Include varied pool fallback while avoiding immediate palette repetition
    ordered = pref + [k for k in AUTO_SHOT_PALETTES if k not in pref]
    shift = (seed + idx * 3) % max(1, min(3, len(ordered)))
    rotated = ordered[shift:] + ordered[:shift]
    chosen_key = rotated[0]
    for k in rotated:
        if k != prev_palette_key:
            chosen_key = k
            break
    th = dict(AUTO_SHOT_PALETTES[chosen_key])
    return "B3", chosen_key, th


def resolve_accent_color(
    accent_color: Optional[str],
    idx: int = 0,
    profile: str = "psychology",
    visual_style: str = "B1",
    seed: int = 0,
) -> str:
    """Resolve accent color while keeping high readability on dark B3 obsidian vs light paper."""
    theme = STYLE_THEMES.get(visual_style, STYLE_THEMES["B1"])
    if isinstance(accent_color, str):
        c = accent_color.strip()
        if c.startswith("#") and len(c) in (4, 7):
            try:
                int(c[1:], 16)
                hex_c = "#" + "".join(ch * 2 for ch in c[1:]) if len(c) == 4 else c
                # Brighten muted dark colors slightly on B3 dark mode so they glow nicely
                if theme["is_dark"] and hex_c.upper() == "#00897B":
                    return "#2DD4BF"
                return hex_c.upper()
            except ValueError:
                pass
    palette = theme["accents"]
    shift = seed % len(palette)
    return palette[(idx + shift) % len(palette)]


def _clean_text(raw: str) -> str:
    if not raw:
        return ""
    text = re.sub(r"^```[a-zA-Z]*\s*", "", raw.strip())
    text = re.sub(r"\s*```$", "", text)
    text = re.sub(r"\[.*?\]", "", text)
    text = re.sub(r"\(.*?\)", "", text)
    return re.sub(r"\s+", " ", text).strip()


def _split_into_sentences(text: str) -> list[str]:
    cleaned = _clean_text(text)
    if not cleaned:
        return []
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    result: list[str] = []
    for p in parts:
        subs = [s.strip() for s in p.split("\n") if s.strip()]
        result.extend(subs)
    sentences = [s for s in result if len(s.split()) >= 2]

    if len(sentences) <= 2 and sum(len(s.split()) for s in sentences) >= 16:
        expanded: list[str] = []
        for s in sentences:
            clauses = re.split(
                r"(?:,\s+(?=but|and|while|when|because|yet|so|then)|;\s+|\s+—\s+)",
                s,
                flags=re.IGNORECASE,
            )
            if len(clauses) > 1:
                for c in clauses:
                    c = c.strip(" ,;—")
                    if len(c.split()) >= 3:
                        expanded.append(c)
            else:
                comma_parts = [cp.strip() for cp in s.split(",") if len(cp.strip().split()) >= 3]
                if len(comma_parts) >= 2:
                    expanded.extend(comma_parts)
                else:
                    expanded.append(s)
        if len(expanded) >= 2:
            return expanded
    return sentences or [cleaned]


def _chunk_sentences(sentences: list[str], density: str = "balanced") -> list[list[str]]:
    if not sentences:
        return [[""]]

    target_words = {"detailed": 10, "balanced": 14, "compact": 22}.get(density, 14)

    if len(sentences) in (2, 3, 4, 5) and density != "compact":
        return [[s] for s in sentences]

    chunks: list[list[str]] = []
    curr: list[str] = []
    curr_wc = 0

    for s in sentences:
        wc = len(s.split())
        if curr and (curr_wc + wc > target_words * 1.25):
            chunks.append(curr)
            curr = [s]
            curr_wc = wc
        else:
            curr.append(s)
            curr_wc += wc

    if curr:
        chunks.append(curr)

    if len(chunks) == 1 and len(chunks[0][0].split()) >= 12:
        words = chunks[0][0].split()
        mid = len(words) // 2
        return [[" ".join(words[:mid])], [" ".join(words[mid:])]]

    return chunks


def _short_phrase(text: str, max_chars: int = 44) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip(" ,;:-")
    return (cut + "...") if cut else text[:max_chars]


def _short_headline(text: str, max_chars: int = 24) -> str:
    text = re.sub(r"\s+", " ", text).strip().rstrip(".,;:")
    if len(text) <= max_chars:
        return text
    cut = text[:max_chars].rsplit(" ", 1)[0].strip(" ,;:-")
    return cut if cut else text[:max_chars]


def _split_clauses(text: str) -> tuple[str, str]:
    cleaned = re.sub(r"\s+", " ", text).strip()
    for sep in (
        r"\.\s+",
        r"\?\s+",
        r"!\s+",
        r",\s+(?:but|yet|while|instead|because|so|then|and)\s+",
        r";\s+",
        r",\s+",
    ):
        m = re.split(sep, cleaned, maxsplit=1, flags=re.IGNORECASE)
        if len(m) == 2 and len(m[0].split()) >= 2 and len(m[1].split()) >= 2:
            return m[0].strip(), m[1].strip()

    words = cleaned.split()
    if len(words) >= 4:
        mid = len(words) // 2
        return " ".join(words[:mid]), " ".join(words[mid:])
    return cleaned, cleaned


def _extract_keywords(text: str, n: int = 4) -> list[str]:
    words = re.findall(r"[A-Za-z][a-zA-Z'-]{2,}", text)
    seen: set[str] = set()
    kws: list[str] = []
    for w in words:
        lw = w.lower()
        if lw not in _STOPWORDS and lw not in seen:
            seen.add(lw)
            kws.append(w.capitalize())
            if len(kws) >= n:
                break
    return kws


def _pick_layout_mode(
    choreo: str,
    idx: int,
    total_scenes: int,
    profile: str,
    seed: int,
    prev_layout: str,
    used_layouts: set[str],
) -> str:
    """
    Ensure every shot gets a fitting, NON-REPETITIVE layout architecture!
    Never traps the video in a single top-header/bottom-note template.
    """
    preferred_by_choreo = {
        "split_cards_slide": ["split_screen", "comic_beats", "clean_stage"],
        "spotlight_shift": ["clean_stage", "comic_beats", "floating_callout"],
        "scale_tipping": ["clean_stage", "big_typo_banner", "floating_callout"],
        "staircase_climb": ["big_typo_banner", "clean_stage", "editorial_spread"],
        "domino_ripple": ["clean_stage", "comic_beats", "floating_callout"],
        "mirror_truth": ["comic_beats", "clean_stage", "editorial_spread"],
        "phone_trap": ["clean_stage", "comic_beats", "big_typo_banner"],
        "question_burst": ["big_typo_banner", "comic_beats", "clean_stage"],
        "hourglass_sprint": ["clean_stage", "floating_callout", "comic_beats"],
        "bridge_cross": ["clean_stage", "comic_beats", "big_typo_banner"],
        "magnet_orbit": ["floating_callout", "clean_stage", "editorial_spread"],
        "rocket_breakthrough": ["big_typo_banner", "clean_stage", "floating_callout"],
        "crowd_filter": ["split_screen", "comic_beats", "clean_stage"],
        "give_and_withdraw": ["comic_beats", "clean_stage", "split_screen"],
        "boundary_shield": ["clean_stage", "floating_callout", "big_typo_banner"],
        "tether_break": ["editorial_spread", "comic_beats", "clean_stage"],
        "mind_storm_calm": ["comic_beats", "clean_stage", "floating_callout"],
        "idea_spark_build": ["floating_callout", "big_typo_banner", "clean_stage"],
        "two_path_fork": ["split_screen", "clean_stage", "comic_beats"],
        "terminal_code_deploy": ["clean_stage", "comic_beats", "floating_callout"],
        "dumbbell_gym_lift": ["clean_stage", "big_typo_banner", "floating_callout"],
        "crypto_market_rally": ["floating_callout", "split_screen", "clean_stage"],
        "atom_quantum_orbit": ["clean_stage", "editorial_spread", "floating_callout"],
        "stoic_pillar_stand": ["clean_stage", "editorial_spread", "comic_beats"],
        "compound_interest_snowball": ["clean_stage", "floating_callout", "big_typo_banner"],
        "focus_pomodoro_timer": ["clean_stage", "floating_callout", "comic_beats"],
        "neural_net_synapse": ["clean_stage", "floating_callout", "editorial_spread"],
        "iceberg_hidden_depth": ["clean_stage", "split_screen", "editorial_spread"],
        "hamster_wheel_break": ["comic_beats", "clean_stage", "floating_callout"],
        "chess_checkmate_move": ["clean_stage", "comic_beats", "editorial_spread"],
        "battery_supercharge": ["clean_stage", "floating_callout", "big_typo_banner"],
        "rocket_launchpad_stage": ["big_typo_banner", "clean_stage", "floating_callout"],
        "scales_of_justice": ["split_screen", "clean_stage", "floating_callout"],
        "puzzle_assembly": ["clean_stage", "comic_beats", "floating_callout"],
        "radar_scanner_sweep": ["clean_stage", "floating_callout", "editorial_spread"],
        "dna_evolution_spiral": ["clean_stage", "editorial_spread", "floating_callout"],
        "eisenhower_grid_sort": ["split_screen", "clean_stage", "floating_callout"],
        "dynamic_synthesizer": ["clean_stage", "floating_callout", "comic_beats", "editorial_spread"],
        "cta_celebration": ["clean_stage"],
    }
    candidates = list(preferred_by_choreo.get(choreo, LAYOUT_MODES))
    shift = (seed + idx * 5) % len(LAYOUT_MODES)
    candidates.extend(LAYOUT_MODES[shift:] + LAYOUT_MODES[:shift])

    # Prioritize layouts not used yet in this reel AND never repeat immediately
    for lay in candidates:
        if lay != prev_layout and lay not in used_layouts:
            return lay
    for lay in candidates:
        if lay != prev_layout:
            return lay
    return LAYOUT_MODES[(seed + idx) % len(LAYOUT_MODES)]


def _extract_prop_kind(text: str) -> str:
    """Identify the concrete visual prop spoken about in the sentence."""
    low = (text or "").lower()
    words = set(re.findall(r"[a-z']+", low))
    prop_rules = [
        ("phone", ("phone", "smartphone", "screen", "scroll", "scrolling", "notification", "app", "text", "replies", "call")),
        ("heart", ("love", "heart", "care", "kindness", "feel", "feeling", "empathy", "emotion", "loyal")),
        ("coin", ("money", "wealth", "rich", "poor", "cost", "worth", "invest", "price", "value", "profit", "favor", "dollar", "crypto")),
        ("book", ("book", "books", "read", "reading", "learn", "study", "page", "pages", "knowledge", "wisdom", "school")),
        ("shield", ("boundary", "boundaries", "protect", "safe", "guard", "respect", "defense", "shield")),
        ("clock", ("time", "clock", "hour", "hours", "minute", "minutes", "late", "wait", "deadline", "morning", "timer")),
        ("lightning", ("anger", "panic", "stress", "anxiety", "overwhelm", "fear", "shock", "storm", "burnout")),
        ("key", ("secret", "truth", "unlock", "answer", "solution", "clarity", "aware", "awareness")),
        ("mask", ("fake", "pretend", "illusion", "lie", "lies", "manipulat", "hide", "double", "ego")),
        ("crown", ("win", "success", "goal", "achieve", "confidence", "king", "leader", "power", "dream", "trophy")),
        ("brain", ("brain", "mind", "think", "thinking", "overthink", "memory", "focus", "habit", "neural", "synapse")),
        ("sun", ("peace", "calm", "hope", "bright", "light", "heal", "free", "freedom")),
        ("code", ("code", "coding", "software", "tech", "developer", "server", "algorithm", "python", "deploy", "terminal")),
        ("dumbbell", ("gym", "workout", "lift", "lifting", "weights", "dumbbells", "barbell", "exercise", "muscle", "fitness")),
        ("rocket", ("rocket", "launch", "space", "cosmos", "fly", "soar", "blast", "mission")),
        ("tree", ("tree", "trees", "forest", "nature", "mountain", "plant", "woods", "wild")),
        ("car", ("car", "cars", "drive", "driving", "road", "highway", "vehicle")),
        ("laptop", ("laptop", "computer", "pc", "digital", "screen")),
        ("coffee", ("coffee", "cup", "tea", "cafe", "drink")),
        ("cat", ("cat", "kitten", "kitty")),
        ("dog", ("dog", "puppy", "hound")),
        ("trophy", ("trophy", "champion", "award", "medal")),
        ("chess", ("chess", "checkmate", "strategy", "tactics", "pawn")),
        ("battery", ("battery", "energy", "charge", "drain", "exhausted", "power")),
        ("iceberg", ("iceberg", "depth", "surface", "hidden", "below")),
    ]
    for kind, kws in prop_rules:
        if any(k in words or k in low for k in kws):
            return kind

    # Check the 1,000+ procedural object engine catalog
    try:
        from engine.procedural_object_engine import ProceduralObjectEngine
        for w in words:
            if w in ProceduralObjectEngine.ALIASES:
                return ProceduralObjectEngine.ALIASES[w].lower()
    except Exception:
        pass

    return "spark"


def _score_choreographies(text: str) -> list[tuple[int, str]]:
    """Score every choreography against phrases + whole words in the narration."""
    lower = (text or "").lower()
    words = set(re.findall(r"[a-z']+", lower))

    choreo_phrases: dict[str, tuple[str, ...]] = {
        "terminal_code_deploy": ("software engineer", "lines of code", "write code", "cloud server", "deploy code", "run code"),
        "dumbbell_gym_lift": ("working out", "lift weights", "hit the gym", "physical fitness", "heavy weights"),
        "crypto_market_rally": ("stock market", "crypto market", "market rally", "trading stocks", "candlestick chart"),
        "atom_quantum_orbit": ("quantum physics", "atomic level", "orbiting particles", "deep science"),
        "stoic_pillar_stand": ("unshakeable peace", "inner pillar", "stand your ground", "stoic calm"),
        "compound_interest_snowball": ("compound interest", "snowball effect", "exponential growth", "wealth building"),
        "focus_pomodoro_timer": ("deep work", "pomodoro timer", "intense focus", "zero distraction"),
        "neural_net_synapse": ("neural network", "brain synapses", "mental connections", "artificial intelligence"),
        "iceberg_hidden_depth": ("tip of the iceberg", "hidden underneath", "beneath the surface", "unseen depth"),
        "hamster_wheel_break": ("rat race", "hamster wheel", "endless cycle", "break the loop"),
        "chess_checkmate_move": ("three steps ahead", "checkmate move", "strategic move", "play the long game"),
        "battery_supercharge": ("recharge your battery", "low battery", "drained of energy", "full power"),
        "rocket_launchpad_stage": ("ready for launch", "rocket launch", "lift off", "reach the stars"),
        "scales_of_justice": ("scales of justice", "fair and unfair", "moral balance", "court of law"),
        "puzzle_assembly": ("missing puzzle piece", "piece together", "solve the puzzle"),
        "radar_scanner_sweep": ("radar scan", "under the radar", "detect the signal"),
        "dna_evolution_spiral": ("genetic code", "human evolution", "dna spiral"),
        "eisenhower_grid_sort": ("urgent vs important", "priority matrix", "four quadrants"),
        "give_and_withdraw": (
            "need something", "remember you", "only text", "only call", "one sided",
            "walk away", "turn away", "use you", "used you", "when they need", "give too much",
        ),
        "boundary_shield": (
            "protect your peace", "set a boundary", "set boundaries", "say no", "protect yourself",
            "keep your peace", "peace of mind",
        ),
        "tether_break": (
            "let go", "move on", "break free", "holding you back", "tied to", "cut ties",
            "stuck in", "breaks the illusion",
        ),
        "mind_storm_calm": (
            "deep breath", "quiet your mind", "calm down", "mental noise", "feel overwhelmed",
            "too much noise", "slow down",
        ),
        "two_path_fork": (
            "easy way", "hard way", "short term", "long term", "choose comfort", "choose discipline",
            "two paths", "wrong direction",
        ),
        "idea_spark_build": (
            "small steps", "learn every", "read every", "new skill", "bright idea",
        ),
        "phone_trap": ("social media", "pick up your phone", "staring at your screen", "texting you", "stopped replying"),
        "spotlight_shift": ("double standard", "most people", "stop caring what"),
    }

    choreo_keywords: dict[str, tuple[str, ...]] = {
        "terminal_code_deploy": ("code", "coding", "software", "terminal", "deploy", "developer", "server", "algorithm", "python", "bug", "program", "stack", "tech"),
        "dumbbell_gym_lift": ("gym", "workout", "lift", "lifting", "weights", "dumbbells", "barbell", "exercise", "muscle", "fitness", "body", "train"),
        "crypto_market_rally": ("crypto", "bitcoin", "trading", "stock", "stocks", "market", "candlestick", "rally", "profit", "bull", "bear", "invest", "wealth"),
        "atom_quantum_orbit": ("atom", "quantum", "orbit", "particle", "physics", "science", "formula", "nucleus", "energy", "star", "stars", "universe", "cosmos", "galaxy", "planet", "planets", "deep space", "space"),
        "stoic_pillar_stand": ("stoic", "pillar", "stand", "unshakeable", "firm", "calm", "storm", "resilient", "strength", "endure"),
        "compound_interest_snowball": ("compound", "compounds", "snowball", "interest", "wealth", "invest", "investing", "multiplier", "accumulate"),
        "focus_pomodoro_timer": ("pomodoro", "timer", "distraction", "concentrate", "concentration", "deep work", "study clock"),
        "neural_net_synapse": ("neural", "synapse", "brain", "network", "nodes", "intelligence", "ai", "neurons", "signals"),
        "iceberg_hidden_depth": ("iceberg", "surface", "depth", "depths", "hidden", "below", "underwater", "unseen", "tip"),
        "hamster_wheel_break": ("hamster", "wheel", "routine", "trap", "cycle", "loop", "endless", "rat"),
        "chess_checkmate_move": ("chess", "checkmate", "strategy", "move", "tactics", "pawn", "king", "mastermind"),
        "battery_supercharge": ("battery", "energy", "charge", "drain", "drained", "exhausted", "power", "recharge", "burnout"),
        "rocket_launchpad_stage": ("launch", "launchpad", "stage", "liftoff", "soar", "blast", "ignition", "mission", "reach", "space"),
        "scales_of_justice": ("justice", "fair", "unfair", "law", "court", "judge", "guilty", "innocent", "verdict", "moral"),
        "puzzle_assembly": ("puzzle", "piece", "pieces", "assembly", "fit", "missing", "complete", "connect", "solve"),
        "radar_scanner_sweep": ("radar", "scanner", "scan", "detect", "detection", "sonar", "sweep", "target", "signal"),
        "dna_evolution_spiral": ("dna", "evolution", "genes", "genetic", "spiral", "biology", "evolve", "mutation", "species"),
        "eisenhower_grid_sort": ("urgent", "important", "priority", "priorities", "matrix", "grid", "delegate", "eliminate", "schedule"),
        "give_and_withdraw": ("favor", "favour", "favors", "one-sided", "ghosted", "abandon", "selfish", "betrayal", "take-advantage", "unreciprocated"),
        "boundary_shield": ("boundary", "boundaries", "protect", "respect", "guard", "toxic", "shield", "drama", "refuse", "defend", "limit"),
        "tether_break": ("attach", "attached", "attachment", "illusion", "chain", "chains", "escape", "quit", "release", "free", "freedom", "drop"),
        "mind_storm_calm": ("anxiety", "anxious", "stress", "stressed", "panic", "overwhelm", "overwhelmed", "storm", "breathe", "calm", "peace", "silence", "quiet", "heal", "healing"),
        "idea_spark_build": ("learn", "learning", "read", "reading", "book", "books", "study", "write", "idea", "ideas", "wisdom", "knowledge", "craft", "create", "skill"),
        "two_path_fork": ("path", "easy", "hard", "shortcut", "comfort", "regret", "discipline", "direction", "road", "choose"),
        "phone_trap": ("phone", "smartphone", "scroll", "scrolling", "screen", "notification", "buzz", "buzzes", "text", "message", "app", "apps", "swipe", "alert", "dopamine"),
        "staircase_climb": ("brick", "bricks", "compound", "compounds", "climb", "stair", "stairs", "level", "habit", "habits", "daily", "build", "progress", "stack", "momentum"),
        "scale_tipping": ("balance", "scale", "weigh", "choice", "choices", "tradeoff", "worth", "cost", "heavy", "either", "value"),
        "domino_ripple": ("domino", "dominoes", "trigger", "triggers", "chain", "ripple", "effect", "spark", "cascade"),
        "mirror_truth": ("mirror", "mirrors", "reflect", "reflection", "reflecting", "honest-look", "self-image"),
        "hourglass_sprint": ("time", "clock", "alarm", "late", "morning", "minute", "minutes", "hour", "wait", "hurry", "rush", "run", "running", "deadline"),
        "bridge_cross": ("gap", "gaps", "bridge", "across", "obstacle", "wall", "stuck", "fear", "leap", "breakthrough", "disappear", "disappears", "forest", "mountain", "mountains", "river", "nature", "tree", "trees", "woods", "hiking"),
        "question_burst": ("overthink", "overthinking", "confused", "curiosity", "puzzle", "mystery", "unsolved"),
        "spotlight_shift": ("spotlight", "attention", "judge", "judging", "stranger", "double", "blame", "credit", "focus", "mistake"),
        "magnet_orbit": ("attract", "pull", "pulls", "energy", "magnet", "relationship", "trust", "loyalty"),
        "crowd_filter": ("crowd", "everyone", "others", "friends", "society", "room", "noise"),
        "split_cards_slide": ("versus", "vs", "instead", "opposite", "difference", "before", "after", "while", "contrast", "different"),
        "rocket_breakthrough": ("launch", "soar", "soars", "future", "dream", "rise", "fly", "vision", "ahead", "achieve"),
    }

    hit_scores: list[tuple[int, str]] = []
    for c_name in CHOREOGRAPHY_TYPES[:-1]:
        score = 0
        for ph in choreo_phrases.get(c_name, ()):
            if ph in lower:
                score += 5
        for kw in choreo_keywords.get(c_name, ()):
            if kw in words:
                score += 3
        if c_name == "question_burst" and ("?" in text and any(w in words for w in ("why", "how", "what", "wonder", "confused", "mystery", "puzzle", "overthink"))):
            score += 2
        if score > 0:
            hit_scores.append((score, c_name))

    # Give dynamic_synthesizer priority when a rich semantic prop from the 1,025+ catalog is present
    try:
        from engine.procedural_object_engine import ProceduralObjectEngine
        has_prop = any(w in ProceduralObjectEngine.ALIASES for w in words)
        if has_prop:
            hit_scores.append((4, "dynamic_synthesizer"))
    except Exception:
        pass

    # Neural Semantic Brain Integration for CIS mode (MiniLM-L6 ONNX Transformer)
    try:
        from engine.semantic_scene_brain import SemanticSceneBrain
        brain = SemanticSceneBrain.get_instance()
        if brain._initialized:
            n_met, n_m_score = brain.match_best_metaphor(text)
            if n_met and n_m_score >= 0.16:
                metaphor_cis_map = {
                    "EXPONENTIAL_COMPOUND": "compound_interest_snowball",
                    "ICEBERG_DEPTH": "iceberg_hidden_depth",
                    "HAMSTER_WHEEL": "hamster_wheel_break",
                    "LEVER_BOULDER": "scale_tipping",
                    "BALANCE_SCALE": "scales_of_justice",
                    "DOMINO_CHAIN": "domino_ripple",
                    "ROCKET_LAUNCH": "rocket_breakthrough",
                    "HOURGLASS": "hourglass_sprint",
                    "STAIRCASE": "staircase_climb",
                    "MIRROR": "split_mirror_ideal",
                    "PHONE": "phone_trap",
                    "SHIELD": "boundary_shield",
                    "LIGHTHOUSE": "lighthouse_fog_beam",
                    "BATTERY": "battery_supercharge",
                    "BRAIN": "neural_net_synapse",
                    "CHESS": "chess_checkmate_move",
                }
                mapped_choreo = metaphor_cis_map.get(n_met)
                if mapped_choreo:
                    hit_scores.append((int(n_m_score * 20), mapped_choreo))

            n_arch, n_a_score = brain.match_best_archetype(text)
            if n_arch and n_a_score >= 0.18:
                archetype_cis_map = {
                    "SPLIT_SCREEN": "split_cards_slide",
                    "FULLSCREEN_INFOGRAPHIC": "compound_interest_snowball",
                    "HERD_REBEL": "crowd_filter",
                    "SCALE_CONTRAST": "stoic_pillar_stand",
                    "HERO_PROP_MECHANIC": "hamster_wheel_break",
                }
                mapped_arch = archetype_cis_map.get(n_arch)
                if mapped_arch:
                    hit_scores.append((int(n_a_score * 16), mapped_arch))
    except Exception as _brain_err:
        logger.debug("CIS Neural Brain pass note: %s", _brain_err)

    hit_scores.sort(key=lambda item: (-item[0], item[1]))
    return hit_scores


def _pick_choreography(
    text: str,
    idx: int,
    total_scenes: int,
    profile: str,
    seed: int,
    prev_choreo: str,
    used_choreos: set[str],
    topic: str = "",
) -> tuple[str, int]:
    """Select the strongest script-matched choreography without repetitive cycling."""
    scoring_text = f"{topic}. {text}" if (idx == 0 and topic) else text
    hit_scores = _score_choreographies(scoring_text)
    best_score = hit_scores[0][0] if hit_scores else 0
    scored = [c for _, c in hit_scores]

    profile_pools = {
        "tech_software": [
            "terminal_code_deploy", "neural_net_synapse", "radar_scanner_sweep",
            "atom_quantum_orbit", "idea_spark_build", "puzzle_assembly",
            "rocket_breakthrough", "battery_supercharge", "dynamic_synthesizer",
        ],
        "fitness_discipline": [
            "dumbbell_gym_lift", "battery_supercharge", "staircase_climb",
            "stoic_pillar_stand", "two_path_fork", "focus_pomodoro_timer",
            "hamster_wheel_break", "rocket_breakthrough", "dynamic_synthesizer",
        ],
        "finance_crypto": [
            "crypto_market_rally", "compound_interest_snowball", "scale_tipping",
            "iceberg_hidden_depth", "chess_checkmate_move", "rocket_launchpad_stage",
            "split_cards_slide", "two_path_fork", "dynamic_synthesizer",
        ],
        "space_science": [
            "atom_quantum_orbit", "rocket_launchpad_stage", "rocket_breakthrough",
            "radar_scanner_sweep", "dna_evolution_spiral", "puzzle_assembly",
            "hourglass_sprint", "neural_net_synapse", "dynamic_synthesizer",
        ],
        "nature_adventure": [
            "bridge_cross", "two_path_fork", "rocket_breakthrough",
            "dna_evolution_spiral", "stoic_pillar_stand", "tether_break",
            "mind_storm_calm", "hourglass_sprint", "dynamic_synthesizer",
        ],
        "education_learning": [
            "idea_spark_build", "staircase_climb", "puzzle_assembly",
            "focus_pomodoro_timer", "eisenhower_grid_sort", "chess_checkmate_move",
            "atom_quantum_orbit", "domino_ripple", "dynamic_synthesizer",
        ],
        "history_epic": [
            "scales_of_justice", "stoic_pillar_stand", "chess_checkmate_move",
            "iceberg_hidden_depth", "pedestal_bust_trap", "two_path_fork",
            "rocket_breakthrough", "crowd_filter", "dynamic_synthesizer",
        ],
        "relationships_dating": [
            "phone_trap", "give_and_withdraw", "protective_couple_shield",
            "notification_fishhook", "split_mirror_ideal", "boundary_shield",
            "tether_break", "mirror_truth", "dynamic_synthesizer",
        ],
        "stoic_wisdom": [
            "stoic_pillar_stand", "mind_storm_calm", "boundary_shield",
            "tether_break", "mirror_truth", "lighthouse_fog_beam",
            "iceberg_hidden_depth", "two_path_fork", "dynamic_synthesizer",
        ],
        "psychology": [
            "give_and_withdraw", "mirror_truth", "question_burst", "boundary_shield",
            "mind_storm_calm", "tether_break", "phone_trap", "spotlight_shift",
            "neural_net_synapse", "dopamine_spike_chart", "dynamic_synthesizer",
        ],
        "growth_discipline": [
            "staircase_climb", "two_path_fork", "idea_spark_build", "hourglass_sprint",
            "domino_ripple", "bridge_cross", "rocket_breakthrough", "scale_tipping",
            "focus_pomodoro_timer", "compound_interest_snowball", "dynamic_synthesizer",
        ],
        "social_contrast": [
            "give_and_withdraw", "split_cards_slide", "spotlight_shift", "crowd_filter",
            "boundary_shield", "phone_trap", "scale_tipping", "mirror_truth",
            "scales_of_justice", "dynamic_synthesizer",
        ],
        "story_wisdom": [
            "tether_break", "mind_storm_calm", "bridge_cross", "mirror_truth",
            "idea_spark_build", "two_path_fork", "magnet_orbit", "rocket_breakthrough",
            "stoic_pillar_stand", "dynamic_synthesizer",
        ],
    }

    # Boost choreographies matching the detected genre profile
    domain_heroes = set(profile_pools.get(profile, []))
    boosted_scores = []
    for s, c_name in hit_scores:
        if c_name in domain_heroes:
            s += 4
        boosted_scores.append((s, c_name))
    boosted_scores.sort(key=lambda item: (-item[0], item[1]))
    scored = [c for _, c in boosted_scores]
    best_score = boosted_scores[0][0] if boosted_scores else 0

    pool = list(profile_pools.get(profile, CHOREOGRAPHY_TYPES[:-1]))
    shift = (seed + idx * 7) % len(pool)
    rotated_pool = pool[shift:] + pool[:shift]
    candidates = scored + rotated_pool + [c for c in CHOREOGRAPHY_TYPES[:-1] if c not in rotated_pool]

    for c in candidates:
        if c != prev_choreo and c not in used_choreos and c != "cta_celebration":
            return c, best_score
    for c in candidates:
        if c != prev_choreo and c != "cta_celebration":
            return c, best_score
    return pool[idx % len(pool)], best_score


def _pick_motion_preset(choreo: str, profile: str, idx: int, seed: int, prev_motion: str) -> str:
    preferred_map = {
        "question_burst": ["dolly_in_smooth", "tilt_drift", "pulse_beat"],
        "phone_trap": ["pulse_beat", "pan_right_glide", "dolly_in_smooth"],
        "scale_tipping": ["dolly_out_wide", "tilt_drift", "pulse_beat"],
        "staircase_climb": ["crane_up_rise", "pan_right_glide", "dolly_in_smooth"],
        "domino_ripple": ["pan_right_glide", "dolly_out_wide", "pulse_beat"],
        "spotlight_shift": ["pan_left_glide", "pan_right_glide", "dolly_in_smooth"],
        "mirror_truth": ["dolly_in_smooth", "pulse_beat", "tilt_drift"],
        "hourglass_sprint": ["pan_right_glide", "crane_up_rise", "dolly_out_wide"],
        "bridge_cross": ["pan_right_glide", "crane_up_rise", "dolly_out_wide"],
        "magnet_orbit": ["dolly_out_wide", "pulse_beat", "dolly_in_smooth"],
        "split_cards_slide": ["dolly_out_wide", "pulse_beat", "pan_left_glide"],
        "rocket_breakthrough": ["crane_up_rise", "pan_right_glide", "dolly_in_smooth"],
        "crowd_filter": ["dolly_in_smooth", "dolly_out_wide", "pan_left_glide"],
        "give_and_withdraw": ["pan_right_glide", "dolly_in_smooth", "tilt_drift"],
        "boundary_shield": ["pulse_beat", "dolly_out_wide", "crane_up_rise"],
        "tether_break": ["pan_right_glide", "dolly_in_smooth", "crane_up_rise"],
        "mind_storm_calm": ["dolly_in_smooth", "dolly_out_wide", "tilt_drift"],
        "idea_spark_build": ["crane_up_rise", "pulse_beat", "dolly_in_smooth"],
        "two_path_fork": ["dolly_out_wide", "pan_left_glide", "crane_up_rise"],
        "cta_celebration": ["pulse_beat"],
    }
    pool = list(preferred_map.get(choreo, MOTION_PRESETS))
    shift = (seed + idx * 3) % len(pool)
    for m in (pool[shift:] + pool[:shift]):
        if m != prev_motion:
            return m
    return MOTION_PRESETS[(seed + idx) % len(MOTION_PRESETS)]


def _natural_sentence_title(narration: str, kws: list[str], fallback: str) -> str:
    """Extract a punchy 2-4 word natural headline directly from the narration words."""
    # Strip leading filler starters so the title reads naturally
    cleaned = re.sub(
        r"^(?:and|but|so|then|when|while|if|because|sometimes|often|always|most people|you)\s+",
        "",
        (narration or "").strip(),
        flags=re.IGNORECASE,
    )
    tokens = re.findall(r"[A-Za-z][A-Za-z'-]*", cleaned)
    if len(tokens) >= 2:
        phrase = " ".join(tokens[:4])
        return _short_headline(phrase.upper(), 24)
    if kws:
        return _short_headline(" ".join(kws[:2]).upper(), 24)
    return _short_headline(fallback.upper(), 24)


def _build_dynamic_scene_fields(
    narration: str,
    topic: str,
    idx: int,
    total_scenes: int,
    choreo: str,
    layout_mode: str,
    accent: str,
    visual_style: str,
    profile: str,
    motion_preset: str,
    seed: int,
    prev_palette_key: str = "",
) -> dict[str, Any]:
    """Build full rich script-derived text labels, custom mixed theme, and literal prop cues."""
    render_style, palette_key, theme = _choose_shot_theme(
        visual_style=visual_style,
        narration=narration,
        choreo=choreo,
        idx=idx,
        seed=seed,
        prev_palette_key=prev_palette_key,
    )
    if (not accent) and theme.get("accents"):
        acc_pool = theme["accents"]
        accent = acc_pool[(seed + idx) % len(acc_pool)]

    part_a, part_b = _split_clauses(narration)
    kws = _extract_keywords(narration, 4) or _extract_keywords(topic, 4) or ["Focus", "Shift", "Clarity", "Growth"]
    kw1 = kws[0] if len(kws) >= 1 else "Focus"
    kw2 = kws[1] if len(kws) >= 2 else "Truth"
    kw3 = kws[2] if len(kws) >= 3 else "Action"
    kw4 = kws[3] if len(kws) >= 4 else "Clarity"

    topic_clean = _short_headline(topic or kw1, 24)
    stamp_word = _natural_sentence_title(part_a, kws, kw1)

    if idx == 0 and topic and len(topic.split()) <= 6:
        scene_title = _short_headline(topic_clean.upper(), 24)
        scene_subtitle = _short_phrase(part_a, 38)
    else:
        scene_title = _natural_sentence_title(part_a, kws, topic_clean)
        scene_subtitle = _short_phrase(part_b if part_b != part_a else narration, 38)

    left_label = _short_headline(part_a, 24)
    right_label = _short_headline(part_b if part_b != part_a else kw2, 24)

    steps = [
        _short_headline(kw1, 14),
        _short_headline(kw2, 14),
        _short_headline(kw3, 14),
        _short_headline(kw4, 14),
    ]
    prop_kind = _extract_prop_kind(narration)

    bg_wash = theme.get("wash_tints", {}).get(profile, theme["paper_bg"])
    return {
        "scene_id": idx + 1,
        "topic": topic,
        "narration": narration,
        "video_profile": profile,
        "visual_style": render_style,
        "requested_visual_style": visual_style,
        "palette_key": palette_key,
        "theme": theme,
        "prop_kind": prop_kind,
        "choreography": choreo,
        "composition_type": choreo,
        "layout_mode": layout_mode,
        "motion_preset": motion_preset,
        "bg_wash_tint": bg_wash,
        "variant_seed": (seed + idx * 101) & 0xFFFF,
        "accent_color": accent,
        "scene_title": scene_title,
        "scene_subtitle": scene_subtitle,
        "stamp_word": stamp_word,
        "beat_a_label": _short_phrase(part_a, 34),
        "beat_b_label": _short_phrase(part_b if part_b != part_a else narration, 34),
        "left_label": left_label,
        "right_label": right_label,
        "left_tag": _short_headline(kw1.upper(), 16),
        "right_tag": _short_headline(kw2.upper(), 16),
        "steps": steps,
        "keywords": kws,
        "takeaway_top": _short_phrase(part_a, 42),
        "takeaway_bottom": _short_phrase(part_b if part_b != part_a else narration, 48),
    }


def _extract_cta_button_label(cta_text: str) -> str:
    low = (cta_text or "").lower()
    if "subscribe" in low:
        return "+ SUBSCRIBE"
    if "save" in low:
        return "BOOKMARK & FOLLOW"
    if "share" in low:
        return "+ FOLLOW & SHARE"
    return "+ FOLLOW"


def _build_cta_scene(
    scene_id: int,
    cta_text: str,
    cta_audio_text: str,
    topic: str,
    accent: str,
    visual_style: str,
    profile: str,
    seed: int,
    prev_palette_key: str = "",
) -> dict[str, Any]:
    render_style, palette_key, theme = _choose_shot_theme(
        visual_style=visual_style,
        narration=cta_text or topic,
        choreo="cta_celebration",
        idx=scene_id,
        seed=seed,
        prev_palette_key=prev_palette_key,
    )
    headline = _short_headline(cta_text or "Follow this page", 44)
    spoken = _clean_text(cta_audio_text) or f"{headline} for more insights like this."
    clean_topic = (topic or "").strip()
    if clean_topic and len(clean_topic.split()) <= 3:
        subtext = _short_phrase(f"More insights on {clean_topic}", 42)
    else:
        subtext = "Save · Share · Follow for more"
    bg_wash = theme.get("wash_tints", {}).get(profile, theme["paper_bg"])
    return {
        "scene_id": scene_id,
        "topic": topic,
        "narration": spoken,
        "video_profile": profile,
        "visual_style": render_style,
        "requested_visual_style": visual_style,
        "palette_key": palette_key,
        "theme": theme,
        "prop_kind": "heart",
        "choreography": "cta_celebration",
        "composition_type": "cta_celebration",
        "layout_mode": "clean_stage",
        "motion_preset": "pulse_beat",
        "bg_wash_tint": bg_wash,
        "variant_seed": (seed + scene_id * 137) & 0xFFFF,
        "accent_color": accent,
        "scene_title": headline.upper(),
        "scene_subtitle": subtext,
        "stamp_word": _extract_cta_button_label(headline),
        "cta_headline": headline,
        "cta_button_label": _extract_cta_button_label(headline),
        "cta_subtext": subtext,
        "takeaway_top": headline,
        "takeaway_bottom": subtext,
    }


def _expand_long_dialogue_turns(turns: list[dict], max_words: int = 34, min_words_per_beat: int = 8) -> list[dict]:
    """
    Splits long multi-sentence dialogue monologues (> max_words) into dynamic consecutive visual beats
    for the same speaker so scenes change naturally every 6-9 seconds without flashing micro-cuts.
    Preserves short reactions and introductory phrases with their parent sentences.
    """
    expanded: list[dict] = []
    for turn in turns:
        text = str(turn.get("text", "")).strip()
        words = text.split()
        if len(words) <= max_words:
            expanded.append(turn)
            continue
        sentences = re.split(r"(?<=[.!?])\s+", text)
        sentences = [s.strip() for s in sentences if s.strip()]
        if len(sentences) <= 1:
            expanded.append(turn)
            continue
        cur_sentences: list[str] = []
        cur_count = 0
        for s in sentences:
            swc = len(s.split())
            if cur_sentences and cur_count >= min_words_per_beat and (cur_count + swc > max_words):
                expanded.append({**turn, "text": " ".join(cur_sentences)})
                cur_sentences = [s]
                cur_count = swc
            else:
                cur_sentences.append(s)
                cur_count += swc
        if cur_sentences:
            if expanded and cur_count < min_words_per_beat:
                prev = expanded[-1]
                if prev.get("speaker") == turn.get("speaker"):
                    expanded[-1] = {**prev, "text": f"{prev['text']} {' '.join(cur_sentences)}"}
                else:
                    expanded.append({**turn, "text": " ".join(cur_sentences)})
            else:
                expanded.append({**turn, "text": " ".join(cur_sentences)})
    return expanded


class CISStoryboardPlanner:
    """Converts any topic + script into a non-repetitive, script-unique storyboard."""

    def __init__(self, llm_manager=None) -> None:
        self.llm = llm_manager

    def _is_ollama_running(self) -> bool:
        return bool(
            self.llm
            and hasattr(self.llm, "check_ollama_running")
            and self.llm.check_ollama_running()
        )

    def plan(
        self,
        script: str,
        topic: str = "",
        accent_color: Optional[str] = None,
        scene_density: str = "balanced",
        enable_cta: bool = False,
        cta_text: str = "",
        cta_audio_text: str = "",
        visual_style: str = "auto",
    ) -> list[dict]:
        """Generate a unique multi-choreography storyboard matched to script & visual medium."""
        cleaned = _clean_text(script)
        if not cleaned:
            from engine.scene_planner import ScenePlanner
            sp = ScenePlanner(llm_manager=self.llm)
            cleaned = sp.generate_script(
                topic=topic or "Human Behavior",
                duration=30,
                style="cis_illustrated",
            )
            cleaned = _clean_text(cleaned)
            if not cleaned:
                cleaned = (
                    f"Have you ever noticed something surprising about {topic or 'human behavior'}? "
                    f"Most people react on impulse, while quiet awareness reveals the truth. "
                    f"When you change how you respond, everything shifts."
                )

        profile = classify_video_profile(cleaned, topic)
        seed = script_fingerprint_seed(cleaned, topic)
        chosen_style = choose_visual_style(visual_style, profile, seed)
        logger.info(
            "CISStoryboardPlanner: profile=%s visual_style=%s seed=%s",
            profile,
            chosen_style,
            seed,
        )

        scenes: list[dict] = []

        # Check for structured story beats & multi-turn dialogue format
        from engine.script_intelligence import ScriptIntelligenceEngine
        story_beats = ScriptIntelligenceEngine.parse_script_to_story_beats(script)
        dialogue_turns = [
            {
                "speaker": b.get("speaker", 1),
                "speaker_name": b.get("speaker_name", "Alex"),
                "text": b.get("narration", ""),
            }
            for b in story_beats
        ] if story_beats else []

        if len(dialogue_turns) >= 2:
            dialogue_turns = _expand_long_dialogue_turns(dialogue_turns, max_words=34, min_words_per_beat=8)
            logger.info(
                "CISStoryboardPlanner: Detected %d structured story beats (expanded to %d visual beats); building dialogue storyboard.",
                len(story_beats),
                len(dialogue_turns),
            )
            scenes = self._plan_dialogue_storyboard(
                dialogue_turns, topic, accent_color, chosen_style, profile, seed
            )
        else:
            if self._is_ollama_running():
                try:
                    scenes = self._plan_with_llm(
                        cleaned, topic, accent_color, scene_density, profile, chosen_style, seed
                    )
                except Exception as exc:
                    logger.warning("CISStoryboardPlanner LLM path failed: %s; using dynamic rule-based", exc)

            if not scenes or len(scenes) < 2:
                scenes = self._plan_rule_based(
                    cleaned, topic, accent_color, scene_density, profile, chosen_style, seed
                )

        if enable_cta:
            eff_vs = "B3" if chosen_style == "AUTO_MIX" else chosen_style
            prev_pal = str(scenes[-1].get("palette_key", "")) if scenes else ""
            cta_accent = resolve_accent_color(
                accent_color, len(scenes), profile=profile, visual_style=eff_vs, seed=seed
            )
            scenes.append(
                _build_cta_scene(
                    scene_id=len(scenes) + 1,
                    cta_text=cta_text,
                    cta_audio_text=cta_audio_text,
                    topic=topic,
                    accent=cta_accent,
                    visual_style=chosen_style,
                    profile=profile,
                    seed=seed,
                    prev_palette_key=prev_pal,
                )
            )

        return scenes

    def _plan_dialogue_storyboard(
        self,
        dialogue_turns: list[dict],
        topic: str,
        accent_color: Optional[str],
        visual_style: str,
        profile: str,
        seed: int,
    ) -> list[dict]:
        total_scenes = len(dialogue_turns)
        scenes: list[dict] = []
        prev_choreo = ""
        prev_layout = ""
        prev_motion = ""
        prev_palette = ""
        used_choreos: set[str] = set()
        used_layouts: set[str] = set()
        eff_vs = "B3" if visual_style == "AUTO_MIX" else visual_style

        for i, turn in enumerate(dialogue_turns):
            narration = turn.get("text", "").strip()
            speaker = turn.get("speaker", 1)
            speaker_name = turn.get("speaker_name", "Alex")

            choreo, _ = _pick_choreography(
                narration, i, total_scenes, profile, seed, prev_choreo, used_choreos, topic=topic
            )
            prev_choreo = choreo
            used_choreos.add(choreo)

            layout_mode = _pick_layout_mode(
                choreo, i, total_scenes, profile, seed, prev_layout, used_layouts
            )
            prev_layout = layout_mode
            used_layouts.add(layout_mode)

            motion = _pick_motion_preset(choreo, profile, i, seed, prev_motion)
            prev_motion = motion

            accent = "" if (not accent_color and visual_style == "AUTO_MIX") else resolve_accent_color(
                accent_color, i, profile=profile, visual_style=eff_vs, seed=seed
            )

            sc = _build_dynamic_scene_fields(
                narration=narration,
                topic=topic,
                idx=i,
                total_scenes=total_scenes,
                choreo=choreo,
                layout_mode=layout_mode,
                accent=accent,
                visual_style=visual_style,
                profile=profile,
                motion_preset=motion,
                seed=seed,
                prev_palette_key=prev_palette,
            )
            prev_palette = str(sc.get("palette_key", ""))
            sc["speaker"] = speaker
            sc["speaker_name"] = speaker_name
            sc["speaker_badge"] = speaker_name.upper()
            sc["narration"] = narration
            scenes.append(sc)

        return scenes

    def _plan_rule_based(
        self,
        script: str,
        topic: str,
        accent_color: Optional[str],
        scene_density: str,
        profile: str,
        visual_style: str,
        seed: int,
    ) -> list[dict]:
        sentences = _split_into_sentences(script)
        chunks = _chunk_sentences(sentences, density=scene_density)
        total_scenes = len(chunks)
        scenes: list[dict] = []
        prev_choreo = ""
        prev_layout = ""
        prev_motion = ""
        prev_palette = ""
        used_choreos: set[str] = set()
        used_layouts: set[str] = set()
        eff_vs = "B3" if visual_style == "AUTO_MIX" else visual_style

        for i, chunk in enumerate(chunks):
            narration = " ".join(chunk).strip()
            choreo, _score = _pick_choreography(
                narration, i, total_scenes, profile, seed, prev_choreo, used_choreos, topic=topic
            )
            prev_choreo = choreo
            used_choreos.add(choreo)

            layout_mode = _pick_layout_mode(
                choreo, i, total_scenes, profile, seed, prev_layout, used_layouts
            )
            prev_layout = layout_mode
            used_layouts.add(layout_mode)

            motion = _pick_motion_preset(choreo, profile, i, seed, prev_motion)
            prev_motion = motion

            accent = "" if (not accent_color and visual_style == "AUTO_MIX") else resolve_accent_color(
                accent_color, i, profile=profile, visual_style=eff_vs, seed=seed
            )
            sc = _build_dynamic_scene_fields(
                narration=narration,
                topic=topic,
                idx=i,
                total_scenes=total_scenes,
                choreo=choreo,
                layout_mode=layout_mode,
                accent=accent,
                visual_style=visual_style,
                profile=profile,
                motion_preset=motion,
                seed=seed,
                prev_palette_key=prev_palette,
            )
            prev_palette = str(sc.get("palette_key", ""))
            scenes.append(sc)

        return scenes

    def _plan_with_llm(
        self,
        script: str,
        topic: str,
        accent_color: Optional[str],
        scene_density: str,
        profile: str,
        visual_style: str,
        seed: int,
    ) -> list[dict]:
        sentences = _split_into_sentences(script)
        chunks = _chunk_sentences(sentences, density=scene_density)
        est_count = max(2, min(12, len(chunks)))
        selectable_choreos = [c for c in CHOREOGRAPHY_TYPES if c != "cta_celebration"]
        prompt = (
            f"You are a cinematic motion director for vertical animated stickman videos.\n"
            f"Topic: '{topic}' (Genre: {profile}, Visual Style: {visual_style})\n"
            f"Break the script into {est_count} scenes covering the script completely.\n"
            f"For each scene pick:\n"
            f"- choreography from: {', '.join(selectable_choreos)} (DO NOT repeat consecutive choreographies)\n"
            f"- layout_mode from: {', '.join(LAYOUT_MODES)} (mix clean_stage, big_typo_banner, split_screen, comic_beats, floating_callout, editorial_spread)\n"
            f"- stamp_word (2-3 punchy uppercase words), beat_a (3-6 words for start of scene), beat_b (3-6 words for twist/payoff).\n"
            f"Return ONLY a JSON array of objects with keys:\n"
            f"scene_id, narration, scene_title (2-3 uppercase words), scene_subtitle (4-7 words), "
            f"choreography, layout_mode, stamp_word, beat_a, beat_b.\n\n"
            f"SCRIPT:\n{script}\n\nJSON:"
        )
        raw = self.llm.generate(prompt, max_tokens=2400, temperature=0.45)
        if not raw:
            return []

        start = raw.find("[")
        end = raw.rfind("]")
        if start == -1 or end == -1:
            return []

        parsed = json.loads(raw[start : end + 1])
        if not isinstance(parsed, list) or not parsed:
            return []

        scenes: list[dict] = []
        total = len(parsed)
        prev_choreo = ""
        prev_layout = ""
        prev_motion = ""
        prev_palette = ""
        used_choreos: set[str] = set()
        used_layouts: set[str] = set()
        eff_vs = "B3" if visual_style == "AUTO_MIX" else visual_style

        for i, item in enumerate(parsed):
            narration = str(item.get("narration", "")).strip()
            if not narration:
                continue
            sem_choreo, sem_score = _pick_choreography(
                narration, i, total, profile, seed, prev_choreo, used_choreos
            )
            llm_choreo = str(item.get("choreography", "")).strip()
            # Keep LLM choreography ONLY when valid, non-repeating, AND not overriding a strong semantic match
            if (
                llm_choreo in selectable_choreos
                and llm_choreo != prev_choreo
                and sem_score < 2
            ):
                choreo = llm_choreo
            else:
                choreo = sem_choreo
            prev_choreo = choreo
            used_choreos.add(choreo)

            layout_mode = str(item.get("layout_mode", "")).strip()
            if layout_mode not in LAYOUT_MODES or layout_mode == prev_layout:
                layout_mode = _pick_layout_mode(
                    choreo, i, total, profile, seed, prev_layout, used_layouts
                )
            prev_layout = layout_mode
            used_layouts.add(layout_mode)

            motion = _pick_motion_preset(choreo, profile, i, seed, prev_motion)
            prev_motion = motion
            accent = "" if (not accent_color and visual_style == "AUTO_MIX") else resolve_accent_color(
                accent_color, i, profile=profile, visual_style=eff_vs, seed=seed
            )
            sc = _build_dynamic_scene_fields(
                narration=narration,
                topic=topic,
                idx=i,
                total_scenes=total,
                choreo=choreo,
                layout_mode=layout_mode,
                accent=accent,
                visual_style=visual_style,
                profile=profile,
                motion_preset=motion,
                seed=seed,
                prev_palette_key=prev_palette,
            )
            prev_palette = str(sc.get("palette_key", ""))

            if item.get("scene_title"):
                sc["scene_title"] = _short_headline(str(item["scene_title"]).upper(), 24)
            if item.get("scene_subtitle"):
                sc["scene_subtitle"] = _short_phrase(str(item["scene_subtitle"]), 38)
            if item.get("stamp_word"):
                sc["stamp_word"] = _short_headline(str(item["stamp_word"]).upper(), 22)
            if item.get("beat_a"):
                ba = _short_phrase(str(item["beat_a"]), 34)
                sc["beat_a_label"] = ba
                sc["left_label"] = _short_headline(ba, 24)
            if item.get("beat_b"):
                bb = _short_phrase(str(item["beat_b"]), 34)
                sc["beat_b_label"] = bb
                sc["right_label"] = _short_headline(bb, 24)

            scenes.append(sc)

        return scenes
