"""
Stickman Animation Engine - Crisp 2x-Supersampled 2D Vector Character Engine.
=========================================================================
Integrates with the 11 Director & Autopilot Style Packs (A1-A6, B1-B5).
Created by Atharv Hatwar.
Features:
- 2x supersampled sprite rasterization for silky-smooth anti-aliased strokes
- Quadratic Bezier organic limb smoothing + anatomical shoulder-to-wrist tapering
- Spring overshoot & motion-feel curves per StylePack (gentle, snappy, tense, etc.)
- Rich style costumes: red beanie & yellow tee (A2), caveman animal hides (A3),
  cozy knit sweaters & scarves (A4), Victorian frock coats & top hats (A5),
  amber-lit noir trench hoodies (A6), hooded white-gloved survivor (B4),
  glasses + bowtie recurring presenter host (B5), and hand-drawn ink wobble (B2).
- Alive faces with irises/pupils, eye catchlights, blinking, lip-sync mouths,
  teardrops, blush, sweatdrops, and anger/surprise cues.
"""

from __future__ import annotations

import hashlib
import math
from typing import Any, Optional

from PIL import Image, ImageDraw

from styles.style_packs import resolve_style_pack


# ---------------------------------------------------------------------------
# Action -> Multi-beat Keyframe Sequences
# ---------------------------------------------------------------------------
POSE_SEQUENCES: dict[str, list[str]] = {
    "WALK_RIGHT":      ["WALK_1", "WALK_2", "WALK_1", "WALK_2"],
    "WALK_LEFT":       ["WALK_1", "WALK_2", "WALK_1", "WALK_2"],
    "RUN":             ["RUN_1", "RUN_2", "RUN_1", "RUN_2"],
    "SNEAK":           ["SNEAK_1", "SNEAK_2", "SNEAK_1", "SNEAK_2"],
    "STAND":           ["STAND", "STAND_BREATHE", "STAND", "STAND_BREATHE"],
    "THINK":           ["STAND", "THINK_CHIN", "THINK_TILT", "THINK_NOD", "THINK_CHIN"],
    "POINT":           ["STAND", "PRESENT_ANTICIPATE", "POINT_RIGHT", "PRESENT_TAP", "POINT_RIGHT"],
    "POINT_RIGHT":     ["STAND", "PRESENT_ANTICIPATE", "POINT_RIGHT", "PRESENT_TAP", "POINT_RIGHT"],
    "POINT_LEFT":      ["STAND", "POINT_LEFT", "POINT_LEFT", "STAND"],
    "POINT_UP":        ["STAND", "PRESENT_ANTICIPATE", "POINT_UP", "POINT_UP", "STAND"],
    "CELEBRATE":       ["STAND_CROUCH", "JUMP", "CELEBRATE", "WAVE", "CELEBRATE"],
    "CRY":             ["CRY", "BOW", "CRY", "BOW"],
    "LAUGH":           ["LAUGH", "LAUGH_UP", "LAUGH", "LAUGH_UP"],
    "ANGRY":           ["STAND", "ANGRY", "POINT_RIGHT", "ANGRY"],
    "SHOUT":           ["STAND", "SHOUT", "POINT_RIGHT", "SHOUT"],
    "FIGHT":           ["FIGHT_1", "FIGHT_2", "FIGHT_1", "FIGHT_2"],
    "CONFUSED":        ["STAND", "CONFUSED", "SHRUG_UP", "CONFUSED"],
    "SHRUG":           ["STAND", "SHRUG_UP", "SHRUG", "SHRUG_SETTLE", "STAND"],
    "SIT":             ["SIT", "SIT_TYPE", "SIT", "SIT_TYPE"],
    "KNEEL":           ["SIT_KNEEL", "RECEIVE", "SIT_KNEEL"],
    "COWER":           ["STAND_CROUCH", "COWER", "COWER", "STAND_CROUCH"],
    "JUMP":            ["STAND_CROUCH", "JUMP", "CELEBRATE", "STAND_CROUCH"],
    "WAVE":            ["STAND", "WAVE", "WAVE_ALT", "WAVE", "WAVE_ALT"],
    "GIVE":            ["STAND", "GIVE", "GIVE", "STOP_HAND"],
    "RECEIVE":         ["SIT_KNEEL", "RECEIVE", "REACH", "SIT_KNEEL"],
    "REACH":           ["SIT_KNEEL", "REACH", "REACH"],
    "STOP":            ["POINT_RIGHT", "STOP_HAND", "STOP_HAND"],
    "HOLD_OBJECT":     ["STAND", "HOLD_OBJECT", "POINT_RIGHT", "HOLD_OBJECT"],
    "PRESENT":         ["STAND", "PRESENT_ANTICIPATE", "PRESENT_POINT", "PRESENT_GESTURE", "PRESENT_POINT"],
    "PHONE_CALL":      ["STAND", "HOLD_OBJECT", "THINK_TILT"],
    "ARGUE":           ["POINT_RIGHT", "SHOUT", "ANGRY", "STOP_HAND"],
    "READ":            ["SIT", "HOLD_OBJECT", "SIT", "HOLD_OBJECT"],
    "READ_SCROLL":     ["STAND", "HOLD_OBJECT", "THINK", "HOLD_OBJECT"],
    "WRITE":           ["SIT", "SIT_TYPE", "SIT", "SIT_TYPE"],
    "FALL":            ["STAND", "FALL"],
    "STRUGGLE":        ["CONFUSED", "STOP_HAND", "BOW", "SHRUG"],
    "HUNT_SPEAR":      ["STAND_CROUCH", "POINT_RIGHT", "STOP_HAND"],
    "WARM_FIRE":       ["SIT_KNEEL", "GIVE", "SIT_KNEEL"],
    # Expressive Modern Creator & Storytelling Actions (Atharv Hatwar)
    "TYPING_LAPTOP":   ["TYPING_1", "TYPING_2", "TYPING_PAUSE", "TYPING_1", "TYPING_2"],
    "COUNT_MONEY":     ["COUNT_MONEY_1", "COUNT_MONEY_2", "COUNT_MONEY_1", "COUNT_MONEY_2"],
    "FACEPALM":        ["STAND", "FACEPALM_ANTICIPATE", "FACEPALM", "FACEPALM_SLIDE", "STAND"],
    "HEADACHE_STRESS": ["STAND", "STRESS_HEAD", "STRESS_TREMBLE", "STRESS_BREATHE", "STRESS_HEAD"],
    "MEDITATE_ZEN":    ["STAND_CROUCH", "MEDITATE_ZEN", "MEDITATE_ZEN_FLOAT", "MEDITATE_ZEN"],
    "SPRINT_FAST":     ["SPRINT_1", "SPRINT_2", "SPRINT_1", "SPRINT_2"],
    "TRIUMPH_FIST":    ["STAND_CROUCH", "TRIUMPH_FIST", "CELEBRATE", "TRIUMPH_FIST"],
    "DISMISSIVE_WAVE": ["STAND", "DISMISS_WAVE", "DISMISS_WAVE", "STAND"],
    "SURRENDER_HANDS": ["STAND", "SURRENDER", "SURRENDER"],
    "PRESENT_CHART":   ["STAND", "PRESENT_ANTICIPATE", "PRESENT_POINT", "PRESENT_TRACE", "PRESENT_TAP", "PRESENT_GESTURE"],
    "SCROLL_PHONE":    ["PHONE_HOLD", "PHONE_SCROLL", "PHONE_TILT", "PHONE_TAP", "PHONE_SCROLL"],
    "CROSS_ARMS":      ["STAND", "CROSS_ARMS", "CROSS_TAP", "CROSS_ARMS"],
    # Story-Driven Contextual Actions (Atharv Hatwar)
    "TEXTING_PHONE":       ["TEXTING_PHONE", "PHONE_SCROLL", "TEXTING_PHONE", "PHONE_TAP"],
    "LOOK_PHONE":          ["LOOK_PHONE", "LOOK_PHONE", "THINK_TILT", "LOOK_PHONE"],
    "CONFUSED_WONDERING":  ["CONFUSED_WONDERING", "CONFUSED", "SHRUG_UP", "CONFUSED_WONDERING"],
    "CHECK_NOTIFICATIONS": ["LOOK_PHONE", "CHECK_NOTIFICATIONS", "CHECK_NOTIFICATIONS", "LOOK_PHONE"],
    "HUG":                 ["STAND", "HUG", "HUG", "STAND"],
    "FALL_IN_LOVE":        ["STAND", "FALL_IN_LOVE", "CELEBRATE", "FALL_IN_LOVE"],
    "TURNING_AWAY":        ["STAND", "TURNING_AWAY", "TURNING_AWAY", "STAND"],
    "WAITING":             ["STAND", "WAITING", "CROSS_ARMS", "WAITING"],
    "DISAPPOINTED":        ["STAND", "DISAPPOINTED", "BOW", "DISAPPOINTED"],
}

