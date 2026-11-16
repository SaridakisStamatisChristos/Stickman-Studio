# Created by Atharv Hatwar
"""
cis_pipeline.py - Full Production Pipeline for Cinematic Illustrated Stickman mode.
Coordinates:
  1. Semantic Storyboard Planning (cis_storyboard_planner)
  2. Scene Illustration (cis_scene_illustrator)
  3. Narration Synthesis (tts_manager)
  4. Manifest Generation (cis_manifest_builder)
  5. Autopilot Engine Rendering (node scripts/autopilot.mjs preview -> approve -> render)
  6. Automatic PIL + FFmpeg pipe fallback
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

logger = logging.getLogger(__name__)

# Optional Autopilot Node.js engine (if available locally or configured)
_local_autopilot = Path(__file__).resolve().parent.parent.parent / "scripts" / "autopilot.mjs"
_skill_autopilot = Path.home() / ".gemini" / "config" / "skills" / "directing-stickman-videos" / "scripts" / "autopilot.mjs"

if _local_autopilot.exists():
    AUTOPILOT_SCRIPT = _local_autopilot
    AUTOPILOT_DIR = _local_autopilot.parent.parent
elif _skill_autopilot.exists():
    AUTOPILOT_SCRIPT = _skill_autopilot
    AUTOPILOT_DIR = _skill_autopilot.parent.parent
else:
    AUTOPILOT_DIR = Path(__file__).resolve().parent.parent.parent
    AUTOPILOT_SCRIPT = AUTOPILOT_DIR / "scripts" / "autopilot.mjs"

FFMPEG_DIR = r"C:\ffmpeg\bin"


def _get_env_with_ffmpeg() -> dict[str, str]:
    """Ensure ffmpeg/ffprobe from local ffmpeg or C:/ffmpeg/bin is in PATH for Node and subprocesses with GPU NVENC enabled."""
    env = os.environ.copy()
    current_path = env.get("PATH", "")
    repo_ffmpeg = Path(__file__).resolve().parent.parent.parent / "ffmpeg"
    if repo_ffmpeg.exists() and str(repo_ffmpeg).lower() not in current_path.lower():
        current_path = f"{repo_ffmpeg};{current_path}"
    if FFMPEG_DIR.lower() not in current_path.lower() and os.path.exists(FFMPEG_DIR):
        current_path = f"{FFMPEG_DIR};{current_path}"
    env["PATH"] = current_path

    local_ffmpeg_exe = repo_ffmpeg / "ffmpeg.exe"
    local_ffprobe_exe = repo_ffmpeg / "ffprobe.exe"
    if local_ffmpeg_exe.exists():
        env["FFMPEG"] = str(local_ffmpeg_exe)
    elif os.path.exists(os.path.join(FFMPEG_DIR, "ffmpeg.exe")):
        env["FFMPEG"] = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
    else:
        env["FFMPEG"] = shutil.which("ffmpeg") or "ffmpeg"

    if local_ffprobe_exe.exists():
        env["FFPROBE"] = str(local_ffprobe_exe)
    elif os.path.exists(os.path.join(FFMPEG_DIR, "ffprobe.exe")):
        env["FFPROBE"] = os.path.join(FFMPEG_DIR, "ffprobe.exe")
    else:
        env["FFPROBE"] = shutil.which("ffprobe") or "ffprobe"

    env["USE_NVENC"] = "1"
    return env


def _notify_progress(cb: Optional[Callable], stage: str, pct: int) -> None:
    if not cb:
        return
    try:
        cb(stage, pct)
    except TypeError:
        try:
            cb(pct)
        except Exception:
            pass
    except Exception:
        pass


def _log(cb: Optional[Callable], msg: str) -> None:
    logger.info(msg)
    if cb:
        try:
            cb(msg)
        except Exception:
            pass


def _get_audio_duration(wav_path: str) -> float:
    """Return WAV duration in seconds using ffprobe for bit-exact match with autopilot.mjs."""
    repo_ffprobe = Path(__file__).resolve().parent.parent.parent / "ffmpeg" / "ffprobe.exe"
    ffprobe_bin = shutil.which("ffprobe") or (str(repo_ffprobe) if repo_ffprobe.exists() else str(Path(FFMPEG_DIR) / "ffprobe.exe"))
    if os.path.exists(ffprobe_bin):
        try:
            import json as _json
            res = subprocess.run(
                [ffprobe_bin, "-v", "quiet", "-print_format", "json", "-show_format", wav_path],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if res.returncode == 0:
                data = _json.loads(res.stdout)
                dur_str = data.get("format", {}).get("duration")
                if dur_str:
                    return float(dur_str)
        except Exception:
            pass

    try:
        import wave
        with wave.open(wav_path, "rb") as wf:
            frames = wf.getnframes()
            rate = wf.getframerate()
            if rate > 0:
                return round(frames / float(rate), 3)
    except Exception:
        pass
    try:
        size = Path(wav_path).stat().st_size
        return round(size / (22050 * 2), 2)
    except Exception:
        return 30.0


def _write_silent_wav(path: str, duration_seconds: float) -> None:
    """Write a valid silent 16-bit mono 22050 Hz WAV file."""
    import struct
    sample_rate = 22050
    n_samples = int(sample_rate * max(1.0, duration_seconds))
    data_size = n_samples * 2

    with open(path, "wb") as f:
        f.write(b"RIFF")
        f.write(struct.pack("<I", 36 + data_size))
        f.write(b"WAVE")
        f.write(b"fmt ")
        f.write(struct.pack("<I", 16))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<H", 1))
        f.write(struct.pack("<I", sample_rate))
        f.write(struct.pack("<I", sample_rate * 2))
        f.write(struct.pack("<H", 2))
        f.write(struct.pack("<H", 16))
        f.write(b"data")
        f.write(struct.pack("<I", data_size))
        f.write(b"\x00" * data_size)


class CISPipeline:
    """Orchestrates the entire Cinematic Illustrated Stickman video creation pipeline."""

    def __init__(
        self,
        llm_manager=None,
        tts_manager=None,
        output_dir: str = "output",
        temp_dir: str = "temp",
    ) -> None:
        self.llm_manager = llm_manager
        self.tts_manager = tts_manager
        self.output_dir = Path(output_dir)
        self.temp_dir = Path(temp_dir)
        self._cancel_event = threading.Event()
        self._active_proc: Optional[subprocess.Popen] = None
        self.last_script_used: str = ""

    def cancel(self) -> None:
        self._cancel_event.set()
        if self._active_proc:
            try:
                self._active_proc.kill()
            except Exception:
                pass

    def _cancelled(self) -> bool:
        return self._cancel_event.is_set()

    def generate_video(
        self,
        params: dict,
        progress_callback: Optional[Callable] = None,
        log_callback: Optional[Callable] = None,
    ) -> Optional[str]:
        """Run full CIS video generation workflow."""
        self._cancel_event.clear()
        t_start = time.time()

        topic = str(params.get("topic", "untitled")).strip() or "untitled"
        script = str(params.get("script", "")).strip()
        script_mode = str(params.get("script_mode", "use_as_is"))
        duration = max(5, int(params.get("duration", 30)))
        voice_id = str(params.get("voice_id", "af_heart"))
        raw_speed = params.get("voice_speed", 1.0)
        auto_voice_speed = bool(
            params.get("auto_voice_speed", False)
            or params.get("cis_auto_speed", False)
            or (isinstance(raw_speed, str) and raw_speed.strip().lower() == "auto")
        )
        try:
            voice_speed = 1.0 if (isinstance(raw_speed, str) and raw_speed.strip().lower() == "auto") else float(raw_speed)
        except (TypeError, ValueError):
            voice_speed = 1.0
        fmt = str(params.get("format", "9:16"))
        preview_mode = bool(params.get("preview_mode", False))
        raw_accent = params.get("cis_accent_color")
        accent_color = None if (not raw_accent or str(raw_accent).lower() == "auto") else str(raw_accent)
        visual_style = str(params.get("cis_visual_style", "auto") or "auto")
        raw_illus = str(params.get("cis_illustration_mode", "pil") or "pil").lower()
        use_lcm_flag = bool(params.get("use_lcm", False))
        illus_mode = "lcm" if (use_lcm_flag or raw_illus == "lcm") else "pil"
        scene_density = str(params.get("cis_scene_density", "balanced"))
        enable_cta = bool(params.get("cis_enable_cta", False))
        cta_text = str(params.get("cis_cta_text", "") or "").strip()
        cta_audio_text = str(params.get("cis_cta_audio_text", "") or "").strip()
        music_path = params.get("music_path") or params.get("custom_music_path") or None
        music_vol = float(params.get("music_volume", 0.12))

        slug = re.sub(r"[^a-z0-9]+", "-", topic.lower())[:36].strip("-") or "cis-video"
        job_dir = self.output_dir / f"{slug}_{int(time.time())}"
        job_dir.mkdir(parents=True, exist_ok=True)
        assets_dir = job_dir / "assets" / "scenes"
        assets_dir.mkdir(parents=True, exist_ok=True)

        _log(log_callback, f"✦ Starting Cinematic Illustrated Stickman generation: '{topic}'")

        # ------------------------------------------------------------------
        # 0. Script Resolution (Auto-generate or Improve if needed)
        # ------------------------------------------------------------------
        if not script or script_mode == "auto_generate":
            _log(log_callback, f"Auto-generating narration script for topic: '{topic}'…")
            _notify_progress(progress_callback, "Understanding script", 3)
            try:
                from engine.scene_planner import ScenePlanner
                sp = ScenePlanner(llm_manager=self.llm_manager)
                script = sp.generate_script(topic=topic, duration=duration, style="cis_illustrated")
            except Exception as exc:
                _log(log_callback, f"LLM script note: {exc}")
                script = ""

            if not script or len(script.split()) < 8:
                from engine.scene_planner import ScenePlanner
                sp = ScenePlanner(llm_manager=self.llm_manager)
                script = sp._generate_offline_script(topic, duration=duration)

            self.last_script_used = script
            _log(log_callback, f"Script ready: {len(script.split())} words.")
        elif script_mode == "improve":
            _log(log_callback, "Polishing narration script…")
            _notify_progress(progress_callback, "Understanding script", 4)
            try:
                from engine.scene_planner import ScenePlanner
                sp = ScenePlanner(llm_manager=self.llm_manager)
                script = sp.improve_script(script=script, topic=topic, style="cis_illustrated", duration=duration)
            except Exception as exc:
                _log(log_callback, f"Script improve note: {exc}")
            self.last_script_used = script

        _notify_progress(progress_callback, "Planning scenes", 10)
        if self._cancelled():
            return None

        # ------------------------------------------------------------------
        # 1. Plan Storyboard
        # ------------------------------------------------------------------
        from engine.cis_storyboard_planner import CISStoryboardPlanner
        planner = CISStoryboardPlanner(llm_manager=self.llm_manager)
        storyboard = planner.plan(
            script=script,
            topic=topic,
            accent_color=accent_color,
            scene_density=scene_density,
            enable_cta=enable_cta,
            cta_text=cta_text,
            cta_audio_text=cta_audio_text,
            visual_style=visual_style,
        )

        if not storyboard:
            _log(log_callback, "Error: Storyboard planner produced no scenes.")
            return None

        chosen_vs = storyboard[0].get("visual_style", "B1")
        _log(log_callback, f"Planned {len(storyboard)} scenes (Style={chosen_vs}, Genre={storyboard[0].get('video_profile')}):")
        for sc in storyboard:
            _log(log_callback, f"  Scene {sc['scene_id']}: [{sc.get('choreography')}/{sc.get('layout_mode')}] {sc['scene_title']} — {sc['scene_subtitle']}")

        _notify_progress(progress_callback, "Creating animations", 15)
        if self._cancelled():
            return None

        # ------------------------------------------------------------------
        # 2. Render Scene Illustrations (100% Offline / Free)
        # ------------------------------------------------------------------
        from engine.cis_scene_illustrator import CISSceneIllustrator
        _log(
            log_callback,
            "Illustration engine: ✨ LCM DreamShaper AI (Diffusion Backdrops)"
            if illus_mode == "lcm"
            else "Illustration engine: ✏️ Procedural Vector AI (B1/B3)",
        )
        illustrator = CISSceneIllustrator(mode=illus_mode, aspect_ratio=fmt)

        scene_png_paths: list[str] = []
        total_scenes = len(storyboard)
        try:
            for i, sc in enumerate(storyboard):
                if self._cancelled():
                    return None
                sid = sc.get("scene_id", i + 1)
                title_slug = sc.get("scene_title", "scene").lower().replace(" ", "_")[:14]
                out_png = str(assets_dir / f"scene{sid:02d}_{title_slug}.png")
                illustrator.illustrate(sc, out_png)
                scene_png_paths.append(out_png)
                pct = 15 + int(35 * (i + 1) / total_scenes)
                _notify_progress(progress_callback, "Creating animations", pct)
        finally:
            if illus_mode == "lcm":
                try:
                    from engine.lcm_image_engine import LCMImageEngine
                    LCMImageEngine.unload_model()
                except Exception:
                    pass

        _notify_progress(progress_callback, "Generating narration", 52)
        if self._cancelled():
            return None

        # ------------------------------------------------------------------
        # 3. TTS Voice Synthesis (with 0ms Audio-Visual Drift Lockstep)
        # ------------------------------------------------------------------
        from engine.timeline_manager import CentralTimelineManager
        from audio.mixer import AudioMixer

        ffmpeg_bin = shutil.which("ffmpeg") or str(Path(FFMPEG_DIR) / "ffmpeg.exe")
        audio_mixer = AudioMixer(ffmpeg_path=ffmpeg_bin)
        timeline_mgr = CentralTimelineManager(fps=30)
        timeline_mgr.register_scenes(storyboard)

        full_narration = " ".join(sc.get("narration", "") for sc in storyboard).strip()
        narration_wav = str(job_dir / "narration.wav")
        tts_scenes_dir = job_dir / "tts_scenes"
        tts_scenes_dir.mkdir(parents=True, exist_ok=True)
        video_profile = str(storyboard[0].get("video_profile", "balanced")) if storyboard else "balanced"

        effective_speed = voice_speed
        if auto_voice_speed:
            try:
                from tts.tts_manager import compute_auto_voice_speed
                effective_speed = compute_auto_voice_speed(
                    full_narration,
                    target_duration=float(duration),
                    video_profile=video_profile,
                )
                _log(log_callback, f"Auto Voice Speed selected: {effective_speed:.2f}x (genre={video_profile}, target={duration}s)")
            except Exception as exc:
                _log(log_callback, f"Auto speed note: {exc}")

        is_dialogue = bool(params.get("dialogue_mode", False)) or any(sc.get("speaker") == 2 for sc in storyboard)
        s1_cfg = dict(params.get("speaker1", {}))
        s2_cfg = dict(params.get("speaker2", {}))
        s1_cfg["speed"] = float(s1_cfg.get("speed") or voice_speed or 1.0)
        s2_cfg["speed"] = float(s2_cfg.get("speed") or voice_speed or 1.0)
        n1 = s1_cfg.get("name", "Alex")
        n2 = s2_cfg.get("name", "Maya")
        master_audio = bool(params.get("acoustic_mastering", True))

        total_scenes_count = len(storyboard)
        _log(log_callback, f"Synthesizing voice narration beat-by-beat for {total_scenes_count} scenes (Dialogue={is_dialogue})…")

        for b_idx, sc in enumerate(storyboard):
            if self._cancelled():
                return None

            raw_text = sc.get("narration", "").strip()
            # Clean out any speaker prefixes or markdown asterisks
            clean_text = re.sub(
                r"^\s*(?:\*\*)?(?:\[)?(?:alex|maya|speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|male\s*voice|female\s*voice|male|female)(?:\])?(?:\s*\([^)]*\))?(?:\*\*)?\s*[:\-–—]\s*",
                "",
                raw_text,
                flags=re.IGNORECASE,
            ).strip()
            clean_text = re.sub(r"[*_]+", "", clean_text).strip()

            spk = sc.get("speaker", 1)
            spk_name = str(sc.get("speaker_name", n1 if spk == 1 else n2))

            if is_dialogue and (spk == 2 or spk_name.lower() in ("maya", "female")):
                eff_voice = s2_cfg.get("voice_id") or "blend:female_warm"
                eff_spd = float(s2_cfg.get("speed") or effective_speed or 1.0)
                eff_pitch = float(s2_cfg.get("pitch", 0.0))
            elif is_dialogue:
                eff_voice = s1_cfg.get("voice_id") or "blend:male_introspective"
                eff_spd = float(s1_cfg.get("speed") or effective_speed or 1.0)
                eff_pitch = float(s1_cfg.get("pitch", 0.0))
            else:
                eff_voice = voice_id or "af_heart"
                eff_spd = effective_speed
                eff_pitch = float(params.get("voice_pitch", 0.0))

            scene_wav = str(tts_scenes_dir / f"scene_{b_idx:03d}.wav")
            synth_ok = False
            a_dur = 0.0

            if clean_text and self.tts_manager:
                try:
                    synth_path = self.tts_manager.synthesize(
                        text=clean_text,
                        voice_id=eff_voice,
                        speed=eff_spd,
                        pitch=eff_pitch,
                        output_path=scene_wav,
                    )
                    if synth_path and os.path.exists(synth_path):
                        synth_ok = True
                        if hasattr(self.tts_manager, "trim_silence"):
                            self.tts_manager.trim_silence(synth_path, synth_path, head_pad=0.030, tail_pad=0.060)
                        a_dur = _get_audio_duration(synth_path)
                except Exception as exc:
                    _log(log_callback, f"Scene {b_idx+1} TTS note: {exc}")

            if not synth_ok:
                a_dur = self.tts_manager.estimate_duration(clean_text, eff_spd) if (clean_text and self.tts_manager) else 0.0

            timeline_mgr.record_audio(
                b_idx,
                scene_wav if synth_ok else None,
                a_dur,
                clean_text=clean_text or raw_text,
            )

            pct = 52 + int(8 * (b_idx + 1) / total_scenes_count)
            _notify_progress(progress_callback, "Generating narration", pct)

        # Authoritative Central Timeline Calculation (0ms drift, comfortable 2.2s minimum scene hold)
        total_timeline_dur = timeline_mgr.compute_timeline(default_gap=0.12, min_scene_duration=2.2)

        # Assemble Master Narration Track (lockstep beat-for-beat with breathing micro-gaps)
        track_built = timeline_mgr.build_synchronized_audio_track(
            output_path=narration_wav,
            audio_mixer=audio_mixer,
            temp_dir=job_dir / "silence",
        )

        if not track_built or not Path(narration_wav).exists():
            _log(log_callback, "Warning: Synchronized audio track build fallback; creating silent track.")
            _write_silent_wav(narration_wav, max(2.0, total_timeline_dur))

        if master_audio and Path(narration_wav).exists() and self.tts_manager and hasattr(self.tts_manager, "apply_acoustic_mastering"):
            try:
                self.tts_manager.apply_acoustic_mastering(narration_wav, narration_wav)
            except Exception as exc:
                _log(log_callback, f"Acoustic mastering note: {exc}")

        narration_duration = _get_audio_duration(narration_wav)
        # Ensure the final scene's end aligns exactly with narration_wav duration
        if storyboard and narration_duration > 0:
            last_start = float(storyboard[-1].get("_audio_start", 0.0))
            storyboard[-1]["duration"] = max(0.5, round(narration_duration - last_start, 3))
            storyboard[-1]["_scene_end_time"] = round(narration_duration, 3)

        _log(log_callback, f"Audio track ready: {narration_duration:.2f}s locked across {len(storyboard)} scenes (0ms drift).")

        _notify_progress(progress_callback, "Adding captions", 65)
        if self._cancelled():
            return None

        # ------------------------------------------------------------------
        # 4. Background Music & Manifest (project.json)
        # ------------------------------------------------------------------
        if not music_path and music_vol > 0.01:
            score_wav = str(job_dir / "assets" / "audio" / "ambient_score.wav")
            try:
                from engine.cis_manifest_builder import generate_ambient_score
                if generate_ambient_score(score_wav, duration=narration_duration):
                    music_path = score_wav
                    _log(log_callback, "Synthesized reference-grade introspective background score.")
            except Exception as exc:
                _log(log_callback, f"Ambient score note: {exc}")

        from engine.cis_manifest_builder import build_manifest
        manifest_path = build_manifest(
            scenes=storyboard,
            scene_png_paths=scene_png_paths,
            narration_wav_path=narration_wav,
            narration_duration=narration_duration,
            music_path=music_path,
            output_project_dir=str(job_dir),
            aspect_ratio=fmt,
            music_gain=music_vol,
        )
        _log(log_callback, f"Manifest written to {manifest_path}")

        _notify_progress(progress_callback, "Rendering video", 72)
        if self._cancelled():
            return None

        # ------------------------------------------------------------------
        # 5. Render Video via Autopilot Engine (or PIL pipe fallback)
        # ------------------------------------------------------------------
        output_mp4: Optional[str] = None
        use_autopilot = AUTOPILOT_SCRIPT.exists() and shutil.which("node") is not None

        if use_autopilot:
            _log(log_callback, "Executing Autopilot rendering engine…")
            output_mp4 = self._render_autopilot(
                manifest_path, job_dir, log_callback, progress_callback, preview_mode=preview_mode
            )

        if not output_mp4 or not Path(output_mp4).exists():
            _log(log_callback, "Executing Native Python + FFmpeg illustrated compositing engine…")
            output_mp4 = self._render_ffmpeg_fallback(
                storyboard=storyboard,
                scene_png_paths=scene_png_paths,
                narration_wav=narration_wav,
                duration=narration_duration,
                job_dir=job_dir,
                log_callback=log_callback,
                manifest_path=manifest_path,
                aspect_ratio=fmt,
            )

        if output_mp4 and Path(output_mp4).exists():
            elapsed = round(time.time() - t_start, 1)
            file_size_mb = round(Path(output_mp4).stat().st_size / (1024 * 1024), 2)
            _log(log_callback, f"✓ Cinematic Illustrated video created successfully in {elapsed}s: {output_mp4} ({file_size_mb} MB)")
            _notify_progress(progress_callback, "Complete", 100)
            return output_mp4

        _log(log_callback, "Error: Final video file could not be produced.")
        return None

    def _render_autopilot(
        self,
        manifest_path: str,
        job_dir: Path,
        log_callback: Optional[Callable],
        progress_callback: Optional[Callable],
        preview_mode: bool = False,
    ) -> Optional[str]:
        """Run autopilot render cycle (preview only if preview_mode, else preview -> approve -> render)."""
        manifest_abs = str(Path(manifest_path).resolve())
        env = _get_env_with_ffmpeg()
        cwd = str(AUTOPILOT_DIR)

        try:
            # Phase 1: Preview (20s)
            _log(log_callback, "Autopilot Phase 1: Generating preview…")
            _notify_progress(progress_callback, "Rendering video", 78)
            p1 = subprocess.run(
                ["node", str(AUTOPILOT_SCRIPT), "preview", manifest_abs, "--seconds", "20"],
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd,
                timeout=180,
            )
            if p1.returncode != 0:
                _log(log_callback, f"Autopilot preview warning: {p1.stderr[-300:]}")

            preview_mp4 = job_dir / "output" / "preview.mp4"
            if preview_mode:
                if preview_mp4.exists():
                    _log(log_callback, "Fast preview rendered successfully.")
                    return str(preview_mp4)
                _log(log_callback, "Preview output not found, falling back to full pipeline…")

            # Phase 2: Approve
            _log(log_callback, "Autopilot Phase 2: Approving production ledger…")
            p2 = subprocess.run(
                ["node", str(AUTOPILOT_SCRIPT), "approve", manifest_abs, "--note", "Automated production approval"],
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd,
                timeout=30,
            )
            if p2.returncode != 0:
                _log(log_callback, f"Autopilot approve warning: {p2.stderr[-300:]}")

            # Phase 3: Full Film Render
            _log(log_callback, "Autopilot Phase 3: Rendering full cinematic film…")
            _notify_progress(progress_callback, "Rendering video", 88)
            p3 = subprocess.run(
                ["node", str(AUTOPILOT_SCRIPT), "render", manifest_abs],
                capture_output=True,
                text=True,
                env=env,
                cwd=cwd,
                timeout=900,
            )
            if p3.returncode != 0:
                _log(log_callback, f"Autopilot render warning: {p3.stderr[-400:]}")

            # Check rendered file
            film_mp4 = job_dir / "output" / "film.mp4"
            if film_mp4.exists():
                return str(film_mp4)

            if preview_mode and preview_mp4.exists():
                _log(log_callback, "Fast preview rendered successfully.")
                return str(preview_mp4)

            _log(log_callback, "Autopilot full film not generated, falling back to direct compositing…")
            return None

        except Exception as exc:
            _log(log_callback, f"Autopilot execution exception: {exc}")

        return None

    def _render_ffmpeg_fallback(
        self,
        storyboard: list[dict],
        scene_png_paths: list[str],
        narration_wav: str,
        duration: float,
        job_dir: Path,
        log_callback: Optional[Callable],
        manifest_path: Optional[str] = None,
        aspect_ratio: str = "9:16",
    ) -> Optional[str]:
        """Direct fallback: streams frames through FFmpeg with Ken Burns zoom and synchronized subtitles."""
        ffmpeg_bin = shutil.which("ffmpeg") or str(Path(FFMPEG_DIR) / "ffmpeg.exe")
        if not os.path.exists(ffmpeg_bin):
            return None

        out_mp4 = str(job_dir / "output_film.mp4")
        fps = 24
        if aspect_ratio == "16:9":
            w, h = 1920, 1080
        elif aspect_ratio == "1:1":
            w, h = 1080, 1080
        else:
            w, h = 1080, 1920

        # Load exact scene durations and timed captions from manifest
        captions: list[dict] = []
        scene_durations: list[float] = []
        if manifest_path and os.path.exists(manifest_path):
            try:
                import json
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                captions = manifest_data.get("captions", [])
                shots = manifest_data.get("shots", [])
                if shots and len(shots) == len(storyboard):
                    scene_durations = [round(max(0.5, float(sh.get("end", 0.0)) - float(sh.get("start", 0.0))), 3) for sh in shots]
            except Exception as exc:
                logger.warning("Could not read manifest in FFmpeg fallback: %s", exc)

        if not scene_durations:
            has_timings = bool(storyboard) and all(sc.get("_audio_duration") is not None for sc in storyboard)
            if has_timings:
                scene_durations = [max(1.0, float(sc.get("_audio_duration", 2.0)) + float(sc.get("_silence_gap", 0.12))) for sc in storyboard]
            else:
                total_w = sum(len(sc.get("narration", "").split()) for sc in storyboard) or 1
                scene_durations = [
                    max(2.0, duration * len(sc.get("narration", "").split()) / total_w)
                    for sc in storyboard
                ]

        # Check NVENC GPU support
        use_nvenc = False
        try:
            chk = subprocess.run([ffmpeg_bin, "-hide_banner", "-encoders"], capture_output=True, text=True, timeout=5)
            use_nvenc = "h264_nvenc" in chk.stdout
        except Exception:
            pass

        vcodec = "h264_nvenc" if use_nvenc else "libx264"
        cmd = [
            ffmpeg_bin, "-y",
            "-f", "rawvideo",
            "-vcodec", "rawvideo",
            "-s", f"{w}x{h}",
            "-pix_fmt", "rgb24",
            "-r", str(fps),
            "-i", "pipe:0",
            "-i", narration_wav,
            "-c:v", vcodec,
            "-preset", "fast" if use_nvenc else "medium",
            "-cq:v" if use_nvenc else "-crf", "22",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            out_mp4,
        ]

        try:
            from PIL import Image
            from captions.renderer import CaptionRenderer

            caption_font_size = max(46, int(h * 0.027))
            cap_renderer = CaptionRenderer(
                width=w,
                height=h,
                style="bold_social",
                font_size=caption_font_size,
                position="bottom",
                style_id="cis_illustrated",
            )

            proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.DEVNULL)
            self._active_proc = proc
            written_frames = 0
            total_target_frames = max(1, int(round(duration * fps)))

            for i, (png, s_dur) in enumerate(zip(scene_png_paths, scene_durations)):
                if self._cancelled():
                    proc.kill()
                    return None

                if png and os.path.exists(png):
                    fg = Image.open(png).convert("RGBA").resize((w, h))
                    paper = Image.new("RGBA", (w, h), "#FAF8F3")
                    base_img = Image.alpha_composite(paper, fg).convert("RGB")
                else:
                    base_img = Image.new("RGB", (w, h), "#FAF8F3")

                if i == len(scene_durations) - 1:
                    frames_n = max(1, total_target_frames - written_frames)
                else:
                    frames_n = max(1, int(round(s_dur * fps)))

                # Cinematic Ken Burns camera motion
                zoom_in = (i % 2 == 0)
                for f_idx in range(frames_n):
                    progress = f_idx / float(frames_n)
                    current_time = written_frames / float(fps)
                    scale = 1.0 + (0.04 * progress if zoom_in else 0.04 * (1.0 - progress))
                    zw, zh = int(w * scale), int(h * scale)
                    scaled = base_img.resize((zw, zh), Image.Resampling.BILINEAR)
                    crop_x = (zw - w) // 2
                    crop_y = (zh - h) // 2
                    frame = scaled.crop((crop_x, crop_y, crop_x + w, crop_y + h))

                    # Render synchronized high-contrast subtitle overlay
                    if captions:
                        for cue in captions:
                            c_start = float(cue.get("start", 0.0))
                            c_end = float(cue.get("end", 0.0))
                            if c_start <= current_time <= c_end:
                                frame = cap_renderer.render_caption(
                                    frame,
                                    {
                                        "text": cue.get("text", ""),
                                        "start": c_start,
                                        "end": c_end,
                                        "style": "bold_social",
                                        "uppercase": True,
                                    },
                                    current_time,
                                )
                                break

                    proc.stdin.write(frame.tobytes())
                    written_frames += 1

            proc.stdin.close()
            proc.wait(timeout=300)
            if proc.returncode == 0 and os.path.exists(out_mp4):
                return out_mp4
        except Exception as exc:
            _log(log_callback, f"FFmpeg fallback failed: {exc}")

        return None
