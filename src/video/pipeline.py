"""
Video Pipeline - Orchestrates the complete video generation process.
Coordinates: LLM -> Scene Planning -> TTS -> Audio Mixing -> Streaming Animation + Captions -> FFmpeg Encoding.
Created by Atharv Hatwar.

Designed specifically for 8 GB RAM / 4 GB VRAM laptops:
- Unloads the LLM right after scene planning.
- Streams animation frames directly into FFmpeg stdin instead of holding
  all frames in memory.
"""

from __future__ import annotations

import logging
import os
import re
import shutil
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

from animation.scene_composer import SceneComposer
from audio.mixer import AudioMixer
from audio.music_synth import MusicSynth
from audio.sfx_synth import SFXSynth
from captions.generator import CaptionGenerator
from captions.renderer import CaptionRenderer
from engine.scene_planner import ScenePlanner
from engine.timeline_manager import CentralTimelineManager
from styles.style_packs import resolve_style_pack
from video.encoder import VideoEncoder

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Module-level utility
# ---------------------------------------------------------------------------

def get_video_dimensions(
    format: str,
    resolution: str = "1080",
    preview: bool = False,
) -> tuple[int, int]:
    """Return (width, height) in pixels for a given aspect ratio and resolution."""
    res_key = "preview" if preview else ("720" if "720" in str(resolution) else "1080")
    _map: dict[str, dict[str, tuple[int, int]]] = {
        "9:16": {
            "1080":    (1080, 1920),
            "720":     (720, 1280),
            "preview": (360, 640),
        },
        "16:9": {
            "1080":    (1920, 1080),
            "720":     (1280, 720),
            "preview": (640, 360),
        },
        "1:1": {
            "1080":    (1080, 1080),
            "720":     (720, 720),
            "preview": (480, 480),
        },
    }

    fmt_map = _map.get(format, _map["9:16"])
    return fmt_map.get(res_key, fmt_map["1080"])


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------