# Raw canonical joint templates relative to hip center (0, 0)
_BASE_POSES: dict[str, dict[str, tuple[float, float]]] = {
    "STAND": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-21, -18), "r_elbow": (21, -18),
        "l_hand": (-22, 4), "r_hand": (22, 4),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "STAND_BREATHE": {
        "head": (0, -65.5), "neck": (0, -45),
        "l_shoulder": (-16, -40), "r_shoulder": (16, -40),
        "l_elbow": (-22, -19), "r_elbow": (22, -19),
        "l_hand": (-23, 3), "r_hand": (23, 3),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "STAND_CROUCH": {
        "head": (4, -52), "neck": (2, -34),
        "l_shoulder": (-16, -30), "r_shoulder": (16, -30),
        "l_elbow": (-24, -12), "r_elbow": (24, -12),
        "l_hand": (-28, 4), "r_hand": (28, 4),
        "hips": (0, 8),
        "l_knee": (-16, 30), "r_knee": (16, 30),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "COWER": {
        "head": (-6, -46), "neck": (-3, -30),
        "l_shoulder": (-14, -27), "r_shoulder": (14, -27),
        "l_elbow": (-18, -32), "r_elbow": (18, -34),
        "l_hand": (-10, -52), "r_hand": (12, -52),
        "hips": (0, 10),
        "l_knee": (-18, 32), "r_knee": (14, 34),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "THINK": {
        "head": (5, -64), "neck": (2, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -16), "r_elbow": (28, -24),
        "l_hand": (-18, 2), "r_hand": (13, -46),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "THINK_TILT": {
        "head": (-4, -63), "neck": (-1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-26, -20), "r_elbow": (27, -25),
        "l_hand": (-24, 0), "r_hand": (11, -47),
        "hips": (0, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "POINT_RIGHT": {
        "head": (3, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -16), "r_elbow": (38, -36),
        "l_hand": (-22, 5), "r_hand": (62, -34),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (12, 27),
        "l_foot": (-16, 56), "r_foot": (16, 56),
    },
    "POINT_LEFT": {
        "head": (-3, -64), "neck": (-1, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (15, -39),
        "l_elbow": (-38, -36), "r_elbow": (22, -16),
        "l_hand": (-62, -34), "r_hand": (22, 5),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (12, 27),
        "l_foot": (-16, 56), "r_foot": (16, 56),
    },
    "POINT_UP": {
        "head": (2, -65), "neck": (0, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -16), "r_elbow": (30, -56),
        "l_hand": (-20, 4), "r_hand": (36, -84),
        "hips": (0, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "WAVE": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -16), "r_elbow": (32, -52),
        "l_hand": (-22, 5), "r_hand": (48, -74),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "WAVE_ALT": {
        "head": (3, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -16), "r_elbow": (36, -48),
        "l_hand": (-22, 5), "r_hand": (32, -76),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "SIT": {
        "head": (2, -58), "neck": (1, -39),
        "l_shoulder": (-12, -35), "r_shoulder": (12, -35),
        "l_elbow": (6, -19), "r_elbow": (18, -17),
        "l_hand": (26, -16), "r_hand": (36, -12),
        "hips": (0, 6),
        "l_knee": (26, 8), "r_knee": (32, 10),
        "l_foot": (28, 42), "r_foot": (36, 42),
    },
    "SIT_TYPE": {
        "head": (5, -56), "neck": (3, -38),
        "l_shoulder": (-12, -34), "r_shoulder": (12, -34),
        "l_elbow": (8, -18), "r_elbow": (22, -17),
        "l_hand": (28, -15), "r_hand": (38, -14),
        "hips": (0, 6),
        "l_knee": (26, 8), "r_knee": (32, 10),
        "l_foot": (28, 42), "r_foot": (36, 42),
    },
    "SIT_KNEEL": {
        "head": (0, -45), "neck": (0, -27),
        "l_shoulder": (-14, -23), "r_shoulder": (14, -23),
        "l_elbow": (-20, -4), "r_elbow": (24, -6),
        "l_hand": (-18, 14), "r_hand": (36, -2),
        "hips": (0, 14),
        "l_knee": (-22, 36), "r_knee": (20, 36),
        "l_foot": (-32, 54), "r_foot": (26, 54),
    },
    "BOW": {
        "head": (18, -32), "neck": (10, -20),
        "l_shoulder": (-10, -16), "r_shoulder": (16, -16),
        "l_elbow": (-18, 4), "r_elbow": (24, 4),
        "l_hand": (-18, 22), "r_hand": (26, 22),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CRY": {
        "head": (2, -57), "neck": (1, -39),
        "l_shoulder": (-15, -35), "r_shoulder": (15, -35),
        "l_elbow": (-22, -22), "r_elbow": (22, -22),
        "l_hand": (-8, -48), "r_hand": (10, -48),
        "hips": (0, 2),
        "l_knee": (-11, 28), "r_knee": (11, 28),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "LAUGH": {
        "head": (-3, -62), "neck": (-1, -43),
        "l_shoulder": (-17, -38), "r_shoulder": (17, -38),
        "l_elbow": (-30, -14), "r_elbow": (30, -14),
        "l_hand": (-20, 2), "r_hand": (20, 2),
        "hips": (0, 3),
        "l_knee": (-12, 28), "r_knee": (12, 28),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "LAUGH_UP": {
        "head": (-5, -65), "neck": (-2, -45),
        "l_shoulder": (-18, -40), "r_shoulder": (18, -40),
        "l_elbow": (-32, -22), "r_elbow": (32, -22),
        "l_hand": (-28, -38), "r_hand": (28, -38),
        "hips": (0, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "ANGRY": {
        "head": (3, -62), "neck": (1, -43),
        "l_shoulder": (-18, -38), "r_shoulder": (18, -38),
        "l_elbow": (-32, -16), "r_elbow": (32, -16),
        "l_hand": (-26, 2), "r_hand": (26, 2),
        "hips": (0, 2),
        "l_knee": (-14, 27), "r_knee": (14, 27),
        "l_foot": (-18, 56), "r_foot": (18, 56),
    },
    "SHRUG": {
        "head": (0, -60), "neck": (0, -42),
        "l_shoulder": (-20, -42), "r_shoulder": (20, -42),
        "l_elbow": (-34, -22), "r_elbow": (34, -22),
        "l_hand": (-42, -32), "r_hand": (42, -32),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CONFUSED": {
        "head": (6, -63), "neck": (2, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-24, -18), "r_elbow": (32, -36),
        "l_hand": (-22, 4), "r_hand": (14, -64),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "HOLD_OBJECT": {
        "head": (2, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -16), "r_elbow": (30, -24),
        "l_hand": (-20, 4), "r_hand": (42, -34),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "GIVE": {
        "head": (5, -63), "neck": (2, -43),
        "l_shoulder": (-13, -38), "r_shoulder": (18, -38),
        "l_elbow": (-18, -14), "r_elbow": (38, -26),
        "l_hand": (-18, 4), "r_hand": (58, -20),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (14, 27),
        "l_foot": (-16, 56), "r_foot": (18, 56),
    },
    "RECEIVE": {
        "head": (4, -46), "neck": (2, -28),
        "l_shoulder": (-14, -24), "r_shoulder": (15, -24),
        "l_elbow": (-22, -8), "r_elbow": (30, -14),
        "l_hand": (-10, -2), "r_hand": (48, -14),
        "hips": (0, 14),
        "l_knee": (-22, 36), "r_knee": (20, 36),
        "l_foot": (-32, 54), "r_foot": (26, 54),
    },
    "REACH": {
        "head": (7, -48), "neck": (3, -29),
        "l_shoulder": (-14, -24), "r_shoulder": (17, -24),
        "l_elbow": (-16, -8), "r_elbow": (38, -26),
        "l_hand": (-10, 4), "r_hand": (56, -34),
        "hips": (0, 14),
        "l_knee": (-22, 36), "r_knee": (20, 36),
        "l_foot": (-32, 54), "r_foot": (26, 54),
    },
    "STOP_HAND": {
        "head": (-2, -64), "neck": (-1, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -16), "r_elbow": (36, -36),
        "l_hand": (-22, 4), "r_hand": (54, -46),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (12, 27),
        "l_foot": (-16, 56), "r_foot": (16, 56),
    },
    "SHOUT": {
        "head": (6, -65), "neck": (2, -44),
        "l_shoulder": (-18, -39), "r_shoulder": (18, -39),
        "l_elbow": (-30, -24), "r_elbow": (34, -28),
        "l_hand": (-32, -44), "r_hand": (48, -44),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (12, 27),
        "l_foot": (-16, 56), "r_foot": (16, 56),
    },
    "CELEBRATE": {
        "head": (0, -78), "neck": (0, -56),
        "l_shoulder": (-18, -51), "r_shoulder": (18, -51),
        "l_elbow": (-32, -66), "r_elbow": (32, -66),
        "l_hand": (-42, -88), "r_hand": (42, -88),
        "hips": (0, -14),
        "l_knee": (-16, 12), "r_knee": (16, 12),
        "l_foot": (-20, 40), "r_foot": (20, 40),
    },
    "JUMP": {
        "head": (0, -82), "neck": (0, -61),
        "l_shoulder": (-16, -55), "r_shoulder": (16, -55),
        "l_elbow": (-28, -68), "r_elbow": (28, -68),
        "l_hand": (-34, -84), "r_hand": (34, -84),
        "hips": (0, -18),
        "l_knee": (-16, 8), "r_knee": (16, 8),
        "l_foot": (-12, 30), "r_foot": (12, 30),
    },
    "FIGHT_1": {
        "head": (6, -60), "neck": (3, -41),
        "l_shoulder": (-14, -37), "r_shoulder": (18, -37),
        "l_elbow": (-8, -22), "r_elbow": (36, -34),
        "l_hand": (8, -30), "r_hand": (58, -38),
        "hips": (0, 3),
        "l_knee": (-18, 28), "r_knee": (18, 26),
        "l_foot": (-26, 56), "r_foot": (24, 56),
    },
    "FIGHT_2": {
        "head": (-2, -60), "neck": (0, -41),
        "l_shoulder": (-18, -37), "r_shoulder": (14, -37),
        "l_elbow": (-34, -30), "r_elbow": (12, -22),
        "l_hand": (-46, -36), "r_hand": (24, -34),
        "hips": (0, 3),
        "l_knee": (-14, 28), "r_knee": (18, 28),
        "l_foot": (-18, 56), "r_foot": (26, 56),
    },
    "FALL": {
        "head": (40, -12), "neck": (24, -4),
        "l_shoulder": (14, -14), "r_shoulder": (26, 10),
        "l_elbow": (-4, -18), "r_elbow": (40, 22),
        "l_hand": (-20, -24), "r_hand": (54, 30),
        "hips": (0, 12),
        "l_knee": (-18, 30), "r_knee": (-6, 36),
        "l_foot": (-38, 46), "r_foot": (-22, 54),
    },
    # --- Modern Expressive Poses (Created by Atharv Hatwar) ---
    "TYPING_1": {
        "head": (3, -60), "neck": (1, -40),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-12, -22), "r_elbow": (12, -20),
        "l_hand": (-10, -10), "r_hand": (14, -4),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "TYPING_2": {
        "head": (3, -60), "neck": (1, -40),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-12, -20), "r_elbow": (12, -22),
        "l_hand": (-12, -4), "r_hand": (10, -10),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "COUNT_MONEY_1": {
        "head": (2, -61), "neck": (1, -42),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-14, -20), "r_elbow": (14, -20),
        "l_hand": (-6, -26), "r_hand": (4, -28),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "COUNT_MONEY_2": {
        "head": (2, -61), "neck": (1, -42),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-14, -20), "r_elbow": (14, -20),
        "l_hand": (-4, -28), "r_hand": (6, -26),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "FACEPALM": {
        "head": (2, -58), "neck": (1, -40),
        "l_shoulder": (-15, -38), "r_shoulder": (15, -38),
        "l_elbow": (-20, -18), "r_elbow": (16, -42),
        "l_hand": (-22, 4), "r_hand": (4, -62),
        "hips": (0, 2),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "STRESS_HEAD": {
        "head": (0, -58), "neck": (0, -40),
        "l_shoulder": (-16, -38), "r_shoulder": (16, -38),
        "l_elbow": (-32, -44), "r_elbow": (32, -44),
        "l_hand": (-14, -64), "r_hand": (14, -64),
        "hips": (0, 2),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "MEDITATE_ZEN": {
        "head": (0, -56), "neck": (0, -38),
        "l_shoulder": (-14, -34), "r_shoulder": (14, -34),
        "l_elbow": (-22, -14), "r_elbow": (22, -14),
        "l_hand": (-18, 12), "r_hand": (18, 12),
        "hips": (0, 10),
        "l_knee": (-24, 28), "r_knee": (24, 28),
        "l_foot": (-6, 36), "r_foot": (6, 36),
    },
    "SPRINT_1": {
        "head": (18, -52), "neck": (12, -36),
        "l_shoulder": (-6, -32), "r_shoulder": (18, -32),
        "l_elbow": (-24, -20), "r_elbow": (38, -44),
        "l_hand": (-32, -6), "r_hand": (48, -58),
        "hips": (0, -4),
        "l_knee": (-22, 14), "r_knee": (28, 16),
        "l_foot": (-34, 42), "r_foot": (14, 52),
    },
    "SPRINT_2": {
        "head": (18, -52), "neck": (12, -36),
        "l_shoulder": (-6, -32), "r_shoulder": (18, -32),
        "l_elbow": (36, -44), "r_elbow": (-24, -20),
        "l_hand": (46, -58), "r_hand": (-32, -6),
        "hips": (0, -4),
        "l_knee": (26, 16), "r_knee": (-22, 14),
        "l_foot": (12, 52), "r_foot": (-34, 42),
    },
    "TRIUMPH_FIST": {
        "head": (2, -66), "neck": (0, -45),
        "l_shoulder": (-15, -40), "r_shoulder": (16, -40),
        "l_elbow": (-20, -20), "r_elbow": (28, -58),
        "l_hand": (-18, -2), "r_hand": (36, -88),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (12, 27),
        "l_foot": (-15, 56), "r_foot": (15, 56),
    },
    "DISMISS_WAVE": {
        "head": (-6, -64), "neck": (-2, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (15, -39),
        "l_elbow": (-20, -18), "r_elbow": (26, -26),
        "l_hand": (-22, 4), "r_hand": (44, -14),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "SURRENDER": {
        "head": (0, -62), "neck": (0, -42),
        "l_shoulder": (-16, -38), "r_shoulder": (16, -38),
        "l_elbow": (-28, -36), "r_elbow": (28, -36),
        "l_hand": (-30, -58), "r_hand": (30, -58),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "PRESENT_CHART": {
        "head": (-2, -65), "neck": (0, -44),
        "l_shoulder": (-15, -40), "r_shoulder": (16, -40),
        "l_elbow": (-18, -18), "r_elbow": (36, -46),
        "l_hand": (-16, 2), "r_hand": (58, -52),
        "hips": (0, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "SCROLL_PHONE": {
        "head": (4, -58), "neck": (2, -40),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-14, -20), "r_elbow": (14, -22),
        "l_hand": (2, -26), "r_hand": (4, -24),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CROSS_ARMS": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -24), "r_elbow": (22, -24),
        "l_hand": (12, -22), "r_hand": (-12, -22),
        "hips": (0, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "TEXTING_PHONE": {
        "head": (0, -60), "neck": (0, -42),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-12, -22), "r_elbow": (12, -22),
        "l_hand": (-5, -24), "r_hand": (5, -24),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "LOOK_PHONE": {
        "head": (2, -61), "neck": (1, -43),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-18, -20), "r_elbow": (14, -22),
        "l_hand": (-16, 2), "r_hand": (10, -25),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CONFUSED_WONDERING": {
        "head": (4, -63), "neck": (2, -43),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -18), "r_elbow": (26, -26),
        "l_hand": (-18, 2), "r_hand": (14, -48),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CHECK_NOTIFICATIONS": {
        "head": (0, -65), "neck": (0, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-16, -24), "r_elbow": (16, -24),
        "l_hand": (-8, -34), "r_hand": (8, -34),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "HUG": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-14, -39), "r_shoulder": (14, -39),
        "l_elbow": (-24, -20), "r_elbow": (24, -20),
        "l_hand": (-12, -12), "r_hand": (12, -12),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "FALL_IN_LOVE": {
        "head": (3, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-10, -26), "r_elbow": (10, -26),
        "l_hand": (-4, -32), "r_hand": (4, -32),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "TURNING_AWAY": {
        "head": (-5, -64), "neck": (-2, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (14, -39),
        "l_elbow": (-24, -18), "r_elbow": (18, -18),
        "l_hand": (-26, 4), "r_hand": (18, 4),
        "hips": (0, 0),
        "l_knee": (-12, 27), "r_knee": (8, 27),
        "l_foot": (-16, 56), "r_foot": (10, 56),
    },
    "WAITING": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (16, -39),
        "l_elbow": (-20, -22), "r_elbow": (20, -22),
        "l_hand": (10, -20), "r_hand": (-10, -20),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (14, 25),
        "l_foot": (-13, 56), "r_foot": (18, 54),
    },
    "DISAPPOINTED": {
        "head": (0, -56), "neck": (0, -38),
        "l_shoulder": (-14, -34), "r_shoulder": (14, -34),
        "l_elbow": (-18, -14), "r_elbow": (18, -14),
        "l_hand": (-18, 8), "r_hand": (18, 8),
        "hips": (0, 2),
        "l_knee": (-10, 28), "r_knee": (10, 28),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    # Dynamic Keyframe Sequences Supporting Poses (Atharv Hatwar)
    "PRESENT_ANTICIPATE": {
        "head": (-3, -63), "neck": (-1, -43),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-20, -18), "r_elbow": (24, -22),
        "l_hand": (-22, 4), "r_hand": (18, -12),
        "hips": (-2, 0),
        "l_knee": (-12, 27), "r_knee": (10, 27),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "PRESENT_POINT": {
        "head": (2, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -16), "r_elbow": (38, -36),
        "l_hand": (-20, 5), "r_hand": (62, -36),
        "hips": (1, 0),
        "l_knee": (-11, 27), "r_knee": (12, 27),
        "l_foot": (-15, 56), "r_foot": (16, 56),
    },
    "PRESENT_GESTURE": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-26, -24), "r_elbow": (36, -26),
        "l_hand": (-38, -14), "r_hand": (52, -18),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "PRESENT_TRACE": {
        "head": (3, -65), "neck": (1, -45),
        "l_shoulder": (-15, -39), "r_shoulder": (16, -39),
        "l_elbow": (-20, -18), "r_elbow": (34, -48),
        "l_hand": (-18, 4), "r_hand": (54, -68),
        "hips": (1, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (15, 56),
    },
    "PRESENT_TAP": {
        "head": (2, -64), "neck": (1, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (16, -39),
        "l_elbow": (-20, -18), "r_elbow": (38, -40),
        "l_hand": (-18, 4), "r_hand": (64, -44),
        "hips": (1, 0),
        "l_knee": (-11, 27), "r_knee": (11, 27),
        "l_foot": (-14, 56), "r_foot": (15, 56),
    },
    "PHONE_HOLD": {
        "head": (3, -59), "neck": (1, -41),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-16, -22), "r_elbow": (16, -22),
        "l_hand": (-2, -26), "r_hand": (6, -26),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "PHONE_SCROLL": {
        "head": (4, -58), "neck": (2, -40),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-16, -22), "r_elbow": (16, -20),
        "l_hand": (-2, -26), "r_hand": (8, -20),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "PHONE_TILT": {
        "head": (6, -56), "neck": (3, -39),
        "l_shoulder": (-14, -37), "r_shoulder": (14, -37),
        "l_elbow": (-18, -24), "r_elbow": (18, -24),
        "l_hand": (-4, -28), "r_hand": (6, -28),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "PHONE_TAP": {
        "head": (5, -57), "neck": (2, -40),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-16, -22), "r_elbow": (14, -26),
        "l_hand": (-2, -26), "r_hand": (2, -28),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "THINK_CHIN": {
        "head": (4, -64), "neck": (2, -44),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -18), "r_elbow": (24, -28),
        "l_hand": (-18, 2), "r_hand": (8, -52),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "THINK_NOD": {
        "head": (1, -61), "neck": (0, -42),
        "l_shoulder": (-15, -39), "r_shoulder": (15, -39),
        "l_elbow": (-22, -18), "r_elbow": (24, -26),
        "l_hand": (-18, 2), "r_hand": (10, -50),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "STRESS_TREMBLE": {
        "head": (1, -56), "neck": (0, -38),
        "l_shoulder": (-18, -39), "r_shoulder": (18, -39),
        "l_elbow": (-30, -42), "r_elbow": (30, -42),
        "l_hand": (-12, -62), "r_hand": (12, -62),
        "hips": (0, 3),
        "l_knee": (-12, 28), "r_knee": (12, 28),
        "l_foot": (-14, 56), "r_foot": (14, 56),
    },
    "STRESS_BREATHE": {
        "head": (-2, -60), "neck": (-1, -42),
        "l_shoulder": (-15, -40), "r_shoulder": (15, -40),
        "l_elbow": (-28, -36), "r_elbow": (28, -36),
        "l_hand": (-16, -58), "r_hand": (16, -58),
        "hips": (0, 1),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "FACEPALM_ANTICIPATE": {
        "head": (-2, -64), "neck": (-1, -44),
        "l_shoulder": (-15, -38), "r_shoulder": (15, -38),
        "l_elbow": (-20, -18), "r_elbow": (22, -34),
        "l_hand": (-22, 4), "r_hand": (14, -46),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "FACEPALM_SLIDE": {
        "head": (2, -56), "neck": (1, -38),
        "l_shoulder": (-15, -38), "r_shoulder": (15, -38),
        "l_elbow": (-20, -18), "r_elbow": (14, -36),
        "l_hand": (-22, 4), "r_hand": (4, -50),
        "hips": (0, 2),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "CROSS_TAP": {
        "head": (0, -64), "neck": (0, -44),
        "l_shoulder": (-16, -39), "r_shoulder": (16, -39),
        "l_elbow": (-22, -24), "r_elbow": (22, -24),
        "l_hand": (12, -22), "r_hand": (-12, -22),
        "hips": (1, 0),
        "l_knee": (-12, 27), "r_knee": (10, 27),
        "l_foot": (-18, 54), "r_foot": (14, 56),
    },
    "SHRUG_UP": {
        "head": (0, -58), "neck": (0, -40),
        "l_shoulder": (-22, -44), "r_shoulder": (22, -44),
        "l_elbow": (-36, -26), "r_elbow": (36, -26),
        "l_hand": (-46, -38), "r_hand": (46, -38),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "SHRUG_SETTLE": {
        "head": (0, -62), "neck": (0, -43),
        "l_shoulder": (-18, -40), "r_shoulder": (18, -40),
        "l_elbow": (-30, -20), "r_elbow": (30, -20),
        "l_hand": (-36, -24), "r_hand": (36, -24),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
    "MEDITATE_ZEN_FLOAT": {
        "head": (0, -60), "neck": (0, -42),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-24, -18), "r_elbow": (24, -18),
        "l_hand": (-20, 6), "r_hand": (20, 6),
        "hips": (0, 6),
        "l_knee": (-24, 24), "r_knee": (24, 24),
        "l_foot": (-6, 32), "r_foot": (6, 32),
    },
    "BED_REST": {
        "head": (-58, 22), "neck": (-38, 25),
        "l_shoulder": (-28, 24), "r_shoulder": (-28, 28),
        "l_elbow": (-12, 22), "r_elbow": (-12, 30),
        "l_hand": (4, 24), "r_hand": (4, 28),
        "hips": (0, 26),
        "l_knee": (32, 28), "r_knee": (34, 28),
        "l_foot": (62, 30), "r_foot": (64, 30),
    },
    "BED_SHOCK": {
        "head": (-52, 6), "neck": (-34, 14),
        "l_shoulder": (-24, 16), "r_shoulder": (-24, 22),
        "l_elbow": (-14, 14), "r_elbow": (-14, 24),
        "l_hand": (2, 16), "r_hand": (2, 24),
        "hips": (0, 26),
        "l_knee": (30, 28), "r_knee": (32, 28),
        "l_foot": (60, 30), "r_foot": (62, 30),
    },
    "TYPING_PAUSE": {
        "head": (0, -62), "neck": (0, -42),
        "l_shoulder": (-14, -38), "r_shoulder": (14, -38),
        "l_elbow": (-16, -26), "r_elbow": (16, -26),
        "l_hand": (-10, -22), "r_hand": (10, -22),
        "hips": (0, 0),
        "l_knee": (-10, 27), "r_knee": (10, 27),
        "l_foot": (-13, 56), "r_foot": (13, 56),
    },
}


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _ease_smooth(t: float, overshoot: float = 0.0) -> float:
    """Smoothstep or back-out spring overshoot curve in [0, 1]."""
    t = max(0.0, min(1.0, t))
    if overshoot > 0.01:
        s = overshoot * 9.0  # e.g. 0.18 -> ~1.62
        u = t - 1.0
        return 1.0 + u * u * ((s + 1.0) * u + s)
    # Quintic smootherstep for silky organic movement
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def _lerp_joints(
    pose_a: dict[str, tuple[float, float]],
    pose_b: dict[str, tuple[float, float]],
    t: float,
) -> dict[str, tuple[float, float]]:
    return {
        k: (
            _lerp(pose_a[k][0], pose_b[k][0], t),
            _lerp(pose_a[k][1], pose_b[k][1], t),
        )
        for k in pose_a
    }


def _quad_bezier(
    p0: tuple[float, float],
    p1: tuple[float, float],
    p2: tuple[float, float],
    steps: int = 8,
) -> list[tuple[float, float]]:
    """Sample a quadratic Bezier spline from p0 through control p1 to p2."""
    pts: list[tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        mt = 1.0 - t
        x = mt * mt * p0[0] + 2.0 * mt * t * p1[0] + t * t * p2[0]
        y = mt * mt * p0[1] + 2.0 * mt * t * p1[1] + t * t * p2[1]
        pts.append((x, y))
    return pts


def _hex_to_rgba(color_str: str, alpha: int = 255) -> tuple[int, int, int, int]:
    if not color_str:
        return (17, 17, 17, alpha)
    h = color_str.strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    try:
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), alpha)
    except Exception:
        return (17, 17, 17, alpha)


def _seeded_jitter(seed_key: str, idx: int, amp: float) -> float:
    """Deterministic frame-stable pen wobble so hand-drawn ink never flickers."""
    if amp <= 0.0:
        return 0.0
    h = hashlib.md5(f"{seed_key}:{idx}".encode("ascii")).digest()
    val = int.from_bytes(h[:2], "little") / 65535.0
    return (val * 2.0 - 1.0) * amp


# ---------------------------------------------------------------------------
# Renderer Class
# ---------------------------------------------------------------------------

class StickmanRenderer:
    """2x Supersampled procedural stickman character engine backed by StylePacks."""

    def __init__(self, style: str = "a1_classic_bw", variant: Optional[str] = None) -> None:
        self.style = style
        self.variant = variant
        self.pack, self.params = resolve_style_pack(style, variant)

    @staticmethod
    def _get_style_params(style: str, variant: Optional[str] = None) -> dict[str, Any]:
        _pack, params = resolve_style_pack(style, variant)
        return params

    # ------------------------------------------------------------------
    # Continuous Procedural Pose & Keyframe Engine
    # ------------------------------------------------------------------

    @staticmethod
    def _kinematic_walk(
        phase: float,
        running: bool = False,
        sneak: bool = False,
        bounce_mult: float = 1.0,
    ) -> dict[str, tuple[float, float]]:
        """Smooth sinusoidal walk/run/sneak kinematics with organic knee bend & hip bob."""
        stride = 28.0 if running else (13.0 if sneak else 18.0)
        lift = 16.0 if running else (11.0 if sneak else 9.0)
        lean = 8.0 if running else (11.0 if sneak else 3.0)
        arm_amp = 32.0 if running else (10.0 if sneak else 19.0)
        bob = -abs(math.sin(phase)) * (6.0 if running else 3.0) * bounce_mult
        crouch_y = 6.0 if sneak else 0.0

        s = math.sin(phase)
        c = math.cos(phase)

        l_swing = max(0.0, math.sin(phase + 0.5))
        r_swing = max(0.0, math.sin(phase + math.pi + 0.5))

        l_foot_x = s * stride
        r_foot_x = -s * stride
        l_foot_y = 56.0 - l_swing * lift + bob
        r_foot_y = 56.0 - r_swing * lift + bob

        l_knee_x = l_foot_x * 0.45 + (6.0 if running else 4.0) * l_swing
        r_knee_x = r_foot_x * 0.45 + (6.0 if running else 4.0) * r_swing
        l_knee_y = 28.0 - l_swing * (lift * 0.7) + bob + crouch_y * 0.4
        r_knee_y = 28.0 - r_swing * (lift * 0.7) + bob + crouch_y * 0.4

        l_hand_x = -19.0 - s * (arm_amp * 0.28)
        r_hand_x = 19.0 + s * (arm_amp * 0.28)
        l_hand_y = -4.0 - abs(c) * 6.0 + bob if running else 2.0 - max(0.0, -s) * 8.0 + bob + crouch_y
        r_hand_y = -4.0 - abs(c) * 6.0 + bob if running else 2.0 - max(0.0, s) * 8.0 + bob + crouch_y

        l_elbow_x = -16.0 - s * (arm_amp * 0.16)
        r_elbow_x = 16.0 + s * (arm_amp * 0.16)
        l_elbow_y = -17.0 + bob + crouch_y * 0.8
        r_elbow_y = -17.0 + bob + crouch_y * 0.8

        return {
            "head":       (lean + 1.5, -63.0 + bob + crouch_y),
            "neck":       (lean * 0.7, -43.0 + bob + crouch_y),
            "l_shoulder": (-13.0 + lean * 0.5, -38.0 + bob + crouch_y),
            "r_shoulder": (13.0 + lean * 0.5, -38.0 + bob + crouch_y),
            "l_elbow":    (l_elbow_x, l_elbow_y),
            "r_elbow":    (r_elbow_x, r_elbow_y),
            "l_hand":     (l_hand_x, l_hand_y),
            "r_hand":     (r_hand_x, r_hand_y),
            "hips":       (0.0, bob + crouch_y * 0.6),
            "l_knee":     (l_knee_x, l_knee_y),
            "r_knee":     (r_knee_x, r_knee_y),
            "l_foot":     (l_foot_x, l_foot_y),
            "r_foot":     (r_foot_x, r_foot_y),
        }

    def get_animated_joints(
        self,
        action: str,
        t_norm: float,
        time_sec: float = 0.0,
        scale: float = 1.0,
        facing: str = "right",
    ) -> dict[str, tuple[float, float]]:
        """Compute smooth StylePack-tuned interpolated joint offsets."""
        act = action.upper()
        p = self.params
        feel = p.get("motion_feel", "smooth")
        overshoot = float(p.get("ease_overshoot", 0.0))
        tremble_amp = float(p.get("tremble_amp", 0.0))
        bounce_mult = 1.4 if feel in ("bouncy_sketch", "snappy_pop") else 1.0

        CYCLICAL_ACTIONS: dict[str, tuple[str, str, float]] = {
            "WAVE":            ("WAVE", "WAVE_ALT", 3.2),
            "DISMISSIVE_WAVE": ("DISMISS_WAVE", "STAND", 2.2),
            "TYPING_LAPTOP":   ("TYPING_1", "TYPING_2", 5.2),
            "COUNT_MONEY":     ("COUNT_MONEY_1", "COUNT_MONEY_2", 3.2),
            "LAUGH":           ("LAUGH", "LAUGH_UP", 3.8),
            "CRY":             ("CRY", "BOW", 2.4),
            "FIGHT":           ("FIGHT_1", "FIGHT_2", 3.4),
            "CELEBRATE":       ("CELEBRATE", "JUMP", 2.6),
            "SCROLL_PHONE":    ("PHONE_HOLD", "PHONE_SCROLL", 2.8),
            "CROSS_ARMS":      ("CROSS_ARMS", "CROSS_TAP", 1.8),
        }

        if act in ("WALK_RIGHT", "WALK_LEFT", "WALK_1", "WALK_2"):
            speed = 5.4 if feel == "gentle_slow" else 6.4
            raw = self._kinematic_walk(time_sec * speed, running=False, bounce_mult=bounce_mult)
        elif act in ("RUN", "RUN_1", "RUN_2"):
            speed = 8.0 if feel == "gentle_slow" else 9.8
            raw = self._kinematic_walk(time_sec * speed, running=True, bounce_mult=bounce_mult)
        elif act in ("SPRINT_FAST", "SPRINT"):
            speed = 11.5
            raw = self._kinematic_walk(time_sec * speed, running=True, bounce_mult=1.3)
        elif act in ("SNEAK", "SNEAK_1", "SNEAK_2"):
            raw = self._kinematic_walk(time_sec * 4.5, running=False, sneak=True, bounce_mult=0.6)
        elif act in CYCLICAL_ACTIONS:
            pa_name, pb_name, freq = CYCLICAL_ACTIONS[act]
            pa = _BASE_POSES.get(pa_name, _BASE_POSES["STAND"])
            pb = _BASE_POSES.get(pb_name, _BASE_POSES["STAND"])
            cycle_frac = 0.5 + 0.5 * math.sin(time_sec * freq * 2.0 * math.pi)
            raw = _lerp_joints(pa, pb, cycle_frac)
            if act in ("LAUGH", "CELEBRATE", "CRY"):
                bounce_y = -abs(math.sin(time_sec * freq * 2.0 * math.pi)) * 3.2
                raw["hips"] = (raw["hips"][0], raw["hips"][1] + bounce_y)
                raw["head"] = (raw["head"][0], raw["head"][1] + bounce_y * 1.2)
        else:
            seq = POSE_SEQUENCES.get(act, [act if act in _BASE_POSES else "STAND"])
            if len(seq) == 1:
                target_pose = _BASE_POSES.get(seq[0], _BASE_POSES["STAND"])
                stand_pose = _BASE_POSES["STAND"]
                # Snappy transition into key acting pose in first 0.32s with overshoot
                snap_t = min(1.0, max(0.0, time_sec / 0.32))
                ease_snap = _ease_smooth(snap_t, overshoot=0.18)
                raw = _lerp_joints(stand_pose, target_pose, ease_snap)
            else:
                span = max(0.0, min(0.9999, t_norm)) * (len(seq) - 1)
                idx = int(span)
                frac = _ease_smooth(span - idx, overshoot=overshoot)
                pa = _BASE_POSES.get(seq[idx], _BASE_POSES["STAND"])
                pb = _BASE_POSES.get(seq[min(len(seq) - 1, idx + 1)], _BASE_POSES["STAND"])
                raw = _lerp_joints(pa, pb, frac)

            # Natural continuous breathing & head attentiveness
            breath_speed = 2.4 if feel == "gentle_slow" else 3.2
            breath = math.sin(time_sec * breath_speed) * 1.5
            sway_x = math.sin(time_sec * 1.7) * (1.2 if feel == "gentle_slow" else 0.7)
            raw["head"] = (raw["head"][0] + sway_x, raw["head"][1] + breath)
            raw["neck"] = (raw["neck"][0] + sway_x * 0.5, raw["neck"][1] + breath * 0.7)
            raw["l_shoulder"] = (raw["l_shoulder"][0], raw["l_shoulder"][1] + breath * 0.6)
            raw["r_shoulder"] = (raw["r_shoulder"][0], raw["r_shoulder"][1] + breath * 0.6)

        # Tense survival micro-tremble for B4 Survival Thriller
        if tremble_amp > 0.0:
            tx = math.sin(time_sec * 29.0) * tremble_amp * 0.7
            ty = math.cos(time_sec * 23.0) * tremble_amp * 0.5
            for k in ("head", "neck", "l_shoulder", "r_shoulder", "l_hand", "r_hand"):
                raw[k] = (raw[k][0] + tx, raw[k][1] + ty)

        scaled = {k: (v[0] * scale, v[1] * scale) for k, v in raw.items()}
        if facing == "left":
            scaled = {k: (-v[0], v[1]) for k, v in scaled.items()}
        return scaled

    @staticmethod
    def _get_pose_joints(pose: str, scale: float, facing: str) -> dict[str, tuple[float, float]]:
        if pose in ("WALK_1", "WALK_2"):
            raw = StickmanRenderer._kinematic_walk(0.8 if pose == "WALK_1" else 3.9, running=False)
        elif pose in ("RUN_1", "RUN_2"):
            raw = StickmanRenderer._kinematic_walk(0.8 if pose == "RUN_1" else 3.9, running=True)
        else:
            raw = _BASE_POSES.get(pose, _BASE_POSES["STAND"])
        scaled = {k: (v[0] * scale, v[1] * scale) for k, v in raw.items()}
        if facing == "left":
            scaled = {k: (-v[0], v[1]) for k, v in scaled.items()}
        return scaled

    # ------------------------------------------------------------------
    # High-Quality 2x Supersampled Composite Entry Point
    # ------------------------------------------------------------------

    def render_character_on_frame(
        self,
        base_img: Image.Image,
        cx: int,
        cy: int,
        pose: str = "STAND",
        scale: float = 1.0,
        facing: str = "right",
        color_override: Optional[str] = None,
        emotion_override: Optional[str] = None,
        joints_override: Optional[dict[str, tuple[float, float]]] = None,
        time_sec: float = 0.0,
        speaking: bool = False,
        accessory: Optional[str] = None,
        outfit_override: Optional[str] = None,
        char_index: int = 0,
        gaze_target: Optional[tuple[float, float]] = None,
    ) -> None:
        """
        Render character into a 2x-resolution tight sprite patch and composite cleanly
        onto *base_img* at hip anchor (cx, cy) with alpha anti-aliasing.
        """
        pad_x = max(110, int(138 * scale))
        pad_top = max(135, int(165 * scale))
        pad_bot = max(85, int(102 * scale))
        spr_w = pad_x * 2
        spr_h = pad_top + pad_bot

        aa = 2
        hi_img = Image.new("RGBA", (spr_w * aa, spr_h * aa), (0, 0, 0, 0))
        hi_draw = ImageDraw.Draw(hi_img)

        hi_joints = None
        if joints_override is not None:
            hi_joints = {k: (v[0] * aa, v[1] * aa) for k, v in joints_override.items()}

        hi_gaze = None
        if gaze_target is not None:
            hi_gaze = ((pad_x + (gaze_target[0] - cx)) * aa, (pad_top + (gaze_target[1] - cy)) * aa)

        self.draw_stickman(
            hi_draw,
            pad_x * aa,
            pad_top * aa,
            pose=pose,
            scale=scale * aa,
            facing=facing,
            color_override=color_override,
            emotion_override=emotion_override,
            joints_override=hi_joints,
            time_sec=time_sec,
            speaking=speaking,
            accessory=accessory,
            outfit_override=outfit_override,
            char_index=char_index,
            gaze_target=hi_gaze,
        )

        lo_img = hi_img.resize((spr_w, spr_h), Image.Resampling.BICUBIC)
        base_img.alpha_composite(lo_img, (int(cx - pad_x), int(cy - pad_top)))

    # ------------------------------------------------------------------
    # Core Drawing Routine (Direct or 2x Supersampled)
    # ------------------------------------------------------------------

    def draw_stickman(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        pose: str = "STAND",
        scale: float = 1.0,
        facing: str = "right",
        color_override: Optional[str] = None,
        emotion_override: Optional[str] = None,
        joints_override: Optional[dict[str, tuple[float, float]]] = None,
        time_sec: float = 0.0,
        speaking: bool = False,
        accessory: Optional[str] = None,
        outfit_override: Optional[str] = None,
        char_index: int = 0,
        gaze_target: Optional[tuple[float, float]] = None,
    ) -> None:
        """Draw an expressive, style-tailored 2D character anchored at hip (cx, cy)."""
        p = self.params
        fg = color_override or p["fg"]
        acc = p.get("accent", "#E94560")
        acc2 = p.get("accent_secondary", "#3B82F6")
        lw = max(2, int(round(p.get("line_width", 4.2) * scale)))
        hr = max(6, int(round(p.get("head_radius", 19.0) * scale)))
        taper = float(p.get("limb_taper", 0.25))
        wobble = float(p.get("wobble_px", 0.0)) * scale
        tech = p.get("line_technique", "crisp")
        rim = p.get("character_rim_color", "")
        dir_sign = 1 if facing == "right" else -1

        outfit = outfit_override or (
            p.get("primary_outfit", "minimalist") if char_index == 0 else p.get("secondary_outfit", "minimal_cap")
        )
        effective_acc = accessory or p.get("default_accessory", "none")

        joints = joints_override or self._get_pose_joints(pose, scale, facing)

        def pt(key: str) -> tuple[float, float]:
            ox, oy = joints[key]
            return (cx + ox, cy + oy)

        # 0. Soft elliptical ground contact shadow under feet
        lf, rf = pt("l_foot"), pt("r_foot")
        floor_y = max(lf[1], rf[1]) + max(2.0, 2.5 * scale)
        foot_span = max(24.0 * scale, abs(lf[0] - rf[0]) * 0.55 + 12.0 * scale)
        shadow_cx = (lf[0] + rf[0]) * 0.5
        shadow_h = max(3.0, 5.2 * scale)
        if tech in ("noir_rim", "glowing_crt") or p.get("bg", "#FFFFFF").startswith("#0"):
            sh_outer = (255, 255, 255, 18) if not rim else _hex_to_rgba(rim, 32)
            sh_inner = (255, 255, 255, 28) if not rim else _hex_to_rgba(rim, 52)
        else:
            sh_outer = (0, 0, 0, 28)
            sh_inner = (0, 0, 0, 52)
        draw.ellipse([shadow_cx - foot_span, floor_y - shadow_h, shadow_cx + foot_span, floor_y + shadow_h], fill=sh_outer)
        draw.ellipse([shadow_cx - foot_span * 0.65, floor_y - shadow_h * 0.65, shadow_cx + foot_span * 0.65, floor_y + shadow_h * 0.65], fill=sh_inner)

        # 0a. Cartoon footstep dust puff clouds during locomotion (Created by Atharv Hatwar)
        act_check = str(pose).upper()
        if any(k in act_check for k in ("WALK", "RUN", "JUMP")):
            back_foot = rf if dir_sign == 1 else lf
            dust_phase = (time_sec * 4.5) % 1.0
            dust_r = max(2.5, 5.0 * scale * dust_phase)
            dust_x = back_foot[0] - dir_sign * (6.0 + 14.0 * dust_phase) * scale
            dust_y = floor_y - dust_r * 0.6
            dust_alpha = int(140 * (1.0 - dust_phase))
            dust_col = (200, 210, 225, dust_alpha) if (tech in ("noir_rim", "glowing_crt") or p.get("bg", "#FFF").startswith("#0")) else (150, 150, 160, dust_alpha)
            draw.ellipse([dust_x - dust_r, dust_y - dust_r * 0.65, dust_x + dust_r, dust_y + dust_r * 0.65], fill=dust_col)

        # Helper: draw organic tapered + optional glowing/double-ink Bezier limb chain
        def draw_tapered_chain(p0: tuple[float, float], p1: tuple[float, float], p2: tuple[float, float], w_start: float, w_end: float, key_seed: str) -> None:
            pts = _quad_bezier(p0, p1, p2, steps=10)
            n_seg = len(pts) - 1

            # Optional phosphor/rim glow halo behind limbs (B3 Retro TV / A6 Amber Noir / B4)
            if rim and tech in ("glowing_crt", "noir_rim"):
                glow_col = _hex_to_rgba(rim, 95 if tech == "glowing_crt" else 135)
                glow_pts = [(x - dir_sign * 1.2 * scale, y - 0.8 * scale) for (x, y) in pts] if tech == "noir_rim" else pts
                gw = max(2, int(w_start * (1.75 if tech == "glowing_crt" else 1.25)))
                draw.line(glow_pts, fill=glow_col, width=gw, joint="curve")

            for i in range(n_seg):
                frac = i / max(1, n_seg)
                seg_w = max(2, int(round(_lerp(w_start, w_end, frac))))
                a, b = pts[i], pts[i + 1]
                draw.line([a, b], fill=fg, width=seg_w)
                r = max(1, seg_w // 2)
                draw.ellipse([a[0] - r, a[1] - r, a[0] + r, a[1] + r], fill=fg)

            end_r = max(1, int(w_end // 2))
            draw.ellipse([pts[-1][0] - end_r, pts[-1][1] - end_r, pts[-1][0] + end_r, pts[-1][1] + end_r], fill=fg)

            # Secondary sketchy double-pass ink stroke (B2 Colorful Hand-Drawn)
            if tech == "hand_drawn" and wobble > 0:
                sketch_pts = [
                    (px + _seeded_jitter(key_seed, i * 2, wobble), py + _seeded_jitter(key_seed, i * 2 + 1, wobble))
                    for i, (px, py) in enumerate(pts[::2])
                ]
                if len(sketch_pts) >= 2:
                    draw.line(sketch_pts, fill=_hex_to_rgba(fg, 140), width=max(1, int(w_end * 0.55)))

        def limb_seg(a: str, b: str, width: float = lw, seed: str = "") -> None:
            pa, pb = pt(a), pt(b)
            mid = ((pa[0] + pb[0]) * 0.5, (pa[1] + pb[1]) * 0.5)
            draw_tapered_chain(pa, mid, pb, width, width * (1.0 - taper * 0.25), seed or a + b)

        # 0b. Dynamic comic speed lines behind moving / energetic actions
        act_u = str(pose).upper()
        if any(k in act_u for k in ("RUN", "WALK", "JUMP", "FIGHT", "SHOUT", "FALL")):
            speed_col = _hex_to_rgba(acc if tech != "minimal_bw" else fg, 115)
            n_lines = 4 if "RUN" in act_u or "FIGHT" in act_u or "JUMP" in act_u else 2
            hx_raw, hy_raw = pt("head")
            for li in range(n_lines):
                phase_off = math.sin(time_sec * 16.0 + li * 1.7) * 5.0 * scale
                ly = hy_raw + (li - 1) * 18.0 * scale + phase_off
                lx1 = hx_raw - dir_sign * (26.0 + (li % 2) * 8.0) * scale
                lx2 = lx1 - dir_sign * (18.0 + (li % 3) * 7.0) * scale
                draw.line([(lx1, ly), (lx2, ly)], fill=speed_col, width=max(1, int(lw * 0.48)))

        # 1. Legs + stylized cartoon shoes
        is_chunky_caveman = (outfit == "hide_tunic_alt")
        w_hip = lw * ((1.55 if is_chunky_caveman else 1.08) + taper * 0.2)
        w_ankle = max(2.0, lw * ((1.22 if is_chunky_caveman else 1.0) - taper * 0.25))
        draw_tapered_chain(pt("hips"), pt("l_knee"), pt("l_foot"), w_hip, w_ankle, f"lleg_{char_index}")
        draw_tapered_chain(pt("hips"), pt("r_knee"), pt("r_foot"), w_hip, w_ankle, f"rleg_{char_index}")

        shoe_w = max(5.5, (9.6 if is_chunky_caveman else 8.8) * scale)
        shoe_h = max(3.2, (4.6 if is_chunky_caveman else 4.2) * scale)
        for fk in ("l_foot", "r_foot"):
            fx, fy = pt(fk)
            if outfit in ("hide_tunic", "hide_tunic_alt"):
                # Barefoot / moccasin toe wrap
                draw.ellipse([fx - shoe_w * 0.45, fy - shoe_h, fx + shoe_w * 0.95, fy + shoe_h], fill="#D9A077" if is_chunky_caveman else "#7C2D12", outline=fg, width=max(1, lw // 2))
            elif outfit in ("samurai_kimono", "samurai_hakama"):
                # Traditional dark tabi/sandal
                draw.rounded_rectangle([fx - shoe_w * 0.4, fy - shoe_h, fx + shoe_w * 0.95, fy + shoe_h], radius=max(2, int(3 * scale)), fill="#1E293B", outline=fg, width=max(1, lw // 2))
            else:
                sx1 = fx - shoe_w * (0.35 if dir_sign > 0 else 1.10)
                sx2 = fx + shoe_w * (1.10 if dir_sign > 0 else 0.35)
                draw.ellipse([sx1, fy - shoe_h, sx2, fy + shoe_h], fill=fg)

        # 2. Back arm BEHIND torso for natural 2D cartoon depth!
        w_sh = lw * (1.28 if is_chunky_caveman else 1.02)
        w_wr = max(2.0, lw * ((1.10 if is_chunky_caveman else 1.0) - taper * 0.35))
        nk = pt("neck")
        hp = pt("hips")
        ls = pt("l_shoulder")
        rs = pt("r_shoulder")
        is_white_glove = (effective_acc == "white_gloves") or (outfit == "survival_hoodie")
        hand_r = max(3.2, (5.8 if (is_white_glove or is_chunky_caveman) else 4.6) * scale)

        back_sh, back_el, back_ha, back_seed = (
            ("l_shoulder", "l_elbow", "l_hand", f"larm_{char_index}")
            if dir_sign >= 0
            else ("r_shoulder", "r_elbow", "r_hand", f"rarm_{char_index}")
        )
        front_sh, front_el, front_ha, front_seed = (
            ("r_shoulder", "r_elbow", "r_hand", f"rarm_{char_index}")
            if dir_sign >= 0
            else ("l_shoulder", "l_elbow", "l_hand", f"larm_{char_index}")
        )

        draw_tapered_chain(pt(back_sh), pt(back_el), pt(back_ha), w_sh, w_wr, back_seed)
        bhx, bhy = pt(back_ha)
        if is_white_glove:
            draw.ellipse([bhx - hand_r, bhy - hand_r, bhx + hand_r, bhy + hand_r], fill="#FFFFFF", outline="#0F172A", width=max(2, lw // 2))
        else:
            draw.ellipse([bhx - hand_r, bhy - hand_r, bhx + hand_r, bhy + hand_r], fill=fg)

        # 3. Stylized Torso & Outfit Costume Silhouette
        self._draw_costume_torso(draw, nk, hp, ls, rs, outfit, fg, acc, acc2, rim, lw, scale, dir_sign, time_sec, char_index)

        # 4. Front Arm ON TOP of torso + sleeve shoulder cap
        draw_tapered_chain(pt(front_sh), pt(front_el), pt(front_ha), w_sh, w_wr, front_seed)
        fhx, fhy = pt(front_ha)
        if is_white_glove:
            draw.ellipse([fhx - hand_r, fhy - hand_r, fhx + hand_r, fhy + hand_r], fill="#FFFFFF", outline="#0F172A", width=max(2, lw // 2))
        else:
            draw.ellipse([fhx - hand_r, fhy - hand_r, fhx + hand_r, fhy + hand_r], fill=fg)

        # 5. Head (with optional chubby jaw/cheek silhouette for chunky caveman & rim/sketch strokes)
        hx, hy = pt("head")
        head_fill = p.get("head_fill", "#FFFFFF")
        if char_index > 0 and p.get("filled_head"):
            head_fill = "#241930"
        if is_chunky_caveman:
            hr = int(hr * 1.14)
            head_fill = "#F5D0A9"  # Warm comic skin tone for chunky caveman

        # Survival / Amber Noir hood shell behind face
        if outfit in ("survival_hoodie", "survival_hoodie_alt"):
            hood_r = hr + int(5 * scale)
            hood_col = "#1E293B" if outfit == "survival_hoodie" else "#334155"
            draw.ellipse([hx - hood_r, hy - hood_r, hx + hood_r, hy + hood_r], fill=hood_col, outline=rim or "#64748B", width=max(2, lw // 2))
        elif outfit == "noir_hoodie":
            hood_r = hr + int(5.5 * scale)
            draw.ellipse([hx - hood_r, hy - hood_r, hx + hood_r, hy + hood_r], fill="#140D1E", outline=acc, width=max(2, lw - 1))

        if rim and tech == "glowing_crt":
            glow_r = hr + int(3.5 * scale)
            draw.ellipse([hx - glow_r, hy - glow_r, hx + glow_r, hy + glow_r], outline=_hex_to_rgba(rim, 95), width=max(2, lw))

        if is_chunky_caveman:
            # Slightly wider rounded potato/jaw cartoon head + clean subtle chin shadow
            draw.ellipse([hx - hr * 1.08, hy - hr * 0.94, hx + hr * 1.08, hy + hr * 1.04], fill=head_fill, outline=fg, width=lw)
            draw.arc([hx - hr * 0.65, hy + hr * 0.25, hx + hr * 0.65, hy + hr * 0.92], start=20, end=160, fill="#8C624A", width=max(1, int(1.4 * scale)))
        else:
            draw.ellipse([hx - hr, hy - hr, hx + hr, hy + hr], fill=head_fill, outline=fg if outfit not in ("noir_hoodie", "survival_hoodie", "survival_hoodie_alt") else (acc if outfit == "noir_hoodie" else "#0F172A"), width=lw)

        if tech == "hand_drawn" and wobble > 0:
            ox = _seeded_jitter(f"head_{char_index}", 0, wobble * 0.7)
            oy = _seeded_jitter(f"head_{char_index}", 1, wobble * 0.7)
            draw.ellipse([hx - hr + ox, hy - hr + oy, hx + hr + ox, hy + hr + oy], outline=_hex_to_rgba(fg, 120), width=max(1, lw // 2))

        # 6. Head & Neck Accessories / Period Costumes / Host Signature
        self._draw_accessories(
            draw, hx, hy, nk, hr, lw, scale, dir_sign, time_sec,
            outfit, effective_acc, fg, acc, acc2, char_index
        )

        # 7. Living Expressive Face
        emotion = emotion_override.upper() if emotion_override else self._pose_to_emotion(pose)
        is_blinking = (int(time_sec * 24) % 74) in (0, 1, 2)
        talk_phase = int(time_sec * 11) % 3
        mouth_open = speaking and (talk_phase != 0)
        face_fg = acc if outfit == "noir_hoodie" else ("#0F172A" if outfit in ("survival_hoodie", "survival_hoodie_alt") else fg)
        use_sclera = outfit in ("hide_tunic", "hide_tunic_alt", "samurai_kimono", "samurai_hakama", "presenter_suit") or (self.style == "b1_minimal_line_art" and emotion in ("SURPRISED", "ANGRY", "CONFUSED"))
        is_female_char = (effective_acc == "ponytail" or outfit in ("feminine_silhouette", "skirt_dress") or char_index == 1)
        self.draw_expression(
            draw, int(hx), int(hy), emotion, scale * (1.06 if hr > 20 * scale else 1.0),
            fg_override=face_fg, head_fill=head_fill,
            blinking=is_blinking, mouth_open=mouth_open,
            mouth_wide=(talk_phase == 2), facing=facing,
            cheek_blush=bool(p.get("cheek_blush", False) or is_female_char),
            has_glasses=(outfit == "presenter_suit" or effective_acc in ("glasses_bowtie", "glasses")),
            has_mustache=(outfit == "historical_coat" and char_index == 1),
            has_sclera=use_sclera,
            has_nose=is_chunky_caveman,
            has_eyelashes=is_female_char,
            time_sec=time_sec,
            gaze_target=gaze_target,
        )

    def _draw_costume_torso(
        self,
        draw: ImageDraw.ImageDraw,
        nk: tuple[float, float],
        hp: tuple[float, float],
        ls: tuple[float, float],
        rs: tuple[float, float],
        outfit: str,
        fg: str,
        acc: str,
        acc2: str,
        rim: str,
        lw: int,
        scale: float,
        dir_sign: int,
        time_sec: float,
        char_index: int,
    ) -> None:
        """Draw torso & smooth rounded style-authentic garment silhouette."""
        sh_w = abs(rs[0] - ls[0]) * 0.52 + 4 * scale
        mid_x = (nk[0] + hp[0]) * 0.5
        sh_left_x = min(ls[0], rs[0])
        sh_right_x = max(ls[0], rs[0])
        top_y = (ls[1] + rs[1]) * 0.5
        bot_y = hp[1] + 2 * scale
        var = str(self.params.get("variant", "default"))

        # Base neck-to-hip spine
        if outfit == "minimalist" and var == "spotlight_chaos":
            # Comic white-filled capsule body with crisp black outline inside spotlight
            cap_w = max(8 * scale, sh_w * 0.72)
            draw.rounded_rectangle(
                [mid_x - cap_w, top_y - 1 * scale, hp[0] + cap_w, bot_y + 2 * scale],
                radius=max(4, int(cap_w * 0.85)),
                fill="#FFFFFF",
                outline=fg,
                width=max(2, lw),
            )
            return

        torso_pts = [(nk[0], nk[1]), (mid_x, (nk[1] + hp[1]) * 0.5), (hp[0], hp[1])]
        draw.line(torso_pts, fill=fg, width=max(lw, int(lw * 1.15)))
        if outfit == "minimalist":
            # Smooth rounded shoulder curve instead of rigid T-bar
            draw.line([ls, nk, rs], fill=fg, width=max(2, lw - 1), joint="curve")
            return

        draw.line([ls, nk, rs], fill=fg, width=max(2, lw - 1), joint="curve")

        if outfit in ("beanie_tee", "pop_hoodie", "modern_hoodie"):
            # Soft rounded t-shirt / hoodie silhouette + curved short sleeve caps
            tee_col = "#FACC15" if outfit == "beanie_tee" else (acc2 if char_index == 0 else acc)
            if outfit == "pop_hoodie" and char_index == 0:
                tee_col = acc
            body_w = sh_w * 0.78
            draw.rounded_rectangle(
                [mid_x - body_w, top_y - 2 * scale, hp[0] + body_w, bot_y],
                radius=max(5, int(9 * scale)),
                fill=tee_col,
                outline=fg,
                width=max(2, lw - 1),
            )
            # Soft round neck crew collar
            draw.arc([nk[0] - 5 * scale, top_y - 4 * scale, nk[0] + 5 * scale, top_y + 4 * scale], start=0, end=180, fill=fg, width=max(1, lw // 2))
            # Short cartoon sleeves wrapping shoulder joints smoothly
            sl_r = 5.5 * scale
            for sx, sy in (ls, rs):
                draw.ellipse([sx - sl_r, sy - sl_r * 0.8, sx + sl_r, sy + sl_r * 1.15], fill=tee_col, outline=fg, width=max(1, lw // 2))
        elif outfit in ("feminine_silhouette", "skirt_dress"):
            # Flared feminine dress/skirt silhouette
            dress_col = acc or "#F43F5E"
            skirt_pts = [
                (sh_left_x - 1 * scale, top_y),
                (sh_right_x + 1 * scale, top_y),
                (hp[0] + sh_w * 1.18, bot_y + 8 * scale),
                (hp[0] - sh_w * 1.18, bot_y + 8 * scale),
            ]
            draw.polygon(skirt_pts, fill=dress_col, outline=fg, width=max(2, lw - 1))
            # Elegant curved waist contour
            draw.line([(mid_x - sh_w * 0.55, (top_y + bot_y) * 0.55), (mid_x + sh_w * 0.55, (top_y + bot_y) * 0.55)], fill=fg, width=max(1, lw // 2))
        elif outfit == "hide_tunic":
            # Prehistoric jagged one-shoulder animal-hide tunic + spotted fur edge
            hide_col = "#C2611A" if char_index == 0 else "#9A4814"
            poly = [
                (sh_left_x - 3 * scale, top_y - 2 * scale),
                (mid_x + 5 * scale, top_y + 9 * scale),
                (hp[0] + sh_w * 1.05, bot_y + 5 * scale),
                (hp[0] + sh_w * 0.40, bot_y - 2 * scale),
                (hp[0] + 1 * scale, bot_y + 6 * scale),
                (hp[0] - sh_w * 0.55, bot_y - 1 * scale),
                (hp[0] - sh_w * 1.05, bot_y + 6 * scale),
            ]
            draw.polygon(poly, fill=hide_col, outline=fg, width=max(2, lw - 1))
            for sx, sy, sr in ((-5, 11, 2.4), (3, 19, 2.6), (-3, 27, 2.1), (6, 29, 1.9)):
                draw.ellipse([mid_x + sx * scale - sr * scale, top_y + sy * scale - sr * scale, mid_x + sx * scale + sr * scale, top_y + sy * scale + sr * scale], fill="#451A03")
        elif outfit == "hide_tunic_alt":
            # Wide chunky prehistoric chief silhouette with thick ragged fur hem
            hide_col = "#B45309"
            belly_w = sh_w * 1.38
            draw.rounded_rectangle(
                [mid_x - belly_w * 0.90, top_y - 2 * scale, hp[0] + belly_w * 0.90, bot_y + 3 * scale],
                radius=max(6, int(13 * scale)),
                fill="#E8B890",
                outline=fg,
                width=max(2, lw - 1),
            )
            # Fur hide wrap with zigzag fur hem + shoulder strap
            wrap_top = top_y + 6 * scale
            hem_y = bot_y + 5 * scale
            poly = [
                (sh_left_x - 3 * scale, top_y),
                (mid_x + 4 * scale, wrap_top + 6 * scale),
                (hp[0] + belly_w, wrap_top + 10 * scale),
                (hp[0] + belly_w * 0.98, hem_y + 5 * scale),
                (hp[0] + belly_w * 0.50, hem_y - 2 * scale),
                (hp[0], hem_y + 6 * scale),
                (hp[0] - belly_w * 0.50, hem_y - 2 * scale),
                (hp[0] - belly_w * 0.98, hem_y + 5 * scale),
            ]
            draw.polygon(poly, fill=hide_col, outline=fg, width=max(2, lw - 1))
            for sx, sy in ((-7, 15), (6, 20), (-2, 26), (9, 29)):
                draw.ellipse([mid_x + sx * scale - 2.6 * scale, top_y + sy * scale - 2.2 * scale, mid_x + sx * scale + 2.6 * scale, top_y + sy * scale + 2.2 * scale], fill="#451A03")
        elif outfit in ("cozy_sweater", "cozy_coat", "vest_casual"):
            # Smooth slim cozy pullover / rounded torso (clean café storybook elegance)
            col = "#E08E45" if (outfit == "cozy_sweater" and char_index == 0) else ("#0D9488" if char_index > 0 else acc2)
            if outfit == "cozy_sweater" and self.style == "a4_cozy_storytelling" and char_index == 0:
                col = "#FAF5EE"  # Soft cream knit pullover matching sunlit café hero!
            body_w = sh_w * 0.72
            draw.rounded_rectangle(
                [mid_x - body_w, top_y - 1 * scale, hp[0] + body_w, bot_y + 1 * scale],
                radius=max(5, int(10 * scale)),
                fill=col,
                outline=fg,
                width=max(2, lw - 1),
            )
            if outfit == "cozy_sweater":
                sy = (top_y + bot_y) * 0.58
                stripe_c = acc if col == "#FAF5EE" else "#FFF7ED"
                draw.line([(hp[0] - body_w + 2 * scale, sy), (hp[0] + body_w - 2 * scale, sy)], fill=stripe_c, width=max(2, int(2.2 * scale)))
        elif outfit in ("samurai_kimono", "samurai_hakama"):
            # Authentic layered Japanese Samurai kimono/haori + hakama + obi + katana
            haori_col = "#1E293B" if char_index == 0 else "#451A22"
            hakama_col = "#78716C" if outfit == "samurai_kimono" else "#57534E"
            obi_col = "#94A3B8" if char_index == 0 else "#D97706"
            kimono_w = sh_w * 1.15
            obi_y = top_y + (bot_y - top_y) * 0.56
            # Pleated hakama lower skirt reaching over upper thighs
            draw.polygon([
                (hp[0] - kimono_w * 0.85, obi_y),
                (hp[0] + kimono_w * 0.85, obi_y),
                (hp[0] + kimono_w * 1.25, bot_y + 16 * scale),
                (hp[0] - kimono_w * 1.25, bot_y + 16 * scale),
            ], fill=hakama_col, outline=fg, width=max(2, lw - 1))
            # Center hakama pleat fold lines
            for off in (-0.42, 0.0, 0.42):
                px = hp[0] + kimono_w * off
                draw.line([(px, obi_y + 3 * scale), (px + off * 4 * scale, bot_y + 15 * scale)], fill="#44403C", width=max(1, lw // 3))
            # Wide-shouldered indigo haori / kimono jacket
            draw.rounded_rectangle(
                [sh_left_x - 5 * scale, top_y - 2 * scale, sh_right_x + 5 * scale, obi_y + 4 * scale],
                radius=max(5, int(7 * scale)),
                fill=haori_col,
                outline=fg,
                width=max(2, lw - 1),
            )
            # Crisp white inner collar V + crossed kimono lapel
            draw.polygon([(mid_x - 6 * scale, top_y - 1 * scale), (mid_x + 6 * scale, top_y - 1 * scale), (mid_x, obi_y - 2 * scale)], fill="#FFFFFF", outline=fg, width=max(1, lw // 2))
            draw.line([(mid_x - 3 * scale, top_y), (mid_x + 3 * scale, obi_y - 4 * scale)], fill=fg, width=max(1, lw // 2))
            # Waist sash belt (obi)
            draw.rounded_rectangle([hp[0] - kimono_w * 0.90, obi_y - 4 * scale, hp[0] + kimono_w * 0.90, obi_y + 5 * scale], radius=max(2, int(2 * scale)), fill=obi_col, outline=fg, width=max(1, lw // 2))
            # Katana scabbard + wrapped hilt tucked at obi waist!
            kat_col = "#1C1917"
            k_x0, k_y0 = hp[0] - dir_sign * 20 * scale, obi_y + 14 * scale
            k_x1, k_y1 = hp[0] + dir_sign * 16 * scale, obi_y - 9 * scale
            draw.line([(k_x0, k_y0), (k_x1, k_y1)], fill=kat_col, width=max(3, int(3.8 * scale)))
            # Tsuba guard + wrapped handle
            hx_k, hy_k = hp[0] + dir_sign * 9 * scale, obi_y - 4 * scale
            draw.line([(hx_k - dir_sign * 2 * scale, hy_k - 4 * scale), (hx_k + dir_sign * 2 * scale, hy_k + 4 * scale)], fill="#D97706", width=max(2, lw // 2))
            draw.line([(hx_k, hy_k), (k_x1, k_y1)], fill="#78350F", width=max(3, int(3.2 * scale)))
        elif outfit in ("historical_coat", "classical_tunic"):
            if outfit == "historical_coat":
                coat_col = "#1E293B" if char_index == 0 else "#7F1D1D"
                poly = [
                    (sh_left_x - 2 * scale, top_y),
                    (sh_right_x + 2 * scale, top_y),
                    (hp[0] + sh_w * 1.05, bot_y + 7 * scale),
                    (hp[0] - sh_w * 1.05, bot_y + 7 * scale),
                ]
                draw.polygon(poly, fill=coat_col, outline=fg, width=max(2, lw - 1))
                for by in (top_y + 9 * scale, top_y + 18 * scale, top_y + 27 * scale):
                    draw.ellipse([mid_x - 2 * scale, by - 2 * scale, mid_x + 2 * scale, by + 2 * scale], fill="#F59E0B")
            else:
                poly = [
                    (sh_left_x - 2 * scale, top_y),
                    (sh_right_x + 2 * scale, top_y),
                    (hp[0] + sh_w * 0.95, bot_y + 6 * scale),
                    (hp[0] - sh_w * 0.95, bot_y + 6 * scale),
                ]
                draw.polygon(poly, fill="#FFFBEB", outline=fg, width=max(2, lw - 1))
                draw.line([(sh_left_x, top_y), (hp[0] + sh_w * 0.8, bot_y)], fill=acc, width=max(3, lw))
        elif outfit in ("noir_hoodie", "noir_trench"):
            draw.rounded_rectangle(
                [sh_left_x - 3 * scale, top_y - 1 * scale, sh_right_x + 3 * scale, bot_y + 8 * scale],
                radius=max(4, int(8 * scale)),
                fill="#161122",
                outline=acc,
                width=max(2, lw - 1),
            )
        elif outfit in ("survival_hoodie", "survival_hoodie_alt"):
            col = "#1E293B" if outfit == "survival_hoodie" else "#334155"
            draw.rounded_rectangle(
                [sh_left_x - 2.5 * scale, top_y - 1 * scale, sh_right_x + 2.5 * scale, bot_y + 3 * scale],
                radius=max(4, int(8 * scale)),
                fill=col,
                outline=rim or "#94A3B8",
                width=max(2, lw - 1),
            )
        elif outfit == "presenter_suit":
            draw.rounded_rectangle(
                [sh_left_x - 2.5 * scale, top_y - 1 * scale, sh_right_x + 2.5 * scale, bot_y + 3 * scale],
                radius=max(4, int(7 * scale)),
                fill="#1E293B",
                outline=fg,
                width=max(2, lw - 1),
            )
            # Crisp white V-shirt & red/accent bowtie
            draw.polygon([(mid_x - 6 * scale, top_y), (mid_x + 6 * scale, top_y), (mid_x, top_y + 18 * scale)], fill="#FFFFFF")
            bw = 7 * scale
            bh = 4 * scale
            draw.polygon([(mid_x, top_y + 3 * scale), (mid_x - bw, top_y + 3 * scale - bh), (mid_x - bw, top_y + 3 * scale + bh)], fill=acc)
            draw.polygon([(mid_x, top_y + 3 * scale), (mid_x + bw, top_y + 3 * scale - bh), (mid_x + bw, top_y + 3 * scale + bh)], fill=acc)

    def _draw_accessories(
        self,
        draw: ImageDraw.ImageDraw,
        hx: float,
        hy: float,
        nk: tuple[float, float],
        hr: float,
        lw: int,
        scale: float,
        dir_sign: int,
        time_sec: float,
        outfit: str,
        accessory: str,
        fg: str,
        acc: str,
        acc2: str,
        char_index: int,
    ) -> None:
        """Draw headwear, scarves, caveman hair + bone, samurai topknot, top hats, beanies."""
        if accessory == "ponytail" or outfit in ("feminine_silhouette", "skirt_dress"):
            # Signature feminine sleek ponytail + ribbon (Maya/Female stickman)
            ribbon_col = acc or "#F43F5E"
            hair_c = fg or "#18181B"
            tie_x = hx - dir_sign * hr * 0.70
            tie_y = hy - hr * 0.35
            # Ribbon tie
            draw.ellipse([tie_x - 3.5 * scale, tie_y - 3.5 * scale, tie_x + 3.5 * scale, tie_y + 3.5 * scale], fill=ribbon_col, outline=fg, width=max(1, lw // 3))
            # Elegant flowing ponytail curves swooping backwards
            pts = [
                (tie_x, tie_y),
                (tie_x - dir_sign * 14 * scale, tie_y + 4 * scale),
                (tie_x - dir_sign * 24 * scale, tie_y + 22 * scale),
                (tie_x - dir_sign * 20 * scale, tie_y + 36 * scale),
                (tie_x - dir_sign * 12 * scale, tie_y + 24 * scale),
                (tie_x, tie_y + 4 * scale),
            ]
            draw.polygon(pts, fill=hair_c, outline=fg, width=max(1, lw // 2))
            # Soft side bangs
            draw.arc([hx - hr * 0.8, hy - hr * 0.9, hx + hr * 0.8, hy - hr * 0.1], start=190, end=340, fill=hair_c, width=max(1, int(2.2 * scale)))
        elif outfit == "beanie_tee" or accessory == "red_beanie":
            beanie_col = "#EF4444" if char_index == 0 else "#3B82F6"
            top_y = hy - hr - 7 * scale
            brim_y = hy - hr * 0.44
            # Soft rounded slouchy knit dome
            draw.chord([hx - hr * 1.00, top_y, hx + hr * 1.00, brim_y + hr * 0.7], start=180, end=360, fill=beanie_col, outline=fg, width=max(2, lw // 2))
            # Soft ribbed beanie cuff
            draw.rounded_rectangle([hx - hr * 1.05, brim_y - 3 * scale, hx + hr * 1.05, brim_y + 4.5 * scale], radius=max(3, int(3.5 * scale)), fill=beanie_col, outline=fg, width=max(2, lw // 2))
            draw.ellipse([hx - 3.5 * scale, top_y - 3.5 * scale, hx + 3.5 * scale, top_y + 2.5 * scale], fill=beanie_col, outline=fg, width=max(1, lw // 3))
        elif outfit in ("samurai_kimono", "samurai_hakama") or accessory == "samurai_topknot":
            # Authentic Samurai chonmage topknot bun + white ribbon tie (matches reference!)
            hair_c = "#18181B"
            bun_x = hx - dir_sign * hr * 0.25
            bun_y = hy - hr * 1.12
            # Lower tied hair base on crown
            draw.ellipse([hx - hr * 0.48, hy - hr * 1.12, hx + hr * 0.42, hy - hr * 0.68], fill=hair_c, outline=fg, width=max(1, lw // 2))
            # Swooped forward topknot lock
            draw.polygon([
                (bun_x - dir_sign * 4 * scale, bun_y + 2 * scale),
                (bun_x + dir_sign * 9 * scale, bun_y - 6 * scale),
                (bun_x + dir_sign * 13 * scale, bun_y - 1 * scale),
                (bun_x + dir_sign * 3 * scale, bun_y + 5 * scale),
            ], fill=hair_c, outline=fg, width=max(1, lw // 2))
            # White traditional tie band + fluttering ribbon tails
            tie_x = hx - dir_sign * hr * 0.12
            tie_y = hy - hr * 0.94
            draw.line([(tie_x - 3 * scale, tie_y - 3 * scale), (tie_x + 3 * scale, tie_y + 3 * scale)], fill="#FFFFFF", width=max(2, int(2.6 * scale)))
            draw.polygon([
                (tie_x - dir_sign * 3 * scale, tie_y),
                (tie_x - dir_sign * 11 * scale, tie_y - 4 * scale),
                (tie_x - dir_sign * 9 * scale, tie_y + 1 * scale),
            ], fill="#FFFFFF", outline=fg, width=max(1, lw // 3))
        elif outfit in ("hide_tunic", "hide_tunic_alt") or accessory == "caveman_hair":
            hair_col = "#221712"
            if outfit == "hide_tunic_alt":
                # Chunky chief: curved bushy cap hair + signature white bone hair-pin!
                draw.chord([hx - hr * 0.98, hy - hr * 1.18, hx + hr * 0.98, hy - hr * 0.22], start=180, end=360, fill=hair_col, outline=fg, width=max(1, lw // 2))
                # Prehistoric white bone on crown
                bx, by = hx, hy - hr * 1.16
                bw = 11 * scale
                draw.rectangle([bx - bw, by - 2.6 * scale, bx + bw, by + 2.6 * scale], fill="#FFFBEB", outline=fg, width=max(1, lw // 3))
                for end_x in (bx - bw, bx + bw):
                    for ky_off in (-2.5 * scale, 2.5 * scale):
                        draw.ellipse([end_x - 3 * scale, by + ky_off - 2.6 * scale, end_x + 3 * scale, by + ky_off + 2.6 * scale], fill="#FFFBEB", outline=fg, width=max(1, lw // 3))
            else:
                # Wild messy radiating black ink hair strands
                for ang_deg, length in ((-138, 1.38), (-118, 1.48), (-95, 1.44), (-75, 1.46), (-52, 1.38), (-32, 1.28)):
                    ang = math.radians(ang_deg)
                    x0 = hx + math.cos(ang) * (hr * 0.72)
                    y0 = hy + math.sin(ang) * (hr * 0.72)
                    x1 = hx + math.cos(ang + 0.08) * (hr * length)
                    y1 = hy + math.sin(ang + 0.08) * (hr * length)
                    draw.line([(x0, y0), (x1, y1)], fill=hair_col, width=max(2, int(2.6 * scale)))
                draw.chord([hx - hr * 0.85, hy - hr * 1.02, hx + hr * 0.85, hy - hr * 0.30], start=185, end=355, fill=hair_col)
        elif outfit == "historical_coat" or accessory == "top_hat":
            brim_y = hy - hr * 0.72
            draw.line([(hx - hr * 1.25, brim_y), (hx + hr * 1.25, brim_y)], fill=fg, width=max(3, lw))
            crown_w = hr * 0.82
            crown_h = hr * 1.1
            draw.rectangle([hx - crown_w, brim_y - crown_h, hx + crown_w, brim_y], fill="#1C1917", outline=fg, width=max(2, lw // 2))
            draw.rectangle([hx - crown_w, brim_y - 5 * scale, hx + crown_w, brim_y], fill=acc)
        elif accessory == "cap" or outfit == "pop_hoodie":
            cap_col = acc if char_index == 0 else acc2
            cap_bot = hy - hr * 0.45
            cap_top = hy - hr - 5 * scale
            draw.pieslice([hx - hr, cap_top, hx + hr, cap_bot + hr * 0.45], start=180, end=360, fill=cap_col, outline=fg, width=max(1, lw - 1))
            brim_x1 = hx - hr if dir_sign > 0 else hx - hr - 8 * scale
            brim_x2 = hx + hr + 8 * scale if dir_sign > 0 else hx + hr
            draw.line([(brim_x1, cap_bot), (brim_x2, cap_bot)], fill=fg, width=max(2, lw))
        elif outfit == "minimalist" and self.style == "b1_minimal_line_art" and char_index == 0:
            # Subtle 2-strand expressive cartoon hair flicks matching Minimal Line Art hero!
            for dx, dy in ((-4, -hr * 1.25), (3, -hr * 1.32)):
                draw.line([(hx, hy - hr * 0.88), (hx + dx * scale, hy + dy)], fill=fg, width=max(1, lw // 2))

        # Flowing scarf on neck (subtle scarf for cozy indoor / b2, skip over minimal cafe look)
        if accessory == "scarf" and outfit not in ("samurai_kimono", "samurai_hakama", "hide_tunic", "hide_tunic_alt") and self.style != "a4_cozy_storytelling":
            sc_col = acc if char_index == 0 else acc2
            flutter = math.sin(time_sec * 4.5) * 3.0 * scale
            draw.rounded_rectangle([nk[0] - 9 * scale, nk[1] - 3 * scale, nk[0] + 9 * scale, nk[1] + 3.5 * scale], radius=max(2, int(2 * scale)), fill=sc_col, outline=fg, width=max(1, lw // 3))
            draw.polygon([
                (nk[0] - dir_sign * 2 * scale, nk[1] + 2 * scale),
                (nk[0] - dir_sign * 7 * scale, nk[1] + 2 * scale),
                (nk[0] - dir_sign * (12 * scale + abs(flutter)), nk[1] + 18 * scale),
                (nk[0] - dir_sign * (6 * scale + abs(flutter) * 0.5), nk[1] + 19 * scale),
            ], fill=sc_col, outline=fg, width=max(1, lw // 3))

        # Dapper Bowtie for Person B or Presenter
        if accessory in ("glasses_bowtie", "bowtie") and outfit != "presenter_suit":
            bow_col = acc if char_index == 0 else acc2
            bw = 6.5 * scale
            bh = 4.0 * scale
            draw.polygon([(nk[0], nk[1] + 4 * scale), (nk[0] - bw, nk[1] + 4 * scale - bh), (nk[0] - bw, nk[1] + 4 * scale + bh)], fill=bow_col, outline=fg, width=max(1, lw // 3))
            draw.polygon([(nk[0], nk[1] + 4 * scale), (nk[0] + bw, nk[1] + 4 * scale - bh), (nk[0] + bw, nk[1] + 4 * scale + bh)], fill=bow_col, outline=fg, width=max(1, lw // 3))
            draw.ellipse([nk[0] - 2.5 * scale, nk[1] + 2 * scale, nk[0] + 2.5 * scale, nk[1] + 6 * scale], fill=bow_col, outline=fg, width=max(1, lw // 3))

    def get_hand_position(
        self,
        cx: int,
        cy: int,
        pose: str = "STAND",
        scale: float = 1.0,
        facing: str = "right",
        hand: str = "right",
        joints_override: Optional[dict[str, tuple[float, float]]] = None,
    ) -> tuple[int, int]:
        joints = joints_override or self._get_pose_joints(pose, scale, facing)
        key = "r_hand" if hand == "right" else "l_hand"
        ox, oy = joints[key]
        return int(cx + ox), int(cy + oy)

    @staticmethod
    def _pose_to_emotion(pose: str) -> str:
        mapping = {
            "LAUGH": "HAPPY", "LAUGH_UP": "HAPPY", "CELEBRATE": "HAPPY",
            "WAVE": "HAPPY", "WAVE_ALT": "HAPPY", "JUMP": "HAPPY",
            "CRY": "SAD", "BOW": "SAD", "SIT_KNEEL": "SAD", "RECEIVE": "SAD", "COWER": "SURPRISED",
            "ANGRY": "ANGRY", "SHOUT": "SURPRISED", "FIGHT_1": "ANGRY",
            "FIGHT_2": "ANGRY", "STOP_HAND": "ANGRY",
            "CONFUSED": "CONFUSED", "SHRUG": "CONFUSED", "THINK": "NEUTRAL",
            "THINK_TILT": "CONFUSED", "FALL": "SURPRISED",
        }
        return mapping.get(pose, "NEUTRAL")

    def draw_expression(
        self,
        draw: ImageDraw.ImageDraw,
        cx: int,
        cy: int,
        emotion: str,
        scale: float,
        fg_override: Optional[str] = None,
        head_fill: str = "#FFFFFF",
        blinking: bool = False,
        mouth_open: bool = False,
        mouth_wide: bool = False,
        facing: str = "right",
        cheek_blush: bool = False,
        has_glasses: bool = False,
        has_mustache: bool = False,
        has_sclera: bool = False,
        has_nose: bool = False,
        has_eyelashes: bool = False,
        time_sec: float = 0.0,
        gaze_target: Optional[tuple[float, float]] = None,
    ) -> None:
        """
        Draw vibrant cartoon eyes (with optional sclera & gaze tracking), brows,
        noses, sweat drops, shock lines, wedge cringes & mouths.
        Created by Atharv Hatwar.
        """
        fg = fg_override or self.params["fg"]
        er = max(2.2, 3.3 * scale) * (1.45 if emotion in ("SHOCKED", "SURPRISED") else 1.0)
        eo = max(5.2, 7.2 * scale)
        ey = max(2.0, 3.6 * scale)
        mw = max(5.2, 8.2 * scale)
        shift_x = (2.8 * scale) if facing == "right" else (-2.8 * scale)
        ew = max(1, int(round(2.0 * scale)))
        dir_sign = 1 if facing == "right" else -1

        # Gaze Tracking Vector Computation (shift pupils toward focal prop or partner)
        norm_gx, norm_gy = 0.0, 0.0
        if gaze_target is not None:
            gdx = float(gaze_target[0]) - cx
            gdy = float(gaze_target[1]) - cy
            dist = math.hypot(gdx, gdy)
            if dist > 1.0:
                max_g = min(2.6 * scale, dist * 0.015)
                norm_gx = (gdx / dist) * max_g
                norm_gy = (gdy / dist) * max_g * 0.75

        # Optional soft pink rosy cheeks for warm/cute styles
        if cheek_blush and emotion not in ("ANGRY", "CRINGE", "DISGUST"):
            cr_x = 3.2 * scale
            cr_y = 2.0 * scale
            for cx_off in (-eo * 1.25, eo * 1.25):
                bx = cx + cx_off + shift_x
                by = cy + 2.8 * scale
                draw.ellipse([bx - cr_x, by - cr_y, bx + cr_x, by + cr_y], fill=(255, 130, 145, 115))

        # ── Eyes (Cartoon sclera, Gaze-shifted pupils, Shock expansion, or Cringe wedge) ──
        for ex in (-eo, eo):
            ex_pos = cx + ex + shift_x
            ey_pos = cy - ey
            if blinking:
                draw.arc([ex_pos - er * 1.15, ey_pos - er * 0.5, ex_pos + er * 1.15, ey_pos + er * 0.9], start=0, end=180, fill=fg, width=ew)
            elif emotion in ("SLEEP", "CALM"):
                # Serene resting curved eyelids
                draw.arc([ex_pos - er * 1.25, ey_pos - er * 0.5, ex_pos + er * 1.25, ey_pos + er * 0.85], start=20, end=160, fill=fg, width=max(1, ew))
            elif emotion in ("CRINGE", "DISGUST"):
                # Comic wedge squint eyes: > for left eye, < for right eye
                ww = er * 1.25
                wh = er * 1.05
                if ex < 0:
                    draw.line([(ex_pos - ww * 0.7, ey_pos - wh), (ex_pos + ww * 0.5, ey_pos)], fill=fg, width=max(2, ew))
                    draw.line([(ex_pos - ww * 0.7, ey_pos + wh), (ex_pos + ww * 0.5, ey_pos)], fill=fg, width=max(2, ew))
                else:
                    draw.line([(ex_pos + ww * 0.7, ey_pos - wh), (ex_pos - ww * 0.5, ey_pos)], fill=fg, width=max(2, ew))
                    draw.line([(ex_pos + ww * 0.7, ey_pos + wh), (ex_pos - ww * 0.5, ey_pos)], fill=fg, width=max(2, ew))
            elif has_sclera or emotion in ("SHOCKED", "SURPRISED"):
                scl_rx = er * (1.45 if emotion in ("SHOCKED", "SURPRISED") else 1.25)
                scl_ry = er * (1.55 if emotion in ("SHOCKED", "SURPRISED") else 1.15)
                draw.ellipse([ex_pos - scl_rx, ey_pos - scl_ry, ex_pos + scl_rx, ey_pos + scl_ry], fill="#FFFFFF", outline=fg, width=max(1, int(1.3 * scale)))
                pr = max(1.5, er * (0.36 if emotion in ("SHOCKED", "SURPRISED") else 0.55))
                px_off = (dir_sign * 1.1 * scale) + norm_gx
                py_off = norm_gy
                draw.ellipse([ex_pos + px_off - pr, ey_pos + py_off - pr, ex_pos + px_off + pr, ey_pos + py_off + pr], fill=fg)
                # Catchlight
                draw.ellipse([ex_pos + px_off - pr * 0.35, ey_pos + py_off - pr * 0.45, ex_pos + px_off - pr * 0.35 + max(0.8, pr * 0.4), ey_pos + py_off - pr * 0.45 + max(0.8, pr * 0.4)], fill="#FFFFFF")
            else:
                # Solid pupil shifted by gaze direction
                draw.ellipse([ex_pos + norm_gx - er, ey_pos + norm_gy - er, ex_pos + norm_gx + er, ey_pos + norm_gy + er], fill=fg)
                if not str(fg).startswith("#16") and head_fill != "#181222":
                    gr = max(0.8, er * 0.34)
                    draw.ellipse([ex_pos + norm_gx - er * 0.30, ey_pos + norm_gy - er * 0.48, ex_pos + norm_gx - er * 0.30 + gr, ey_pos + norm_gy - er * 0.48 + gr], fill="#FFFFFF")

            if has_glasses:
                gl_r = er * 1.75
                draw.ellipse([ex_pos - gl_r, ey_pos - gl_r, ex_pos + gl_r, ey_pos + gl_r], outline=fg, width=max(1, ew))

        if has_glasses:
            draw.line([(cx - eo + er * 1.7 + shift_x, cy - ey), (cx + eo - er * 1.7 + shift_x, cy - ey)], fill=fg, width=max(1, ew))

        # Cartoon curved eyelashes for female stickman
        if has_eyelashes:
            for ex in (-eo, eo):
                ex_pos = cx + ex + shift_x
                ey_pos = cy - ey - er * 0.7
                lash_dir = 1 if ex > 0 else -1
                draw.line([(ex_pos + lash_dir * er * 0.8, ey_pos + er * 0.2), (ex_pos + lash_dir * er * 1.6, ey_pos - er * 0.6)], fill=fg, width=max(1, int(1.8 * scale)))
                draw.line([(ex_pos + lash_dir * er * 0.5, ey_pos - er * 0.1), (ex_pos + lash_dir * er * 1.2, ey_pos - er * 1.0)], fill=fg, width=max(1, int(1.5 * scale)))

        # Optional cartoon bulbous nose (chunky caveman)
        if has_nose:
            nx = cx + shift_x + dir_sign * 1.5 * scale
            ny = cy + 0.5 * scale
            draw.ellipse([nx - 3.6 * scale, ny - 2.6 * scale, nx + 3.6 * scale, ny + 2.6 * scale], fill="#E59866", outline=fg, width=max(1, int(1.3 * scale)))

        # ── Expressive Eyebrows (Thick comic strokes) ──
        brow_y = cy - ey - er - max(2.2, 3.4 * scale)
        brow_w = max(2, int(round(2.4 * scale)))
        if emotion in ("SHOCKED", "SURPRISED"):
            # High arched surprised eyebrows
            brow_y_shock = cy - ey - er - max(3.5, 6.0 * scale)
            draw.arc([cx - eo - 4.2 * scale + shift_x, brow_y_shock - 3.2 * scale, cx - eo + 4.2 * scale + shift_x, brow_y_shock + 3.2 * scale], start=180, end=360, fill=fg, width=brow_w)
            draw.arc([cx + eo - 4.2 * scale + shift_x, brow_y_shock - 3.2 * scale, cx + eo + 4.2 * scale + shift_x, brow_y_shock + 3.2 * scale], start=180, end=360, fill=fg, width=brow_w)
            # Radiant shock lines radiating outward from head
            for ang in (-35, -15, 0, 15, 35):
                rad = math.radians(ang - 90)
                r_in = 22.0 * scale
                r_out = 32.0 * scale
                lx1 = cx + shift_x + math.cos(rad) * r_in
                ly1 = cy + math.sin(rad) * r_in
                lx2 = cx + shift_x + math.cos(rad) * r_out
                ly2 = cy + math.sin(rad) * r_out
                draw.line([(lx1, ly1), (lx2, ly2)], fill=fg, width=max(1, ew))
        elif emotion == "ANGRY":
            draw.line([(cx - eo - 3.8 * scale + shift_x, brow_y - 3.2 * scale), (cx - eo + 4.2 * scale + shift_x, brow_y + 2.0 * scale)], fill=fg, width=brow_w)
            draw.line([(cx + eo + 3.8 * scale + shift_x, brow_y - 3.2 * scale), (cx + eo - 4.2 * scale + shift_x, brow_y + 2.0 * scale)], fill=fg, width=brow_w)
        elif emotion == "SAD":
            draw.line([(cx - eo - 3.8 * scale + shift_x, brow_y + 1.8 * scale), (cx - eo + 4.2 * scale + shift_x, brow_y - 2.2 * scale)], fill=fg, width=ew)
            draw.line([(cx + eo + 3.8 * scale + shift_x, brow_y + 1.8 * scale), (cx + eo - 4.2 * scale + shift_x, brow_y - 2.2 * scale)], fill=fg, width=ew)
            drop_y = cy - ey + er + 4 * scale + (math.sin(time_sec * 4.0) * 1.5 * scale)
            tx = cx + eo + shift_x
            draw.polygon([(tx, drop_y - 2 * scale), (tx - 2 * scale, drop_y + 2 * scale), (tx + 2 * scale, drop_y + 2 * scale)], fill="#38BDF8")
        elif emotion == "CONFUSED":
            draw.arc([cx - eo - 3.5 * scale + shift_x, brow_y - 4.5 * scale, cx - eo + 4.5 * scale + shift_x, brow_y + 1.5 * scale], start=190, end=350, fill=fg, width=ew)
            draw.arc([cx + eo - 4.5 * scale + shift_x, brow_y - 2.5 * scale, cx + eo + 3.5 * scale + shift_x, brow_y + 2.5 * scale], start=190, end=350, fill=fg, width=ew)
        elif emotion in ("CRINGE", "DISGUST"):
            # Furrowed tight brows
            draw.line([(cx - eo - 3.0 * scale + shift_x, brow_y + 1.5 * scale), (cx - eo + 3.5 * scale + shift_x, brow_y - 1.0 * scale)], fill=fg, width=brow_w)
            draw.line([(cx + eo + 3.0 * scale + shift_x, brow_y + 1.5 * scale), (cx + eo - 3.5 * scale + shift_x, brow_y - 1.0 * scale)], fill=fg, width=brow_w)
        elif has_sclera or has_nose:
            draw.line([(cx - eo - 3 * scale + shift_x, brow_y), (cx - eo + 3 * scale + shift_x, brow_y - 1 * scale)], fill=fg, width=ew)
            draw.line([(cx + eo - 3 * scale + shift_x, brow_y - 1 * scale), (cx + eo + 3 * scale + shift_x, brow_y)], fill=fg, width=ew)

        # Optional period mustache (A5 secondary)
        if has_mustache:
            my_mu = cy + 3.0 * scale
            mx_mu = cx + shift_x
            draw.arc([mx_mu - mw, my_mu - 2 * scale, mx_mu, my_mu + 4 * scale], start=180, end=360, fill=fg, width=max(2, ew))
            draw.arc([mx_mu, my_mu - 2 * scale, mx_mu + mw, my_mu + 4 * scale], start=180, end=360, fill=fg, width=max(2, ew))

        # ── Expressive Animated Mouth ──
        my = cy + max(4.2, 6.4 * scale)
        mx = cx + shift_x
        if mouth_open and emotion not in ("SAD", "CRINGE"):
            mh = (5.0 if mouth_wide else 3.2) * scale
            mw_o = mw * (0.72 if mouth_wide else 0.55)
            draw.ellipse([mx - mw_o, my - mh * 0.7, mx + mw_o, my + mh], fill=fg)
            if mouth_wide:
                draw.arc([mx - mw_o * 0.7, my, mx + mw_o * 0.7, my + mh * 0.9], start=0, end=180, fill="#F43F5E", width=max(1, ew))
        elif emotion in ("SHOCKED", "SURPRISED"):
            or_w = max(4.2, 6.2 * scale)
            or_h = max(5.0, 7.2 * scale)
            draw.ellipse([mx - or_w, my - or_h * 0.55, mx + or_w, my + or_h * 0.75], fill="#7F1D1D" if has_sclera else head_fill, outline=fg, width=ew)
        elif emotion in ("CRINGE", "DISGUST"):
            # Wavy nervous squiggly mouth
            pts = [
                (mx - mw * 0.85, my),
                (mx - mw * 0.40, my + 3.0 * scale),
                (mx, my - 2.5 * scale),
                (mx + mw * 0.40, my + 3.0 * scale),
                (mx + mw * 0.85, my - 1.0 * scale),
            ]
            draw.line(pts, fill=fg, width=max(1, ew))
        elif emotion in ("SLEEP", "CALM"):
            # Gentle relaxed slight smile
            draw.arc([mx - mw * 0.5, my - 2 * scale, mx + mw * 0.5, my + 3.2 * scale], start=20, end=160, fill=fg, width=ew)
        elif emotion == "HAPPY":
            pts = [
                (mx - mw, my),
                (mx - mw * 0.5, my + 4.8 * scale),
                (mx, my + 6.6 * scale),
                (mx + mw * 0.5, my + 4.8 * scale),
                (mx + mw, my),
            ]
            draw.line(pts, fill=fg, width=ew, joint="curve")
        elif emotion == "SAD":
            pts = [
                (mx - mw, my + 5.2 * scale),
                (mx - mw * 0.5, my + 1.8 * scale),
                (mx, my),
                (mx + mw * 0.5, my + 1.8 * scale),
                (mx + mw, my + 5.2 * scale),
            ]
            draw.line(pts, fill=fg, width=ew, joint="curve")
        elif emotion == "ANGRY":
            draw.rounded_rectangle([mx - mw * 0.75, my - 2.5 * scale, mx + mw * 0.75, my + 3.2 * scale], radius=max(1, int(2 * scale)), fill="#FFFFFF", outline=fg, width=max(1, ew))
            draw.line([(mx - mw * 0.7, my + 0.3 * scale), (mx + mw * 0.7, my + 0.3 * scale)], fill=fg, width=max(1, int(1.2 * scale)))
        elif emotion == "CONFUSED":
            pts = [
                (mx - mw, my + 2 * scale),
                (mx - mw * 0.3, my - 1 * scale),
                (mx + mw * 0.3, my + 2 * scale),
                (mx + mw, my - 1 * scale),
            ]
            draw.line(pts, fill=fg, width=ew, joint="curve")
        else:
            draw.line([(mx - mw + 2 * scale, my), (mx + mw - 2 * scale, my)], fill=fg, width=ew)

        # ── Cartoon Emotion Overlays (Created by Atharv Hatwar) ──
        if emotion in ("CONFUSED", "SAD", "CRINGE", "DISGUST"):
            # Blue animated cartoon sweat drop rolling down temple
            sw_x = cx - dir_sign * eo * 1.55 + shift_x
            sw_y = cy - ey - 5.0 * scale + (time_sec * 10.0 * scale) % (14.0 * scale)
            draw.polygon([(sw_x, sw_y - 4.5 * scale), (sw_x - 2.8 * scale, sw_y + 2.0 * scale), (sw_x + 2.8 * scale, sw_y + 2.0 * scale)], fill="#38BDF8")
            draw.ellipse([sw_x - 2.8 * scale, sw_y - 1.0 * scale, sw_x + 2.8 * scale, sw_y + 4.5 * scale], fill="#38BDF8")
        elif emotion == "ANGRY":
            # Red pulsing anger vein mark on forehead
            av_x = cx + dir_sign * eo * 1.35 + shift_x
            av_y = cy - ey - 7.0 * scale
            draw.line([(av_x - 3.5 * scale, av_y - 3.5 * scale), (av_x + 3.5 * scale, av_y + 3.5 * scale)], fill="#EF4444", width=max(2, int(2.0 * scale)))
            draw.line([(av_x + 3.5 * scale, av_y - 3.5 * scale), (av_x - 3.5 * scale, av_y + 3.5 * scale)], fill="#EF4444", width=max(2, int(2.0 * scale)))
        elif emotion in ("EXCITED", "HAPPY"):
            # Subtle sparkle star glints next to head
            gl_x = cx + dir_sign * eo * 1.65 + shift_x
            gl_y = cy - ey - 6.0 * scale
            sp_sz = max(2.5, 4.0 * scale)
            draw.line([(gl_x - sp_sz, gl_y), (gl_x + sp_sz, gl_y)], fill="#FBBF24", width=max(1, int(1.5 * scale)))
            draw.line([(gl_x, gl_y - sp_sz), (gl_x, gl_y + sp_sz)], fill="#FBBF24", width=max(1, int(1.5 * scale)))

    @staticmethod
    def get_walk_cycle_pose(frame: int) -> str:
        return "WALK_1" if frame % 2 == 0 else "WALK_2"

    @staticmethod
    def get_run_cycle_pose(frame: int) -> str:
        return "RUN_1" if frame % 2 == 0 else "RUN_2"
