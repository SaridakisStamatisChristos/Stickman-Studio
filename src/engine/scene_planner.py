"""
scene_planner.py - Converts topics and scripts into structured, non-repeating
visual storyboards and duration-paced scripts using local Ollama or an
intelligent offline domain & style-aware engine.
"""

from __future__ import annotations

import json
import logging
import math
import re
import textwrap
from typing import Any

from engine.json_repair import parse_scene_json
from engine.llm_manager import LLMManager
from engine.procedural_scene_engine import ProceduralSceneEngine
from engine.scene_templates import (
    normalize_scene_for_composer,
    select_diverse_scene_template,
)
from styles.style_packs import StylePack, resolve_style_pack

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Valid option sets
# ---------------------------------------------------------------------------

_VALID_ACTIONS = {
    "WALK_RIGHT", "WALK_LEFT", "STAND", "THINK", "POINT", "POINT_RIGHT",
    "POINT_LEFT", "POINT_UP", "SIT", "KNEEL", "COWER", "RUN", "SNEAK", "JUMP",
    "WAVE", "FALL", "CELEBRATE", "ARGUE", "SHOUT", "FIGHT", "READ",
    "READ_SCROLL", "WRITE", "PHONE_CALL", "PRESENT", "GIVE", "RECEIVE",
    "REACH", "STOP", "HOLD_OBJECT", "CONFUSED", "CRY", "LAUGH",
    "HUNT_SPEAR", "WARM_FIRE", "STRUGGLE",
    # Additional actions supported by POSE_SEQUENCES in stickman.py (Atharv Hatwar)
    "SHRUG", "ANGRY",
    "TYPING_LAPTOP", "COUNT_MONEY", "FACEPALM", "HEADACHE_STRESS",
    "MEDITATE_ZEN", "SPRINT_FAST", "TRIUMPH_FIST", "DISMISSIVE_WAVE",
    "SURRENDER_HANDS", "PRESENT_CHART", "SCROLL_PHONE", "CROSS_ARMS",
}
_VALID_BACKGROUNDS = {
    "OFFICE", "STREET", "HOME", "PARK", "CLASSROOM",
    "ABSTRACT", "CITY", "HOSPITAL", "SHOP", "FACTORY",
    "BEACH", "MOUNTAIN", "LIBRARY", "STAGE",
    "CAVE", "CAFE", "STATION", "CASTLE",
    "BEDROOM", "BEDROOM_RETREAT", "GALLERY", "GALLERY_REFLECT",
    "FITNESS_GYM", "SPACE_COSMOS", "HIGHWAY_ROAD", "DESERT_PYRAMIDS", "STUDIO",
}
_VALID_CHARACTERS = {
    "PERSON_A", "PERSON_B", "PERSON_C",
    "NARRATOR", "BOSS", "CUSTOMER", "DOCTOR", "TEACHER",
}
_VALID_OBJECTS = {
    "PHONE", "MONEY", "COIN", "HOUSE", "CAR", "CHART", "BAR_CHART", "LINE_CHART",
    "PIE_CHART", "LAPTOP", "GLASS_CARD", "BOOK", "SCROLL", "CLOCK", "BAG",
    "SIGN", "TROPHY", "CROWN", "ENVELOPE", "LIGHTBULB", "HAMMER", "PLANT",
    "TREE", "TABLE", "CHAIR", "HEART", "STAR", "SOCIAL_MEDIA",
    "CONTROL_STRINGS", "CHAINS", "CAMPFIRE", "SPEAR", "CLUB", "COFFEE_CUP",
    "LANTERN", "WARNING", "ARROW", "QUESTION_MARK", "CHECK", "XMARK",
    "EXCLAMATION",
    # Procedural Metaphors (Created by Atharv Hatwar)
    "LEVER_BOULDER", "ICEBERG", "HAMSTER_WHEEL", "JUGGLING_BALLS", "DOMINOES",
    "BRICK_WALL", "CRACKED_WALL", "BATTERY_DRAIN", "BALANCE_SCALE", "HOURGLASS",
    "PODIUM", "SHIELD", "MAGNIFYING_GLASS",
    # Advanced Psychological & Storytelling Metaphors
    "MOUSETRAP", "GLASS_JAR_PRISON", "TETHER_THREAD", "PUPPET_STRINGS",
    "SIGH_SHOCKWAVES", "DOORWAY_SUNLIGHT", "NOTIFICATION_POPUP", "BREADCRUMB_TRAIL",
    "BROKEN_CROWN", "GIANT_CLOCK", "SNIPPED_THREAD_SUNRISE", "CHASM_CRACK",
    "EGO_TROPHY",
    # Animals & Dynamic Story Props (Atharv Hatwar)
    "DOG", "PUPPY", "CAT", "KITTEN", "BIRD", "HORSE", "FISH",
    "ROCKET", "BICYCLE", "BIKE", "TREASURE_CHEST", "TREASURE", "BRAIN",
}
_VALID_EFFECTS = {
    "SPEECH_BUBBLE", "THOUGHT_BUBBLE", "ARROW",
    "EMPHASIS", "SPARKLE", "EXPLOSION", "QUESTION_MARK",
    "EXCLAMATION", "CONFETTI", "TIMER", "VIGNETTE", "WARM", "COOL",
    "FLASH_CUT", "SPEED_LINES", "SPARKLES", "GOLD_SPARKLES",
}
_VALID_TRANSITIONS = {
    "FADE", "SLIDE_LEFT", "SLIDE_RIGHT", "CUT", "SNAP_CUT", "ZOOM_IN", "ZOOM_OUT", "WIPE", "VHS_GLITCH",
}
_VALID_CAMERAS = {
    "WIDE", "MEDIUM", "CLOSE", "ZOOM_IN", "ZOOM_OUT", "PAN_LEFT", "PAN_RIGHT",
    "PUNCH_IN", "SNAP_ZOOM", "CAMERA_SHAKE", "SLOW_ZOOM_IN", "SLOW_ZOOM_OUT",
}
_VALID_EMOTIONS = {"HAPPY", "SAD", "ANGRY", "CONFUSED", "NEUTRAL", "EXCITED", "SURPRISED"}
_VALID_CAPTION_STYLES = {"normal", "highlight", "subtitle", "none"}

