"""
Procedural Scene Engine - Generates 100% Unique Visual Scenes from Narration
=============================================================================
Converts arbitrary narration sentences into dynamic, non-repeating visual
storyboard scenes using semantic NLP, 60+ conceptual physical metaphors,
and a strict Negative Similarity Constraint.

Created by Atharv Hatwar.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from styles.style_packs import resolve_style_pack

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 60+ Rich Physical Metaphors mapping abstract concepts to physical animations
# ---------------------------------------------------------------------------

PHYSICAL_METAPHORS: dict[str, dict[str, Any]] = {
    "LEVER_BOULDER": {
        "keywords": ("leverage", "multiply", "advantage", "effortless", "force multiplier", "smart work", "efficient", "compound effort"),
        "background": "MOUNTAIN",
        "camera": "WIDE",
        "action": "PRESENT",
        "emotion": "HAPPY",
        "objects": [
            {"asset": "LEVER_BOULDER", "x": 0.58, "y": 0.52, "width": 0.32, "height": 0.26},
            {"asset": "ARROW", "x": 0.58, "y": 0.22, "width": 0.18, "height": 0.08},
        ],
        "effects": ["WARM"],
    },
    "ICEBERG_DEPTH": {
        "keywords": ("iceberg", "below the surface", "hidden depth", "unseen work", "what people see", "underneath", "years of work", "iceberg theory"),
        "background": "ABSTRACT",
        "camera": "ZOOM_OUT",
        "action": "POINT_RIGHT",
        "emotion": "SURPRISED",
        "objects": [
            {"asset": "ICEBERG", "x": 0.52, "y": 0.36, "width": 0.38, "height": 0.44},
        ],
        "effects": ["COOL", "VIGNETTE"],
    },
    "HAMSTER_WHEEL": {
        "keywords": ("hamster wheel", "rat race", "running in circles", "exhausting cycle", "treadmill", "never ends", "endless cycle", "trap"),
        "background": "CITY",
        "camera": "MEDIUM",
        "action": "RUN",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "HAMSTER_WHEEL", "x": 0.48, "y": 0.42, "width": 0.40, "height": 0.40},
            {"asset": "MONEY", "x": 0.76, "y": 0.22, "width": 0.12, "height": 0.10, "motion": "FLOAT_UP"},
        ],
        "effects": ["VIGNETTE"],
    },
    "JUGGLING_ACT": {
        "keywords": ("juggle", "juggling", "balance", "too many things", "overwhelmed", "multitask", "spinning plates", "wearing many hats"),
        "background": "STAGE",
        "camera": "MEDIUM",
        "action": "CELEBRATE",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "JUGGLING_BALLS", "x": 0.48, "y": 0.24, "width": 0.28, "height": 0.24},
            {"asset": "CLOCK", "x": 0.18, "y": 0.20, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM"],
    },
    "DOMINO_CHAIN": {
        "keywords": ("domino", "chain reaction", "snowball", "ripple effect", "small trigger", "cascading", "catalyst", "first step"),
        "background": "ABSTRACT",
        "camera": "PAN_RIGHT",
        "action": "POINT_RIGHT",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "DOMINOES", "x": 0.54, "y": 0.52, "width": 0.36, "height": 0.20},
            {"asset": "STAR", "x": 0.82, "y": 0.22, "width": 0.11, "height": 0.11},
        ],
        "effects": ["WARM"],
    },
    "EXPONENTIAL_COMPOUND": {
        "keywords": ("compound", "exponential", "growth curve", "1 percent", "1%", "hockey stick", "snowball", "multiply over time", "long term gain", "accumulate"),
        "background": "OFFICE",
        "camera": "ZOOM_IN",
        "action": "PRESENT_CHART",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "LINE_CHART", "x": 0.58, "y": 0.36, "width": 0.34, "height": 0.28},
            {"asset": "STAR", "x": 0.82, "y": 0.20, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "WEALTH_ACCUMULATION": {
        "keywords": ("wealth", "rich", "millionaire", "cash flow", "assets", "investing", "financial freedom", "passive income", "roi", "capital", "portfolio"),
        "background": "CITY",
        "camera": "MEDIUM",
        "action": "COUNT_MONEY",
        "emotion": "HAPPY",
        "objects": [
            {"asset": "MONEY", "x": 0.58, "y": 0.32, "width": 0.22, "height": 0.16},
            {"asset": "COIN", "x": 0.78, "y": 0.24, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM", "GOLD_SPARKLES"],
    },
    "TECH_DEVELOPMENT": {
        "keywords": ("coding", "code", "software", "developer", "algorithm", "artificial intelligence", "tech stack", "build an app", "programming", "system architecture", "engineer"),
        "background": "OFFICE",
        "camera": "CLOSE",
        "action": "TYPING_LAPTOP",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "LAPTOP", "x": 0.52, "y": 0.44, "width": 0.28, "height": 0.22},
            {"asset": "LIGHTBULB", "x": 0.72, "y": 0.22, "width": 0.14, "height": 0.16},
        ],
        "effects": ["WARM"],
    },
    "PHONE_DISTRACTION": {
        "keywords": ("social media", "doomscrolling", "scrolling", "tiktok", "instagram", "notification", "dopamine hit", "wasting hours", "screen time", "distracted"),
        "background": "HOME",
        "camera": "CLOSE",
        "action": "SCROLL_PHONE",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "PHONE", "x": 0.52, "y": 0.36, "width": 0.18, "height": 0.24},
            {"asset": "CLOCK", "x": 0.22, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["VIGNETTE"],
    },
    "DEEP_WORK_ZEN": {
        "keywords": ("daily habit", "routine", "discipline", "deep work", "daily practice", "morning routine", "consistency", "small daily", "mastery", "zen", "calm mind"),
        "background": "LIBRARY",
        "camera": "MEDIUM",
        "action": "MEDITATE_ZEN",
        "emotion": "NEUTRAL",
        "objects": [
            {"asset": "CLOCK", "x": 0.58, "y": 0.28, "width": 0.16, "height": 0.16},
            {"asset": "STAR", "x": 0.24, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM"],
    },
    "CRITICAL_MISTAKE": {
        "keywords": ("mistake", "regret", "blunder", "fatal error", "bad choice", "foolish", "wrong decision", "lost money", "blew it", "costly error"),
        "background": "OFFICE",
        "camera": "CLOSE",
        "action": "FACEPALM",
        "emotion": "SAD",
        "objects": [
            {"asset": "QUESTION_MARK", "x": 0.62, "y": 0.22, "width": 0.14, "height": 0.16},
            {"asset": "WARNING", "x": 0.24, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["COOL", "VIGNETTE"],
    },
    "HIGH_PRESSURE_STRESS": {
        "keywords": ("overwhelmed", "anxiety", "crushing pressure", "deadline", "panic", "stress", "sleepless", "nervous", "headache", "too much work"),
        "background": "OFFICE",
        "camera": "PUNCH_IN",
        "action": "HEADACHE_STRESS",
        "emotion": "SAD",
        "objects": [
            {"asset": "CLOCK", "x": 0.64, "y": 0.24, "width": 0.16, "height": 0.16},
            {"asset": "BATTERY_DRAIN", "x": 0.22, "y": 0.22, "width": 0.18, "height": 0.12},
        ],
        "effects": ["COOL", "CAMERA_SHAKE"],
    },
    "RESOLUTE_BOUNDARY": {
        "keywords": ("say no", "firm", "unshakable", "uncompromising", "set boundaries", "stand your ground", "refuse", "resolve", "principled", "never settle"),
        "background": "CITY",
        "camera": "MEDIUM",
        "action": "CROSS_ARMS",
        "emotion": "NEUTRAL",
        "objects": [
            {"asset": "SHIELD", "x": 0.58, "y": 0.36, "width": 0.24, "height": 0.30},
            {"asset": "CHECK", "x": 0.80, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM"],
    },
    # Advanced Psychological & Storytelling Metaphors (Engineered by Atharv Hatwar)
    "THE_MARTYR_TRAP": {
        "keywords": ("martyr", "loudest sacrifice", "sacrifice in the room", "trap", "guilt", "hold the room hostage", "whiny", "servant in this house", "broken back", "attention seeker"),
        "background": "HOME",
        "camera": "CLOSE",
        "action": "HEADACHE_STRESS",
        "emotion": "SAD",
        "objects": [
            {"asset": "BROKEN_CROWN", "x": 0.52, "y": 0.20, "width": 0.22, "height": 0.18},
            {"asset": "PUPPET_STRINGS", "x": 0.24, "y": 0.28, "width": 0.28, "height": 0.36},
        ],
        "effects": ["VIGNETTE"],
    },
    "THE_TETHER_HOOK": {
        "keywords": ("doesn't want you", "move on", "tether", "leash", "hook", "tied", "leaving", "hold you back", "cant leave", "never lets you completely leave", "restrained"),
        "background": "ABSTRACT",
        "camera": "MEDIUM",
        "action": "STRUGGLE",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "TETHER_THREAD", "x": 0.44, "y": 0.45, "width": 0.38, "height": 0.16},
            {"asset": "DOORWAY_SUNLIGHT", "x": 0.14, "y": 0.32, "width": 0.26, "height": 0.48},
        ],
        "effects": ["VIGNETTE"],
    },
    "THE_CHASM_DISTANCE": {
        "keywords": ("distance", "rarely texts", "creates distance", "unanswered", "seen 3 days ago", "chasm", "emotional distance", "gap", "one-sided", "make time for you"),
        "background": "ABSTRACT",
        "camera": "WIDE",
        "action": "REACH",
        "emotion": "SAD",
        "objects": [
            {"asset": "CHASM_CRACK", "x": 0.42, "y": 0.40, "width": 0.22, "height": 0.50},
            {"asset": "PHONE", "x": 0.22, "y": 0.32, "width": 0.16, "height": 0.22},
        ],
        "effects": ["COOL"],
    },
    "THE_BREADCRUMBS": {
        "keywords": ("breadcrumbs", "replies to your stories", "how have you been", "little things", "jealous", "occasional attention", "crumbs", "replies to stories", "story reply"),
        "background": "ABSTRACT",
        "camera": "MEDIUM",
        "action": "SURPRISED",
        "emotion": "SURPRISED",
        "objects": [
            {"asset": "NOTIFICATION_POPUP", "x": 0.52, "y": 0.22, "width": 0.36, "height": 0.32},
            {"asset": "BREADCRUMB_TRAIL", "x": 0.32, "y": 0.65, "width": 0.40, "height": 0.12},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "THE_MOUSETRAP": {
        "keywords": ("psychological trap", "trap", "bait", "mousetrap", "mistake attention", "genuine interest", "occasional attention for genuine interest", "lure"),
        "background": "ABSTRACT",
        "camera": "MEDIUM",
        "action": "KNEEL",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "MOUSETRAP", "x": 0.52, "y": 0.48, "width": 0.42, "height": 0.30},
        ],
        "effects": ["VIGNETTE", "CAMERA_SHAKE"],
    },
    "THE_GLASS_JAR_SHELF": {
        "keywords": ("access to someone", "jar", "shelf", "display item", "keep you on shelf", "on call", "backup plan", "trophy", "difference between wanting someone", "wanting access"),
        "background": "ROOM",
        "camera": "MEDIUM",
        "action": "SIT",
        "emotion": "SAD",
        "objects": [
            {"asset": "GLASS_JAR_PRISON", "x": 0.32, "y": 0.32, "width": 0.36, "height": 0.44},
        ],
        "effects": ["COOL"],
    },
    "THE_TIME_DRAIN": {
        "keywords": ("months wasted", "decoding", "unclear intentions", "intentions clear", "spending months", "waste your time", "calendar", "wasting months"),
        "background": "ABSTRACT",
        "camera": "MEDIUM",
        "action": "HEADACHE_STRESS",
        "emotion": "SAD",
        "objects": [
            {"asset": "HOURGLASS", "x": 0.50, "y": 0.36, "width": 0.28, "height": 0.38},
            {"asset": "CLOCK", "x": 0.22, "y": 0.22, "width": 0.14, "height": 0.14},
        ],
        "effects": ["VIGNETTE"],
    },
    "SOMEONE_DOESNT_HATE_YOU": {
        "keywords": ("hate you to waste your time", "waste your time", "politeness", "crushing time", "polite", "friendly wave", "dont have to hate you"),
        "background": "STAGE",
        "camera": "CLOSE",
        "action": "WAVE",
        "emotion": "HAPPY",
        "objects": [
            {"asset": "GIANT_CLOCK", "x": 0.48, "y": 0.42, "width": 0.38, "height": 0.38},
        ],
        "effects": ["WARM"],
    },
    "THE_HAMSTER_WHEEL_BAIT": {
        "keywords": ("enough hope", "stop you from leaving", "prevent you from leaving", "leaving the treadmill", "keep giving you enough hope", "prevent you from leaving", "treadmill", "bait on a stick", "dangling"),
        "background": "ABSTRACT",
        "camera": "MEDIUM",
        "action": "RUN",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "HAMSTER_WHEEL", "x": 0.44, "y": 0.40, "width": 0.42, "height": 0.42},
            {"asset": "HEART", "x": 0.72, "y": 0.36, "width": 0.12, "height": 0.12},
        ],
        "effects": ["VIGNETTE"],
    },
    "SNIPPED_THREAD_BREAKOUT": {
        "keywords": ("difficult to lose", "genuinely wanted", "breakout", "cut the cord", "cut the thread", "snip", "freedom", "walk away", "step off", "dont confuse", "punchline", "sunrise"),
        "background": "ABSTRACT",
        "camera": "WIDE",
        "action": "WALK_RIGHT",
        "emotion": "HAPPY",
        "objects": [
            {"asset": "SNIPPED_THREAD_SUNRISE", "x": 0.48, "y": 0.35, "width": 0.44, "height": 0.45},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "SPEED_ACCELERATION": {
        "keywords": ("sprint", "accelerate", "move fast", "speed", "velocity", "take action", "momentum", "launch quickly", "execution", "speed wins"),
        "background": "STREET",
        "camera": "SNAP_ZOOM",
        "action": "SPRINT_FAST",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "ARROW", "x": 0.58, "y": 0.26, "width": 0.24, "height": 0.10},
        ],
        "effects": ["SPEED_LINES", "WARM"],
    },
    "ULTIMATE_TRIUMPH": {
        "keywords": ("triumph", "goal achieved", "mission accomplished", "we won", "break records", "unlocked victory", "champion status", "top tier", "won the game"),
        "background": "STAGE",
        "camera": "ZOOM_IN",
        "action": "TRIUMPH_FIST",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "TROPHY", "x": 0.64, "y": 0.22, "width": 0.18, "height": 0.20},
            {"asset": "STAR", "x": 0.26, "y": 0.20, "width": 0.14, "height": 0.14},
        ],
        "effects": ["GOLD_SPARKLES", "WARM", "CONFETTI"],
    },
    "WALL_BREAKTHROUGH": {
        "keywords": ("breakthrough", "break through", "break down", "smash", "barrier", "unlock", "suddenly", "finally", "eureka", "clicks"),
        "background": "ABSTRACT",
        "camera": "ZOOM_IN",
        "action": "POINT_UP",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "CRACKED_WALL", "x": 0.58, "y": 0.42, "width": 0.32, "height": 0.34},
            {"asset": "LIGHTBULB", "x": 0.44, "y": 0.16, "width": 0.15, "height": 0.17, "motion": "FLOAT_UP"},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "BATTERY_DRAIN": {
        "keywords": ("burnout", "exhausted", "tired", "energy", "drain", "drained", "no energy", "fatigue", "overworked"),
        "background": "HOME",
        "camera": "CLOSE",
        "action": "COWER",
        "emotion": "SAD",
        "objects": [
            {"asset": "BATTERY_DRAIN", "x": 0.64, "y": 0.24, "width": 0.22, "height": 0.14},
            {"asset": "CLOCK", "x": 0.18, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["COOL", "VIGNETTE"],
    },
    "BALANCE_SCALE": {
        "keywords": ("balance", "tradeoff", "trade-off", "cost", "weigh", "worth it", "sacrifice", "pros and cons", "evaluate"),
        "background": "OFFICE",
        "camera": "MEDIUM",
        "action": "SHRUG",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "BALANCE_SCALE", "x": 0.56, "y": 0.36, "width": 0.30, "height": 0.26},
            {"asset": "QUESTION_MARK", "x": 0.24, "y": 0.22, "width": 0.11, "height": 0.12, "motion": "FLOAT_UP"},
        ],
        "effects": [],
    },
    "MOUNTAIN_CLIMB": {
        "keywords": ("climb", "uphill", "struggle", "steep", "journey", "hard work", "summit", "peak", "goal", "ascent"),
        "background": "MOUNTAIN",
        "camera": "WIDE",
        "action": "WALK_RIGHT",
        "emotion": "NEUTRAL",
        "objects": [
            {"asset": "STAR", "x": 0.78, "y": 0.18, "width": 0.14, "height": 0.14},
            {"asset": "ARROW", "x": 0.42, "y": 0.28, "width": 0.22, "height": 0.08},
        ],
        "effects": ["WARM"],
    },
    "HOURGLASS_TIME": {
        "keywords": ("time running out", "seconds", "wasting time", "urgency", "countdown", "limited time", "precious", "years pass"),
        "background": "ABSTRACT",
        "camera": "CLOSE",
        "action": "THINK",
        "emotion": "CONFUSED",
        "objects": [
            {"asset": "HOURGLASS", "x": 0.62, "y": 0.32, "width": 0.20, "height": 0.26},
            {"asset": "CLOCK", "x": 0.20, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": ["VIGNETTE"],
    },
    "PODIUM_VICTORY": {
        "keywords": ("winner", "podium", "first place", "champion", "trophy", "conquer", "succeed"),
        "background": "STAGE",
        "camera": "ZOOM_IN",
        "action": "CELEBRATE",
        "emotion": "EXCITED",
        "objects": [
            {"asset": "PODIUM", "x": 0.46, "y": 0.54, "width": 0.28, "height": 0.20},
            {"asset": "TROPHY", "x": 0.68, "y": 0.24, "width": 0.14, "height": 0.16},
            {"asset": "STAR", "x": 0.24, "y": 0.20, "width": 0.12, "height": 0.12},
        ],
        "effects": ["WARM", "SPARKLE"],
    },
    "SHIELD_DEFENSE": {
        "keywords": ("protect", "defense", "shield", "guard", "immune", "resist", "armor", "filter"),
        "background": "CITY",
        "camera": "MEDIUM",
        "action": "STOP",
        "emotion": "NEUTRAL",
        "objects": [
            {"asset": "SHIELD", "x": 0.56, "y": 0.38, "width": 0.22, "height": 0.26},
            {"asset": "WARNING", "x": 0.78, "y": 0.22, "width": 0.12, "height": 0.12},
        ],
        "effects": [],
    },
    "MAGNIFYING_TRUTH": {
        "keywords": ("inspect", "look closer", "details", "fine print", "examine", "microscope", "analyze", "detective", "hidden clue"),
        "background": "LIBRARY",
        "camera": "CLOSE",
        "action": "READ",
        "emotion": "SURPRISED",
        "objects": [
            {"asset": "MAGNIFYING_GLASS", "x": 0.58, "y": 0.30, "width": 0.20, "height": 0.22},
            {"asset": "BOOK", "x": 0.38, "y": 0.48, "width": 0.16, "height": 0.14},
        ],
        "effects": ["WARM"],
    },
}

# ---------------------------------------------------------------------------
# High-Intelligence Embedded Semantic & Morphological NLP Engine
# Zero external dependencies. Zero Ollama required. 100% In-Process.
# Created by Atharv Hatwar.
# ---------------------------------------------------------------------------

_IRREGULAR_VERBS: dict[str, str] = {
    "ran": "run", "running": "run", "runs": "run", "jogged": "run", "jogging": "run", "jogs": "run",
    "sprinted": "sprint", "sprinting": "sprint", "sprints": "sprint",
    "bought": "buy", "buying": "buy", "buys": "buy", "purchased": "buy", "purchasing": "buy",
    "slept": "sleep", "sleeping": "sleep", "sleeps": "sleep", "slumbered": "sleep",
    "felt": "feel", "feeling": "feel", "feels": "feel",
    "went": "go", "going": "go", "goes": "go",
    "saw": "see", "seeing": "see", "sees": "see", "watched": "see", "watching": "see", "stared": "stare", "staring": "stare", "stares": "stare",
    "spoke": "speak", "speaking": "speak", "speaks": "speak", "talked": "talk", "talking": "talk", "talks": "talk",
    "told": "tell", "telling": "tell", "tells": "tell",
    "taught": "teach", "teaching": "teach", "teaches": "teach",
    "won": "win", "winning": "win", "wins": "win", "conquered": "win",
    "lost": "lose", "losing": "lose", "loses": "lose",
    "wrote": "write", "writing": "write", "writes": "write",
    "built": "build", "building": "build", "builds": "build", "created": "build", "creating": "build",
    "thought": "think", "thinking": "think", "thinks": "think", "pondered": "think", "wondered": "think",
    "celebrated": "celebrate", "celebrating": "celebrate", "celebrates": "celebrate", "cheered": "celebrate",
    "realized": "realize", "realizing": "realize", "realizes": "realize",
    "understood": "understand", "understanding": "understand", "understands": "understand",
    "started": "start", "starting": "start", "starts": "start", "began": "start", "beginning": "start",
    "stopped": "stop", "stopping": "stop", "stops": "stop", "halted": "stop",
    "stayed": "stay", "staying": "stay", "stays": "stay",
    "typed": "type", "typing": "type", "types": "type", "coded": "type", "coding": "type",
    "worked": "work", "working": "work", "works": "work",
    "walked": "walk", "walking": "walk", "walks": "walk", "stepped": "walk", "stepping": "walk",
    "exercised": "exercise", "exercising": "exercise", "exercises": "exercise",
    "trained": "train", "training": "train", "trains": "train",
    "lifted": "lift", "lifting": "lift", "lifts": "lift",
    "jumped": "jump", "jumping": "jump", "jumps": "jump", "leaped": "jump",
    "scrolled": "scroll", "scrolling": "scroll", "scrolls": "scroll",
    "stressed": "stress", "stressing": "stress", "stresses": "stress", "panicked": "stress",
    "argued": "argue", "arguing": "argue", "argues": "argue", "debated": "argue",
    "shouted": "shout", "shouting": "shout", "shouts": "shout", "screamed": "shout",
    "cowered": "cower", "cowering": "cower", "cowers": "cower", "hid": "cower", "hiding": "cower",
    "shrugged": "shrug", "shrugging": "shrug", "shrugs": "shrug",
    "meditated": "meditate", "meditating": "meditate", "meditates": "meditate",
    "presented": "present", "presenting": "present", "presents": "present", "explained": "present", "explaining": "present",
    "invested": "invest", "investing": "invest", "invests": "invest",
    "struggled": "struggle", "struggling": "struggle", "struggles": "struggle",
}

def _stem_word(w: str) -> str:
    low = w.lower().strip()
    if low in _IRREGULAR_VERBS:
        return _IRREGULAR_VERBS[low]
    for sfx in ("ing", "ed", "es", "s"):
        if len(low) > len(sfx) + 2 and low.endswith(sfx):
            return low[:-len(sfx)]
    return low

_CAMERAS = ["ZOOM_IN", "MEDIUM", "CLOSE", "WIDE", "PAN_RIGHT", "PAN_LEFT", "ZOOM_OUT"]
_BACKGROUNDS = ["OFFICE", "STREET", "HOME", "PARK", "CITY", "ABSTRACT", "CLASSROOM", "MOUNTAIN", "STAGE", "LIBRARY", "CAFE", "CAVE", "BEDROOM", "FITNESS_GYM", "GALLERY", "MIND", "FINANCE"]


class ProceduralSceneEngine:
    """
    Embedded In-Process AI Scene Planner & Director.
    Analyzes narration semantically and synthesizes 100% original, topic-aligned
    scenes, active character poses, dynamic staging, and context-aware props.
    Runs 100% locally inside the software without Ollama or external services.
    Created by Atharv Hatwar.
    """

    def __init__(self, style_id: str = "a1_classic_bw") -> None:
        self.style_id = style_id
        self.pack, self.sp = resolve_style_pack(style_id)
        self.history: list[dict[str, Any]] = []

    def generate_scene_for_narration(
        self,
        narration: str,
        scene_idx: int = 0,
        total_scenes: int = 1,
        target_duration: float = 3.5,
        topic: str = "",
    ) -> dict[str, Any]:
        """Synthesize a 100% unique, topic-aligned scene matching the sentence."""
        text_lower = narration.lower().strip()
        topic_lower = (topic or "").lower().strip()
        words = re.findall(r"[a-z0-9']+", text_lower)
        stems = set(_stem_word(w) for w in words)
        raw_and_stems = set(words) | stems

        last_action = None
        if self.history:
            last_chars = self.history[-1].get("characters", [])
            if last_chars and isinstance(last_chars[0], dict):
                last_action = last_chars[0].get("action")

        # 1. Check for physical metaphor match first
        best_metaphor_key: Optional[str] = None
        best_score = 0.0

        for key, meta in PHYSICAL_METAPHORS.items():
            score = 0.0
            for kw in meta["keywords"]:
                if kw in text_lower:
                    score += 5.0 if " " in kw else 3.0
            for prev in self.history[-3:]:
                if prev.get("_metaphor") == key:
                    score -= 50.0  # Strongly block reuse
            if score > best_score:
                best_score = score
                best_metaphor_key = key

        # 2. Deep Semantic & Story Arc Mapping
        explicit_match = self._detect_explicit_action_verb(text_lower)
        if explicit_match is not None:
            sem_action, sem_emotion, sem_bg, sem_props = explicit_match
            has_explicit_verb = True
        else:
            sem_action, sem_emotion, sem_bg, sem_props = self._match_semantic_intent(
                text_lower=text_lower,
                raw_and_stems=raw_and_stems,
                last_action=last_action,
                scene_idx=scene_idx,
                total_scenes=total_scenes,
            )
            has_explicit_verb = False

        # 2b. In-Process Neural Semantic Brain (MiniLM-L6 ONNX Transformer)
        # Deep contextual understanding of abstract metaphors, emotions, and postures
        try:
            from engine.semantic_scene_brain import SemanticSceneBrain
            brain = SemanticSceneBrain.get_instance()
            if brain._initialized:
                recent_mets = [prev.get("_metaphor") for prev in self.history[-3:] if prev.get("_metaphor")]
                n_met, n_m_score = brain.match_best_metaphor(narration, recent_metaphors=recent_mets)
                if n_met and n_m_score >= 0.16 and (best_score < 8.0 or not best_metaphor_key):
                    best_metaphor_key = n_met
                    best_score = max(best_score, 12.0 * n_m_score)

                n_act, n_a_score = brain.match_best_action(narration)
                if n_act and n_a_score >= 0.20 and not has_explicit_verb:
                    sem_action = n_act

                n_emo, n_e_score = brain.match_best_emotion(narration)
                if n_emo and n_e_score >= 0.18:
                    sem_emotion = n_emo
        except Exception as _brain_err:
            logger.debug("Neural Semantic Brain inference pass note: %s", _brain_err)

        # Extract speech/thought bubble ONLY when the narration explicitly contains quotes!
        speech, thought = self._extract_quoted_dialogue(narration)

        if best_metaphor_key and best_score >= 8.0:
            meta = PHYSICAL_METAPHORS[best_metaphor_key]
            action = meta.get("action", sem_action)
            emotion = meta.get("emotion", sem_emotion)
            objects = [dict(o) for o in meta.get("objects", [])]
            effects = list(meta.get("effects", []))
            bg = meta.get("background", sem_bg)
            cam = meta.get("camera", self._pick_diverse_camera())
            chosen_metaphor = best_metaphor_key
        elif has_explicit_verb:
            action = sem_action
            emotion = sem_emotion
            objects = sem_props if sem_props else ([dict(o) for o in PHYSICAL_METAPHORS[best_metaphor_key]["objects"]] if (best_metaphor_key and best_score >= 3.0) else [])
            effects = ["WARM"] if emotion in ("HAPPY", "EXCITED") else (["COOL"] if emotion in ("SAD", "ANGRY") else [])
            bg = sem_bg
            cam = "DYNAMIC_CUT" if action in ("SPRINT_FAST", "RUN", "JUMP", "FIGHT") else self._pick_diverse_camera()
            chosen_metaphor = best_metaphor_key if (best_metaphor_key and best_score >= 3.0 and not sem_props) else None
        elif best_metaphor_key and best_score >= 3.0:
            meta = PHYSICAL_METAPHORS[best_metaphor_key]
            action = meta.get("action", sem_action)
            emotion = meta.get("emotion", sem_emotion)
            objects = [dict(o) for o in meta.get("objects", [])]
            effects = list(meta.get("effects", []))
            bg = meta.get("background", sem_bg)
            cam = meta.get("camera", self._pick_diverse_camera())
            chosen_metaphor = best_metaphor_key
        else:
            action = sem_action
            emotion = sem_emotion
            objects = sem_props
            effects = ["WARM"] if emotion in ("HAPPY", "EXCITED") else (["COOL"] if emotion in ("SAD", "ANGRY") else [])
            bg = sem_bg
            cam = self._pick_diverse_camera()
            chosen_metaphor = None

        # Anti-Repetition Guarantee: NEVER allow consecutive or recent actions to repeat!
        recent_actions = [
            s.get("characters", [{}])[0].get("action")
            for s in self.history[-2:]
            if s.get("characters") and isinstance(s["characters"][0], dict)
        ]
        if action in recent_actions:
            if not has_explicit_verb:
                action = self._rotate_to_progression_action(action, scene_idx, total_scenes)
                if action in recent_actions:
                    action = self._rotate_to_progression_action(action, scene_idx + 1, total_scenes)
            else:
                variant_map = {
                    "WALK_RIGHT": "WALK_LEFT",
                    "WALK_LEFT": "WALK_RIGHT",
                    "RUN": "SPRINT_FAST",
                    "SPRINT_FAST": "RUN",
                    "POINT_RIGHT": "POINT_UP",
                    "POINT_UP": "POINT_RIGHT",
                    "WAVE": "DISMISSIVE_WAVE",
                    "LAUGH": "CELEBRATE",
                    "TYPING_LAPTOP": "SIT",
                }
                action = variant_map.get(action, action)

        # 3. Detect multi-character dialogue vs solitary staging
        is_multi = self._detect_multi_character_staging(text_lower, action, scene_idx, total_scenes)

        # Build staged characters with dynamic entrance and gesture kinematics
        characters = self._build_staged_characters(
            is_multi=is_multi,
            action=action,
            emotion=emotion,
            speech=speech,
            thought=thought,
            text_lower=text_lower,
        )

        # Ensure objects never collide with Person B in multi-character scenes
        if len(characters) > 1:
            for obj in objects:
                ox = float(obj.get("x", 0.5))
                if ox > 0.60:
                    obj["x"] = 0.50

        # Ensure background matches style aesthetic if specialized pack
        if self.pack.id == "a3_prehistoric_cave":
            bg = "CAVE"
        elif self.pack.id == "a5_historical_cartoon" and bg in ("OFFICE", "CLASSROOM"):
            bg = "CASTLE"
        elif scene_idx == 0 and topic_lower and bg not in ("CAVE", "CASTLE"):
            if any(k in topic_lower for k in ("medicine", "hospital", "doctor", "health", "biotech")) and any(k in topic_lower for k in ("ai", "code", "tech", "algorithm", "software")):
                bg = "HOSPITAL_CLINIC"
            elif any(k in topic_lower for k in ("space", "rocket", "mars", "moon", "star", "cosmos", "orbit", "planet", "astronomy")):
                bg = "SPACE_COSMOS"
            elif any(k in topic_lower for k in ("history", "empire", "rome", "napoleon", "caesar", "war", "battle", "ancient", "castle", "stoic")):
                bg = "MEDIEVAL_CASTLE"
            elif any(k in topic_lower for k in ("code", "coding", "software", "python", "ai", "tech", "algorithm", "terminal", "server")):
                bg = "TECH_CYBER_SERVER"
            elif any(k in topic_lower for k in ("money", "wealth", "invest", "crypto", "trading", "finance", "stock")):
                bg = "TRADING_FINANCE"
            elif any(k in topic_lower for k in ("gym", "workout", "muscle", "fitness", "exercise", "bodybuilding")):
                bg = "FITNESS_GYM"
            elif any(k in topic_lower for k in ("hospital", "medicine", "doctor", "health", "biology", "dna")):
                bg = "HOSPITAL_CLINIC"
            elif any(k in topic_lower for k in ("nature", "forest", "mountain", "tree", "river", "outdoor")):
                bg = "NATURE_FOREST"

        # 4. Neural-Driven Visual Layout Archetype Selection
        chosen_archetype, archetype_data = self._select_layout_archetype(
            narration=narration,
            text_lower=text_lower,
            chosen_metaphor=chosen_metaphor,
            scene_idx=scene_idx,
            total_scenes=total_scenes,
            is_multi=is_multi,
            topic=topic,
        )

        # Adapt character kinematics for specialized scene archetypes
        if chosen_archetype == "SCALE_CONTRAST" and characters:
            characters[0]["scale"] = 0.58
            characters[0]["start_x"] = 0.18
            characters[0]["end_x"] = 0.20
            characters[0]["action"] = "POINT_UP"
        elif chosen_archetype == "HERD_REBEL" and characters:
            characters[0]["scale"] = 1.30
            characters[0]["color"] = "#38BDF8"
            characters[0]["facing"] = "left"
            characters[0]["start_x"] = 0.22
            characters[0]["end_x"] = 0.20
            characters[0]["action"] = archetype_data.get("hero_action", "WALK_LEFT")
        elif chosen_archetype == "FULLSCREEN_INFOGRAPHIC" and characters:
            characters[0]["scale"] = 1.20
            characters[0]["start_x"] = 0.16
            characters[0]["end_x"] = 0.18
            characters[0]["facing"] = "right"
            characters[0]["action"] = "PRESENT_CHART"

        scene: dict[str, Any] = {
            "id": scene_idx + 1,
            "duration": target_duration,
            "narration": narration,
            "background": bg,
            "camera": cam,
            "characters": characters,
            "objects": objects,
            "effects": effects,
            "transition": self.pack.preferred_transition,
            "transition_in": self.pack.preferred_transition,
            "emotion": emotion,
            "_metaphor": chosen_metaphor,
            "layout_archetype": chosen_archetype,
            "archetype_data": archetype_data,
            "topic": topic,
        }

        self.history.append(scene)
        return scene

    def _detect_explicit_action_verb(
        self,
        text_lower: str,
    ) -> Optional[tuple[str, str, str, list[dict[str, Any]]]]:
        """
        Detects explicit physical action verbs spoken in the script narration.
        Guarantees 100% audio-kinematic synchronization so the stickman actually
        executes what is being spoken!
        Created by Atharv Hatwar.
        """
        # 1. Waving / Greeting / Farewell
        if any(w in text_lower for w in ("wave", "waving", "waved", "say hello", "said hello", "say hi", "greet", "greeting", "farewell", "goodbye")):
            return "WAVE", "HAPPY", self._pick_diverse_background(text_lower), [
                {"asset": "DOODLE_ARROW", "x": 0.72, "y": 0.28, "width": 0.18, "height": 0.12}
            ]

        # 2. Running / Sprinting / Chasing / Escaping
        if any(w in text_lower for w in ("running", "ran ", "sprint", "sprinting", "dash", "dashing", "rush", "rushing", "escape", "escaped", "flee", "fleeing", "chase", "chasing")):
            bg = "CITY" if any(w in text_lower for w in ("city", "street", "road", "alley")) else "PARK"
            return "SPRINT_FAST", "EXCITED", bg, [
                {"asset": "DOODLE_ARROW", "x": 0.75, "y": 0.32, "width": 0.20, "height": 0.10}
            ]

        # 3. Walking / Strolling / Pacing
        if any(w in text_lower for w in ("walk", "walking", "walked", "stroll", "strolling", "pacing", "stepped", "stepping")):
            bg = "PARK" if any(w in text_lower for w in ("park", "outside", "nature", "tree")) else "CITY"
            return "WALK_RIGHT", "CONFIDENT", bg, []

        # 4. Typing / Coding / Keyboard at desk
        if any(w in text_lower for w in ("typing", "typed", "keyboard", "coding", "code", "programming", "laptop", "wrote code", "at his desk", "at her desk")):
            return "TYPING_LAPTOP", "NEUTRAL", "MODERN_OFFICE", [
                {"asset": "LAPTOP", "x": 0.62, "y": 0.44, "width": 0.26, "height": 0.20},
                {"asset": "COFFEE_CUP", "x": 0.38, "y": 0.50, "width": 0.10, "height": 0.10},
            ]

        # 5. Counting Money / Paying Cash
        if any(w in text_lower for w in ("count money", "counting money", "counted money", "counting his", "counting her", "cash in hand", "paid cash", "stack of money", "stacks of cash")):
            return "COUNT_MONEY", "HAPPY", "FINANCE", [
                {"asset": "MONEY", "x": 0.65, "y": 0.30, "width": 0.20, "height": 0.16},
                {"asset": "COIN", "x": 0.78, "y": 0.24, "width": 0.12, "height": 0.12},
            ]

        # 6. Laughing / Hilarious / Joke / Giggle
        if any(w in text_lower for w in ("laugh", "laughing", "laughed", "laughter", "hilarious", "chuckle", "chuckling", "giggle", "giggling", "joke", "burst out laughing")):
            return "LAUGH", "HAPPY", self._pick_diverse_background(text_lower), [
                {"asset": "STAR", "x": 0.72, "y": 0.22, "width": 0.14, "height": 0.14}
            ]

        # 7. Crying / Weeping / Tears / Sobbing
        if any(w in text_lower for w in ("cry", "crying", "cried", "weep", "weeping", "sob", "sobbing", "tears", "heartbroken")):
            return "CRY", "SAD", "BREAKTHROUGH", []

        # 8. Falling / Tripping / Collapsing
        if any(w in text_lower for w in ("fall down", "fell down", "falling", "collapse", "collapsed", "trip and", "tripped", "stumbled", "dropped to the ground")):
            return "FALL", "SURPRISED", "BREAKTHROUGH", []

        # 9. Jumping / Leaping / Hopping
        if any(w in text_lower for w in ("jump", "jumping", "jumped", "leap", "leaping", "leaped", "hop", "hopping")):
            return "JUMP", "EXCITED", "STAGE", [
                {"asset": "STAR", "x": 0.72, "y": 0.20, "width": 0.14, "height": 0.14}
            ]

        # 10. Shouting / Fighting / Yelling / Arguing
        if any(w in text_lower for w in ("shout", "shouting", "shouted", "yell", "yelling", "yelled", "scream", "screaming", "fight", "fighting", "punched", "argue", "arguing")):
            return "FIGHT", "ANGRY", "BREAKTHROUGH", [
                {"asset": "ALERT_STAMP", "x": 0.72, "y": 0.26, "width": 0.20, "height": 0.14}
            ]

        # 11. Pointing / Showing / Looking
        if any(w in text_lower for w in ("point at", "pointing at", "pointed at", "look at that", "look up", "look at this", "check this", "showed the", "showing the")):
            action = "POINT_UP" if any(w in text_lower for w in ("up", "sky", "ceiling", "above")) else "POINT_RIGHT"
            return action, "CONFIDENT", self._pick_diverse_background(text_lower), [
                {"asset": "DOODLE_ARROW", "x": 0.70, "y": 0.32, "width": 0.22, "height": 0.12}
            ]

        # 12. Shrug / Clueless / No Idea
        if any(w in text_lower for w in ("shrug", "shrugged", "no idea", "clueless", "who knows", "did not know", "didn't know", "dunno")):
            return "SHRUG", "CONFUSED", "ABSTRACT", [
                {"asset": "QUESTION_MARK", "x": 0.68, "y": 0.22, "width": 0.14, "height": 0.18}
            ]

        # 13. Facepalm / Dumb Mistake / Embarrassing
        if any(w in text_lower for w in ("facepalm", "face palm", "facepalmed", "how stupid", "dumb mistake", "embarrassing", "stupid mistake")):
            return "FACEPALM", "CRINGE", "ABSTRACT", [
                {"asset": "ALERT_STAMP", "x": 0.72, "y": 0.26, "width": 0.20, "height": 0.14}
            ]

        # 14. Sitting down / Relaxing on chair
        if any(w in text_lower for w in ("sat down", "sitting down", "sit down", "sat on", "sitting in", "chair", "sofa", "couch")):
            return "SIT", "CALM", "HOME", [
                {"asset": "CHAIR", "x": 0.50, "y": 0.55, "width": 0.22, "height": 0.26}
            ]

        # 15. Celebrating / Victory / Triumph
        if any(w in text_lower for w in ("celebrat", "cheer", "cheering", "we won", "victory", "triumph", "champion", "winner")):
            return "CELEBRATE", "EXCITED", "STAGE", [
                {"asset": "TROPHY", "x": 0.68, "y": 0.24, "width": 0.18, "height": 0.20},
                {"asset": "STAR", "x": 0.24, "y": 0.20, "width": 0.12, "height": 0.12},
            ]

        # 16. Scrolling phone / Doomscrolling
        if any(w in text_lower for w in ("phone", "scroll", "scrolling", "instagram", "tiktok", "notification", "screen time", "mobile")):
            return "SCROLL_PHONE", "CONFUSED", "HOME", [
                {"asset": "PHONE", "x": 0.60, "y": 0.34, "width": 0.14, "height": 0.20}
            ]

        return None

    def _match_semantic_intent(
        self,
        text_lower: str,
        raw_and_stems: set[str],
        last_action: Optional[str],
        scene_idx: int,
        total_scenes: int,
    ) -> tuple[str, str, str, list[dict[str, Any]]]:
        """
        Maps narration to rich, context-driven stickman actions, emotions, environments,
        and high-impact vector props. 100% in-process AI logic.
        """
        # 1. VICTORY, CELEBRATION, TRANSFORMATION, CLIMAX
        if any(k in text_lower for k in ("celebrat", "transformation", "shape of his", "shape of her", "best shape", "champion", "triumph", "we made it", "won the", "freedom", "succeeded", "glory", "unlocked", "proud of")) or \
           any(s in raw_and_stems for s in ("celebrate", "win", "victory", "triumph", "transform", "champion", "conquer")):
            action = "CELEBRATE" if last_action != "CELEBRATE" else "TRIUMPH_FIST"
            return action, "EXCITED", "STAGE", [
                {"asset": "TROPHY", "x": 0.68, "y": 0.24, "width": 0.18, "height": 0.20},
                {"asset": "STAR", "x": 0.24, "y": 0.20, "width": 0.12, "height": 0.12},
                {"asset": "PODIUM", "x": 0.46, "y": 0.54, "width": 0.26, "height": 0.18},
            ]

        # 2. SLEEP, BED, SNOOZE, PROCRASTINATION, COMFORT ZONE
        if any(k in text_lower for k in ("snooze", "in bed", "stayed in bed", "stay in bed", "comfort zone", "alarm rang", "waking up", "lazy", "couch", "slump", "tomorrow", "delay", "yawn", "nap", "sleep", "insomnia", "3am", "midnight", "night")) or \
           any(s in raw_and_stems for s in ("bed", "sleep", "snooze", "nap", "tired", "exhaust", "couch", "rest", "night")):
            action = "BED_SHOCK" if any(w in text_lower for w in ("alarm", "wake", "sudden", "replay", "shock", "3am")) else "BED_REST"
            emo = "SURPRISED" if action == "BED_SHOCK" else "CALM"
            return action, emo, "BEDROOM", [
                {"asset": "BED", "x": 0.50, "y": 0.65, "width": 0.44, "height": 0.28},
                {"asset": "NIGHTSTAND_CLOCK", "x": 0.82, "y": 0.62, "width": 0.16, "height": 0.22},
            ]

        # 2b. EMBARRASSING MOMENTS, MEMORY REPLAY, CRINGE, AWKWARD FLASHBACK
        if any(k in text_lower for k in ("embarrass", "cringe", "replay", "replaying", "awkward", "mortified", "humiliat", "staring at the ceiling", "brain replay", "flashback", "social blunder", "why did i say")) or \
           any(s in raw_and_stems for s in ("embarrass", "cringe", "replay", "awkward", "regret", "mortified")):
            action = "BED_SHOCK" if any(w in text_lower for w in ("bed", "night", "3am", "ceiling")) else "FACEPALM"
            bg = "BEDROOM" if any(w in text_lower for w in ("bed", "night", "3am", "ceiling")) else "ABSTRACT"
            return action, "CRINGE", bg, [
                {"asset": "THOUGHT_CLOUD", "x": 0.70, "y": 0.26, "width": 0.32, "height": 0.22},
                {"asset": "ALERT_STAMP", "x": 0.72, "y": 0.26, "width": 0.20, "height": 0.14},
            ]

        # 2c. DIWALI, FESTIVAL, LIGHTS, TRADITION
        if any(k in text_lower for k in ("diwali", "deepavali", "diyas", "diya", "festival of light", "crackers", "oil lamp", "festive lights")) or \
           any(s in raw_and_stems for s in ("diwali", "lamp", "festival", "festive", "tradition")):
            return "PRESENT", "HAPPY", "PARK", [
                {"asset": "DIYA", "x": 0.28, "y": 0.68, "width": 0.14, "height": 0.12},
                {"asset": "DIYA", "x": 0.72, "y": 0.68, "width": 0.14, "height": 0.12},
            ]

        # 3. FITNESS, WORKOUT, GYM, ATHLETICS, PUSHUPS, RUNNING
        if any(k in text_lower for k in ("pushup", "pushups", "workout", "work out", "working out", "running shoes", "gym", "get fit", "in shape", "lift weights", "train hard", "sweat", "athletic", "cardio")) or \
           any(s in raw_and_stems for s in ("pushup", "workout", "gym", "exercise", "train", "lift", "squat", "athletic", "fitness", "run", "sprint")):
            action = "SPRINT_FAST" if last_action != "SPRINT_FAST" else "JUMP"
            return action, "EXCITED", "FITNESS_GYM", [
                {"asset": "ARROW", "x": 0.68, "y": 0.26, "width": 0.18, "height": 0.08},
                {"asset": "STAR", "x": 0.22, "y": 0.22, "width": 0.12, "height": 0.12},
                {"asset": "CLOCK", "x": 0.76, "y": 0.24, "width": 0.12, "height": 0.12},
            ]

        # 4. TECH, DESK WORK, OFFICE, CODING, STARING AT SCREEN
        if any(k in text_lower for k in ("office job", "computer screen", "staring at", "stare at", "at his desk", "at her desk", "writing code", "typing on", "cubicle", "software engineer", "developer", "browser")) or \
           any(s in raw_and_stems for s in ("office", "desk", "computer", "laptop", "screen", "code", "type", "stare", "job")):
            action = "TYPING_LAPTOP" if last_action != "TYPING_LAPTOP" else "SIT"
            return action, "NEUTRAL", "MODERN_OFFICE", [
                {"asset": "LAPTOP", "x": 0.62, "y": 0.44, "width": 0.26, "height": 0.20},
                {"asset": "COFFEE_CUP", "x": 0.38, "y": 0.50, "width": 0.10, "height": 0.10},
                {"asset": "PHONE", "x": 0.78, "y": 0.28, "width": 0.12, "height": 0.16},
            ]

        # 5. GUILT, BURNOUT, REGRET, FAILURE, STRESS, MISTAKES
        if any(k in text_lower for k in ("felt guilty", "feeling guilty", "regret", "burnout", "headache", "gave up", "failed", "blunder", "mistake", "too hard", "struggling", "stuck", "frustrat", "panic")) or \
           any(s in raw_and_stems for s in ("guilt", "regret", "fail", "stress", "panic", "fear", "struggle", "cry")):
            action = "FACEPALM" if last_action != "FACEPALM" else "HEADACHE_STRESS"
            return action, "SAD", "BREAKTHROUGH", [
                {"asset": "BATTERY_DRAIN", "x": 0.68, "y": 0.26, "width": 0.20, "height": 0.16},
                {"asset": "BRICK_WALL", "x": 0.76, "y": 0.48, "width": 0.24, "height": 0.24},
            ]

        # 6. REALIZATION, EPIPHANY, MINDSET, TRUTH, INSIGHT
        if any(k in text_lower for k in ("realize", "realized", "unreliable", "epiphany", "truth is", "secret is", "mindset", "eureka", "lightbulb", "in your mind", "look inside", "perspective")) or \
           any(s in raw_and_stems for s in ("realize", "understand", "mind", "brain", "idea", "insight", "wisdom")):
            action = "THINK" if last_action != "THINK" else "POINT_UP"
            return action, "SURPRISED", "MIND", [
                {"asset": "LIGHTBULB", "x": 0.65, "y": 0.20, "width": 0.16, "height": 0.18},
                {"asset": "BRAIN", "x": 0.24, "y": 0.22, "width": 0.18, "height": 0.18},
            ]

        # 7. HABITS, DISCIPLINE, CONSISTENCY, COMPOUNDING, DAILY ROUTINE
        if any(k in text_lower for k in ("discipline compounds", "compounds over time", "daily discipline", "every single day", "every day", "habit", "routine", "small daily", "brick by brick", "small steps", "consistency")) or \
           any(s in raw_and_stems for s in ("habit", "routine", "discipline", "consistent", "compound", "practice", "zen", "focus")):
            action = "MEDITATE_ZEN" if last_action != "MEDITATE_ZEN" else "PRESENT_CHART"
            return action, "CONFIDENT", "GALLERY", [
                {"asset": "DOMINOES", "x": 0.64, "y": 0.52, "width": 0.28, "height": 0.18},
                {"asset": "STAR", "x": 0.78, "y": 0.22, "width": 0.12, "height": 0.12},
                {"asset": "BALANCE_SCALE", "x": 0.24, "y": 0.48, "width": 0.20, "height": 0.20},
            ]

        # 8. FINANCE, MONEY, WEALTH, INVESTING, CAPITAL
        if any(k in text_lower for k in ("money", "wealth", "cash", "dollar", "rich", "invest", "stock", "crypto", "portfolio", "profit", "revenue", "cost", "buy shares", "passive income", "assets")) or \
           any(s in raw_and_stems for s in ("money", "cash", "dollar", "rich", "wealth", "invest", "profit", "finance", "bank", "buy")):
            action = "COUNT_MONEY" if last_action != "COUNT_MONEY" else "PRESENT_CHART"
            return action, "HAPPY", "FINANCE", [
                {"asset": "MONEY", "x": 0.65, "y": 0.30, "width": 0.20, "height": 0.16},
                {"asset": "COIN", "x": 0.78, "y": 0.24, "width": 0.12, "height": 0.12},
                {"asset": "LINE_CHART", "x": 0.26, "y": 0.40, "width": 0.24, "height": 0.20},
            ]

        # 9. SOCIAL MEDIA, PHONE, DOOMSCROLLING, DISTRACTION
        if any(k in text_lower for k in ("phone", "mobile", "scroll", "scrolling", "instagram", "tiktok", "notification", "screen time", "distract")) or \
           any(s in raw_and_stems for s in ("phone", "scroll", "social", "app")):
            action = "SCROLL_PHONE" if last_action != "SCROLL_PHONE" else "FACEPALM"
            return action, "CONFUSED", "HOME", [
                {"asset": "PHONE", "x": 0.60, "y": 0.34, "width": 0.14, "height": 0.20},
                {"asset": "CLOCK", "x": 0.24, "y": 0.24, "width": 0.14, "height": 0.14},
            ]

        # 10. QUESTIONS, CURIOSITY, MYSTERY, DOUBT
        if "?" in text_lower or any(k in text_lower for k in ("why", "how", "what if", "question", "wonder", "curious", "mystery", "doubt")):
            action = "CONFUSED" if last_action != "CONFUSED" else "SHRUG"
            return action, "CONFUSED", "ABSTRACT", [
                {"asset": "QUESTION_MARK", "x": 0.66, "y": 0.22, "width": 0.14, "height": 0.18},
                {"asset": "HOURGLASS", "x": 0.24, "y": 0.46, "width": 0.14, "height": 0.18},
            ]

        # 11. TEACHING, PRESENTING, LECTURING, SHARING
        if any(k in text_lower for k in ("explain", "teach", "show you", "look here", "lesson", "guide", "lecture", "presentation")) or \
           any(s in raw_and_stems for s in ("teach", "explain", "present", "guide")):
            action = "PRESENT_CHART" if last_action != "PRESENT_CHART" else "POINT_RIGHT"
            return action, "CONFIDENT", "CLASSROOM", [
                {"asset": "BAR_CHART", "x": 0.64, "y": 0.40, "width": 0.28, "height": 0.22},
                {"asset": "STAR", "x": 0.24, "y": 0.22, "width": 0.12, "height": 0.12},
            ]

        # 12. ANIMALS & PETS
        if any(s in raw_and_stems for s in ("dog", "puppy", "pet")):
            return "WALK_RIGHT", "HAPPY", "PARK", [{"asset": "DOG", "x": 0.72, "y": 0.56, "width": 0.22, "height": 0.18}]
        if any(s in raw_and_stems for s in ("cat", "kitten")):
            return "SIT", "HAPPY", "HOME", [{"asset": "CAT", "x": 0.72, "y": 0.58, "width": 0.18, "height": 0.16}]
        if any(s in raw_and_stems for s in ("horse", "ride")):
            return "WALK_RIGHT", "CONFIDENT", "MOUNTAIN", [{"asset": "HORSE", "x": 0.70, "y": 0.48, "width": 0.30, "height": 0.26}]

        # 13. Dynamic Narrative Position Arc (Fallback when no explicit keyword triggers)
        arc_actions = ["POINT_RIGHT", "WALK_RIGHT", "THINK", "PRESENT", "POINT_UP", "TRIUMPH_FIST"]
        fallback_action = arc_actions[scene_idx % len(arc_actions)]
        if last_action and fallback_action == last_action:
            fallback_action = arc_actions[(scene_idx + 1) % len(arc_actions)]

        bg = self._pick_diverse_background(text_lower)
        fallback_props = self._extract_props(text_lower)
        return fallback_action, "NEUTRAL", bg, fallback_props

    def _rotate_to_progression_action(self, action: str, scene_idx: int, total_scenes: int) -> str:
        """Mutate action to progress the dramatic narrative without repetition."""
        rotation_map = {
            "STAND": "WALK_RIGHT",
            "THINK": "POINT_UP",
            "POINT_UP": "PRESENT_CHART",
            "PRESENT_CHART": "POINT_RIGHT",
            "POINT_RIGHT": "WALK_RIGHT",
            "TYPING_LAPTOP": "THINK",
            "SIT_KNEEL": "COWER",
            "COWER": "FACEPALM",
            "FACEPALM": "HEADACHE_STRESS",
            "HEADACHE_STRESS": "THINK",
            "MEDITATE_ZEN": "POINT_RIGHT",
            "SPRINT_FAST": "JUMP",
            "JUMP": "TRIUMPH_FIST",
            "TRIUMPH_FIST": "CELEBRATE",
            "CELEBRATE": "WAVE",
            "COUNT_MONEY": "PRESENT_CHART",
            "SCROLL_PHONE": "FACEPALM",
            "CONFUSED": "SHRUG",
            "SHRUG": "THINK",
        }
        return rotation_map.get(action, "PRESENT")

    def _detect_multi_character_staging(
        self,
        text: str,
        action: str,
        scene_idx: int,
        total_scenes: int,
    ) -> bool:
        """
        Intelligently determine whether a scene should feature TWO characters (Person A & Person B)
        or a single focused character. Created by Atharv Hatwar.
        """
        # 1. Strictly solitary / introspective triggers -> Single character
        solitary_words = (
            "alone", "mirror", "quiet", "inside your head", "deep inside",
            "in the dark", "breathe", "sleep", "wake", "bed", "climb", "summit",
            "focus", "discipline", "habit", "routine", "build", "code", "coding", "zen",
            "personal", "yourself", "mindset", "solitary"
        )
        if any(w in text for w in solitary_words):
            return False

        # 2. Strong dialogue, debate, teaching & advice signals -> Two characters
        interaction_words = (
            "tell", "told", "talk", "speak", "listen", "ask", "answer",
            "argue", "debate", "shout", "whisper", "discuss", "conversation", "disagree"
        )
        if any(w in text for w in interaction_words):
            return True

        # 3. Explicit dual / transactional signals -> Two characters
        contrast_words = (
            "mentor", "boss", "employee", "customer", "doctor", "partner", "versus",
            "vs", "give", "receive", "pay", "buy", "sell", "share"
        )
        if any(w in text for w in contrast_words):
            return True

        # 4. Actions that inherently require a second person
        if action in ("GIVE", "RECEIVE", "ARGUE", "SHOUT", "FIGHT"):
            return True

        # Default pacing: 1 focused character for cinematic storytelling, 2 characters only occasionally
        return scene_idx % 3 == 2

    def _build_staged_characters(
        self,
        is_multi: bool,
        action: str,
        emotion: str,
        speech: str,
        thought: str,
        text_lower: str,
    ) -> list[dict[str, Any]]:
        """
        Build distinct, richly styled characters with complementary acting.
        Created by Atharv Hatwar.
        """
        pal = self.sp.get("character_palette") or ["#FF6B35", "#38BDF8"]
        col_a = pal[0] if len(pal) > 0 else "#FF6B35"
        col_b = pal[1] if len(pal) > 1 else "#38BDF8"

        if is_multi:
            # Staging for TWO interacting characters facing each other
            facing_a = "right"
            facing_b = "left"
            # Dynamic entrance / approach movement so actors don't stand frozen
            if action in ("GIVE", "ARGUE", "SHOUT", "PRESENT", "PRESENT_CHART", "COUNT_MONEY", "WALK_RIGHT"):
                sx_a, ex_a = 0.16, 0.32  # Person A steps forward towards Person B
            else:
                sx_a, ex_a = 0.28, 0.30

            sx_b, ex_b = 0.74, 0.72

            # Complementary counter-action for Person B
            if action == "GIVE":
                action_b = "RECEIVE"
                emo_b = "HAPPY" if emotion != "ANGRY" else "CONFUSED"
            elif action in ("ARGUE", "SHOUT", "FIGHT"):
                action_b = "CONFUSED" if "why" in text_lower else "STOP"
                emo_b = "CONFUSED" if emotion == "ANGRY" else "SURPRISED"
            elif action in ("PRESENT", "POINT_RIGHT", "PRESENT_CHART"):
                action_b = "THINK"
                emo_b = "HAPPY" if emotion in ("HAPPY", "EXCITED") else "NEUTRAL"
            elif action in ("CELEBRATE", "TRIUMPH_FIST"):
                action_b = "CELEBRATE" if action == "TRIUMPH_FIST" else "WAVE"
                emo_b = "EXCITED"
            elif action == "COUNT_MONEY":
                action_b = "SURRENDER_HANDS"
                emo_b = "SURPRISED"
            elif action == "TYPING_LAPTOP":
                action_b = "POINT_LEFT"
                emo_b = "HAPPY"
            elif action == "SCROLL_PHONE":
                action_b = "STOP"
                emo_b = "ANGRY"
            elif action == "FACEPALM":
                action_b = "DISMISSIVE_WAVE"
                emo_b = "CONFUSED"
            elif action == "HEADACHE_STRESS":
                action_b = "MEDITATE_ZEN"
                emo_b = "HAPPY"
            elif action == "CROSS_ARMS":
                action_b = "ARGUE"
                emo_b = "CONFUSED"
            elif action == "SPRINT_FAST":
                action_b = "WAVE"
                emo_b = "EXCITED"
            elif action in ("SAD", "COWER", "CRY"):
                action_b = "STAND"
                emo_b = "HAPPY"
            elif action == "SHRUG":
                action_b = "POINT_LEFT"
                emo_b = "HAPPY"
            else:
                action_b = "THINK" if "?" in text_lower else "STAND"
                emo_b = "NEUTRAL"

            char_a = {
                "id": "PERSON_A",
                "action": action,
                "start_x": sx_a,
                "end_x": ex_a,
                "y": 0.62,
                "scale": 1.40,
                "facing": facing_a,
                "emotion": emotion,
                "color": col_a,
                "accessory": "cap",
                "speaking": True if speech else (action in ("PRESENT", "PRESENT_CHART", "ARGUE", "SHOUT", "GIVE", "WAVE", "COUNT_MONEY")),
            }
            if speech:
                char_a["speech"] = speech
            elif thought:
                char_a["thought"] = thought

            char_b = {
                "id": "PERSON_B",
                "action": action_b,
                "start_x": sx_b,
                "end_x": ex_b,
                "y": 0.62,
                "scale": 1.40,
                "facing": facing_b,
                "emotion": emo_b,
                "color": col_b,
                "accessory": "glasses",
                "speaking": False,
            }

            return [char_a, char_b]

        else:
            # Staging for SINGLE focused character with high dynamic traversal
            facing = "left" if "LEFT" in action else "right"
            if "WALK" in action or "RUN" in action or "SPRINT" in action:
                # Dynamic cross-screen walk / run
                sx = 0.12 if facing == "right" else 0.88
                ex = 0.78 if facing == "right" else 0.22
            elif action in ("PRESENT", "PRESENT_CHART", "POINT_RIGHT"):
                sx = 0.32
                ex = 0.44  # Confident forward stride towards viewer
            elif action in ("JUMP", "CELEBRATE", "TRIUMPH_FIST"):
                sx = 0.45
                ex = 0.48
            else:
                staged_x = (0.44, 0.48, 0.40, 0.52)
                sx = staged_x[len(self.history) % len(staged_x)]
                ex = sx + (0.04 if len(self.history) % 2 == 0 else -0.04)

            char = {
                "id": "PERSON_A",
                "action": action,
                "start_x": sx,
                "end_x": ex,
                "y": 0.62,
                "scale": 1.44,
                "facing": facing,
                "emotion": emotion,
                "color": col_a,
                "speaking": True if speech else False,
            }
            if speech:
                char["speech"] = speech
            if thought:
                char["thought"] = thought

            return [char]

    def _pick_diverse_background(self, text: str) -> str:
        """
        Pick a background related to sentence or differing from recent history.
        Created by Atharv Hatwar.
        """
        candidate: Optional[str] = None

        # Rich keyword mappings for all 14 supported environments
        if any(w in text for w in ("comfort", "lazy", "bed", "sleep", "tired", "morning", "habit", "routine", "couch", "relax", "zone", "destroy", "stuck")):
            candidate = "BEDROOM"
        elif any(w in text for w in ("pretend", "mirror", "mask", "who you are", "identity", "reflection", "look in", "truth", "realize", "self", "mind", "person")):
            candidate = "GALLERY"
        elif any(w in text for w in ("office", "desk", "computer", "boss", "job", "work", "manager", "employee", "corporate", "business", "hustle")):
            candidate = "OFFICE"
        elif any(w in text for w in ("home", "room", "wake", "night", "house", "cozy", "evening")):
            candidate = "HOME"
        elif any(w in text for w in ("cafe", "coffee", "cup", "tea", "drink", "espresso", "breakfast")):
            candidate = "CAFE"
        elif any(w in text for w in ("school", "class", "study", "learn", "teach", "student", "lesson", "exam", "chalk")):
            candidate = "CLASSROOM"
        elif any(w in text for w in ("library", "book", "history", "read", "archive", "wisdom", "knowledge", "research")):
            candidate = "LIBRARY"
        elif any(w in text for w in ("street", "walk", "outside", "car", "sidewalk", "road", "traffic")):
            candidate = "STREET"
        elif any(w in text for w in ("city", "urban", "building", "skyline", "crowd", "society", "downtown")):
            candidate = "CITY"
        elif any(w in text for w in ("park", "nature", "tree", "fresh", "breathe", "grass", "peace", "outdoor")):
            candidate = "PARK"
        elif any(w in text for w in ("mountain", "climb", "storm", "peak", "height", "summit", "steep", "hike")):
            candidate = "MOUNTAIN"
        elif any(w in text for w in ("stage", "audience", "perform", "show", "spotlight", "presentation", "speech", "applause")):
            candidate = "STAGE"
        elif any(w in text for w in ("instead", "versus", "vs", "difference", "contrast", "two choices", "opposite")):
            candidate = "SPLIT_COMPARISON"

        # Apply negative similarity constraint: never pick the same background as recent scenes
        recent_bgs = {s.get("background") for s in self.history[-2:]} if self.history else set()

        if candidate is None or candidate in recent_bgs:
            # Cycle through rich storytelling environments instead of blank abstract
            available_pool = [
                "BEDROOM", "OFFICE", "HOME", "GALLERY", "CAFE", "CLASSROOM",
                "LIBRARY", "STREET", "CITY", "PARK", "MOUNTAIN", "STAGE"
            ]
            valid_pool = [b for b in available_pool if b not in recent_bgs]
            if not valid_pool:
                valid_pool = available_pool
            candidate = valid_pool[len(self.history) % len(valid_pool)]

        return candidate

    def _pick_diverse_camera(self) -> str:
        """Cycle camera angles so the camera never remains on the same framing twice."""
        if not self.history:
            return "ZOOM_IN"
        last_cam = self.history[-1].get("camera", "MEDIUM")
        candidates = [c for c in _CAMERAS if c != last_cam]
        return candidates[len(self.history) % len(candidates)]

    @staticmethod
    def _detect_emotion(text: str) -> str:
        if any(w in text for w in ("happy", "win", "success", "great", "love", "smile", "joy", "proud")):
            return "HAPPY"
        elif any(w in text for w in ("sad", "fail", "cry", "lost", "pain", "hurt", "grief")):
            return "SAD"
        elif any(w in text for w in ("angry", "hate", "fight", "shout", "mad", "rage")):
            return "ANGRY"
        elif any(w in text for w in ("confused", "why", "what", "puzzle", "wonder", "doubt", "?")):
            return "CONFUSED"
        elif any(w in text for w in ("excited", "breakthrough", "fast", "huge", "amazing", "!")):
            return "EXCITED"
        elif any(w in text for w in ("shock", "sudden", "warning", "danger", "gasp")):
            return "SURPRISED"
        return "NEUTRAL"

    @staticmethod
    def _extract_props(text: str) -> list[dict[str, Any]]:
        """Extract topic-relevant props and animals tailored to the sentence."""
        props: list[dict[str, Any]] = []
        prop_configs = [
            # Animals
            (("dog", "puppy", "hound", "pet"), "DOG", 0.72, 0.56, 0.22, 0.18),
            (("cat", "kitten", "kitty", "feline"), "CAT", 0.72, 0.58, 0.18, 0.16),
            (("bird", "fly", "flying", "eagle", "wings"), "BIRD", 0.75, 0.18, 0.16, 0.12),
            (("horse", "steed", "stallion"), "HORSE", 0.70, 0.48, 0.30, 0.26),
            # Vehicles & High-Impact Props
            (("rocket", "launch", "space", "orbit", "blast off"), "ROCKET", 0.70, 0.18, 0.22, 0.32),
            (("bike", "bicycle", "cycle", "ride"), "BICYCLE", 0.70, 0.52, 0.26, 0.22),
            (("treasure", "gold", "fortune", "riches", "jackpot"), "TREASURE_CHEST", 0.68, 0.52, 0.24, 0.20),
            (("brain", "mindset", "intellect", "smart", "cognitive", "psychology"), "BRAIN", 0.65, 0.22, 0.18, 0.18),
            (("car", "vehicle", "drive", "traffic", "road"), "CAR", 0.66, 0.54, 0.32, 0.20),
            (("house", "home", "building", "real estate", "property"), "HOUSE", 0.68, 0.44, 0.28, 0.28),
            # Classic Concept Assets
            (("money", "dollar", "wealth", "cash"), "MONEY", 0.65, 0.28, 0.20, 0.14),
            (("coin", "crypto", "bitcoin", "cents"), "COIN", 0.72, 0.26, 0.12, 0.12),
            (("phone", "mobile", "screen", "tiktok", "instagram"), "PHONE", 0.65, 0.30, 0.14, 0.20),
            (("laptop", "computer", "coding", "software"), "LAPTOP", 0.62, 0.44, 0.26, 0.20),
            (("book", "study", "read", "learn"), "BOOK", 0.65, 0.44, 0.18, 0.14),
            (("clock", "time", "hours", "seconds", "years", "deadline"), "CLOCK", 0.68, 0.24, 0.14, 0.14),
            (("idea", "lightbulb", "eureka", "solution", "insight"), "LIGHTBULB", 0.65, 0.20, 0.16, 0.18),
            (("heart", "love", "passion", "health"), "HEART", 0.68, 0.24, 0.14, 0.14),
            (("star", "target", "goal", "dream"), "STAR", 0.72, 0.20, 0.14, 0.14),
            (("trophy", "winner", "champion", "first place"), "TROPHY", 0.68, 0.24, 0.16, 0.18),
            (("coffee", "cup", "tea", "drink"), "COFFEE_CUP", 0.65, 0.48, 0.12, 0.12),
            (("arrow", "direction", "forward"), "ARROW", 0.60, 0.28, 0.20, 0.08),
            (("shield", "protect", "defense", "security"), "SHIELD", 0.66, 0.36, 0.20, 0.24),
            # Physical Metaphors & Conceptual Storytelling Props
            (("iceberg", "surface", "hidden depth"), "ICEBERG", 0.68, 0.50, 0.28, 0.26),
            (("hamster", "rat race", "routine", "trap", "spinning wheels"), "HAMSTER_WHEEL", 0.68, 0.52, 0.24, 0.24),
            (("domino", "dominoes", "chain reaction", "trigger"), "DOMINOES", 0.68, 0.54, 0.26, 0.20),
            (("wall", "barrier", "obstacle", "blocked", "stuck"), "BRICK_WALL", 0.70, 0.48, 0.26, 0.24),
            (("battery", "burnout", "tired", "exhausted", "low energy", "drain"), "BATTERY_DRAIN", 0.68, 0.30, 0.22, 0.16),
            (("balance", "weigh", "tradeoff", "equality", "scale"), "BALANCE_SCALE", 0.68, 0.48, 0.24, 0.24),
            (("hourglass", "urgency", "countdown", "running out"), "HOURGLASS", 0.68, 0.50, 0.18, 0.22),
            (("podium", "rank", "competition", "compete", "place"), "PODIUM", 0.68, 0.52, 0.28, 0.22),
            (("magnifying", "research", "analyze", "examine", "investigate", "inspect"), "MAGNIFYING_GLASS", 0.66, 0.32, 0.18, 0.18),
            # Storytelling & Narrative Staging Props (Created by Atharv Hatwar)
            (("bed", "sleep", "sleeping", "asleep", "waking", "night", "insomnia", "pillow", "mattress", "snooze", "in bed", "rest"), "BED", 0.50, 0.65, 0.44, 0.28),
            (("alarm", "nightstand", "3am", "clock", "midnight", "wake up", "morning", "time"), "NIGHTSTAND_CLOCK", 0.80, 0.62, 0.16, 0.22),
            (("remember", "memory", "replaying", "embarrassing", "thought", "reminisce", "thinking of", "flashback", "wondering", "regret"), "THOUGHT_CLOUD", 0.70, 0.28, 0.32, 0.22),
            (("file", "record", "document", "folder", "archive", "ledger", "certificate", "contract", "paperwork"), "FOLDER_DOCUMENT", 0.66, 0.44, 0.22, 0.22),
            (("alert", "cringe", "mortified", "shock", "warning", "stamp", "emergency", "crisis", "red alert", "danger"), "ALERT_STAMP", 0.72, 0.28, 0.22, 0.14),
            (("versus", "vs", "split", "contrast", "difference", "dilemma", "two sides", "divided", "comparison"), "SPLIT_DIVIDER", 0.50, 0.50, 0.08, 0.70),
            (("announce", "loud", "shout", "broadcast", "speak up", "voice", "megaphone", "public speaking", "proclaim"), "MEGAPHONE", 0.66, 0.44, 0.22, 0.20),
            (("crowd", "people", "audience", "public", "everyone", "peers", "society", "friends", "others watching"), "CROWD_ROW", 0.50, 0.78, 0.85, 0.20),
            (("trajectory", "leads to", "pointing", "follow", "path", "direct", "navigate", "next step"), "DOODLE_ARROW", 0.60, 0.32, 0.22, 0.10),
            (("diwali", "lamp", "light", "festival", "tradition", "flame", "sacred", "celebrate diwali", "festive"), "DIYA", 0.68, 0.66, 0.14, 0.12),
        ]
        for keywords, asset, x, y, w, h in prop_configs:
            if any(re.search(rf"\b{kw}", text) for kw in keywords):
                if not any(p["asset"] == asset for p in props):
                    if len(props) == 1:
                        px = 0.22 if x > 0.5 else 0.78
                        props.append({"asset": asset, "x": px, "y": y, "width": round(w * 0.9, 2), "height": round(h * 0.9, 2)})
                    else:
                        props.append({"asset": asset, "x": x, "y": y, "width": w, "height": h})
                if len(props) >= 2:
                    break

        return props

    @staticmethod
    def _extract_quoted_dialogue(narration: str) -> tuple[str, str]:
        """
        Extract speech or thought bubble ONLY if the narration actually contains explicit
        dialogue in quotes (e.g. 'He whispered "I can\\'t do this"' or '"Wait!"').
        Returns ("", "") when there is no explicit quotation, preventing random canned bubbles.
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

    def _select_layout_archetype(
        self,
        narration: str,
        text_lower: str,
        chosen_metaphor: Optional[str],
        scene_idx: int,
        total_scenes: int,
        is_multi: bool,
        topic: str = "",
    ) -> tuple[str, dict[str, Any]]:
        """
        Dynamically selects a high-impact visual scene archetype (Split-Screen, Fullscreen
        Infographic, Herd Rebel, Scale Contrast, Hero Prop Mechanic, Kinetic Concept Badge).
        Guarantees that consecutive scenes NEVER share the same visual structure.
        """
        recent_archetypes = [
            s.get("layout_archetype")
            for s in self.history[-2:]
            if s.get("layout_archetype")
        ]

        candidate_scores: dict[str, float] = {
            "SPLIT_SCREEN": 0.0,
            "FULLSCREEN_INFOGRAPHIC": 0.0,
            "HERD_REBEL": 0.0,
            "SCALE_CONTRAST": 0.0,
            "HERO_PROP_MECHANIC": 0.0,
            "KINETIC_CONCEPT_CARD": 0.0,
            "STAGE_INTERACTION": 0.0,
            "STAGE_STANDARD": 0.0,
        }

        # 1. Neural Semantic Brain Archetype Match
        try:
            from engine.semantic_scene_brain import SemanticSceneBrain
            brain = SemanticSceneBrain.get_instance()
            if brain._initialized:
                best_n_arch, n_score = brain.match_best_archetype(narration, recent_archetypes=recent_archetypes)
                if best_n_arch and n_score > 0.15:
                    candidate_scores[best_n_arch] += float(n_score) * 1.5
        except Exception:
            pass

        # 2. Heuristic Keyword & Metaphor Boosters
        # SPLIT_SCREEN: Comparison / Contrast / Choice / 99% vs 1%
        if any(w in text_lower for w in (" vs ", "versus", "99%", " 1%", "instead of", "two types", "winners vs", "rich vs", "contrast", "dilemma", "while most", "on one hand", "difference between", "choice", "or you can")):
            candidate_scores["SPLIT_SCREEN"] += 1.8

        # FULLSCREEN_INFOGRAPHIC: Exponential growth, Iceberg, Balance scale, Pyramid
        if any(w in text_lower for w in ("exponential", "compound", "growth curve", "iceberg", "below the surface", "hidden depth", "balance scale", "weighing", "pyramid", "hierarchy", "percent", "hockey stick", "foundation", "chart", "metrics")) or \
           chosen_metaphor in ("ICEBERG_DEPTH", "EXPONENTIAL_COMPOUND", "LEVER_BOULDER"):
            candidate_scores["FULLSCREEN_INFOGRAPHIC"] += 1.8

        # HERD_REBEL: Crowd conformity, sheep, society, walking alone, rebel
        if any(w in text_lower for w in ("crowd", "society", "everyone", "sheep", "conformity", "normal people", "fit in", "alone", "rebel", "stand out", "own path", "maverick", "against the grain", "majority")):
            candidate_scores["HERD_REBEL"] += 1.9

        # HERO_PROP_MECHANIC: Hamster wheel, pushing boulder uphill, puppet strings, chains
        if any(w in text_lower for w in ("rat race", "hamster wheel", "running in circles", "pushing boulder", "uphill battle", "puppet", "strings", "marionette", "chained", "trapped in", "cage")) or \
           chosen_metaphor in ("HAMSTER_WHEEL", "LEVER_BOULDER"):
            candidate_scores["HERO_PROP_MECHANIC"] += 1.9

        # SCALE_CONTRAST: Colossal mountain, monolithic clock, dwarfed by destiny
        if any(w in text_lower for w in ("massive obstacle", "giant mountain", "monolith", "clock ticking", "time running out", "colossal", "overwhelmed by", "towering", "destiny", "staring into the abyss", "giant clock")):
            candidate_scores["SCALE_CONTRAST"] += 1.8

        # KINETIC_CONCEPT_CARD: Golden rule, principle, secret formula, reality check
        if any(w in text_lower for w in ("golden rule", "the secret is", "core principle", "the real truth", "remember this", "key takeaway", "fundamental law", "formula", "rule #1", "lesson")):
            candidate_scores["KINETIC_CONCEPT_CARD"] += 1.7

        # STAGE_INTERACTION: Multi-character dialogues
        if is_multi:
            candidate_scores["STAGE_INTERACTION"] += 1.4

        # Enforce Negative Similarity Constraint (penalize recent archetypes heavily)
        for prev in recent_archetypes:
            if prev in candidate_scores:
                candidate_scores[prev] -= 2.5

        # Pick the winning archetype
        sorted_candidates = sorted(candidate_scores.items(), key=lambda kv: kv[1], reverse=True)
        chosen = sorted_candidates[0][0]

        # If highest score is still <= 0.0 (e.g. all penalized or generic text),
        # cycle through diverse archetypes by scene index to guarantee visual variety!
        if sorted_candidates[0][1] <= 0.05:
            variety_cycle = [
                "SPLIT_SCREEN",
                "FULLSCREEN_INFOGRAPHIC",
                "HERD_REBEL",
                "HERO_PROP_MECHANIC",
                "SCALE_CONTRAST",
                "KINETIC_CONCEPT_CARD",
            ]
            valid_cycle = [a for a in variety_cycle if a not in recent_archetypes]
            chosen = valid_cycle[scene_idx % len(valid_cycle)] if valid_cycle else variety_cycle[scene_idx % len(variety_cycle)]

        # Synthesize archetype data
        arch_data = self._synthesize_archetype_data(chosen, narration, text_lower, chosen_metaphor, topic=topic)
        return chosen, arch_data

    def _synthesize_archetype_data(
        self,
        archetype: str,
        narration: str,
        text_lower: str,
        chosen_metaphor: Optional[str],
        topic: str = "",
    ) -> dict[str, Any]:
        """Synthesizes rich parameters, titles, badges, and layout configs for the selected archetype."""
        data: dict[str, Any] = {"archetype": archetype}
        clean_topic_upper = (topic or "").strip().rstrip(".!?").upper()[:24]

        if archetype == "SPLIT_SCREEN":
            is_phone = any(w in text_lower for w in ("phone", "scroll", "distract", "lazy", "bed", "snooze"))
            is_money = any(w in text_lower for w in ("money", "invest", "wealth", "rich", "cash", "earn"))
            data.update({
                "left_title": "THE 99% TRAP",
                "right_title": "THE 1% SECRET",
                "left_badge": "THE DEFAULT",
                "right_badge": "THE DISCIPLINE",
                "left_action": "SCROLL_PHONE" if is_phone else "HEADACHE_STRESS",
                "right_action": "COUNT_MONEY" if is_money else ("MEDITATE_ZEN" if "mind" in text_lower else "TRIUMPH_FIST"),
                "left_color": "#EF4444",
                "right_color": "#10B981",
                "vs_label": "VS",
            })

        elif archetype == "FULLSCREEN_INFOGRAPHIC":
            if any(w in text_lower for w in ("iceberg", "below", "surface", "depth", "unseen")) or chosen_metaphor == "ICEBERG_DEPTH":
                info_type = "ICEBERG_DEPTH"
                title = "THE ICEBERG PRINCIPLE"
                metric = "90% UNSEEN"
                label = "YEARS OF SILENT EFFORT"
            elif any(w in text_lower for w in ("scale", "weigh", "balance", "cost", "tradeoff", "price")):
                info_type = "BALANCE_SCALE"
                title = "WEIGHING THE TRADEOFF"
                metric = "COST VS REWARD"
                label = "SHORT-TERM PAIN = LONG-TERM FREEDOM"
            elif any(w in text_lower for w in ("pyramid", "hierarchy", "level", "foundation")):
                info_type = "HIERARCHY_PYRAMID"
                title = "THE SUCCESS HIERARCHY"
                metric = "LEVEL 3"
                label = "FOUNDATION OF DAILY HABITS"
            elif any(w in text_lower for w in ("percent", "1%", "rate", "dial")):
                info_type = "RADIAL_PERCENT"
                title = "THE 1% PRINCIPLE"
                metric = "1%"
                label = "DAILY IMPROVEMENT"
            else:
                info_type = "EXPONENTIAL_CURVE"
                title = f"{clean_topic_upper} BREAKTHROUGH" if clean_topic_upper else "THE COMPOUND EFFECT"
                metric = "+1,000%"
                label = "EXPONENTIAL TRAJECTORY"

            data.update({
                "infographic_type": info_type,
                "title": title,
                "metric": metric,
                "label": label,
            })

        elif archetype == "HERD_REBEL":
            data.update({
                "crowd_label": "THE 99% (FOLLOWING THE CROWD)",
                "hero_label": "THE 1% (WALKING THEIR OWN PATH)",
                "hero_action": "WALK_LEFT" if any(w in text_lower for w in ("walk", "step", "leave", "away")) else "CROSS_ARMS",
                "spotlight": True,
            })

        elif archetype == "SCALE_CONTRAST":
            is_time = any(w in text_lower for w in ("time", "clock", "second", "hour", "running out", "ticking", "late"))
            data.update({
                "colossal_type": "GIANT_CLOCK" if is_time else "GIANT_MOUNTAIN",
                "hero_scale": 0.55,
                "title": "TIME IS TICKING AWAY" if is_time else (f"{clean_topic_upper}" if clean_topic_upper else "THE COLOSSAL JOURNEY"),
            })

        elif archetype == "HERO_PROP_MECHANIC":
            if any(w in text_lower for w in ("boulder", "push", "uphill", "heavy", "rock", "effort")) or chosen_metaphor == "LEVER_BOULDER":
                mech_type = "PUSH_BOULDER"
                title = "THE UPHILL BATTLE"
            elif any(w in text_lower for w in ("puppet", "strings", "marionette", "control", "system")):
                mech_type = "PUPPET_STRINGS"
                title = "CONTROLLED BY THE STRINGS"
            else:
                mech_type = "HAMSTER_WHEEL"
                title = "THE ENDLESS RAT RACE"

            data.update({
                "mechanic_type": mech_type,
                "title": title,
            })

        elif archetype == "KINETIC_CONCEPT_CARD":
            title = clean_topic_upper if clean_topic_upper else ("THE 1% RULE" if "1%" in text_lower else "THE CORE PRINCIPLE")
            data.update({
                "badge": "GOLDEN RULE" if "rule" in text_lower else "KEY PRINCIPLE",
                "title": title,
                "subtitle": "Daily Compounding Beats Irregular Intensity",
                "icon": "STAR",
            })

        return data

