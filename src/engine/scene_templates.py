"""
Scene Templates & Visual Reasoning Brain
========================================
Understands script sentences semantically and maps narrative beats to distinct,
non-repeating visual storyboards with multi-character interactions, visual
metaphors, contextual props, and StylePack-authentic environments.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from styles.style_packs import resolve_style_pack


# ---------------------------------------------------------------------------
# Rich Reusable Story Templates (18 distinct visual archetypes)
# ---------------------------------------------------------------------------

SCENE_TEMPLATES: dict[str, dict[str, Any]] = {
    "HOOK_QUESTION": {
        "keywords": ("have you ever", "did you know", "why do", "ever noticed", "what if", "imagine", "secret", "?"),
        "background": "STAGE",
        "camera": "ZOOM_IN",
        "emotion": "CONFUSED",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "CONFUSED",
                "start_x": 0.48,
                "end_x": 0.48,
                "y": 0.62,
                "scale": 1.48,
                "facing": "right",
                "emotion": "CONFUSED",
                "speaking": True,
            },
        ],
        "objects": [
            {"asset": "QUESTION_MARK", "x": 0.62, "y": 0.24, "width": 0.14, "height": 0.14, "motion": "FLOAT_UP"},
        ],
        "effects": ["VIGNETTE"],
    },
    "GIVE_AND_CONTROL": {
        "keywords": ("beggar", "charity", "give money", "spend", "dictate", "poor", "donate", "coin", "generosity", "give"),
        "background": "STREET",
        "camera": "MEDIUM",
        "emotion": "ANGRY",
        "transition": "SLIDE_LEFT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "GIVE",
                "start_x": 0.27,
                "end_x": 0.34,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "held_object": "MONEY",
                "emotion": "ANGRY",
                "speaking": True,
            },
            {
                "id": "PERSON_B",
                "action": "RECEIVE",
                "start_x": 0.70,
                "end_x": 0.66,
                "y": 0.62,
                "scale": 1.38,
                "facing": "left",
                "accessory": "cap",
                "emotion": "SAD",
            },
        ],
        "objects": [
            {"asset": "XMARK", "x": 0.73, "y": 0.36, "width": 0.10, "height": 0.10},
        ],
        "effects": ["EMPHASIS"],
    },
    "INVISIBLE_STRINGS": {
        "keywords": ("strings", "invisible", "expectation", "control", "manipulate", "puppet", "trap", "pressure", "rules"),
        "background": "ABSTRACT",
        "camera": "CLOSE",
        "emotion": "SAD",
        "transition": "ZOOM_IN",
        "characters": [
            {
                "id": "PERSON_B",
                "action": "STRUGGLE",
                "start_x": 0.50,
                "end_x": 0.50,
                "y": 0.62,
                "scale": 1.48,
                "facing": "right",
                "accessory": "cap",
                "emotion": "SAD",
            },
        ],
        "objects": [
            {"asset": "CONTROL_STRINGS", "x": 0.34, "y": 0.16, "width": 0.32, "height": 0.22},
            {"asset": "CHAINS", "x": 0.32, "y": 0.54, "width": 0.36, "height": 0.12},
        ],
        "effects": ["VIGNETTE"],
    },
    "PHONE_SCROLL_TRAP": {
        "keywords": ("phone", "scroll", "social media", "dopamine", "screen", "notification", "distract", "addict", "instagram", "noise", "endless"),
        "background": "HOME",
        "camera": "CLOSE",
        "emotion": "CONFUSED",
        "transition": "SLIDE_LEFT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "PHONE_CALL",
                "start_x": 0.42,
                "end_x": 0.42,
                "y": 0.62,
                "scale": 1.46,
                "facing": "right",
                "held_object": "PHONE",
                "emotion": "SAD",
            },
        ],
        "objects": [
            {"asset": "SOCIAL_MEDIA", "x": 0.60, "y": 0.28, "width": 0.18, "height": 0.18, "motion": "FLOAT_UP"},
            {"asset": "CLOCK", "x": 0.14, "y": 0.24, "width": 0.14, "height": 0.14},
        ],
        "effects": ["VIGNETTE"],
    },
    "OVERTHINKING_MAZE": {
        "keywords": ("stress", "anxious", "anxiety", "overthink", "worry", "panic", "fear", "mind", "psychology", "brain", "doubt", "judgment"),
        "background": "CITY",
        "camera": "PAN_RIGHT",
        "emotion": "CONFUSED",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "THINK",
                "start_x": 0.38,
                "end_x": 0.56,
                "y": 0.62,
                "scale": 1.46,
                "facing": "right",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "QUESTION_MARK", "x": 0.22, "y": 0.24, "width": 0.11, "height": 0.11, "motion": "FLOAT_UP"},
            {"asset": "EXCLAMATION", "x": 0.72, "y": 0.26, "width": 0.10, "height": 0.12},
        ],
        "effects": ["COOL"],
    },
    "EUREKA_CLARITY": {
        "keywords": ("clarity", "idea", "realize", "truth", "insight", "solution", "learn", "understand", "discover", "smart", "begins", "starts", "secret"),
        "background": "CLASSROOM",
        "camera": "ZOOM_IN",
        "emotion": "EXCITED",
        "transition": "ZOOM_IN",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "POINT_UP",
                "start_x": 0.46,
                "end_x": 0.48,
                "y": 0.62,
                "scale": 1.48,
                "facing": "right",
                "emotion": "HAPPY",
                "speaking": True,
            },
        ],
        "objects": [
            {"asset": "LIGHTBULB", "x": 0.43, "y": 0.18, "width": 0.15, "height": 0.17, "motion": "FLOAT_UP"},
            {"asset": "CHECK", "x": 0.72, "y": 0.34, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM"],
    },
    "LET_GO_FREEDOM": {
        "keywords": ("let go", "freely", "free", "kindness", "true kindness", "peace", "calm", "trust", "release", "relief", "happy"),
        "background": "PARK",
        "camera": "WIDE",
        "emotion": "HAPPY",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "WALK_RIGHT",
                "start_x": 0.24,
                "end_x": 0.44,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "HAPPY",
            },
            {
                "id": "PERSON_B",
                "action": "CELEBRATE",
                "start_x": 0.68,
                "end_x": 0.64,
                "y": 0.62,
                "scale": 1.42,
                "facing": "left",
                "accessory": "cap",
                "emotion": "HAPPY",
            },
        ],
        "objects": [
            {"asset": "HEART", "x": 0.44, "y": 0.24, "width": 0.12, "height": 0.12, "motion": "FLOAT_UP"},
            {"asset": "STAR", "x": 0.74, "y": 0.20, "width": 0.10, "height": 0.10},
        ],
        "effects": ["WARM"],
    },
    "WEALTH_GROWTH_CHART": {
        "keywords": ("money", "rich", "wealth", "invest", "saving", "save", "profit", "income", "budget", "finance", "success", "compound", "grow"),
        "background": "OFFICE",
        "camera": "MEDIUM",
        "emotion": "HAPPY",
        "transition": "SLIDE_LEFT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "PRESENT",
                "start_x": 0.28,
                "end_x": 0.32,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "held_object": "MONEY",
                "emotion": "HAPPY",
                "speaking": True,
            },
        ],
        "objects": [
            {"asset": "BAR_CHART", "x": 0.54, "y": 0.32, "width": 0.30, "height": 0.24},
            {"asset": "ARROW", "x": 0.52, "y": 0.22, "width": 0.24, "height": 0.08},
            {"asset": "COIN", "x": 0.78, "y": 0.18, "width": 0.11, "height": 0.11},
        ],
        "effects": [],
    },
    "TECH_DASHBOARD": {
        "keywords": ("ai", "app", "software", "algorithm", "tech", "code", "tool", "model", "digital", "system", "data", "future", "automation"),
        "background": "OFFICE",
        "camera": "MEDIUM",
        "emotion": "EXCITED",
        "transition": "ZOOM_IN",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "POINT_RIGHT",
                "start_x": 0.28,
                "end_x": 0.32,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "emotion": "HAPPY",
                "speaking": True,
            },
        ],
        "objects": [
            {"asset": "GLASS_CARD", "x": 0.50, "y": 0.25, "width": 0.34, "height": 0.26},
            {"asset": "LAPTOP", "x": 0.56, "y": 0.54, "width": 0.18, "height": 0.14},
        ],
        "effects": [],
    },
    "CONFLICT_DEBATE": {
        "keywords": ("argue", "fight", "conflict", "blame", "angry", "toxic", "society", "judge", "debate", "disagree", "shout", "against", "ego"),
        "background": "CITY",
        "camera": "MEDIUM",
        "emotion": "ANGRY",
        "transition": "CUT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "ARGUE",
                "start_x": 0.28,
                "end_x": 0.34,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "ANGRY",
                "speaking": True,
            },
            {
                "id": "PERSON_B",
                "action": "SHOUT",
                "start_x": 0.72,
                "end_x": 0.66,
                "y": 0.62,
                "scale": 1.42,
                "facing": "left",
                "accessory": "cap",
                "emotion": "ANGRY",
            },
        ],
        "objects": [
            {"asset": "EXCLAMATION", "x": 0.46, "y": 0.24, "width": 0.10, "height": 0.14},
        ],
        "effects": ["EMPHASIS"],
    },
    "WORK_DEADLINE_GRIND": {
        "keywords": ("work", "focus", "habit", "procrastinat", "lazy", "deadline", "goal", "daily", "routine", "laptop", "study", "effort", "build"),
        "background": "OFFICE",
        "camera": "PAN_LEFT",
        "emotion": "NEUTRAL",
        "transition": "SLIDE_RIGHT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "SIT",
                "start_x": 0.34,
                "end_x": 0.34,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "NEUTRAL",
            },
        ],
        "objects": [
            {"asset": "TABLE", "x": 0.48, "y": 0.56, "width": 0.28, "height": 0.16},
            {"asset": "LAPTOP", "x": 0.54, "y": 0.45, "width": 0.14, "height": 0.12},
            {"asset": "CLOCK", "x": 0.74, "y": 0.22, "width": 0.13, "height": 0.13},
        ],
        "effects": [],
    },
    "COMPARISON_SPLIT": {
        "keywords": ("instead", "versus", "vs", "difference", "wrong", "right", "rather", "surface", "miss", "actually", "contrast"),
        "background": "ABSTRACT",
        "camera": "WIDE",
        "emotion": "NEUTRAL",
        "transition": "SLIDE_LEFT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "SHRUG",
                "start_x": 0.28,
                "end_x": 0.28,
                "y": 0.62,
                "scale": 1.40,
                "facing": "right",
                "emotion": "CONFUSED",
            },
            {
                "id": "PERSON_B",
                "action": "POINT_LEFT",
                "start_x": 0.72,
                "end_x": 0.72,
                "y": 0.62,
                "scale": 1.40,
                "facing": "left",
                "accessory": "cap",
                "emotion": "HAPPY",
                "speaking": True,
            },
        ],
        "objects": [
            {"asset": "XMARK", "x": 0.22, "y": 0.28, "width": 0.10, "height": 0.10},
            {"asset": "CHECK", "x": 0.68, "y": 0.28, "width": 0.10, "height": 0.10},
        ],
        "effects": [],
    },
    "TEAMWORK_EMPATHY": {
        "keywords": ("friend", "family", "empathy", "respect", "relationship", "together", "help", "share", "support", "people", "care"),
        "background": "HOME",
        "camera": "MEDIUM",
        "emotion": "HAPPY",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "WALK_RIGHT",
                "start_x": 0.26,
                "end_x": 0.38,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "HAPPY",
            },
            {
                "id": "PERSON_B",
                "action": "WAVE",
                "start_x": 0.68,
                "end_x": 0.62,
                "y": 0.62,
                "scale": 1.42,
                "facing": "left",
                "accessory": "cap",
                "emotion": "HAPPY",
            },
        ],
        "objects": [
            {"asset": "HEART", "x": 0.44, "y": 0.26, "width": 0.12, "height": 0.12, "motion": "FLOAT_UP"},
        ],
        "effects": ["WARM"],
    },
    "PROGRESS_JOURNEY": {
        "keywords": ("walk", "start", "journey", "step", "future", "life", "move", "change", "victory", "win", "today", "outcome"),
        "background": "STREET",
        "camera": "PAN_RIGHT",
        "emotion": "EXCITED",
        "transition": "ZOOM_OUT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "WALK_RIGHT",
                "start_x": 0.20,
                "end_x": 0.72,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "HAPPY",
            },
        ],
        "objects": [
            {"asset": "STAR", "x": 0.76, "y": 0.24, "width": 0.12, "height": 0.12},
            {"asset": "ARROW", "x": 0.36, "y": 0.28, "width": 0.28, "height": 0.08},
        ],
        "effects": [],
    },
    "PREHISTORIC_FIRE_HUNT": {
        "keywords": ("cave", "caveman", "fire", "stone", "tribe", "hunt", "spear", "mammoth", "ancient human", "ancestor", "instinct"),
        "background": "CAVE",
        "camera": "MEDIUM",
        "emotion": "SURPRISED",
        "transition": "CUT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "HUNT_SPEAR",
                "start_x": 0.30,
                "end_x": 0.36,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "held_object": "SPEAR",
                "emotion": "SURPRISED",
            },
            {
                "id": "PERSON_B",
                "action": "WARM_FIRE",
                "start_x": 0.72,
                "end_x": 0.70,
                "y": 0.62,
                "scale": 1.38,
                "facing": "left",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "CAMPFIRE", "x": 0.44, "y": 0.56, "width": 0.15, "height": 0.16},
        ],
        "effects": ["WARM"],
    },
    "COZY_CAFE_REFLECT": {
        "keywords": ("coffee", "cafe", "morning", "quiet", "station", "train", "memory", "gentle", "breathe", "slow", "evening", "warmth"),
        "background": "CAFE",
        "camera": "ZOOM_IN",
        "emotion": "HAPPY",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "SIT",
                "start_x": 0.36,
                "end_x": 0.36,
                "y": 0.62,
                "scale": 1.42,
                "facing": "right",
                "emotion": "HAPPY",
            },
        ],
        "objects": [
            {"asset": "TABLE", "x": 0.50, "y": 0.56, "width": 0.24, "height": 0.15},
            {"asset": "COFFEE_CUP", "x": 0.56, "y": 0.49, "width": 0.11, "height": 0.11},
        ],
        "effects": ["WARM"],
    },
    "HISTORICAL_EDICT": {
        "keywords": ("history", "king", "emperor", "empire", "century", "royal", "kingdom", "crown", "ancient", "scroll", "rome", "medieval", "law", "samurai", "castle", "warrior", "clan", "honor", "decree"),
        "background": "CASTLE",
        "camera": "PAN_RIGHT",
        "emotion": "NEUTRAL",
        "transition": "SLIDE_RIGHT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "READ_SCROLL",
                "start_x": 0.34,
                "end_x": 0.40,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "held_object": "SCROLL",
                "emotion": "SURPRISED",
                "speaking": True,
            },
            {
                "id": "PERSON_B",
                "action": "POINT_LEFT",
                "start_x": 0.70,
                "end_x": 0.66,
                "y": 0.62,
                "scale": 1.42,
                "facing": "left",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "CROWN", "x": 0.45, "y": 0.22, "width": 0.14, "height": 0.11},
        ],
        "effects": [],
    },
    "SURVIVAL_DANGER": {
        "keywords": ("survive", "survival", "danger", "storm", "alone", "darkness", "warning", "countdown", "panic", "escape", "seconds", "risk", "threat", "shadow"),
        "background": "MOUNTAIN",
        "camera": "CLOSE",
        "emotion": "SURPRISED",
        "transition": "ZOOM_IN",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "SNEAK",
                "start_x": 0.32,
                "end_x": 0.52,
                "y": 0.62,
                "scale": 1.46,
                "facing": "right",
                "held_object": "LANTERN",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "WARNING", "x": 0.68, "y": 0.22, "width": 0.14, "height": 0.14},
            {"asset": "CLOCK", "x": 0.16, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["VIGNETTE"],
    },
    # ---- New diverse templates ----
    "MIRROR_REFLECTION": {
        "keywords": ("mirror", "reflect", "honest", "character", "alone", "dark", "unseen", "nobody", "real", "true self", "behave", "integrity", "shadow"),
        "background": "HOME",
        "camera": "CLOSE",
        "emotion": "CONFUSED",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "THINK",
                "start_x": 0.44,
                "end_x": 0.46,
                "y": 0.62,
                "scale": 1.50,
                "facing": "right",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "QUESTION_MARK", "x": 0.64, "y": 0.22, "width": 0.12, "height": 0.14, "motion": "FLOAT_UP"},
        ],
        "effects": ["VIGNETTE", "COOL"],
    },
    "CROWD_PRESSURE": {
        "keywords": ("crowd", "public", "judge", "watch", "seen", "social", "approval", "peers", "expectation", "society", "image"),
        "background": "CITY",
        "camera": "WIDE",
        "emotion": "CONFUSED",
        "transition": "SLIDE_LEFT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "COWER",
                "start_x": 0.46,
                "end_x": 0.46,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "emotion": "SAD",
            },
            {
                "id": "PERSON_B",
                "action": "POINT",
                "start_x": 0.22,
                "end_x": 0.26,
                "y": 0.62,
                "scale": 1.36,
                "facing": "right",
                "emotion": "ANGRY",
            },
            {
                "id": "PERSON_C",
                "action": "SHOUT",
                "start_x": 0.74,
                "end_x": 0.70,
                "y": 0.62,
                "scale": 1.36,
                "facing": "left",
                "emotion": "ANGRY",
            },
        ],
        "objects": [
            {"asset": "EXCLAMATION", "x": 0.44, "y": 0.22, "width": 0.10, "height": 0.14},
        ],
        "effects": ["VIGNETTE"],
    },
    "TEACHER_LESSON": {
        "keywords": ("teach", "lesson", "class", "school", "education", "study", "learn", "student", "knowledge", "wisdom", "explain", "present"),
        "background": "CLASSROOM",
        "camera": "PAN_RIGHT",
        "emotion": "HAPPY",
        "transition": "SLIDE_RIGHT",
        "characters": [
            {
                "id": "TEACHER",
                "action": "PRESENT",
                "start_x": 0.26,
                "end_x": 0.30,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "emotion": "HAPPY",
                "speaking": True,
            },
            {
                "id": "PERSON_A",
                "action": "READ",
                "start_x": 0.68,
                "end_x": 0.68,
                "y": 0.62,
                "scale": 1.38,
                "facing": "left",
                "emotion": "NEUTRAL",
            },
        ],
        "objects": [
            {"asset": "BOOK", "x": 0.56, "y": 0.26, "width": 0.14, "height": 0.14},
            {"asset": "LIGHTBULB", "x": 0.72, "y": 0.20, "width": 0.11, "height": 0.13, "motion": "FLOAT_UP"},
        ],
        "effects": ["WARM"],
    },
    "MORNING_ROUTINE": {
        "keywords": ("morning", "wake", "daily", "routine", "habit", "every day", "start", "begin", "rise", "alarm", "fresh"),
        "background": "HOME",
        "camera": "MEDIUM",
        "emotion": "NEUTRAL",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "STAND",
                "start_x": 0.40,
                "end_x": 0.44,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "emotion": "NEUTRAL",
            },
        ],
        "objects": [
            {"asset": "CLOCK", "x": 0.68, "y": 0.24, "width": 0.14, "height": 0.14},
            {"asset": "COFFEE_CUP", "x": 0.24, "y": 0.26, "width": 0.11, "height": 0.11},
        ],
        "effects": ["WARM"],
    },
    "CROSSROADS_CHOICE": {
        "keywords": ("choose", "choice", "decide", "decision", "path", "direction", "option", "dilemma", "question", "turning point", "moment"),
        "background": "STREET",
        "camera": "WIDE",
        "emotion": "CONFUSED",
        "transition": "ZOOM_OUT",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "CONFUSED",
                "start_x": 0.46,
                "end_x": 0.48,
                "y": 0.62,
                "scale": 1.46,
                "facing": "right",
                "emotion": "CONFUSED",
            },
        ],
        "objects": [
            {"asset": "ARROW", "x": 0.24, "y": 0.30, "width": 0.18, "height": 0.08},
            {"asset": "ARROW", "x": 0.60, "y": 0.30, "width": 0.18, "height": 0.08},
            {"asset": "QUESTION_MARK", "x": 0.44, "y": 0.20, "width": 0.12, "height": 0.14, "motion": "FLOAT_UP"},
        ],
        "effects": [],
    },
    "CELEBRATION_VICTORY": {
        "keywords": ("success", "achieve", "accomplish", "win", "done", "victory", "result", "proud", "earned", "congratulation", "reward", "goal reached"),
        "background": "STAGE",
        "camera": "ZOOM_IN",
        "emotion": "EXCITED",
        "transition": "ZOOM_IN",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "CELEBRATE",
                "start_x": 0.36,
                "end_x": 0.40,
                "y": 0.62,
                "scale": 1.48,
                "facing": "right",
                "emotion": "HAPPY",
            },
            {
                "id": "PERSON_B",
                "action": "WAVE",
                "start_x": 0.66,
                "end_x": 0.62,
                "y": 0.62,
                "scale": 1.44,
                "facing": "left",
                "emotion": "HAPPY",
            },
        ],
        "objects": [
            {"asset": "TROPHY", "x": 0.47, "y": 0.24, "width": 0.14, "height": 0.16},
            {"asset": "STAR", "x": 0.22, "y": 0.22, "width": 0.10, "height": 0.10},
            {"asset": "STAR", "x": 0.72, "y": 0.20, "width": 0.10, "height": 0.10},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "READING_DISCOVERY": {
        "keywords": ("read", "book", "library", "knowledge", "research", "discover", "find", "document", "study", "information", "article", "text"),
        "background": "LIBRARY",
        "camera": "PAN_LEFT",
        "emotion": "NEUTRAL",
        "transition": "FADE",
        "characters": [
            {
                "id": "PERSON_A",
                "action": "READ",
                "start_x": 0.38,
                "end_x": 0.38,
                "y": 0.62,
                "scale": 1.44,
                "facing": "right",
                "held_object": "BOOK",
                "emotion": "NEUTRAL",
            },
        ],
        "objects": [
            {"asset": "BOOK", "x": 0.62, "y": 0.28, "width": 0.14, "height": 0.14},
            {"asset": "LIGHTBULB", "x": 0.68, "y": 0.20, "width": 0.11, "height": 0.12, "motion": "FLOAT_UP"},
        ],
        "effects": [],
    },
}


# Entity keyword -> automatic prop injection if mentioned in sentence
_NOUN_TO_PROP: dict[str, str] = {
    "car": "CAR",
    "drive": "CAR",
    "house": "HOUSE",
    "home": "HOUSE",
    "phone": "PHONE",
    "mobile": "PHONE",
    "money": "MONEY",
    "cash": "MONEY",
    "coin": "COIN",
    "dollar": "MONEY",
    "book": "BOOK",
    "read": "BOOK",
    "scroll": "SCROLL",
    "laptop": "LAPTOP",
    "computer": "LAPTOP",
    "time": "CLOCK",
    "clock": "CLOCK",
    "hour": "CLOCK",
    "idea": "LIGHTBULB",
    "heart": "HEART",
    "love": "HEART",
    "tree": "TREE",
    "chart": "BAR_CHART",
    "graph": "LINE_CHART",
    "trophy": "TROPHY",
    "goal": "STAR",
    "coffee": "COFFEE_CUP",
    "fire": "CAMPFIRE",
    "spear": "SPEAR",
    "lantern": "LANTERN",
    "king": "CROWN",
    "crown": "CROWN",
}

# Preferred fallback templates biased gently per StylePack aesthetic when script is neutral
_STYLE_TEMPLATE_AFFINITY: dict[str, tuple[str, ...]] = {
    "a1_classic_bw": ("HOOK_QUESTION", "COMPARISON_SPLIT", "EUREKA_CLARITY", "MIRROR_REFLECTION"),
    "a2_modern_pop": ("TECH_DASHBOARD", "WEALTH_GROWTH_CHART", "EUREKA_CLARITY", "CELEBRATION_VICTORY"),
    "a3_prehistoric_cave": ("PREHISTORIC_FIRE_HUNT", "GIVE_AND_CONTROL", "CONFLICT_DEBATE"),
    "a4_cozy_storytelling": ("COZY_CAFE_REFLECT", "TEAMWORK_EMPATHY", "LET_GO_FREEDOM", "MORNING_ROUTINE"),
    "a5_historical_cartoon": ("HISTORICAL_EDICT", "CONFLICT_DEBATE", "GIVE_AND_CONTROL", "READING_DISCOVERY"),
    "a6_amber_noir": ("OVERTHINKING_MAZE", "INVISIBLE_STRINGS", "SURVIVAL_DANGER", "MIRROR_REFLECTION"),
    "b1_minimal_line_art": ("EUREKA_CLARITY", "COMPARISON_SPLIT", "PROGRESS_JOURNEY", "CROSSROADS_CHOICE"),
    "b2_colorful_hand_drawn": ("TEAMWORK_EMPATHY", "LET_GO_FREEDOM", "PROGRESS_JOURNEY", "CELEBRATION_VICTORY"),
    "b3_retro_tv": ("HOOK_QUESTION", "OVERTHINKING_MAZE", "EUREKA_CLARITY", "CROWD_PRESSURE"),
    "b4_survival_thriller": ("SURVIVAL_DANGER", "INVISIBLE_STRINGS", "PROGRESS_JOURNEY", "MIRROR_REFLECTION"),
    "b5_character_explainer": ("WEALTH_GROWTH_CHART", "TECH_DASHBOARD", "COMPARISON_SPLIT", "TEACHER_LESSON"),
}


def _derive_context_bubble(narration: str, template_name: str) -> tuple[str, str]:
    """
    Extract speech or thought bubble ONLY if the narration explicitly contains quotes.
    Returns ("", "") when there is no quotation, preventing random canned bubbles.
    Created by Atharv Hatwar.
    """
    match = re.search(r'["\u201c\u201d]([^"\u201c\u201d]{2,40})["\u201c\u201d]', narration)
    if not match:
        match = re.search(r"['\u2018\u2019]([^'\u2018\u2019]{2,30})['\u2018\u2019]", narration)
    if match:
        text = match.group(1).strip()
        lower = narration.lower()
        if any(w in lower for w in ("thought", "wondered", "pondered", "inside his head", "inside her head", "secretly")):
            return ("", text)
        return (text, "")
    return ("", "")


def select_diverse_scene_template(
    narration: str,
    scene_idx: int = 0,
    total_scenes: int = 1,
    prev_template: Optional[str] = None,
    prev_bg: Optional[str] = None,
    used_templates: Optional[set[str]] = None,
    style_id: str = "a1_classic_bw",
) -> tuple[str, dict[str, Any]]:
    """
    Semantically score THIS narration beat against SCENE_TEMPLATES while factoring in
    narrative arc position, active StylePack affinity, and strong anti-repetition.
    """
    text = narration.lower().strip()
    used = used_templates or set()
    pack, _sp = resolve_style_pack(style_id)
    affinity = _STYLE_TEMPLATE_AFFINITY.get(pack.id, ())

    scores: list[tuple[float, str]] = []
    for name, tpl in SCENE_TEMPLATES.items():
        score = 0.0
        for kw in tpl["keywords"]:
            if kw == "?":
                if "?" in text:
                    score += 3.2
            elif re.search(rf"\b{re.escape(kw)}", text):
                score += 4.2 if " " in kw else 2.6

        if name in affinity:
            score += 1.4

        # Narrative arc nudges
        if scene_idx == 0 and name == "HOOK_QUESTION" and ("?" in text or "ever" in text or "why" in text or "what if" in text):
            score += 4.0
        if scene_idx == total_scenes - 1 and total_scenes > 2 and name in ("EUREKA_CLARITY", "LET_GO_FREEDOM", "PROGRESS_JOURNEY"):
            score += 1.8

        # Strong anti-repetition penalties so consecutive scenes look distinct
        if name == prev_template:
            score -= 100.0
        elif name in used:
            # If we still have unused templates available, heavily penalize repeating
            remaining_unused = len(SCENE_TEMPLATES) - len(used)
            score -= 25.0 if remaining_unused > 2 else 12.0
        if tpl["background"] == prev_bg:
            score -= 8.0

        scores.append((score, name))

    scores.sort(key=lambda x: x[0], reverse=True)
    best_name = scores[0][1]
    tpl = SCENE_TEMPLATES[best_name]

    # Pick background matching StylePack preference if the template background clashes (e.g. OFFICE in Cave)
    bg = tpl["background"]
    if pack.id == "a3_prehistoric_cave" and bg in ("OFFICE", "CITY", "CLASSROOM"):
        bg = "CAVE"
    elif pack.id == "a5_historical_cartoon" and bg == "OFFICE":
        bg = "CASTLE"
    elif pack.id == "b4_survival_thriller" and bg in ("OFFICE", "PARK", "CLASSROOM"):
        bg = "MOUNTAIN"
    elif prev_bg and bg == prev_bg and pack.preferred_backgrounds:
        for alt_bg in pack.preferred_backgrounds:
            if alt_bg != prev_bg:
                bg = alt_bg
                break

    chars = [dict(c) for c in tpl["characters"]]
    # Attach concise contextual speech/thought ONLY when relevant
    sp_txt, th_txt = _derive_context_bubble(narration, best_name)
    if chars:
        if sp_txt and not chars[0].get("speech"):
            chars[0]["speech"] = sp_txt
        elif th_txt and not chars[0].get("thought"):
            chars[0]["thought"] = th_txt

    out: dict[str, Any] = {
        "template": best_name,
        "background": bg,
        "camera": tpl["camera"],
        "emotion": tpl["emotion"],
        "transition": pack.preferred_transition if best_name not in ("SURVIVAL_DANGER",) else tpl["transition"],
        "characters": chars,
        "objects": [dict(o) for o in tpl["objects"]],
        "effects": list(tpl["effects"]),
    }

    # Inject any explicit sentence-mentioned prop into a FREE slot (avoid overlap with existing props/actors)
    _GROUND_PROPS = {"CAMPFIRE", "CAR", "HOUSE", "TREE", "TABLE", "CHAIR", "COFFEE_CUP"}
    existing_assets = {o.get("asset", "").upper() for o in out["objects"]} | {
        c.get("held_object", "").upper() for c in out["characters"]
    }
    for word, asset in _NOUN_TO_PROP.items():
        if re.search(rf"\b{re.escape(word)}", text) and asset not in existing_assets:
            if len(out["objects"]) < 3:
                candidates = (
                    [(0.45, 0.56), (0.16, 0.56), (0.80, 0.56)]
                    if asset in _GROUND_PROPS
                    else [(0.45, 0.24), (0.20, 0.26), (0.76, 0.26)]
                )
                chosen = candidates[0]
                for cx, cy in candidates:
                    too_close_obj = any(abs(cx - o.get("x", 0)) < 0.14 and abs(cy - o.get("y", 0)) < 0.14 for o in out["objects"])
                    too_close_char = (asset in _GROUND_PROPS) and any(abs(cx - c.get("start_x", 0)) < 0.14 for c in out["characters"])
                    if not too_close_obj and not too_close_char:
                        chosen = (cx, cy)
                        break
                out["objects"].append({"asset": asset, "x": chosen[0], "y": chosen[1], "width": 0.14, "height": 0.14})
                existing_assets.add(asset)

    # Adapt modern OFFICE laptops/glass UI in Cave/Historical styles into native props unless explicitly spoken
    if pack.id == "a3_prehistoric_cave" and "laptop" not in text:
        out["objects"] = [o for o in out["objects"] if o.get("asset") not in ("LAPTOP", "TABLE", "GLASS_CARD")]
        if "CAMPFIRE" not in existing_assets:
            out["objects"].append({"asset": "CAMPFIRE", "x": 0.44, "y": 0.56, "width": 0.16, "height": 0.16})
    elif pack.id == "a5_historical_cartoon" and "laptop" not in text:
        out["objects"] = [o for o in out["objects"] if o.get("asset") not in ("LAPTOP", "GLASS_CARD")]
        if "SCROLL" not in existing_assets and len(out["objects"]) < 2:
            out["objects"].append({"asset": "SCROLL", "x": 0.68, "y": 0.25, "width": 0.14, "height": 0.14})

    return best_name, out


def match_scene_template(narration: str, topic: str = "", style_id: str = "a1_classic_bw") -> tuple[str, dict[str, Any]]:
    return select_diverse_scene_template(narration=narration, style_id=style_id)


def normalize_scene_for_composer(scene: dict[str, Any], style_id: str = "a1_classic_bw") -> dict[str, Any]:
    """Ensure any scene dict (from LLM JSON or templates) is 100% ready for SceneComposer."""
    normalized = dict(scene)
    narration = str(scene.get("narration", ""))
    raw_chars = scene.get("characters", ["PERSON_A"])
    action = str(scene.get("action", "STAND")).upper()
    emotion = str(scene.get("emotion", "NEUTRAL")).upper()
    effects = [str(e).upper() for e in scene.get("effects", [])]
    raw_objs = scene.get("objects", [])

    pack, _sp = resolve_style_pack(style_id)

    if raw_chars and all(isinstance(c, str) for c in raw_chars):
        _, tpl = select_diverse_scene_template(narration, style_id=pack.id)
        tpl_chars = tpl["characters"]
        chars_out: list[dict[str, Any]] = []
        n = max(1, len(raw_chars))
        for idx, cid in enumerate(raw_chars[:3]):
            if idx < len(tpl_chars) and len(raw_chars) == len(tpl_chars):
                cdict = dict(tpl_chars[idx])
                cdict["id"] = cid
                if action not in ("STAND", ""):
                    cdict["action"] = action
                if emotion not in ("NEUTRAL", ""):
                    cdict["emotion"] = emotion
            else:
                if n == 1:
                    is_trav = any(k in action for k in ("WALK", "RUN", "SNEAK", "SPRINT", "MOVE"))
                    facing = "left" if "LEFT" in action else "right"
                    if is_trav:
                        sx, ex = (0.76, 0.20) if facing == "left" else (0.20, 0.76)
                    elif action in ("PRESENT", "POINT_RIGHT", "WAVE", "EXPLAIN"):
                        sx, ex = (0.36, 0.48)
                    elif action in ("JUMP", "CELEBRATE", "TRIUMPH_FIST"):
                        sx, ex = (0.42, 0.50)
                    else:
                        # Natural deliberate pacing step during monologue delivery
                        sx, ex = (0.42, 0.50) if facing == "right" else (0.58, 0.50)
                    act_c = action
                    emo_c = emotion
                    acc_c = "cap" if pack.id != "a3_prehistoric_cave" else "caveman_hair"
                else:
                    if idx == 0:
                        # Speaker steps forward toward Person B with purposeful engagement
                        sx, ex = 0.20, 0.34
                        facing = "right"
                    elif idx == 1:
                        # Listener stands grounded and reacts
                        sx, ex = 0.74, 0.68
                        facing = "left"
                    else:
                        sx, ex = 0.84, 0.82
                        facing = "left"
                    acc_c = ("cap" if idx == 0 else "glasses") if pack.id != "a3_prehistoric_cave" else "none"
                    if idx == 0:
                        act_c = action
                        emo_c = emotion
                    else:
                        # Contextual complementary counter-acting for Person B
                        if action == "GIVE":
                            act_c = "RECEIVE"
                            emo_c = "HAPPY" if emotion != "ANGRY" else "CONFUSED"
                        elif action in ("ARGUE", "SHOUT", "FIGHT"):
                            act_c = "STOP" if emotion == "ANGRY" else "CONFUSED"
                            emo_c = "CONFUSED"
                        elif action in ("PRESENT", "POINT_RIGHT"):
                            act_c = "THINK"
                            emo_c = "HAPPY" if emotion in ("HAPPY", "EXCITED") else "NEUTRAL"
                        elif action == "CELEBRATE":
                            act_c = "WAVE"
                            emo_c = "HAPPY"
                        elif action in ("SAD", "COWER", "CRY"):
                            act_c = "STAND"
                            emo_c = "HAPPY"
                        elif action == "SHRUG":
                            act_c = "POINT_LEFT"
                            emo_c = "HAPPY"
                        else:
                            act_c = "THINK" if "?" in narration else "STAND"
                            emo_c = "NEUTRAL"

                cdict = {
                    "id": cid,
                    "action": act_c,
                    "start_x": sx,
                    "end_x": ex,
                    "y": 0.62,
                    "scale": 1.40,
                    "facing": facing,
                    "emotion": emo_c,
                    "accessory": acc_c,
                    "speaking": idx == 0 and (action in ("PRESENT", "ARGUE", "SHOUT", "GIVE", "WAVE") or "SPEECH_BUBBLE" in effects),
                }
            if idx == 0 and ("SPEECH_BUBBLE" in effects or "THOUGHT_BUBBLE" in effects):
                sp_t, th_t = _derive_context_bubble(narration, "")
                if sp_t and not cdict.get("speech"):
                    cdict["speech"] = sp_t
                elif th_t and not cdict.get("thought"):
                    cdict["thought"] = th_t
            chars_out.append(cdict)
        normalized["characters"] = chars_out
    elif isinstance(raw_chars, list):
        normalized["characters"] = [dict(c) for c in raw_chars if isinstance(c, dict)]

    if raw_objs and all(isinstance(o, str) for o in raw_objs):
        objs_out: list[dict[str, Any]] = []
        slots = [(0.68, 0.34), (0.18, 0.28), (0.46, 0.20), (0.74, 0.50)]
        for idx, asset_name in enumerate(raw_objs[:4]):
            ox, oy = slots[idx % len(slots)]
            objs_out.append({
                "asset": asset_name.upper(),
                "x": ox,
                "y": oy,
                "width": 0.14,
                "height": 0.14,
            })
        normalized["objects"] = objs_out
    elif isinstance(raw_objs, list):
        normalized["objects"] = [dict(o) for o in raw_objs if isinstance(o, dict)]

    trans = str(normalized.get("transition", normalized.get("transition_in", pack.preferred_transition))).upper()
    normalized["transition_in"] = trans
    normalized.setdefault("camera", pack.preferred_camera)
    normalized.setdefault("background", pack.default_background)
    return normalized
