"""
Smart Video Director Engine - Professional Automated Video Editing & Motion Graphics
=====================================================================================
Analyzes script narration semantically and orchestrates professional video editing
techniques: dynamic camera choreography (snap zooms, camera shakes, slow push-ins),
kinetic motion graphics badges, elastic prop pop-ins, and cinematic visual FX.

Created by Atharv Hatwar.
"""

from __future__ import annotations

import hashlib
import logging
import math
import random
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class SmartVideoDirector:
    """
    Intelligent AI Video Director & Editor.
    Transforms simple scenes into dynamic, professionally edited videos.
    Created by Atharv Hatwar.
    """

    @classmethod
    def direct_storyboard(cls, scenes: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Enriches an entire storyboard with editorial pacing, dynamic camera cuts,
        kinetic callout badges, and scene-specific visual FX.
        """
        total = len(scenes)
        enriched: list[dict[str, Any]] = []

        last_camera = ""
        last_badge_title = ""

        for idx, sc in enumerate(scenes):
            scene_copy = dict(sc)
            narr = str(scene_copy.get("narration", "")).strip()

            # 1. Semantic Mood & Beat Analysis
            beat_info = cls.analyze_narrative_beat(narr, idx, total)

            # 2. Camera Choreography (Avoid repeating same camera consecutively)
            cam = beat_info["camera"]
            if cam == last_camera:
                alternatives = [c for c in beat_info["candidate_cameras"] if c != last_camera]
                cam = alternatives[0] if alternatives else "SLOW_ZOOM_IN"
            scene_copy["camera"] = cam
            last_camera = cam

            # 3. Editorial Pacing & Visual FX (intrusive top banner badges disabled per user directive)
            scene_copy["editor_badge"] = None

            # 4. Cinematic Effects Overlay
            current_effects = list(scene_copy.get("effects", []))
            for eff in beat_info["effects"]:
                if eff not in current_effects:
                    current_effects.append(eff)
            # Add dynamic action speed lines for fast moves
            first_char_act = str(scene_copy.get("characters", [{}])[0].get("action", "")).upper() if scene_copy.get("characters") else ""
            if first_char_act in ("SPRINT_FAST", "RUN", "JUMP", "FIGHT") and "SPEED_LINES" not in current_effects:
                current_effects.append("SPEED_LINES")
            scene_copy["effects"] = current_effects

            # 5. Dynamic Transitions (Punchy cuts & directional slides)
            if idx == 0:
                scene_copy["transition_in"] = "FADE"
            elif beat_info["energy"] == "HIGH":
                scene_copy["transition_in"] = "SNAP_CUT"
            elif "vs" in narr.lower() or "contrast" in narr.lower():
                scene_copy["transition_in"] = "SLIDE_LEFT"

            enriched.append(scene_copy)

        return enriched

    @classmethod
    def analyze_narrative_beat(cls, narration: str, idx: int, total: int) -> dict[str, Any]:
        """Classify narration into an emotional storytelling beat."""
        text = narration.lower()

        # Opening Hook (Scene 0)
        if idx == 0:
            return {
                "beat": "HOOK",
                "energy": "HIGH",
                "camera": "DYNAMIC_CUT",
                "candidate_cameras": ["DYNAMIC_CUT", "PUNCH_IN", "SNAP_ZOOM", "CLOSE"],
                "effects": ["VIGNETTE", "FLASH_CUT"],
            }

        # Final Resolution / Climax
        if idx == total - 1:
            return {
                "beat": "RESOLUTION",
                "energy": "CELEBRATION",
                "camera": "SLOW_ZOOM_OUT",
                "candidate_cameras": ["SLOW_ZOOM_OUT", "DYNAMIC_CUT", "WIDE"],
                "effects": ["CONFETTI", "SPARKLES"],
            }

        # Danger / Warning / Mistake / Struggle
        if any(w in text for w in ("mistake", "wrong", "trap", "danger", "fail", "lost", "struggle", "debt", "fear", "anxiety", "pain", "stop", "never")):
            return {
                "beat": "WARNING",
                "energy": "HIGH",
                "camera": "CAMERA_SHAKE",
                "candidate_cameras": ["CAMERA_SHAKE", "DYNAMIC_CUT", "PUNCH_IN", "CLOSE"],
                "effects": ["VIGNETTE", "SPEED_LINES"],
            }

        # Core Insight / Revelation / Shift
        if any(w in text for w in ("secret", "truth", "realize", "clicks", "key", "insight", "solution", "eureka", "understand", "clear", "actually")):
            return {
                "beat": "INSIGHT",
                "energy": "FOCUSED",
                "camera": "DYNAMIC_CUT",
                "candidate_cameras": ["DYNAMIC_CUT", "PUNCH_IN", "SLOW_ZOOM_IN", "CLOSE"],
                "effects": ["SPARKLES", "LIGHT_BURST"],
            }

        # Contrast / Comparison
        if any(w in text for w in ("instead", "versus", "vs", "difference", "compare", "opposite", "while others")):
            return {
                "beat": "CONTRAST",
                "energy": "DYNAMIC",
                "camera": "PAN_LEFT",
                "candidate_cameras": ["PAN_LEFT", "PAN_RIGHT", "WIDE"],
                "effects": ["VIGNETTE"],
            }

        # Financial / Growth / Habit Compounding
        if any(w in text for w in ("money", "invest", "dollar", "grow", "habit", "compound", "discipline", "daily", "routine", "build", "future", "rich")):
            return {
                "beat": "GROWTH",
                "energy": "POSITIVE",
                "camera": "OBJECT_FOCUS",
                "candidate_cameras": ["OBJECT_FOCUS", "SLOW_ZOOM_IN", "DYNAMIC_CUT"],
                "effects": ["GOLD_SPARKLES"],
            }

        # Default Storytelling Cadence
        cams = ["DYNAMIC_CUT", "OBJECT_FOCUS", "SLOW_ZOOM_IN", "PAN_RIGHT", "PAN_LEFT", "MEDIUM"]
        chosen_cam = cams[idx % len(cams)]
        return {
            "beat": "NARRATIVE",
            "energy": "STEADY",
            "camera": chosen_cam,
            "candidate_cameras": cams,
            "effects": ["VIGNETTE"],
        }

    @classmethod
    def synthesize_editor_badge(cls, narration: str, beat_info: dict[str, Any], scene_idx: int) -> Optional[dict[str, Any]]:
        """
        Synthesizes a sleek, Ali Abdaal / Vox style kinetic motion graphic badge
        matching the spoken sentence.
        """
        text = narration.lower().strip()
        if len(text) < 8:
            return None

        # 1. Finance / Wealth / Investment
        if any(w in text for w in ("money", "wealth", "invest", "compound", "saving", "spend", "rich", "dollar", "cost")):
            return {
                "icon": "💰",
                "title": "COMPOUND ASSETS",
                "tagline": "LONG-TERM EXPONENTIAL GROWTH",
                "accent": "#10B981",  # Emerald Green
                "badge_type": "METRIC",
            }

        # 2. Daily Habits / Discipline / Time
        if any(w in text for w in ("habit", "discipline", "routine", "daily", "day by day", "consistency", "hours", "time")):
            return {
                "icon": "🔥",
                "title": "1% DAILY STREAK",
                "tagline": "CONSISTENCY BEATS TALENT",
                "accent": "#F59E0B",  # Amber Fire
                "badge_type": "ACHIEVEMENT",
            }

        # 3. Mistake / Warning / Trap
        if any(w in text for w in ("mistake", "trap", "danger", "wrong", "fail", "procrastinat", "delay", "regret")):
            return {
                "icon": "⚠️",
                "title": "CRITICAL MISTAKE",
                "tagline": "99% OF PEOPLE FALL FOR THIS",
                "accent": "#EF4444",  # Crimson Red
                "badge_type": "ALERT",
            }

        # 4. Insight / Breakthrough / Solution
        if any(w in text for w in ("secret", "truth", "realize", "key", "solution", "insight", "eureka", "understand", "clarity")):
            return {
                "icon": "💡",
                "title": "CORE INSIGHT",
                "tagline": "THE BREAKTHROUGH SHIFT",
                "accent": "#06B6D4",  # Neon Cyan
                "badge_type": "INSIGHT",
            }

        # 5. Contrast / Two Paths
        if any(w in text for w in ("instead", "versus", "vs", "difference", "opposite", "two paths")):
            return {
                "icon": "⚖️",
                "title": "THE PARADOX",
                "tagline": "ACTION VS DISTRACTION",
                "accent": "#8B5CF6",  # Electric Violet
                "badge_type": "COMPARISON",
            }

        # 6. Tech / Software / AI
        if any(w in text for w in ("tech", "software", "code", "ai", "computer", "algorithm", "digital", "system")):
            return {
                "icon": "⚡",
                "title": "SYSTEM ARCHITECTURE",
                "tagline": "AUTOMATED HIGH-LEVERAGE",
                "accent": "#38BDF8",  # Sky Blue
                "badge_type": "TECH",
            }

        # 7. Action / Challenge (Hook or Climax)
        if beat_info["beat"] in ("HOOK", "RESOLUTION"):
            words = [w for w in re.findall(r"\w+", narration) if len(w) > 3][:3]
            kw_title = " ".join(words).upper() if words else "KEY TAKEAWAY"
            return {
                "icon": "🎯" if beat_info["beat"] == "HOOK" else "🏆",
                "title": kw_title,
                "tagline": "APPLY THIS PRINCIPLE TODAY",
                "accent": "#EC4899",  # Rose Fuchsia
                "badge_type": "CALL_TO_ACTION",
            }

        return None