_SCENE_TEMPLATE: dict[str, Any] = {
    "id": 0,
    "duration": 4.5,
    "narration": "",
    "action": "STAND",
    "background": "ABSTRACT",
    "characters": ["PERSON_A"],
    "objects": [],
    "effects": [],
    "transition": "FADE",
    "camera": "MEDIUM",
    "emotion": "NEUTRAL",
    "caption_style": "normal",
}

_WORDS_PER_SECOND = 2.4


def _clean_script_text(raw: str) -> str:
    """Strip markdown, stage brackets, speaker prefixes, metadata lines, and excess whitespace."""
    if not raw:
        return ""
    text = raw.strip()
    text = re.sub(r"^```[a-zA-Z]*\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Remove [stage directions] or (Pause) cues
    text = re.sub(r"\[[^\]]*\]", " ", text)
    text = re.sub(r"\((?:pause|sfx|music|scene|beat|slow and emotional)[^)]*\)", " ", text, flags=re.IGNORECASE)

    meta_tag = re.compile(
        r"^\s*(?:#+\s*|\*\*)?(?:duration|genre|voices|target|resolution|fps|aspect|end\s*screen|final\s*screen)\s*[:\-–—].*$",
        re.IGNORECASE,
    )
    cleaned_lines: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        # Skip markdown titles like # TITLE
        if line.startswith("#") and len(line.split()) <= 14 and not any(k in line.lower() for k in ("alex:", "maya:", "voice:", "scene:")):
            continue
        if meta_tag.match(line):
            continue
        if re.match(r"^['\"]?Read that again\.?.*?['\"]?$", line, re.IGNORECASE):
            continue

        # Remove "Narrator:" / "Host:" / "Male Voice:" / "Female Voice:" / "Alex:" / "Maya:" prefixes
        line = re.sub(
            r"^\s*(?:\*\*)?(?:narrator|host|speaker\s*\d*|voiceover|scene\s*\d+|male\s*voice|female\s*voice|male|female|alex|maya)(?:\*\*)?\s*[:\-–—]\s*",
            "",
            line,
            flags=re.IGNORECASE,
        )
        line = re.sub(r"^\s*[-*•]\s+", "", line)
        line = re.sub(r"[*_]+", "", line).strip()
        if line:
            cleaned_lines.append(line)
    out = re.sub(r"\s+", " ", " ".join(cleaned_lines)).strip()
    return out


class ScenePlanner:
    """Converts scripts & topics into structured storyboards + paced narration."""

    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm = llm_manager

    def _is_ollama_running(self) -> bool:
        return bool(self.llm and hasattr(self.llm, "check_ollama_running") and self.llm.check_ollama_running())

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def plan_scenes(
        self,
        script: str,
        topic: str = "",
        duration: int = 30,
        style: str = "a1_classic_bw",
        format: str = "9:16",
    ) -> list[dict]:
        """Parse *script* into validated, non-repeating, StylePack-aligned scene dicts."""
        pack, _sp = resolve_style_pack(style)
        if not script.strip():
            script = self.generate_script(topic=topic or "Human Behavior", duration=duration, style=pack.id)

        try:
            if self._is_ollama_running():
                prompt = self._build_planning_prompt(script, topic, duration, pack, format)
                response = self.llm.generate(
                    prompt,
                    max_tokens=2048,
                    temperature=0.35,
                )
                if response:
                    scenes = parse_scene_json(response)
                    if scenes:
                        scenes = [
                            normalize_scene_for_composer(self._validate_scene(s, pack), style_id=pack.id)
                            for s in scenes
                        ]
                        scenes = self._diversify_scenes(scenes, pack=pack)
                        scenes = self._assign_ids_and_durations(scenes, duration)
                        from engine.smart_video_director import SmartVideoDirector
                        scenes = SmartVideoDirector.direct_storyboard(scenes)
                        logger.info("ScenePlanner: LLM produced %d scenes directed by SmartVideoDirector for style %s", len(scenes), pack.id)
                        return scenes
        except Exception as exc:
            logger.warning("ScenePlanner.plan_scenes LLM path failed: %s", exc)

        logger.info("ScenePlanner: using intelligent semantic story planner (%s)", pack.id)
        try:
            from engine.script_intelligence import ScriptIntelligenceEngine
            beats = ScriptIntelligenceEngine.parse_script_to_story_beats(script)
            if len(beats) >= 2:
                sec_per_beat = max(1.5, duration / float(len(beats)))
                planned_scenes: list[dict] = []
                for b_idx, beat in enumerate(beats):
                    sc = ScriptIntelligenceEngine.plan_visual_for_beat(
                        beat=beat,
                        context_history=planned_scenes,
                        duration=sec_per_beat,
                    )
                    sc["id"] = b_idx + 1
                    planned_scenes.append(normalize_scene_for_composer(sc, style_id=pack.id))
                from engine.smart_video_director import SmartVideoDirector
                return SmartVideoDirector.direct_storyboard(planned_scenes)
        except Exception as exc:
            logger.warning("ScenePlanner ScriptIntelligenceEngine path note: %s", exc)

        fallback_scenes = self._create_fallback_scenes(script, duration, topic=topic, style_id=pack.id)
        from engine.smart_video_director import SmartVideoDirector
        return SmartVideoDirector.direct_storyboard(fallback_scenes)

    def shorten_script(
        self,
        script: str,
        target_duration: int,
        topic: str = "",
        style: str = "a1_classic_bw",
    ) -> str:
        """Condense *script* to fit *target_duration* while preserving hook + climax + outro."""
        max_words = max(16, int(target_duration * _WORDS_PER_SECOND))
        words = script.split()
        if len(words) <= max_words:
            return script.strip()

        pack, _sp = resolve_style_pack(style)
        prompt = textwrap.dedent(f"""
            Condense this narration script for a {target_duration}-second "{pack.name}"
            video about "{topic}" into {max_words} words or fewer.
            Keep the opening hook, the core insight, and a strong closing punchline.
            Return ONLY plain spoken sentences, no brackets or commentary.

            ORIGINAL:
            {script}

            SHORTENED:
        """).strip()

        try:
            if self._is_ollama_running():
                shortened = _clean_script_text(self.llm.generate(prompt, max_tokens=512, temperature=0.35))
                if shortened and 12 <= len(shortened.split()) <= max_words * 1.15:
                    return shortened
        except Exception as exc:
            logger.warning("shorten_script LLM failed: %s", exc)

        # Smart offline condensation: always preserve first sentence + last sentence + middle core!
        sentences = _split_into_sentences(script)
        if len(sentences) <= 2:
            trimmed = " ".join(sentences[0].split()[:max_words]).rstrip(",;:") + "."
            return trimmed

        hook = sentences[0]
        closing = sentences[-1]
        hook_w = len(hook.split())
        end_w = len(closing.split())

        if hook_w + end_w > max_words:
            return " ".join(sentences[0].split()[:max_words]).rstrip(",;:") + "."

        budget = max_words - hook_w - end_w
        middle_kept: list[str] = []
        for s in sentences[1:-1]:
            sw = len(s.split())
            if sw <= budget:
                middle_kept.append(s)
                budget -= sw
        return " ".join([hook] + middle_kept + [closing])

    def improve_script(
        self,
        script: str,
        topic: str = "",
        style: str = "a1_classic_bw",
        duration: int = 30,
        dialogue_mode: bool = False,
        name1: str = "Alex",
        name2: str = "Maya",
        address_by_name: bool = True,
    ) -> str:
        """Enhance *script* clarity, hook punch, and rhythm for TTS while preserving meaning."""
        if not script.strip():
            return script

        if dialogue_mode:
            try:
                from engine.inbuilt_ai_director import InbuiltAIDirector
                return InbuiltAIDirector.improve_script(
                    script=script,
                    target_duration=duration,
                    dialogue_mode=True,
                    name1=name1,
                    name2=name2,
                    address_by_name=address_by_name,
                )
            except Exception as exc:
                logger.warning("InbuiltAIDirector improve dialogue error: %s", exc)

        pack, _sp = resolve_style_pack(style)
        target_words = max(18, int(duration * _WORDS_PER_SECOND))
        prompt = textwrap.dedent(f"""
            You are an expert short-form narration scriptwriter for stickman animation.
            Improve the script below for a {duration}-second "{pack.name}" video ({pack.short_desc})
            about "{topic or 'this topic'}".

            Rules:
            - Keep the exact same meaning and message.
            - Target ~{target_words} words so it fits {duration} seconds naturally.
            - Use crisp, punchy spoken sentences (ideal for voiceover and captions).
            - Return ONLY spoken narration text. No labels, no brackets, no scene directions.

            ORIGINAL:
            {script}

            IMPROVED:
        """).strip()

        try:
            if self._is_ollama_running():
                improved = _clean_script_text(self.llm.generate(prompt, max_tokens=1024, temperature=0.55))
                if improved and len(improved.split()) >= 8:
                    return improved
        except Exception as exc:
            logger.warning("improve_script LLM failed: %s", exc)

        # Intelligent offline rhythmic cleanup: break walls of text into crisp voiced beats
        return self._improve_script_offline(script, target_duration=duration, topic=topic)

    def generate_script(
        self,
        topic: str,
        duration: int = 30,
        style: str = "a1_classic_bw",
        dialogue_mode: bool = False,
        name1: str = "Alex",
        name2: str = "Maya",
        address_by_name: bool = True,
        seed: int = 0,
    ) -> str:
        """Generate a duration-paced, style-toned narration script from *topic*."""
        pack, _sp = resolve_style_pack(style)
        clean_topic = (topic or "human behavior").strip()

        if seed == 0:
            import time as _time, random as _random
            seed = (int(_time.time() * 1000) ^ _random.randint(1, 999999)) & 0x7FFFFFFF

        # If dialogue mode requested, route directly to high-speed Inbuilt AI Director
        if dialogue_mode:
            try:
                from engine.inbuilt_ai_director import InbuiltAIDirector
                return InbuiltAIDirector.generate_script(
                    topic=clean_topic,
                    duration=duration,
                    dialogue_mode=True,
                    name1=name1,
                    name2=name2,
                    address_by_name=address_by_name,
                    style=style,
                    seed=seed,
                )
            except Exception as exc:
                logger.warning("InbuiltAIDirector dialogue generation error: %s", exc)

        word_count = max(20, int(duration * _WORDS_PER_SECOND))
        prompt = textwrap.dedent(f"""
            Write an engaging spoken narration script for a {duration}-second stickman animation.
            Topic: {clean_topic}
            Visual Style: {pack.name} ({pack.short_desc})
            Target Length: approximately {word_count} words.

            Requirements:
            - Open with a curiosity hook in the very first sentence.
            - Build a clear visual contrast or story twist in the middle.
            - End with one memorable takeaway or punchline.
            - Short, natural spoken sentences for voiceover.
            - Output ONLY pure narration text. No stage notes, no JSON, no bullet lists.
        """).strip()

        try:
            if self._is_ollama_running():
                script = _clean_script_text(self.llm.generate(prompt, max_tokens=1024, temperature=0.72))
                if script and len(script.split()) >= 12:
                    return script
        except Exception as exc:
            logger.warning("generate_script LLM failed: %s", exc)

        # High-intelligence in-process fallback
        try:
            from engine.inbuilt_ai_director import InbuiltAIDirector
            return InbuiltAIDirector.generate_script(
                topic=clean_topic,
                duration=duration,
                dialogue_mode=False,
                style=style,
                seed=seed,
            )
        except Exception:
            return self._generate_offline_script(clean_topic, duration=duration, pack=pack)

    # ------------------------------------------------------------------
    # Offline Domain & Style-Tailored Script Engine
    # ------------------------------------------------------------------

    @staticmethod
    def _improve_script_offline(script: str, target_duration: int = 30, topic: str = "") -> str:
        text = _clean_script_text(script)
        # Replace clunky filler phrases with cleaner conversational flow
        replacements = [
            (r"\bIn order to\b", "To"),
            (r"\bAs a matter of fact,?\s*", ""),
            (r"\bDue to the fact that\b", "Because"),
            (r"\bBasically,?\s*", ""),
            (r"\bAt the end of the day,?\s*", "Ultimately, "),
        ]
        for pat, rep in replacements:
            text = re.sub(pat, rep, text, flags=re.IGNORECASE)

        sentences = _split_into_sentences(text)
        polished: list[str] = []
        for s in sentences:
            words = s.split()
            # Split long breathless sentences at natural pivot conjunctions
            if len(words) > 18:
                parts = re.split(r",\s+(?=(?:but|yet|however|so|because|while|instead)\b)", s, flags=re.IGNORECASE)
                if len(parts) > 1:
                    for idx, p in enumerate(parts):
                        p = p.strip().rstrip(",")
                        if not p:
                            continue
                        p = p[0].upper() + p[1:]
                        if p[-1] not in ".!?":
                            p += "."
                        polished.append(p)
                    continue
            s = s.strip()
            if s:
                s = s[0].upper() + s[1:]
                if s[-1] not in ".!?":
                    s += "."
                polished.append(s)

        joined = " ".join(polished)
        # If noticeably over target duration, tighten cleanly to budget
        max_w = int(target_duration * _WORDS_PER_SECOND * 1.15)
        if len(joined.split()) > max_w and len(polished) > 3:
            kept = [polished[0]]
            rem_budget = max_w - len(polished[0].split()) - len(polished[-1].split())
            for mid in polished[1:-1]:
                mw = len(mid.split())
                if mw <= rem_budget:
                    kept.append(mid)
                    rem_budget -= mw
            kept.append(polished[-1])
            return " ".join(kept)
        return joined

    @staticmethod
    def _generate_offline_script(topic: str, duration: int, pack: StylePack) -> str:
        raw_t = topic.strip() or "human behavior"
        low = raw_t.lower()

        # Intelligently separate "Title: Question/Subtitle" so grammar stays 100% natural!
        if ":" in raw_t:
            head_part, tail_part = [p.strip() for p in raw_t.split(":", 1)]
            short_subject = head_part.rstrip(".!?") or raw_t.rstrip(".!?")
            hook_line = tail_part if len(tail_part.split()) >= 4 else raw_t
        else:
            short_subject = raw_t.rstrip(".!?")
            if len(short_subject.split()) > 6:
                short_subject = "this idea"
            hook_line = raw_t

        is_question = "?" in raw_t or any(low.startswith(q) for q in ("if ", "why ", "what ", "how ", "would ", "could ", "should "))
        t_clean = short_subject

        if any(k in low for k in ("invisible", "nobody could see", "judge you", "unseen", "honest", "integrity", "character", "shadow", "behave differently")):
            opening = hook_line if is_question else f"Think about {t_clean}: if nobody could ever watch or judge you, who would you really be?"
            if not opening.endswith(("?", ".", "!")):
                opening += "?"
            beats = [
                opening,
                "In public, every smile, promise, and kind choice runs under invisible strings of expectation.",
                "We act polite when a camera, boss, or crowd watches closely from across the room.",
                "Yet imagine waking up tomorrow completely unseen, with zero consequences hanging over your name.",
                "At first, temptation whispers that rules only exist to cage your freedom.",
                "Look closer at that quiet mirror, and you realize character is forged precisely when nobody applauds.",
                "Every small honest choice in the dark rewires who you become out in the daylight.",
                "Before deciding today, ask what choice you would respect most even if no one ever knew.",
            ]
        elif pack.id == "a3_prehistoric_cave" or any(k in low for k in ("cave", "stone age", "tribe", "ancestor", "instinct")):
            opening = hook_line if is_question else f"Thousands of years ago, surviving {t_clean} meant one mistake could cost your tribe everything."
            beats = [
                opening,
                "Picture sitting by a roaring cave fire while everyone argues over what worked yesterday.",
                "Fear keeps the whole clan huddled in the shadows instead of exploring past the ridge.",
                "Then one restless hunter grabs a flint spear and tests a path nobody dared walk.",
                "The hidden surprise is our modern brains still run on that exact ancient survival wiring.",
                "Whenever a deadline or crowd panics you today, notice the nervous caveman inside your head.",
                "Slow down, question that ancient alarm, and choose your next step with calm courage.",
                "Master the instinct meant for survival, and you unlock freedom in modern life.",
            ]
        elif pack.id == "b4_survival_thriller" or any(k in low for k in ("survive", "survival", "danger", "emergency", "seconds")):
            opening = hook_line if is_question else f"Picture being trapped in {t_clean} with only sixty seconds left on the clock."
            beats = [
                opening,
                "In the first ten seconds, blind panic tricks most people into freezing or running toward noise.",
                "Look closely at the warning signs most people miss until every exit feels locked.",
                "Instead of fighting the storm head-on, the smartest move is slowing your breath and scanning clearly.",
                "Focus on one immediate checkpoint instead of worrying about what waits ten steps ahead.",
                "One calm choice turns a hopeless countdown into steady survival.",
                "Ask yourself right now: if that warning alarm sounded tonight, would panic or clarity win?",
            ]
        elif any(k in low for k in ("procrastinat", "delay", "lazy", "comfort zone", "tomorrow", "snooze", "later", "slump")):
            opening = hook_line if is_question else f"Why is {t_clean} the most dangerous trap you face every day?"
            beats = [
                opening,
                "The comfort zone feels warm and safe, whispering that you can always start tomorrow.",
                "When your alarm rings, you hit snooze, stay in bed, and trade your future for five more minutes.",
                "At work, you stare at screens and feel quiet guilt watching hours slip through your fingers.",
                "The truth is motivation never arrives first: momentum only comes after you take the first uncomfortable step.",
                "Break your biggest goal down to a single tiny action you can finish in sixty seconds.",
                "Step past the fear today, take that one small action, and watch momentum carry you forward.",
            ]
        elif any(k in low for k in ("fitness", "workout", "gym", "exercise", "health", "muscle", "train", "body", "pushup", "run")):
            opening = hook_line if is_question else f"What does real {t_clean} actually require to succeed?"
            beats = [
                opening,
                "Most people buy running shoes, sign up for a gym, and swear this time will be different.",
                "Yet the first cold morning they feel sore or tired, motivation vanishes into thin air.",
                "They blame lack of willpower, not realizing that relying on feelings is a losing game.",
                "Real transformation begins the day you commit to small, non-negotiable daily standards.",
                "Even just five pushups every single day rewires your self-image into someone who never quits.",
                "Honor that promise today, stack one more brick, and celebrate the person you are becoming.",
            ]
        elif any(k in low for k in ("compound", "compounding", "habit", "habits", "discipline", "consistency", "routine", "exponential")):
            opening = hook_line if is_question else f"How does the quiet math of {t_clean} transform an ordinary life?"
            beats = [
                opening,
                "On day one, choosing discipline looks completely invisible to the outside world.",
                "You read ten pages, invest fifty dollars, or choose a healthy meal, and nothing seems to change.",
                "Months pass, and the quiet curve of exponential compounding begins its magic.",
                "Tiny daily habits multiply like dominoes, creating results that look like an overnight miracle to strangers.",
                "You realize mastery was never about grand dramatic leaps, but relentless daily consistency.",
                "Place your next brick today with quiet patience, and let compounding do the rest.",
            ]
        elif any(k in low for k in ("money", "wealth", "rich", "finance", "invest", "saving", "beggar", "spend", "generosity", "charity")):
            opening = hook_line if is_question else f"Why do smart people still get trapped by {t_clean}?"
            beats = [
                opening,
                "On the surface, money looks like a simple exchange of paper bills and numbers.",
                "Yet hidden ego and unseen strings quietly dictate how we judge other people's choices.",
                "When we try to control every coin after giving it away, generosity turns into a cage.",
                "Look instead at what actually builds trust, dignity, and steady compounding over years.",
                "Real wealth begins the moment your habits buy peace of mind rather than status.",
                "Measure what truly frees your time today, and watch small deliberate choices compound.",
            ]
        elif any(k in low for k in ("ai", "tech", "software", "app", "phone", "scroll", "algorithm", "future", "youtube", "channel")):
            opening = hook_line if is_question else f"Have you noticed how {t_clean} quietly reshapes every waking hour?"
            beats = [
                opening,
                "At first, every glowing screen and smart notification promises effortless speed and progress.",
                "Before long, endless feeds hijack your focus before your morning coffee even cools.",
                "The real edge never belongs to whoever taps fastest, but whoever thinks clearest.",
                "Step back from the noise, simplify your tools, and protect deep uninterrupted attention.",
                "Use technology to create something lasting instead of feeding an infinite scroll.",
                "Start with one focused block today, and watch your sharpest ideas come back alive.",
            ]
        elif pack.id == "a4_cozy_storytelling" or any(k in low for k in ("kindness", "friend", "life", "peace", "sleep", "slow", "happy", "love", "coffee")):
            opening = hook_line if is_question else f"Sometimes the truest lesson about {t_clean} arrives in a quiet ordinary moment."
            beats = [
                opening,
                "You rush down busy streets from station to station waiting for perfection before you allow rest.",
                "Your mind keeps writing endless to-do lists while warm mornings slip past unnoticed.",
                "Yet when you finally sit at a sunlit corner cafe with a warm cup, everything slows down.",
                "You see how tightly you were gripping outcomes that never belonged to you in the first place.",
                "True kindness and inner peace do not ask for grand speeches or heavy perfection.",
                "Be present with the moment in front of you today, breathe deeper, and notice how light life feels.",
            ]
        elif pack.id == "a5_historical_cartoon" or any(k in low for k in ("history", "empire", "king", "ancient", "rome", "century", "samurai", "castle", "warrior")):
            opening = hook_line if is_question else f"Centuries ago beneath towering castle walls, rulers thought {t_clean} could be solved by decree alone."
            beats = [
                opening,
                "Long scrolls traveled across kingdoms while proud warriors guarded gates of stone and timber.",
                "On the surface, crowns and banners seemed to decide who held real power.",
                "Yet behind every grand edict stood ordinary humans wrestling the same pride and fear we feel now.",
                "Great clans rose when leaders listened humbly, and fell the hour ego silenced truth.",
                "History changes armor, castles, and titles, yet human nature rarely alters one rule.",
                "Remember what stood the test of centuries today, and apply quiet discipline to your own path.",
            ]
        else:
            opening = hook_line if is_question else f"What really happens beneath the surface with {t_clean}?"
            if not opening.endswith(("?", ".", "!")):
                opening += "?"
            beats = [
                opening,
                "At first glance, most people accept the loudest easy answer on the surface and keep walking.",
                "Look one layer deeper, and hidden habits quietly pull invisible strings behind every decision.",
                "Conflict starts when automatic fear reacts faster than calm curiosity.",
                "The turning point arrives the moment you pause and question your own first impulse.",
                "Small deliberate shifts repeated daily beat dramatic bursts of willpower every single time.",
                "Put one clear habit into practice today, and watch how quickly clarity follows.",
            ]

        target_words = max(20, int(duration * _WORDS_PER_SECOND))
        selected: list[str] = []
        used_w = 0
        for b in beats:
            bw = len(b.split())
            if not selected or (used_w + bw <= target_words * 1.15):
                selected.append(b)
                used_w += bw
        if len(selected) >= 3 and selected[-1] != beats[-1] and used_w < target_words:
            selected.append(beats[-1])
        return " ".join(selected)

    # ------------------------------------------------------------------
    # Prompt building & LLM response validation
    # ------------------------------------------------------------------

    def _build_planning_prompt(
        self,
        script: str,
        topic: str,
        duration: int,
        pack: StylePack,
        format: str,
    ) -> str:
        scene_count = self._estimate_scene_count(script, duration, pack.pacing_multiplier)
        example_scene_single = json_compact({
            "id": 1,
            "duration": 4.5,
            "narration": "Welcome to our story.",
            "action": "WAVE",
            "background": pack.default_background,
            "characters": ["PERSON_A"],
            "objects": ["LIGHTBULB"],
            "effects": ["WARM"],
            "transition": pack.preferred_transition,
            "camera": pack.preferred_camera,
            "emotion": "HAPPY",
            "caption_style": "normal",
        })
        example_scene_multi = json_compact({
            "id": 2,
            "duration": 4.5,
            "narration": "When you try to explain it, people often disagree.",
            "action": "ARGUE",
            "background": "CITY",
            "characters": ["PERSON_A", "PERSON_B"],
            "objects": ["EXCLAMATION"],
            "effects": ["EMPHASIS"],
            "transition": "SLIDE_LEFT",
            "camera": "MEDIUM",
            "emotion": "ANGRY",
            "caption_style": "normal",
        })

        valid_opts = textwrap.dedent(f"""
            Valid VALUES (use only these):
            action     : {', '.join(sorted(_VALID_ACTIONS))}
            background : {', '.join(sorted(_VALID_BACKGROUNDS))}
            characters : (array) {', '.join(sorted(_VALID_CHARACTERS))}
            objects    : (array) {', '.join(sorted(_VALID_OBJECTS))}
            effects    : (array) {', '.join(sorted(_VALID_EFFECTS))}
            transition : {', '.join(sorted(_VALID_TRANSITIONS))}
            camera     : {', '.join(sorted(_VALID_CAMERAS))}
            emotion    : {', '.join(sorted(_VALID_EMOTIONS))}
        """).strip()

        return textwrap.dedent(f"""
            You are an animation director working in style "{pack.name}" ({pack.short_desc}).
            Break the script below into {scene_count} visually distinct scenes for a {duration}-second
            {format} video about "{topic}".
            
            Key Directing Rules:
            - Never repeat the exact same background or camera angle back-to-back.
            - MULTI-CHARACTER STAGING: For dialogues, debates, contrasts ("they vs you", "some people"),
              transactions, advice, or comparisons, feature TWO characters: ["PERSON_A", "PERSON_B"].
              Avoid keeping the entire video single-character.
            - Prefer style-authentic backgrounds ({', '.join(pack.preferred_backgrounds)}) when appropriate.

            {valid_opts}

            Output ONLY a valid JSON array matching these schemas:
            [{example_scene_single}, {example_scene_multi}]

            SCRIPT:
            {script}

            JSON OUTPUT:
        """).strip()

    def _validate_scene(self, scene: dict, pack: StylePack) -> dict:
        result: dict[str, Any] = {}
        result["id"] = int(scene.get("id", 0))
        try:
            dur = float(scene.get("duration", 4.5))
        except (TypeError, ValueError):
            dur = 4.5
        result["duration"] = dur if dur > 0 else 4.5
        result["narration"] = str(scene.get("narration", "")).strip()

        act = str(scene.get("action", "STAND")).upper()
        result["action"] = act if act in _VALID_ACTIONS else "STAND"

        bg = str(scene.get("background", pack.default_background)).upper()
        result["background"] = bg if bg in _VALID_BACKGROUNDS else pack.default_background

        for field, valid_set, default in (
            ("characters", _VALID_CHARACTERS, ["PERSON_A"]),
            ("objects", _VALID_OBJECTS, []),
            ("effects", _VALID_EFFECTS, []),
        ):
            raw = scene.get(field, default)
            if isinstance(raw, list):
                result[field] = [v.upper() for v in raw if isinstance(v, str) and v.upper() in valid_set] or list(default)
            else:
                result[field] = list(default)

        # Intelligent multi-character enrichment:
        # If characters has only PERSON_A, check if action or narration indicates a 2-party interaction
        if result["characters"] == ["PERSON_A"]:
            act_u = result["action"]
            narr_l = result["narration"].lower()
            if act_u in ("ARGUE", "GIVE", "RECEIVE", "SHOUT", "FIGHT") or any(
                w in narr_l for w in ("they", "them", "other", "people", "someone", "ask", "tell", "say", "versus", "vs", "instead", "friend", "boss", "mentor", "debate", "warn")
            ):
                result["characters"] = ["PERSON_A", "PERSON_B"]

        trans = str(scene.get("transition", pack.preferred_transition)).upper()
        result["transition"] = trans if trans in _VALID_TRANSITIONS else pack.preferred_transition
        cam = str(scene.get("camera", pack.preferred_camera)).upper()
        result["camera"] = cam if cam in _VALID_CAMERAS else pack.preferred_camera
        emo = str(scene.get("emotion", "NEUTRAL")).upper()
        result["emotion"] = emo if emo in _VALID_EMOTIONS else "NEUTRAL"
        result["caption_style"] = str(scene.get("caption_style", "normal")).lower()
        return result

    def _assign_ids_and_durations(self, scenes: list[dict], total_duration: int) -> list[dict]:
        if not scenes:
            return scenes
        raw_total = sum(s["duration"] for s in scenes)
        scale = total_duration / raw_total if raw_total > 0 else 1.0
        for i, scene in enumerate(scenes, start=1):
            scene["id"] = i
            scene["duration"] = round(max(1.2, scene["duration"] * scale), 2)
        actual_sum = sum(s["duration"] for s in scenes)
        scenes[-1]["duration"] = round(max(1.2, scenes[-1]["duration"] + (total_duration - actual_sum)), 2)
        return scenes

    # ------------------------------------------------------------------
    # Intelligent Semantic Storyboard Planner (Offline & Anti-Repetition)
    # ------------------------------------------------------------------

    def _create_fallback_scenes(
        self,
        script: str,
        duration: int,
        topic: str = "",
        style_id: str = "a1_classic_bw",
    ) -> list[dict]:
        pack, _sp = resolve_style_pack(style_id)
        beats = _split_into_visual_beats(script)
        if not beats:
            beats = [script.strip() or "Scene"]

        scene_count = max(1, min(len(beats), self._estimate_scene_count(script, duration, pack.pacing_multiplier)))
        buckets = _distribute(beats, scene_count)

        # Weight scene duration naturally by spoken word count per beat
        bucket_words = [max(3, sum(len(x.split()) for x in b)) for b in buckets]
        total_w = sum(bucket_words) or 1

        engine = ProceduralSceneEngine(style_id=pack.id)
        scenes: list[dict] = []

        for i, bucket in enumerate(buckets):
            narration = " ".join(bucket).strip()
            est_dur = round(max(1.5, duration * (bucket_words[i] / total_w)), 2)
            sc = engine.generate_scene_for_narration(
                narration=narration,
                scene_idx=i,
                total_scenes=len(buckets),
                target_duration=est_dur,
            )
            scenes.append(normalize_scene_for_composer(sc, style_id=pack.id))

        total_assigned = sum(s["duration"] for s in scenes)
        scenes[-1]["duration"] = round(max(1.2, scenes[-1]["duration"] + (duration - total_assigned)), 2)
        return scenes

    def _diversify_scenes(self, scenes: list[dict], pack: StylePack | None = None) -> list[dict]:
        cameras = ["ZOOM_IN", "MEDIUM", "CLOSE", "PAN_RIGHT", "WIDE", "PAN_LEFT"]
        bgs = list(pack.preferred_backgrounds) if pack and pack.preferred_backgrounds else [
            "STAGE", "STREET", "ABSTRACT", "HOME", "OFFICE", "PARK", "CITY", "CLASSROOM"
        ]
        for i in range(1, len(scenes)):
            if scenes[i].get("background") == scenes[i - 1].get("background") and len(bgs) > 1:
                cur = scenes[i].get("background")
                idx = (bgs.index(cur) + 1) % len(bgs) if cur in bgs else i % len(bgs)
                scenes[i]["background"] = bgs[idx]
            if scenes[i].get("camera") == scenes[i - 1].get("camera"):
                scenes[i]["camera"] = cameras[i % len(cameras)]
        return scenes

    def _estimate_scene_count(self, script: str, duration: int, pacing_mult: float = 1.0) -> int:
        beat_sec = 4.2 * max(0.75, min(1.35, pacing_mult))
        word_count = len(script.split())
        by_duration = max(1, round(duration / beat_sec))
        by_words = max(1, math.ceil(word_count / (_WORDS_PER_SECOND * beat_sec)))
        return max(1, min(by_duration, by_words, 24))


def json_compact(obj: Any) -> str:
    return json.dumps(obj, separators=(",", ":"))


def _split_into_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    result: list[str] = []
    for part in parts:
        sub = [s.strip() for s in part.split("\n") if s.strip()]
        result.extend(sub)
    return [s for s in result if s]


def _split_into_visual_beats(text: str) -> list[str]:
    """Split long sentences at dramatic pivots so every turn gets its own animation."""
    sentences = _split_into_sentences(text)
    beats: list[str] = []
    for s in sentences:
        if len(s.split()) > 12:
            sub = re.split(
                r"(?:;\s+|,\s+(?=(?:yet|but|however|meanwhile|instead|while|because|until|and then)\b))",
                s,
                flags=re.IGNORECASE,
            )
            cleaned = [p.strip() for p in sub if len(p.strip().split()) >= 3]
            if len(cleaned) > 1:
                beats.extend(cleaned)
                continue
        beats.append(s)
    return beats


def _distribute(items: list[str], buckets: int) -> list[list[str]]:
    if not items:
        return [[""] for _ in range(buckets)]
    buckets = min(buckets, len(items))
    result: list[list[str]] = []
    size = len(items) / buckets
    for i in range(buckets):
        start = round(i * size)
        end = round((i + 1) * size)
        chunk = items[start:end]
        result.append(chunk if chunk else [""])
    return result
