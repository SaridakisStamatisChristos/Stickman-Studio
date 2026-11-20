# Created by Atharv Hatwar
"""
script_intelligence.py - Intelligent Script Interpretation & Semantic Story Planner.
=====================================================================================
Understands the complete narrative context, story progression, and dialogue structure:
  1. Distinguishes spoken dialogue from all metadata, scene headings, timestamps,
     speaker labels, production notes, camera cues, and emotion brackets.
  2. Never sends non-dialogue labels to TTS or captions.
  3. Decomposes turns into visual narrative beats with semantic continuity.
  4. Plans accurate character actions (texting, looking at phone, smile fading,
     unanswered calls, turning away, hugging, crying, arguing, thinking, etc.).
  5. Enforces character consistency (Male stickman vs Female stickman with ponytail/lashes).
  6. Maintains narrative continuity (locations, lighting, character presence don't jump randomly).
  7. 100% Free, Local, Offline, optimized for Ryzen 5 / GTX 1650 / 8GB RAM (Zero Ollama required).
"""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class ScriptIntelligenceEngine:
    """Intelligently interprets scripts, extracts clean spoken dialogue, and plans story-aligned visuals."""

    @classmethod
    def parse_script_to_story_beats(
        cls,
        raw_script: str,
        name1: str = "Alex",
        name2: str = "Maya",
    ) -> list[dict[str, Any]]:
        """
        Parses raw user script into structured story beats with 100% clean spoken narration.
        Strips scene headings, timestamps, speaker prefixes, visual instructions, and metadata.
        """
        n1 = (name1 or "Alex").strip().title()
        n2 = (name2 or "Maya").strip().title()

        lines = raw_script.splitlines()
        raw_turns: list[dict[str, Any]] = []

        current_speaker = 1
        current_speaker_name = n1
        current_emotion = "NEUTRAL"
        current_visual_hint = ""
        current_buffer: list[str] = []

        # Regex patterns for stripping non-spoken metadata
        meta_line_pattern = re.compile(
            r"^\s*(?:#+\s*|\*\*)?(?:duration|genre|voices|target|resolution|fps|aspect|format|end\s*screen|final\s*screen)\s*[:\-–—].*$",
            re.IGNORECASE,
        )
        scene_heading_pattern = re.compile(
            r"^\s*(?:#+\s*|\*\*)?(?:scene\s*\d+|act\s*\d+|hook|story|psychology|dark\s*realisation|twist|punchline).*$",
            re.IGNORECASE,
        )
        end_card_pattern = re.compile(
            r"^\s*(?:['\"]?read\s*that\s*again.*?['\"]?|###\s*end\s*screen|end\s*screen).*$",
            re.IGNORECASE,
        )

        speaker_header_pattern = re.compile(
            rf"^\s*(?:\*\*)?(?:\[)?(?:"
            rf"male\s*voice|female\s*voice|male|female|"
            rf"speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|"
            rf"{re.escape(n1)}|{re.escape(n2)}|"
            rf"final\s*line\s*[-–—]\s*(?:female|male)\s*voice|"
            rf"narrator|host"
            rf")(?:\s*\([^)]*\))?(?:\])?(?:\*\*)?\s*[:\-–—]?\s*$",
            re.IGNORECASE,
        )

        inline_speaker_pattern = re.compile(
            rf"^\s*(?:\*\*)?(?:\[)?(?:"
            rf"male\s*voice|female\s*voice|male|female|"
            rf"speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|"
            rf"{re.escape(n1)}|{re.escape(n2)}|"
            rf"final\s*line\s*[-–—]\s*(?:female|male)\s*voice|"
            rf"narrator|host"
            rf")(?:\s*\([^)]*\))?(?:\])?(?:\*\*)?\s*[:\-–—]\s*(.+)$",
            re.IGNORECASE,
        )

        has_explicit_speakers = False

        def flush_turn():
            nonlocal current_buffer, current_emotion, current_visual_hint
            text = " ".join(current_buffer).strip()
            current_buffer = []
            if not text:
                return

            # Clean all remaining brackets, timestamps, and stage directions
            clean_text, extracted_hints, extracted_emo = cls._clean_narration_line(text)
            if not clean_text:
                return

            eff_emo = extracted_emo or current_emotion
            eff_hint = extracted_hints or current_visual_hint

            raw_turns.append({
                "speaker": current_speaker,
                "speaker_name": current_speaker_name,
                "raw_text": clean_text,
                "emotion": eff_emo,
                "visual_hint": eff_hint,
            })
            current_emotion = "NEUTRAL"
            current_visual_hint = ""

        for line in lines:
            line_str = line.strip()
            if not line_str:
                continue

            # Skip document titles (# Title), document metadata, scene headings, and end cards
            if line_str.startswith("#"):
                continue
            if meta_line_pattern.match(line_str) or end_card_pattern.match(line_str):
                continue
            if scene_heading_pattern.match(line_str) and not any(k in line_str.lower() for k in (f"{n1.lower()}:", f"{n2.lower()}:", "voice:")):
                continue

            # Check for explicit visual cue brackets: [Visual: Character looking at phone]
            vis_match = re.search(r"\[(?:visual|animation|camera|scene)\s*[:\-–—]\s*([^\]]+)\]", line_str, re.IGNORECASE)
            if vis_match:
                current_visual_hint = vis_match.group(1).strip()
                line_str = re.sub(r"\[(?:visual|animation|camera|scene)\s*[:\-–—]\s*[^\]]+\]", "", line_str, flags=re.IGNORECASE).strip()
                if not line_str:
                    continue

            # Check for standalone speaker header: **MALE VOICE:**
            if speaker_header_pattern.match(line_str):
                flush_turn()
                has_explicit_speakers = True
                low_h = line_str.lower()
                if any(k in low_h for k in ("female", n2.lower(), "speaker 2", "voice 2")):
                    current_speaker = 2
                    current_speaker_name = n2
                else:
                    current_speaker = 1
                    current_speaker_name = n1

                # Check for emotion in header: (SLOW AND EMOTIONAL) or [MALE, EMOTIONAL]
                emo_m = re.search(r"\(([^)]+)\)|\[([^\]]+)\]", line_str)
                if emo_m:
                    emo_text = (emo_m.group(1) or emo_m.group(2) or "").upper()
                    if any(e in emo_text for e in ("EMOTIONAL", "SAD", "SLOW")):
                        current_emotion = "SAD"
                    elif any(e in emo_text for e in ("ANGRY", "SHOUT")):
                        current_emotion = "ANGRY"
                    elif any(e in emo_text for e in ("CONFUSED", "DOUBT")):
                        current_emotion = "CONFUSED"
                continue

            # Check for inline speaker tag: **MALE VOICE:** Dialogue here
            inline_m = inline_speaker_pattern.match(line_str)
            if inline_m:
                flush_turn()
                has_explicit_speakers = True
                low_tag = line_str[:inline_m.start(1)].lower()
                if any(k in low_tag for k in ("female", n2.lower(), "speaker 2", "voice 2")):
                    current_speaker = 2
                    current_speaker_name = n2
                else:
                    current_speaker = 1
                    current_speaker_name = n1

                rem_text = inline_m.group(1).strip()
                if rem_text:
                    current_buffer.append(rem_text)
                continue

            # Normal dialogue sentence line
            current_buffer.append(line_str)

        flush_turn()

        # If no explicit speaker tags were found, treat as solo narrator script and segment by sentence
        if not has_explicit_speakers:
            raw_turns = []
            full_clean, hints, emo = cls._clean_narration_line(raw_script)
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_clean) if len(s.strip().split()) >= 2]
            for s in sentences:
                raw_turns.append({
                    "speaker": 1,
                    "speaker_name": n1,
                    "raw_text": s,
                    "emotion": emo or "NEUTRAL",
                    "visual_hint": hints or "",
                })

        # ------------------------------------------------------------------
        # Dramatic Beat Segmentation: Split turns at narrative pivots!
        # e.g., "One day, they're texting... But suddenly, they become distant."
        # ------------------------------------------------------------------
        beats: list[dict[str, Any]] = []
        for turn in raw_turns:
            turn_text = turn["raw_text"]
            spk = turn["speaker"]
            spk_name = turn["speaker_name"]
            emo = turn["emotion"]
            hint = turn["visual_hint"]

            sub_beats = cls._split_into_dramatic_beats(turn_text)
            for s_idx, beat_text in enumerate(sub_beats):
                beats.append({
                    "beat_id": len(beats) + 1,
                    "speaker": spk,
                    "speaker_name": spk_name,
                    "narration": beat_text,
                    "emotion": emo,
                    "visual_hint": hint if s_idx == 0 else "",
                })

        return beats

    @classmethod
    def _clean_narration_line(cls, text: str) -> tuple[str, str, str]:
        """Completely strips non-dialogue metadata, stage directions, and timestamps."""
        t = text.strip()
        hints = ""
        emotion = ""

        # Extract visual hints in brackets [Visual: ...]
        vis_m = re.findall(r"\[(?:visual|animation|camera|scene)\s*[:\-–—]\s*([^\]]+)\]", t, re.IGNORECASE)
        if vis_m:
            hints = " ".join(vis_m).strip()
            t = re.sub(r"\[(?:visual|animation|camera|scene)\s*[:\-–—]\s*[^\]]+\]", "", t, flags=re.IGNORECASE)

        # Extract emotion tags [MALE, EMOTIONAL] or (SLOW AND EMOTIONAL)
        emo_m = re.findall(r"(?:\[|\()([A-Z\s,]{4,})(?:\]|\))", t)
        for em in emo_m:
            em_up = em.upper()
            if any(k in em_up for k in ("EMOTIONAL", "SAD", "SLOW", "HEARTBROKEN")):
                emotion = "SAD"
            elif any(k in em_up for k in ("ANGRY", "SHOUT", "UPSET")):
                emotion = "ANGRY"
            elif any(k in em_up for k in ("CONFUSED", "DOUBT")):
                emotion = "CONFUSED"
            elif any(k in em_up for k in ("HAPPY", "JOY", "SMILE")):
                emotion = "HAPPY"

        # Remove bracketed cues [pause], [sfx: ...], (0:00–0:15)
        t = re.sub(r"\[[^\]]*\]", " ", t)
        t = re.sub(r"\((?:\d+:\d+|pause|beat|slow|sfx|music|crying|whisper)[^)]*\)", " ", t, flags=re.IGNORECASE)
        t = re.sub(r"\([A-Z\s]{4,}\)", " ", t)

        # Remove markdown symbols and quotes
        t = re.sub(r"[*_#`~]+", "", t)
        t = re.sub(r"^\s*[-*•]\s+", "", t)
        t = re.sub(r'\s+"([^"]+)"\s+', r" \1 ", t)  # Keep quote content clean
        t = re.sub(r"\s+", " ", t).strip()

        # Final defensive check against speaker name leaking into speech
        t = re.sub(
            r"^\s*(?:male\s*voice|female\s*voice|speaker\s*\d+|voice\s*\d+|male|female|alex|maya)\s*[:\-–—]\s*",
            "",
            t,
            flags=re.IGNORECASE,
        ).strip()

        return t, hints, emotion

    @classmethod
    def _split_into_dramatic_beats(cls, text: str) -> list[str]:
        """
        Splits a dialogue turn into distinct dramatic beats when the story pivots.
        Guarantees that visual events change exactly when narration meaning changes!
        """
        words = text.split()
        if len(words) <= 18:
            return [text]

        # Sentence-based segmentation for multi-sentence turns
        sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if len(sents) >= 2:
            beats = []
            curr = ""
            for s in sents:
                if not curr:
                    curr = s
                elif len((curr + " " + s).split()) <= 18:
                    curr += " " + s
                else:
                    beats.append(curr)
                    curr = s
            if curr:
                beats.append(curr)
            if len(beats) >= 2:
                return beats

        # Pivots like "But suddenly", "Then, just when", "However", "Instead"
        pivot_pattern = re.compile(
            r"(?<=[.!?])\s+(?=(?:But\s+suddenly|Then,\s+just\s+when|Suddenly|However|Instead|And\s+every\s+unexpected|Psychologists\s+call)\b)",
            re.IGNORECASE,
        )
        parts = pivot_pattern.split(text)
        if len(parts) > 1:
            return [p.strip() for p in parts if p.strip()]

        # For long single sentences (>24 words), split at natural conjunction boundaries
        if len(words) > 24:
            conj_parts = re.split(r",\s+(?=(?:but|yet|however|so|because|while|instead|and|then)\b)", text, flags=re.IGNORECASE)
            if len(conj_parts) >= 2:
                sub: list[str] = []
                for p in conj_parts:
                    p_clean = p.strip().rstrip(",")
                    if p_clean:
                        if p_clean[-1] not in ".!?":
                            p_clean += "."
                        sub.append(p_clean)
                if len(sub) >= 2:
                    return sub

        return [text]

    @classmethod
    def plan_visual_for_beat(
        cls,
        beat: dict[str, Any],
        context_history: Optional[list[dict[str, Any]]] = None,
        duration: float = 4.0,
        style_id: str = "a1_classic_bw",
        topic: str = "",
        total_beats: int = 1,
    ) -> dict[str, Any]:
        """
        Creates a structured, story-aligned visual scene description for a single dialogue beat.
        Guarantees narrative continuity, character consistency, and exact action correspondence.
        """
        history = list(context_history or [])
        last_scene = history[-1] if history else {}

        narration = beat["narration"]
        text_lower = narration.lower()
        speaker = beat.get("speaker", 1)
        speaker_name = beat.get("speaker_name", "Alex")
        user_hint = beat.get("visual_hint", "").lower()
        explicit_emo = beat.get("emotion")

        # ------------------------------------------------------------------
        # 1. Character Assignment (Male Alex vs Female Maya with Ponytail & Lashes)
        # ------------------------------------------------------------------
        # Check if Maya / Female is speaking
        is_female_speaker = (speaker == 2) or (speaker_name.lower() in ("maya", "female"))

        # Default character specs
        char_a = {
            "id": "person_a",
            "name": "Alex",
            "gender": "male",
            "color": "#38BDF8",  # Vibrant cyan
            "scale": 1.0,
            "facing": "right",
            "accessory": "none",
            "hair_style": "short",
            "outfit": "minimalist",
        }
        char_b = {
            "id": "person_b",
            "name": "Maya",
            "gender": "female",
            "color": "#F43F5E",  # Elegant rose coral
            "scale": 0.96,
            "facing": "left",
            "accessory": "ponytail",  # Signature feminine ponytail!
            "hair_style": "ponytail",
            "outfit": "feminine_silhouette",
            "has_eyelashes": True,
            "cheek_blush": True,
        }

        # ------------------------------------------------------------------
        # 2. Contextual Story Understanding & Action Mapping
        # ------------------------------------------------------------------
        action = "STAND"
        emotion = explicit_emo or "NEUTRAL"
        background = "ABSTRACT"
        camera = "MEDIUM"
        objects: list[dict[str, Any]] = []
        effects: list[str] = []
        characters: list[dict[str, Any]] = []

        # Only activate the specialized dating/texting drama scenes for unambiguous romantic-drama text.
        # shortcut: broad keywords ("texting", "dating", "romantic") removed — they appear in too many
        # non-romance scripts and caused the procedural engine to be bypassed incorrectly.
        has_dating_context = any(w in text_lower for w in (
            "unanswered calls", "mixed signals", "ex-boyfriend", "ex-girlfriend", "ghosted me",
        ))

        # Primary Universal Engine (Procedural + In-Process Neural Semantic Brain)
        if not has_dating_context:
            from engine.procedural_scene_engine import ProceduralSceneEngine
            engine = ProceduralSceneEngine(style_id=style_id)
            engine.history = list(history)
            eff_total = max(total_beats, len(history) + 1)
            proc_sc = engine.generate_scene_for_narration(
                narration=narration,
                scene_idx=len(history),
                total_scenes=eff_total,
                target_duration=round(max(duration, 1.2), 3),
                topic=topic,
            )
            proc_sc["id"] = len(history) + 1
            proc_sc["scene_id"] = len(history) + 1
            proc_sc["speaker"] = speaker
            proc_sc["speaker_name"] = speaker_name

            if is_female_speaker and proc_sc.get("characters"):
                c0 = proc_sc["characters"][0]
                c0["name"] = speaker_name or "Maya"
                c0["gender"] = "female"
                c0["hair_style"] = "ponytail"
                c0["has_eyelashes"] = True
                c0["cheek_blush"] = True

            return proc_sc

        # A. TEXTING ALL NIGHT / SMILING AT SMARTPHONE / WARM MESSAGES
        if has_dating_context and any(k in text_lower for k in ("texting you all night", "texting all night", "asking about your day", "making you feel special", "maybe they actually like me")):
            action = "TEXTING_PHONE"
            emotion = "HAPPY"
            background = "BEDROOM_NIGHT"
            camera = "MEDIUM"
            objects = [
                {"asset": "PHONE", "x": 0.58, "y": 0.46, "width": 0.16, "height": 0.22, "motion": "GLOW_WARM"},
                {"asset": "MESSAGE_BUBBLE_INCOMING", "x": 0.72, "y": 0.28, "width": 0.24, "height": 0.14},
                {"asset": "MESSAGE_BUBBLE_INCOMING", "x": 0.76, "y": 0.16, "width": 0.20, "height": 0.12},
                {"asset": "HEART", "x": 0.62, "y": 0.20, "width": 0.10, "height": 0.10, "motion": "FLOAT_UP"},
            ]
            effects = ["WARM"]
            # Male character sitting in his room at night smiling at phone
            ca = dict(char_a)
            ca["action"] = "TEXTING_PHONE"
            ca["emotion"] = "HAPPY"
            ca["speaking"] = True
            characters = [ca]

        # B. SUDDEN DISTANCE / REPLIES GET SHORTER / CALLS DISAPPEAR / "WHAT DID I DO WRONG?"
        elif any(k in text_lower for k in ("become distant", "replies get shorter", "calls disappear", "what did i do wrong", "smile disappears")):
            action = "CONFUSED_WONDERING"
            emotion = "CONFUSED"
            background = "BEDROOM_NIGHT"  # Maintain continuity from previous bedroom shot!
            camera = "CLOSE"
            objects = [
                {"asset": "PHONE", "x": 0.54, "y": 0.48, "width": 0.15, "height": 0.20},
                {"asset": "SHORT_REPLY_BUBBLE", "x": 0.70, "y": 0.32, "width": 0.18, "height": 0.10},  # Shorter "k." bubble!
                {"asset": "MISSED_CALL_ICON", "x": 0.74, "y": 0.18, "width": 0.12, "height": 0.12},   # Missed call indicator!
                {"asset": "QUESTION_MARK", "x": 0.30, "y": 0.22, "width": 0.14, "height": 0.18},
            ]
            effects = ["COOL", "VIGNETTE"]
            ca = dict(char_a)
            ca["action"] = "LOOK_PHONE"
            ca["emotion"] = "SAD"
            ca["speaking"] = True
            characters = [ca]

        # C. THE RETURN / SIMPLE "HEY I MISSED YOU" / SUDDEN REWARD
        elif any(k in text_lower for k in ("trying to forget", "they return", "hey, i missed you", "feelings come rushing back", "simple hey")):
            action = "CHECK_NOTIFICATIONS"
            emotion = "SURPRISED"
            background = "BEDROOM_NIGHT"
            camera = "PUNCH_IN"
            objects = [
                {"asset": "PHONE", "x": 0.52, "y": 0.46, "width": 0.16, "height": 0.22},
                {"asset": "NOTIFICATION_POPUP", "x": 0.50, "y": 0.18, "width": 0.32, "height": 0.14},
                {"asset": "HEART", "x": 0.76, "y": 0.26, "width": 0.14, "height": 0.14, "motion": "FLOAT_UP"},
            ]
            effects = ["WARM", "FLASH_CUT"]
            if is_female_speaker:
                cb = dict(char_b)
                cb["action"] = "POINT_RIGHT"
                cb["emotion"] = "HAPPY"
                cb["speaking"] = True
                characters = [cb]
            else:
                ca = dict(char_a)
                ca["action"] = "CHECK_NOTIFICATIONS"
                ca["emotion"] = "SURPRISED"
                ca["speaking"] = True
                characters = [ca]

        # D. HOOK: LEAST ATTENTION BECOMES PERSON YOU THINK ABOUT MOST
        elif any(k in text_lower for k in ("least attention", "think about the most", "noticed something strange")):
            action = "THINK"
            emotion = "CONFUSED"
            background = "MIND"
            camera = "MEDIUM"
            objects = [
                {"asset": "LIGHTHOUSE_FOG_BEAM", "x": 0.65, "y": 0.44, "width": 0.36, "height": 0.34},
                {"asset": "QUESTION_MARK", "x": 0.24, "y": 0.22, "width": 0.14, "height": 0.18},
            ]
            effects = ["COOL"]
            ca = dict(char_a)
            ca["action"] = "THINK"
            ca["emotion"] = "CONFUSED"
            ca["speaking"] = True
            characters = [ca]

        # D2. WHY QUESTIONS: "WHY DOES THIS HAPPEN? WHY DO WE BECOME ATTACHED?"
        elif any(k in text_lower for k in ("why does this happen", "why do we become", "consistent attention", "am i actually falling in love")):
            action = "THINK"
            emotion = "CONFUSED"
            background = "MIND"
            camera = "MEDIUM"
            objects = [
                {"asset": "BRAIN", "x": 0.68, "y": 0.26, "width": 0.18, "height": 0.18},
                {"asset": "QUESTION_MARK", "x": 0.24, "y": 0.22, "width": 0.14, "height": 0.18},
                {"asset": "HEART", "x": 0.50, "y": 0.44, "width": 0.12, "height": 0.12},
            ]
            effects = ["COOL"]
            ca = dict(char_a)
            ca["action"] = "THINK"
            ca["emotion"] = "CONFUSED"
            ca["speaking"] = True
            characters = [ca]

        # E. FEMALE EXPLANATION: WORST PART, YOU KNOW THEY'RE CONFUSING YOU
        elif any(k in text_lower for k in ("worst part", "confusing you", "happy again")):
            action = "POINT_RIGHT"
            emotion = "CALM"
            background = "MIND"
            camera = "MEDIUM"
            objects = [
                {"asset": "BALANCE_SCALE", "x": 0.68, "y": 0.46, "width": 0.24, "height": 0.22},
                {"asset": "HEART", "x": 0.72, "y": 0.22, "width": 0.12, "height": 0.12},
            ]
            cb = dict(char_b)
            cb["action"] = "POINT_RIGHT"
            cb["emotion"] = "CALM"
            cb["speaking"] = True
            characters = [cb]

        # F. INTERMITTENT REINFORCEMENT / BRAIN CHASING UNCERTAINTY / DOPAMINE REWARD
        elif any(k in text_lower for k in ("intermittent reinforcement", "chasing the uncertainty", "unpredictably", "feels like a reward", "unexpected message")):
            action = "PRESENT_CHART"
            emotion = "CONFIDENT"
            background = "MIND"
            camera = "ZOOM_IN"
            objects = [
                {"asset": "DOPAMINE_SPIKE_CHART", "x": 0.60, "y": 0.40, "width": 0.36, "height": 0.28},
                {"asset": "BRAIN", "x": 0.22, "y": 0.24, "width": 0.16, "height": 0.16},
                {"asset": "STAR", "x": 0.82, "y": 0.20, "width": 0.12, "height": 0.12},
            ]
            effects = ["WARM"]
            if is_female_speaker:
                cb = dict(char_b)
                cb["action"] = "PRESENT_CHART"
                cb["emotion"] = "CONFIDENT"
                cb["speaking"] = True
                characters = [cb]
            else:
                ca = dict(char_a)
                ca["action"] = "PRESENT_CHART"
                ca["emotion"] = "CONFIDENT"
                ca["speaking"] = True
                characters = [ca]

        # G. ATTACHED TO THE FEELING / REMEMBERING BEAUTIFUL MOMENTS / FANTASY VS REALITY
        elif any(k in text_lower for k in ("attached to the feeling", "beautiful moments", "painful ones", "if only they changed", "version of them")):
            action = "THINK"
            emotion = "SAD"
            background = "ABSTRACT"
            camera = "MEDIUM"
            objects = [
                {"asset": "SPLIT_MIRROR_IDEAL", "x": 0.54, "y": 0.42, "width": 0.36, "height": 0.34},
                {"asset": "THOUGHT_CLOUD", "x": 0.68, "y": 0.22, "width": 0.26, "height": 0.20},
            ]
            effects = ["COOL", "VIGNETTE"]
            if is_female_speaker:
                cb = dict(char_b)
                cb["action"] = "POINT_RIGHT"
                cb["emotion"] = "CALM"
                cb["speaking"] = True
                characters = [cb]
            else:
                ca = dict(char_a)
                ca["action"] = "THINK"
                ca["emotion"] = "CONFUSED"
                ca["speaking"] = True
                characters = [ca]

        # H. QUESTION YOUR WORTH / PEDESTAL OF HOPE
        elif any(k in text_lower for k in ("question your worth", "pedestal", "waiting for the person", "special at the beginning")):
            action = "DISMISSIVE_WAVE"
            emotion = "SAD"
            background = "ABSTRACT"
            camera = "MEDIUM"
            objects = [
                {"asset": "PEDESTAL_BUST_TRAP", "x": 0.64, "y": 0.46, "width": 0.30, "height": 0.32},
                {"asset": "BROKEN_CROWN", "x": 0.72, "y": 0.24, "width": 0.14, "height": 0.14},
            ]
            effects = ["COOL"]
            if is_female_speaker:
                cb = dict(char_b)
                cb["action"] = "DISMISSIVE_WAVE"
                cb["emotion"] = "SAD"
                cb["speaking"] = True
                characters = [cb]
            else:
                ca = dict(char_a)
                ca["action"] = "HEADACHE_STRESS"
                ca["emotion"] = "SAD"
                ca["speaking"] = True
                characters = [ca]

        # I. REAL LOVE / SECURE IN THEIR PRESENCE / MUTUAL EFFORT
        elif any(k in text_lower for k in ("real love", "secure in their presence", "addicted to someone's attention", "protect your peace")):
            action = "HUG"
            emotion = "CALM"
            background = "HOME"
            camera = "MEDIUM"
            objects = [
                {"asset": "SHIELD", "x": 0.50, "y": 0.44, "width": 0.34, "height": 0.34, "motion": "PULSE_SLOW"},
                {"asset": "HEART", "x": 0.50, "y": 0.20, "width": 0.14, "height": 0.14},
            ]
            effects = ["WARM"]
            # Dual interaction scene: Alex and Maya standing together in safety
            ca = dict(char_a)
            ca["facing"] = "right"
            ca["emotion"] = "CALM"
            cb = dict(char_b)
            cb["facing"] = "left"
            cb["emotion"] = "CALM"
            if is_female_speaker:
                cb["speaking"] = True
                ca["speaking"] = False
            else:
                ca["speaking"] = True
                cb["speaking"] = False
            characters = [ca, cb]

        # J. FINAL CLIMAX: ADDICTED TO HOPE THAT ONE DAY THEY WILL LOVE YOU
        elif has_dating_context and any(k in text_lower for k in ("addicted to the hope", "love you the way you deserve")):
            action = "POINT_UP"
            emotion = "CALM"
            background = "STAGE"
            camera = "SLOW_ZOOM_IN"
            objects = [
                {"asset": "HEART", "x": 0.50, "y": 0.32, "width": 0.20, "height": 0.20, "motion": "PULSE_SLOW"},
                {"asset": "STAR", "x": 0.28, "y": 0.22, "width": 0.12, "height": 0.12},
                {"asset": "STAR", "x": 0.72, "y": 0.22, "width": 0.12, "height": 0.12},
            ]
            effects = ["WARM"]
            cb = dict(char_b)
            cb["action"] = "POINT_UP"
            cb["emotion"] = "CALM"
            cb["speaking"] = True
            characters = [cb]

        # K. GENERAL / UNIVERSAL TOPIC MASTER ENGINE (Procedural + Neural Semantic Brain)
        else:
            from engine.procedural_scene_engine import ProceduralSceneEngine
            engine = ProceduralSceneEngine(style_id=style_id)
            engine.history = list(history)
            proc_sc = engine.generate_scene_for_narration(
                narration=narration,
                scene_idx=len(history),
                total_scenes=max(total_beats, len(history) + 1),
                target_duration=round(max(duration, 1.2), 3),
                topic=topic,
            )
            proc_sc["id"] = len(history) + 1
            proc_sc["scene_id"] = len(history) + 1
            proc_sc["speaker"] = speaker
            proc_sc["speaker_name"] = speaker_name

            if is_female_speaker and proc_sc.get("characters"):
                c0 = proc_sc["characters"][0]
                c0["name"] = speaker_name or "Maya"
                c0["gender"] = "female"
                c0["hair_style"] = "ponytail"
                c0["has_eyelashes"] = True
                c0["cheek_blush"] = True

            return proc_sc

        # Build clean scene dictionary for dating drama
        scene_dict: dict[str, Any] = {
            "id": len(history) + 1,
            "scene_id": len(history) + 1,
            "duration": round(max(duration, 1.2), 3),
            "narration": narration,
            "speaker": speaker,
            "speaker_name": speaker_name,
            "action": action,
            "emotion": emotion,
            "background": background,
            "camera": camera,
            "characters": characters,
            "objects": objects,
            "effects": effects,
            "transition": "FADE",
            "transition_in": "FADE",
            "_metaphor": "DATING_DRAMA",
        }

        return scene_dict