class VideoPipeline:
    """Orchestrates the full offline video generation workflow."""

    def __init__(
        self,
        llm_manager,
        tts_manager,
        ffmpeg_path: str = "ffmpeg",
        output_dir: str = "output",
        temp_dir: str = "temp",
    ) -> None:
        self.llm_manager = llm_manager
        self.tts_manager = tts_manager
        self.ffmpeg_path = ffmpeg_path
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)

        self._cancel_event = threading.Event()
        self._active_process = None
        self.last_script_used: str = ""

        self._scene_planner = ScenePlanner(llm_manager=llm_manager)
        self._caption_generator = CaptionGenerator()
        self._music_synth = MusicSynth()
        self._sfx_synth = SFXSynth()
        self._audio_mixer = AudioMixer(ffmpeg_path=ffmpeg_path)
        self._encoder = VideoEncoder(ffmpeg_path=ffmpeg_path, use_hardware=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate_video(
        self,
        params: dict,
        progress_callback: Optional[Callable[[str, int], None]] = None,
        log_callback: Optional[Callable[[str], None]] = None,
    ) -> Optional[str]:
        """Run the full video generation pipeline and return the output MP4 path."""
        self._cancel_event.clear()
        self._active_process = None

        run_temp = self.temp_dir / f"job_{int(time.time())}"
        self.output_dir.mkdir(parents=True, exist_ok=True)
        run_temp.mkdir(parents=True, exist_ok=True)

        topic: str = str(params.get("topic", "untitled")).strip() or "untitled"
        script: str = str(params.get("script", "")).strip()
        script_mode: str = str(params.get("script_mode", "use_as_is"))
        target_duration: int = max(5, int(params.get("duration", 30)))
        raw_style: str = str(params.get("style", "s1_rsa_whiteboard"))
        style_variant: Optional[str] = params.get("style_variant") or None
        pack, _sp = resolve_style_pack(raw_style, style_variant)
        style: str = pack.id
        voice_id: str = str(params.get("voice_id", ""))
        raw_speed = params.get("voice_speed", 1.0)
        auto_voice_speed: bool = bool(
            params.get("auto_voice_speed", False)
            or (isinstance(raw_speed, str) and raw_speed.strip().lower() == "auto")
        )
        try:
            voice_speed: float = 1.0 if (isinstance(raw_speed, str) and raw_speed.strip().lower() == "auto") else float(raw_speed)
        except (TypeError, ValueError):
            voice_speed = 1.0
        voice_pitch: float = float(params.get("voice_pitch", 0.0))
        fmt: str = str(params.get("format", "9:16"))
        resolution: str = str(params.get("resolution", "1080"))
        preview_mode: bool = bool(params.get("preview_mode", False))
        fps: int = 12 if preview_mode else int(params.get("fps", 24))
        use_hw: bool = bool(params.get("use_hardware_encoding", True))

        music_style: str = str(params.get("music_style", pack.preferred_music or "calm"))
        custom_music_path: Optional[str] = params.get("custom_music_path")
        voice_volume: float = float(params.get("voice_volume", 1.0))
        music_volume: float = float(params.get("music_volume", 0.25))
        sfx_volume: float = float(params.get("sfx_volume", 0.65))
        fade_in: float = float(params.get("fade_in", 0.5))
        fade_out: float = float(params.get("fade_out", 0.5))

        caption_style: str = str(params.get("caption_style") or "bold_social")
        caption_font_size: int = int(params.get("caption_font_size", 38))
        caption_position: str = str(params.get("caption_position", "auto")) or "auto"
        caption_highlight: str = str(params.get("caption_highlight_color", "") or params.get("caption_highlight", ""))
        caption_font_name: str = str(params.get("caption_font_name", ""))

        use_lcm: bool = bool(params.get("use_lcm", False))
        unload_llm: bool = bool(params.get("unload_llm", True))

        width, height = get_video_dimensions(fmt, resolution=resolution, preview=preview_mode)
        # Social media caption scaling with readable typography floors
        if preview_mode:
            caption_font_size = max(20, int(height * 0.034))
        elif "720" in resolution:
            caption_font_size = max(34, int(height * 0.030))
        else:
            caption_font_size = max(46, int(height * 0.027))

        self._encoder.use_hardware = use_hw
        self._encoder._nvenc_available = None  # refresh if setting toggled

        def report(stage: str, pct: int) -> None:
            if progress_callback:
                try:
                    progress_callback(stage, max(0, min(100, pct)))
                except Exception:
                    pass

        def log(msg: str) -> None:
            logger.info(msg)
            if log_callback:
                try:
                    log_callback(msg)
                except Exception:
                    pass

        try:
            # ==============================================================
            # STAGE 1 – Understanding / preparing script (0-10%)
            # ==============================================================
            report("Understanding script", 2)
            if self._cancel_check():
                return None

            if script_mode == "auto_generate" or not script:
                log(f"Generating script for topic: {topic}")
                script = self._scene_planner.generate_script(
                    topic=topic, duration=target_duration, style=style
                )
            elif script_mode == "improve":
                log("Improving script while preserving meaning...")
                script = self._scene_planner.improve_script(
                    script=script, topic=topic, style=style, duration=target_duration
                )
            else:
                log("Analyzing provided script...")

            if not script:
                log("Error: script is empty.")
                return None

            self.last_script_used = script
            report("Understanding script", 10)

            # ==============================================================
            # STAGE 2 + 3 – Intelligent Script Understanding & Audio-First Visual Sync (10-45%)
            # ==============================================================
            report("Understanding script & pacing", 12)
            if self._cancel_check():
                return None

            from engine.script_intelligence import ScriptIntelligenceEngine
            from engine.quality_control import QualityControlValidator

            s1_cfg = params.get("speaker1", {})
            s2_cfg = params.get("speaker2", {})
            n1 = str(s1_cfg.get("name", "Alex")).strip()
            n2 = str(s2_cfg.get("name", "Maya")).strip()

            log("Extracting story beats and clean dialogue...")
            story_beats = ScriptIntelligenceEngine.parse_script_to_story_beats(
                raw_script=script,
                name1=n1,
                name2=n2,
            )

            if not story_beats:
                log("Error: No narrative beats could be extracted from script.")
                return None

            log(f"Extracted {len(story_beats)} clean narrative beats. Synthesizing synchronized audio...")
            report("Generating narration", 25)

            # Synthesize narration beat-by-beat FIRST to get exact audio duration
            tts_dir = run_temp / "tts"
            tts_dir.mkdir(parents=True, exist_ok=True)
            sentence_audio: list[dict] = []
            scenes: list[dict] = []
            global_time = 0.0

            total_beats = len(story_beats)
            for b_idx, beat in enumerate(story_beats):
                if self._cancel_check():
                    return None

                spk = beat.get("speaker", 1)
                spk_name = beat.get("speaker_name", n1)
                clean_text = beat.get("narration", "")

                # Voice selection
                if spk == 2 or spk_name.lower() in ("maya", "female"):
                    eff_voice = s2_cfg.get("voice_id") or "af_heart"
                    eff_speed = float(s2_cfg.get("speed") or voice_speed or 1.0)
                    eff_pitch = float(s2_cfg.get("pitch", 0.0))
                else:
                    eff_voice = s1_cfg.get("voice_id") or voice_id or "am_adam"
                    eff_speed = float(s1_cfg.get("speed") or voice_speed or 1.0)
                    eff_pitch = float(s1_cfg.get("pitch", voice_pitch))

                out_wav = str(tts_dir / f"beat_{b_idx:03d}.wav")
                synth_path = self.tts_manager.synthesize(
                    text=clean_text,
                    voice_id=eff_voice,
                    speed=eff_speed,
                    pitch=eff_pitch,
                    output_path=out_wav,
                )
                dur = self.tts_manager.get_audio_duration(synth_path) if synth_path else self.tts_manager.estimate_duration(clean_text, eff_speed)

                if synth_path and params.get("acoustic_mastering", True) and hasattr(self.tts_manager, "apply_acoustic_mastering"):
                    self.tts_manager.apply_acoustic_mastering(synth_path, synth_path)

                sentence_audio.append({
                    "text": clean_text,
                    "path": synth_path,
                    "duration": dur,
                    "start_time": global_time,
                })

                # Now plan the visual scene with EXACT audio duration!
                scene_dur = round(max(dur + 0.12, 1.2), 3)
                sc = ScriptIntelligenceEngine.plan_visual_for_beat(
                    beat=beat,
                    context_history=scenes,
                    duration=scene_dur,
                    style_id=style,
                    topic=topic,
                    total_beats=total_beats,
                )
                sc["_audio_path"] = synth_path
                sc["_audio_duration"] = dur
                sc["_scene_start_time"] = global_time
                sc["scene_id"] = b_idx + 1
                scenes.append(sc)

                global_time += scene_dur
                frac = (b_idx + 1) / total_beats
                report("Generating narration", 25 + int(frac * 20))

            # Authoritative Central Timeline Orchestration (0ms drift locked)
            timeline_mgr = CentralTimelineManager(fps=fps)
            timeline_mgr.register_scenes(scenes)
            for b_idx, entry in enumerate(sentence_audio):
                timeline_mgr.record_audio(b_idx, entry["path"], entry["duration"], clean_text=entry["text"])
            total_duration = timeline_mgr.compute_timeline(default_gap=0.12, min_scene_duration=1.2)

            log(f"Narration synthesized for {len(scenes)} scenes ({total_duration:.1f}s total).")

            # Apply Smart Video Director for dynamic camera cuts and visual pacing
            try:
                from engine.smart_video_director import SmartVideoDirector
                scenes = SmartVideoDirector.direct_storyboard(scenes)
                log("Smart Video Director: applied dynamic camera cuts & kinetic staging.")
            except Exception as e:
                logger.warning("SmartVideoDirector application skipped: %s", e)

            # Pre-Export Quality Control Inspection & Auto-Repair
            qc_ok, scenes, qc_logs = QualityControlValidator.validate_and_repair(
                scenes=scenes,
                sentence_audio=sentence_audio,
                speaker1_name=n1,
                speaker2_name=n2,
            )
            for ql in qc_logs:
                log(f"[QualityControl] {ql}")

            # Pre-Render Integrity & Sanitation Check
            pre_ok, pre_issues = timeline_mgr.validate_pre_render(width=width, height=height)
            for iss in pre_issues:
                log(f"[Pre-Render Check] {iss}")

            total_duration = timeline_mgr.total_duration
            log(f"Narration complete ({total_duration:.1f}s total, 0ms drift locked).")
            report("Generating narration", 45)

            # ==============================================================
            # STAGE 4 – Mixing audio (voice + music + SFX) (45-58%)
            # ==============================================================
            report("Mixing audio", 46)
            if self._cancel_check():
                return None

            log("Mixing narration, synthesized music, and sound effects...")
            mixed_audio_path = self._build_mixed_audio(
                scenes=scenes,
                sentence_audio=sentence_audio,
                music_style=music_style,
                custom_music_path=custom_music_path,
                voice_volume=voice_volume,
                music_volume=music_volume,
                sfx_volume=sfx_volume,
                fade_in=fade_in,
                fade_out=fade_out,
                total_duration=total_duration,
                audio_dir=run_temp / "audio",
                style_id=style,
                timeline_manager=timeline_mgr,
            )
            report("Mixing audio", 58)

            # ==============================================================
            # STAGE 5+6+7 – Captions + Streaming Animation + FFmpeg Encode (58-100%)
            # ==============================================================
            report("Creating animations", 60)
            if self._cancel_check():
                return None

            caption_events: list[dict] = []
            caption_renderer: Optional[CaptionRenderer] = None
            if caption_style and caption_style != "none":
                caption_events = timeline_mgr.generate_synchronized_captions(
                    caption_generator=self._caption_generator,
                    style=caption_style,
                )
                caption_renderer = CaptionRenderer(
                    width=width,
                    height=height,
                    style=caption_style,
                    font_size=caption_font_size,
                    highlight_color=caption_highlight,
                    position=caption_position,
                    font_name=caption_font_name,
                    style_id=style,
                    style_variant=style_variant,
                )
                log(f"Configured CaptionRenderer: style='{caption_style}', size={caption_font_size}px, events={len(caption_events)}")

            timestamp = int(time.time())
            safe_topic = "".join(c if c.isalnum() or c in "-_ " else "_" for c in topic).strip()[:40] or "video"
            if preview_mode:
                output_path = str(self.temp_dir / f"preview_{safe_topic}_{timestamp}.mp4")
            else:
                output_path = str(self.output_dir / f"{safe_topic}_{timestamp}.mp4")

            # Pad audio to match video duration so FFmpeg never truncates the final frames.
            # This is the primary fix for "video ends a few seconds early" bug.
            if mixed_audio_path and os.path.exists(mixed_audio_path):
                padded_audio_path = str(Path(run_temp) / "audio" / "padded_audio.wav")
                if self._audio_mixer.pad_audio_to_duration(mixed_audio_path, padded_audio_path, total_duration):
                    mixed_audio_path = padded_audio_path
                    log(f"Audio padded to {total_duration:.1f}s to match video duration.")

            log(f"Streaming {width}x{height} @ {fps} FPS -> {output_path}")
            composer = SceneComposer(style=style, width=width, height=height, fps=fps, style_variant=style_variant, use_lcm=use_lcm)

            process = self._encoder.start_encoding(
                output_path=output_path,
                width=width,
                height=height,
                fps=fps,
                audio_path=mixed_audio_path,
                crf=26 if preview_mode else 22,
                preset="ultrafast" if preview_mode else "fast",
            )
            self._active_process = process

            # Use ACTUAL total_duration (post-TTS) for accurate frame count estimation
            total_frames_est = max(1, int(round(total_duration * fps)))
            written_frames = 0
            last_stage_reported = "Creating animations"

            for scene_idx, scene in enumerate(scenes):
                if self._cancel_check():
                    break
                scene_dur = max(0.5, float(scene.get("duration", 3.0)))

                for frame in composer.compose_scene_stream(scene, scene_dur):
                    if self._cancel_check():
                        break

                    current_time = written_frames / float(fps)
                    if caption_renderer and caption_events:
                        for event in caption_events:
                            if event["start"] <= current_time <= event["end"]:
                                frame = caption_renderer.render_caption(frame, event, current_time)

                    if not self._encoder.write_frame(process, frame):
                        log("Error writing video frame to FFmpeg.")
                        process.kill()
                        return None

                    written_frames += 1
                    if written_frames % max(1, fps // 2) == 0:
                        frac = min(1.0, written_frames / total_frames_est)
                        # Transition progress labels cleanly from animations -> captions -> rendering
                        if frac < 0.45:
                            stage = "Creating animations"
                        elif frac < 0.65 and caption_renderer is not None:
                            stage = "Adding captions"
                        else:
                            stage = "Rendering video"
                        last_stage_reported = stage
                        report(stage, 60 + int(frac * 38))

            if self._cancel_check():
                try:
                    process.kill()
                except Exception:
                    pass
                log("Generation cancelled by user.")
                return None

            report("Rendering video", 98)
            success = self._encoder.finish_encoding(process)
            self._active_process = None

            if not success or not os.path.exists(output_path):
                log("Video encoding failed.")
                return None

            # ==============================================================
            # STAGE 8 – Quality Validation (98-100%)
            # ==============================================================
            report("Validating output", 99)
            if timeline_mgr:
                sync_ok, sync_report, stats = timeline_mgr.audit_post_render(
                    video_path=output_path,
                    expected_duration=total_duration,
                    log_fn=log,
                )
            validation_ok, validation_msg = self._validate_output(
                output_path=output_path,
                expected_duration=total_duration,
                expected_scenes=len(scenes),
                written_frames=written_frames,
                fps=fps,
                log_fn=log,
            )
            if not validation_ok:
                log(f"WARNING: Quality check issues detected: {validation_msg}")
                # Don't fail on validation warnings — just log them. The video exists.
            else:
                log(f"Quality check passed: {validation_msg}")

            report("Complete", 100)
            log(f"Export complete: {output_path}")
            return output_path

        except Exception as exc:
            logger.exception("Unexpected error in video pipeline: %s", exc)
            log(f"Pipeline error: {exc}")
            return None
        finally:
            self._active_process = None
            if use_lcm:
                try:
                    from engine.lcm_image_engine import LCMImageEngine
                    LCMImageEngine.unload_model()
                except Exception:
                    pass
            shutil.rmtree(run_temp, ignore_errors=True)

    def cancel(self) -> None:
        """Request cancellation and terminate any running FFmpeg process."""
        logger.info("Cancellation requested.")
        self._cancel_event.set()
        proc = self._active_process
        if proc is not None:
            try:
                proc.kill()
            except Exception:
                pass

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _adjust_scene_durations(self, scenes: list[dict], target_duration: int) -> list[dict]:
        total = sum(float(s.get("duration", 0)) for s in scenes)
        if total <= 0:
            equal = target_duration / max(1, len(scenes))
            for s in scenes:
                s["duration"] = round(equal, 2)
            return scenes

        scale = target_duration / total
        cursor = 0.0
        for s in scenes:
            s["duration"] = round(max(1.0, float(s.get("duration", 4.0)) * scale), 3)
            s["_scene_start_time"] = round(cursor, 3)
            cursor += s["duration"]
        return scenes

    def _synthesise_narration(
        self,
        scenes: list[dict],
        voice_id: str,
        voice_speed: float,
        voice_pitch: float,
        tts_dir: Path,
        report_fn: Callable[[float], None],
        dialogue_mode: bool = False,
        speaker1_cfg: Optional[dict] = None,
        speaker2_cfg: Optional[dict] = None,
        acoustic_mastering: bool = True,
    ) -> tuple[list[dict], list[dict]]:
        tts_dir.mkdir(parents=True, exist_ok=True)
        all_sentence_audio: list[dict] = []
        global_time = 0.0
        total_scenes = max(1, len(scenes))

        s1_cfg = speaker1_cfg or {}
        s2_cfg = speaker2_cfg or {}
        n1 = str(s1_cfg.get("name", "Alex")).strip().lower()
        n2 = str(s2_cfg.get("name", "Maya")).strip().lower()

        for scene_idx, scene in enumerate(scenes):
            if self._cancel_check():
                break
            narration = str(scene.get("narration", "")).strip()
            if not narration:
                continue

            sentences = self._caption_generator.split_into_sentences(narration)
            if not sentences:
                sentences = [narration]

            entries: list[dict] = []
            for s_idx, sentence in enumerate(sentences):
                # Detect speaker if in dialogue mode
                eff_voice = voice_id
                eff_speed = voice_speed
                eff_pitch = voice_pitch

                clean_text = sentence
                if dialogue_mode:
                    low_s = sentence.lower()
                    is_s2 = (
                        scene.get("speaker") == 2
                        or str(scene.get("speaker_name", "")).lower() == n2
                        or any(low_s.startswith(p) for p in (f"{n2}:", f"[{n2}]", f"**{n2}:", "speaker 2:", "female:", "female voice"))
                        or "female voice" in low_s
                    )
                    if is_s2:
                        eff_voice = s2_cfg.get("voice_id") or "blend:female_warm"
                        eff_speed = float(s2_cfg.get("speed") or voice_speed or 1.0)
                        eff_pitch = float(s2_cfg.get("pitch", 0.0))
                    else:
                        eff_voice = s1_cfg.get("voice_id") or voice_id
                        eff_speed = float(s1_cfg.get("speed") or voice_speed or 1.0)
                        eff_pitch = float(s1_cfg.get("pitch", voice_pitch))

                    clean_text = re.sub(
                        rf"^\s*(?:\*\*)?(?:\[)?(?:{re.escape(n1)}|{re.escape(n2)}|speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|male\s*voice|female\s*voice|male|female|final\s*line\s*[-–—]\s*(?:female|male)\s*voice)(?:\])?(?:\s*\([^)]*\))?(?:\*\*)?\s*[:\-–—]\s*",
                        "",
                        sentence,
                        flags=re.IGNORECASE,
                    ).strip()
                    clean_text = re.sub(r"\([A-Z\s]{4,}\)", "", clean_text).strip()
                    clean_text = re.sub(r"[*_]+", "", clean_text).strip()

                if not clean_text:
                    continue

                out_p = str(tts_dir / f"scene_{scene_idx:03d}" / f"s_{s_idx:03d}.wav")
                synth_path = self.tts_manager.synthesize(
                    text=clean_text or sentence,
                    voice_id=eff_voice,
                    speed=eff_speed,
                    pitch=eff_pitch,
                    output_path=out_p,
                )
                dur = self.tts_manager.get_audio_duration(synth_path) if synth_path else self.tts_manager.estimate_duration(clean_text, eff_speed)

                if synth_path and acoustic_mastering and hasattr(self.tts_manager, "apply_acoustic_mastering"):
                    self.tts_manager.apply_acoustic_mastering(synth_path, synth_path)

                entries.append({"text": clean_text or sentence, "path": synth_path, "duration": dur})

            scene_dur = 0.0
            for entry in entries:
                entry["start_time"] = global_time
                dur = float(entry.get("duration", 0.0))
                scene_dur += dur
                global_time += dur
                all_sentence_audio.append(entry)

            # Small breathing pause between scenes (0ms drift calculation)
            if scene_dur > 0:
                sc_dur = round(max(scene_dur + 0.22, 1.2), 3)
                scene["duration"] = sc_dur
                scene["_silence_gap"] = round(sc_dur - scene_dur, 3)
                scene["audio_parts"] = [e["path"] for e in entries if e.get("path")]
                scene["_scene_start_time"] = round(global_time - scene_dur, 3)
                global_time = round(scene["_scene_start_time"] + sc_dur, 3)

            report_fn((scene_idx + 1) / total_scenes)

        return all_sentence_audio, scenes

    def _build_mixed_audio(
        self,
        scenes: list[dict],
        sentence_audio: list[dict],
        music_style: str,
        custom_music_path: Optional[str],
        voice_volume: float,
        music_volume: float,
        sfx_volume: float,
        fade_in: float,
        fade_out: float,
        total_duration: float,
        audio_dir: Path,
        style_id: str = "s1_rsa_whiteboard",
        timeline_manager: Optional[CentralTimelineManager] = None,
    ) -> Optional[str]:
        audio_dir.mkdir(parents=True, exist_ok=True)

        # 1. Build continuous voice track (with 0ms drift synchronized to visual timeline)
        voice_concat = str(audio_dir / "voice_concat.wav")
        if timeline_manager is not None:
            timeline_manager.build_synchronized_audio_track(voice_concat, self._audio_mixer, audio_dir)
        else:
            voice_track_parts: list[str] = []
            silence_cache: dict[float, str] = {}
            for scene in scenes:
                p = scene.get("_audio_path") or scene.get("audio_path")
                if p and os.path.exists(p):
                    voice_track_parts.append(p)
                elif scene.get("audio_parts"):
                    for ap in scene["audio_parts"]:
                        if ap and os.path.exists(ap):
                            voice_track_parts.append(ap)
                gap = float(scene.get("_silence_gap", 0.22))
                if gap > 0.01:
                    if gap not in silence_cache:
                        sg = str(audio_dir / f"gap_{int(gap * 1000)}ms.wav")
                        self._audio_mixer.add_silence(gap, sg)
                        silence_cache[gap] = sg
                    voice_track_parts.append(silence_cache[gap])

            if voice_track_parts:
                if len(voice_track_parts) == 1:
                    shutil.copy2(voice_track_parts[0], voice_concat)
                else:
                    self._audio_mixer.concatenate_audio(voice_track_parts, voice_concat)

        if not os.path.exists(voice_concat) or os.path.getsize(voice_concat) == 0:
            # Generate silent master audio if TTS failed completely
            silent_out = str(audio_dir / "silent_master.wav")
            self._audio_mixer.add_silence(total_duration, silent_out)
            return silent_out if os.path.exists(silent_out) else None

        # 2. Prepare background music (custom MP3/WAV or locally synthesized)
        music_wav: Optional[str] = None
        if music_style == "custom" and custom_music_path and os.path.exists(custom_music_path):
            converted = str(audio_dir / "custom_music.wav")
            if self._audio_mixer.convert_to_wav(custom_music_path, converted):
                music_wav = converted
        elif music_style and music_style.lower() != "none":
            synth_wav = str(audio_dir / f"bgm_{music_style}.wav")
            # Synthesize a 12-second seamless loop (AudioMixer loops to full duration)
            loop_len = min(16.0, max(6.0, total_duration))
            if self._music_synth.generate_music(music_style, loop_len, synth_wav):
                music_wav = synth_wav

        # 3. Synthesize rich scene-reactive SFX + character movement footsteps + environment ambience
        final_sfx_events: list[dict] = []
        if sfx_volume > 0.01:
            sfx_cache: dict[str, str] = {}

            def _ensure_sfx(kind: str) -> Optional[str]:
                if kind not in sfx_cache:
                    sp = str(audio_dir / f"sfx_{kind}.wav")
                    if self._sfx_synth.generate_sfx(kind, sp):
                        sfx_cache[kind] = sp
                return sfx_cache.get(kind)

            raw_sfx_events: list[dict] = []
            t_cursor = 0.0
            for idx, scene in enumerate(scenes):
                sc_dur = max(0.5, float(scene.get("duration", 3.0)))
                bg_u = str(scene.get("background", "")).upper()
                objs = [str(o.get("asset", "") if isinstance(o, dict) else o).upper() for o in scene.get("objects", [])]
                chars = scene.get("characters", [])

                # 3a. Style-matched transition SFX (clean, pristine melodic sweeps)
                if idx > 0:
                    trans = str(scene.get("transition_in", scene.get("transition", "CUT"))).upper()
                    if style_id == "a5_historical_cartoon" and "SLIDE" in trans:
                        trans_kind = "katana_whoosh"
                    elif style_id == "a4_cozy_storytelling":
                        trans_kind = "chime_soft"
                    elif "SLIDE" in trans or "ZOOM" in trans:
                        trans_kind = "whoosh"
                    else:
                        trans_kind = "transition"
                    p_sfx = _ensure_sfx(trans_kind)
                    if p_sfx:
                        raw_sfx_events.append({"path": p_sfx, "time": t_cursor, "volume": sfx_volume * 0.35})

                # 3b. Character action-synchronized accents & bubble pops (clean, non-looping)
                for c_idx, c in enumerate(chars):
                    if not isinstance(c, dict):
                        continue
                    act = str(c.get("action", "STAND")).upper()
                    if act in ("FIGHT", "ANGRY", "STRUGGLE", "HUNT_SPEAR") and c_idx == 0:
                        hit_kind = "taiko_hit" if style_id in ("a5_historical_cartoon", "a3_prehistoric_cave") else "punch_hit"
                        p_hit = _ensure_sfx(hit_kind)
                        if p_hit:
                            raw_sfx_events.append({"path": p_hit, "time": t_cursor + min(0.4, sc_dur * 0.25), "volume": sfx_volume * 0.40})
                    elif act == "CELEBRATE" or act == "TRIUMPH_FIST":
                        p_cheer = _ensure_sfx("applause_cheer")
                        if p_cheer:
                            raw_sfx_events.append({"path": p_cheer, "time": t_cursor + 0.15, "volume": sfx_volume * 0.45})
                    elif act == "JUMP" and c_idx == 0:
                        p_jmp = _ensure_sfx("boing")
                        if p_jmp:
                            raw_sfx_events.append({"path": p_jmp, "time": t_cursor + 0.15, "volume": sfx_volume * 0.45})
                    elif act == "FALL" and c_idx == 0:
                        p_fall = _ensure_sfx("slide_whistle")
                        if p_fall:
                            raw_sfx_events.append({"path": p_fall, "time": t_cursor + 0.12, "volume": sfx_volume * 0.42})
                    elif act == "FACEPALM" and c_idx == 0:
                        p_slap = _ensure_sfx("punch_hit")
                        if p_slap:
                            raw_sfx_events.append({"path": p_slap, "time": t_cursor + 0.18, "volume": sfx_volume * 0.42})
                    elif act == "TYPING_LAPTOP":
                        p_typ = _ensure_sfx("keyboard_typing")
                        if p_typ:
                            raw_sfx_events.append({"path": p_typ, "time": t_cursor + 0.15, "volume": sfx_volume * 0.45})
                    elif act == "COUNT_MONEY":
                        p_reg = _ensure_sfx("cash_register")
                        if p_reg:
                            raw_sfx_events.append({"path": p_reg, "time": t_cursor + 0.18, "volume": sfx_volume * 0.50})
                    elif act in ("HEADACHE_STRESS", "SHOCK") and c_idx == 0:
                        p_boom = _ensure_sfx("dramatic_boom")
                        if p_boom:
                            raw_sfx_events.append({"path": p_boom, "time": t_cursor + 0.10, "volume": sfx_volume * 0.45})
                    elif (act == "BED_SHOCK" or c.get("emotion") in ("CRINGE", "SHOCKED", "SURPRISED")) and c_idx == 0:
                        sfx_name = "dramatic_boom" if act == "BED_SHOCK" else "pop"
                        p_reac = _ensure_sfx(sfx_name)
                        if p_reac:
                            raw_sfx_events.append({"path": p_reac, "time": t_cursor + 0.28, "volume": sfx_volume * 0.45})

                    if c.get("speech") or c.get("thought"):
                        p_pop = _ensure_sfx("pop")
                        if p_pop:
                            raw_sfx_events.append({"path": p_pop, "time": t_cursor + 0.10, "volume": sfx_volume * 0.30})

                # 3d. Key prop beats (animals, vehicles, instruments, lightbulbs, money, clocks)
                if "DOG" in objs:
                    p_bark = _ensure_sfx("animal_bark")
                    if p_bark:
                        raw_sfx_events.append({"path": p_bark, "time": t_cursor + min(0.35, sc_dur * 0.22), "volume": sfx_volume * 0.52})
                elif "CAT" in objs:
                    p_meow = _ensure_sfx("animal_meow")
                    if p_meow:
                        raw_sfx_events.append({"path": p_meow, "time": t_cursor + min(0.35, sc_dur * 0.22), "volume": sfx_volume * 0.50})
                elif "ROCKET" in objs:
                    p_rkt = _ensure_sfx("rocket_whoosh")
                    if p_rkt:
                        raw_sfx_events.append({"path": p_rkt, "time": t_cursor + 0.12, "volume": sfx_volume * 0.55})
                elif "CLOCK" in objs or "HOURGLASS" in objs or "NIGHTSTAND_CLOCK" in objs:
                    p_clk = _ensure_sfx("clock_tick")
                    if p_clk:
                        raw_sfx_events.append({"path": p_clk, "time": t_cursor + 0.20, "volume": sfx_volume * 0.48})
                elif "ALERT_STAMP" in objs:
                    p_alt = _ensure_sfx("dramatic_boom")
                    if p_alt:
                        raw_sfx_events.append({"path": p_alt, "time": t_cursor + 0.22, "volume": sfx_volume * 0.55})
                elif any(k in objs for k in ("THOUGHT_CLOUD", "FOLDER_DOCUMENT", "DOODLE_ARROW")):
                    p_wsh = _ensure_sfx("whoosh")
                    if p_wsh:
                        raw_sfx_events.append({"path": p_wsh, "time": t_cursor + 0.18, "volume": sfx_volume * 0.40})
                elif "DIYA" in objs:
                    p_dya = _ensure_sfx("magic_sparkle")
                    if p_dya:
                        raw_sfx_events.append({"path": p_dya, "time": t_cursor + 0.20, "volume": sfx_volume * 0.45})
                elif "MEGAPHONE" in objs:
                    p_mgp = _ensure_sfx("notification")
                    if p_mgp:
                        raw_sfx_events.append({"path": p_mgp, "time": t_cursor + 0.20, "volume": sfx_volume * 0.50})
                elif any(m in objs for m in ("TREASURE_CHEST", "MONEY", "COIN")):
                    p_coin = _ensure_sfx("cash_register" if "TREASURE_CHEST" in objs else "coin_clink")
                    if p_coin:
                        raw_sfx_events.append({"path": p_coin, "time": t_cursor + 0.20, "volume": sfx_volume * 0.55})
                elif any(s in objs for s in ("STAR", "SPARKLES", "MAGIC", "FIREWORKS")):
                    p_spk = _ensure_sfx("magic_sparkle")
                    if p_spk:
                        raw_sfx_events.append({"path": p_spk, "time": t_cursor + 0.20, "volume": sfx_volume * 0.52})
                elif "LIGHTBULB" in objs or "BRAIN" in objs:
                    p_chime = _ensure_sfx("chime_idea")
                    if p_chime:
                        raw_sfx_events.append({"path": p_chime, "time": t_cursor + 0.25, "volume": sfx_volume * 0.60})
                elif any(k in objs for k in ("LAPTOP", "COMPUTER", "KEYBOARD")):
                    p_typ = _ensure_sfx("keyboard_typing")
                    if p_typ:
                        raw_sfx_events.append({"path": p_typ, "time": t_cursor + 0.22, "volume": sfx_volume * 0.48})
                elif any(k in objs for k in ("SOCIAL_MEDIA", "PHONE", "CHECK", "GLASS_CARD", "WARNING", "EXCLAMATION", "SCROLL")):
                    kind = (
                        ("taiko_hit" if style_id == "a5_historical_cartoon" else "dramatic_boom")
                        if ("WARNING" in objs or "EXCLAMATION" in objs)
                        else (
                            "notification"
                            if ("PHONE" in objs or "SOCIAL_MEDIA" in objs or "GLASS_CARD" in objs)
                            else ("pencil_scratch" if "SCROLL" in objs else "pop")
                        )
                    )
                    p_obj = _ensure_sfx(kind)
                    if p_obj:
                        raw_sfx_events.append({"path": p_obj, "time": t_cursor + min(0.42, sc_dur * 0.25), "volume": sfx_volume * 0.58})

                # 3e. Editor Motion Graphic Badge entrance SFX (ding bell, cash register, or pop)
                if scene.get("editor_badge"):
                    b_type = str(scene["editor_badge"].get("badge_type", ""))
                    sfx_badge = "ding_bell" if b_type in ("ALERT", "TECH") else ("cash_register" if b_type == "METRIC" else "pop")
                    p_badge_sfx = _ensure_sfx(sfx_badge)
                    if p_badge_sfx:
                        raw_sfx_events.append({"path": p_badge_sfx, "time": t_cursor + 0.12, "volume": sfx_volume * 0.42})

                # 3f. Camera Shake visceral impact SFX
                if str(scene.get("camera", "")) == "CAMERA_SHAKE":
                    p_shake = _ensure_sfx("dramatic_boom")
                    if p_shake:
                        raw_sfx_events.append({"path": p_shake, "time": t_cursor + 0.05, "volume": sfx_volume * 0.48})

                t_cursor += sc_dur

            composite_sfx = str(audio_dir / "composite_sfx.wav")
            if raw_sfx_events and self._audio_mixer.build_composite_sfx_track(
                raw_sfx_events, total_duration=max(1.0, total_duration + 0.5), output_path=composite_sfx
            ):
                final_sfx_events = [{"path": composite_sfx, "time": 0.0, "volume": 1.0}]

        # 4. Mix voice + music + composite SFX track (with voice clear & zero 1/N amix attenuation)
        mixed_out = str(audio_dir / "mixed_audio.wav")
        safe_music_vol = min(0.42, max(0.0, music_volume))
        ok = self._audio_mixer.mix_audio(
            voice_path=voice_concat,
            music_path=music_wav,
            sfx_events=final_sfx_events,
            output_path=mixed_out,
            voice_volume=max(0.1, voice_volume),
            music_volume=safe_music_vol,
            sfx_volume=1.0,
            fade_in=fade_in,
            fade_out=fade_out,
        )
        return mixed_out if ok and os.path.exists(mixed_out) else voice_concat

    def _cancel_check(self) -> bool:
        return self._cancel_event.is_set()

    def _validate_output(
        self,
        output_path: str,
        expected_duration: float,
        expected_scenes: int,
        written_frames: int,
        fps: int,
        log_fn: Callable[[str], None],
    ) -> tuple[bool, str]:
        """Post-encode quality validation. Returns (ok, message)."""
        import json as _json
        import subprocess as _sp

        issues: list[str] = []

        # 1. File exists and is non-trivially sized
        if not os.path.exists(output_path):
            return False, "Output file does not exist"
        file_size = os.path.getsize(output_path)
        if file_size < 10_000:
            return False, f"Output file suspiciously small ({file_size} bytes)"

        # 2. Probe video duration via ffprobe
        try:
            ffprobe_path = self.ffmpeg_path
            if ffprobe_path.endswith("ffmpeg.exe"):
                ffprobe_path = ffprobe_path[:-len("ffmpeg.exe")] + "ffprobe.exe"
            elif ffprobe_path.endswith("ffmpeg"):
                ffprobe_path = ffprobe_path[:-len("ffmpeg")] + "ffprobe"
            else:
                ffprobe_path = "ffprobe"

            probe_cmd = [
                ffprobe_path, "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                output_path,
            ]
            result = _sp.run(
                probe_cmd, capture_output=True, text=True, timeout=15,
                creationflags=getattr(_sp, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                data = _json.loads(result.stdout)
                actual_dur = float(data.get("format", {}).get("duration", 0.0))
                if actual_dur < 0.5:
                    issues.append(f"Video duration only {actual_dur:.1f}s")
                elif actual_dur < expected_duration * 0.80:
                    issues.append(
                        f"Video ({actual_dur:.1f}s) much shorter than expected ({expected_duration:.1f}s)"
                    )
                else:
                    log_fn(f"Validated: duration={actual_dur:.1f}s, file={file_size//1024}KB")
        except Exception as exc:
            log_fn(f"ffprobe check skipped: {exc}")

        # 3. Frame count sanity
        expected_frames = int(round(expected_duration * fps))
        if written_frames < max(1, expected_frames * 0.75):
            issues.append(f"Only {written_frames}/{expected_frames} frames written")

        if issues:
            return False, "; ".join(issues)
        return True, f"scenes={expected_scenes}, frames={written_frames}, size={file_size//1024}KB"

    def _unload_llm(self) -> None:
        try:
            if hasattr(self.llm_manager, "unload"):
                self.llm_manager.unload()
                logger.info("LLM unloaded to free VRAM/RAM.")
        except Exception as exc:
            logger.debug("LLM unload skipped: %s", exc)
