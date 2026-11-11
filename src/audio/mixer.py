"""
Audio Mixer - Mixes voice narration, background music, and SFX using FFmpeg.
No MoviePy or other heavy libraries. All mixing done via subprocess FFmpeg calls.
Created by Atharv Hatwar.
"""

from __future__ import annotations

import logging
import os
import subprocess
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)


class AudioMixer:
    """
    Combines voice, music, and SFX audio files into a final mixed track.
    Requires FFmpeg (and ffprobe) to be on PATH or supplied via *ffmpeg_path*.
    """

    def __init__(self, ffmpeg_path: str = "ffmpeg") -> None:
        self.ffmpeg_path = ffmpeg_path
        # Derive ffprobe from ffmpeg path
        parent = os.path.dirname(ffmpeg_path)
        self.ffprobe_path = os.path.join(parent, "ffprobe") if parent else "ffprobe"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def mix_audio(
        self,
        voice_path: str,
        music_path: Optional[str],
        sfx_events: list[dict],
        output_path: str,
        voice_volume: float = 1.0,
        music_volume: float = 0.3,
        sfx_volume: float = 0.7,
        fade_in: float = 0.5,
        fade_out: float = 0.5,
    ) -> bool:
        """
        Mix voice narration, optional background music, and timed SFX into one file.

        Parameters
        ----------
        voice_path   : path to the narration WAV
        music_path   : path to background music WAV (or None)
        sfx_events   : list of {"path": str, "time": float, "volume": float}
        output_path  : destination WAV path
        voice_volume : linear gain for voice (1.0 = unity)
        music_volume : linear gain for music
        sfx_volume   : default linear gain for SFX (overridden per-event by event["volume"])
        fade_in      : fade-in duration (seconds) applied to entire output
        fade_out     : fade-out duration (seconds) applied to entire output
        """
        if not os.path.exists(voice_path):
            logger.error("Voice file not found: %s", voice_path)
            return False

        try:
            total_duration = self.get_duration(voice_path)

            # ---- Build input list and filter graph ----
            inputs: list[str] = ["-i", voice_path]
            filter_parts: list[str] = []
            stream_idx = 0

            # Voice stream
            voice_stream = f"[{stream_idx}:a]"
            filter_parts.append(f"{voice_stream}volume={voice_volume:.4f}[voice]")
            stream_idx += 1

            mix_labels = ["[voice]"]

            # Music stream with Automatic Smart Ducking (Created by Atharv Hatwar)
            if music_path and os.path.exists(music_path):
                inputs += ["-i", music_path]
                music_stream = f"[{stream_idx}:a]"
                # Loop music if shorter than voice, trim to voice length
                filter_parts.append(
                    f"{music_stream}"
                    f"aloop=loop=-1:size=2e+09,"
                    f"atrim=end={total_duration:.4f},"
                    f"volume={music_volume:.4f}[music_raw]"
                )
                # Duck music dynamically against voice narration so voice is always clear
                filter_parts.append(
                    f"[music_raw][voice]sidechaincompress=threshold=0.08:ratio=4:attack=20:release=350[music]"
                )
                mix_labels.append("[music]")
                stream_idx += 1

            # SFX streams
            for ev_idx, event in enumerate(sfx_events):
                sfx_path = event.get("path", "")
                if not sfx_path or not os.path.exists(sfx_path):
                    logger.warning("SFX file missing, skipping: %s", sfx_path)
                    continue
                ev_time = float(event.get("time", 0.0))
                ev_vol = float(event.get("volume", sfx_volume))
                label = f"sfx{ev_idx}"
                inputs += ["-i", sfx_path]
                filter_parts.append(
                    f"[{stream_idx}:a]"
                    f"volume={ev_vol:.4f},"
                    f"adelay={int(ev_time * 1000)}|{int(ev_time * 1000)},"
                    f"apad=whole_dur={total_duration:.4f}"
                    f"[{label}]"
                )
                mix_labels.append(f"[{label}]")
                stream_idx += 1

            # Merge streams with clean headroom and smooth soft-knee limiter (zero distortion/crunch)
            n_streams = len(mix_labels)
            mix_input = "".join(mix_labels)
            filter_parts.append(
                f"{mix_input}amix=inputs={n_streams}:duration=first:dropout_transition=0:normalize=0,"
                f"volume=0.88,"
                f"alimiter=limit=0.92:attack=7:release=100:asc=1[mixed]"
            )

            # Apply fade in/out to the final mix
            filter_parts.append(
                f"[mixed]"
                f"afade=t=in:st=0:d={fade_in:.4f},"
                f"afade=t=out:st={max(0.0, total_duration - fade_out):.4f}:d={fade_out:.4f}"
                f"[out]"
            )

            filtergraph = ";".join(filter_parts)

            cmd = (
                [self.ffmpeg_path, "-y"]
                + inputs
                + [
                    "-filter_complex", filtergraph,
                    "-map", "[out]",
                    "-ar", "44100",
                    "-ac", "1",
                    "-c:a", "pcm_s16le",
                    output_path,
                ]
            )

            return self._run(cmd, f"mix_audio → {os.path.basename(output_path)}")

        except Exception as exc:
            logger.error("mix_audio failed: %s", exc, exc_info=True)
            return False

    def concatenate_audio(self, audio_paths: list[str], output_path: str) -> bool:
        """
        Concatenate multiple audio files in order.
        Uses FFmpeg concat demuxer for lossless joining.
        """
        if not audio_paths:
            logger.error("concatenate_audio: no input files provided")
            return False

        # Filter missing files
        valid = [p for p in audio_paths if os.path.exists(p)]
        if not valid:
            logger.error("concatenate_audio: none of the input files exist")
            return False

        try:
            # Write a temporary concat list file
            with tempfile.NamedTemporaryFile(
                mode="w",
                suffix=".txt",
                delete=False,
                encoding="utf-8",
            ) as fh:
                list_path = fh.name
                for p in valid:
                    # FFmpeg concat list requires forward slashes and escaped apostrophes
                    safe = p.replace("\\", "/").replace("'", r"\'")
                    fh.write(f"file '{safe}'\n")

            cmd = [
                self.ffmpeg_path, "-y",
                "-f", "concat",
                "-safe", "0",
                "-i", list_path,
                "-c:a", "pcm_s16le",
                "-ar", "44100",
                "-ac", "1",
                output_path,
            ]
            result = self._run(cmd, f"concat → {os.path.basename(output_path)}")
        finally:
            try:
                os.unlink(list_path)
            except OSError:
                pass

        return result

    def get_duration(self, audio_path: str) -> float:
        """
        Return audio duration in seconds using ffprobe.
        Falls back to wave module for WAV files if ffprobe is unavailable.
        """
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "error",
                    "-show_entries", "format=duration",
                    "-of", "default=noprint_wrappers=1:nokey=1",
                    audio_path,
                ],
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return float(result.stdout.strip())
        except (FileNotFoundError, ValueError, subprocess.TimeoutExpired):
            pass

        # Fallback: wave module for WAV files
        if audio_path.lower().endswith(".wav"):
            try:
                import wave as _wave
                with _wave.open(audio_path, "rb") as wf:
                    return wf.getnframes() / float(wf.getframerate())
            except Exception:
                pass

        logger.warning("Could not determine duration of '%s'", audio_path)
        return 0.0

    def convert_to_wav(self, input_path: str, output_path: str) -> bool:
        """Convert any FFmpeg-supported audio format to 16-bit mono 44100 Hz WAV."""
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        return self._run(cmd, f"convert → {os.path.basename(output_path)}")

    def normalize_audio(self, input_path: str, output_path: str) -> bool:
        """
        Normalize audio loudness using FFmpeg's loudnorm filter
        (EBU R128, target -16 LUFS) for consistent voice levels.
        """
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
            "-ar", "44100",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        return self._run(cmd, f"normalize → {os.path.basename(output_path)}")

    def build_composite_sfx_track(
        self,
        sfx_events: list[dict],
        total_duration: float,
        output_path: str,
        sample_rate: int = 44100,
    ) -> bool:
        """
        Pre-mix an unlimited timeline of timed SFX events into ONE clean mono WAV track
        so FFmpeg amix stays fast & light while supporting exact footstep/action sync.
        """
        if not sfx_events or total_duration <= 0:
            return False
        try:
            import wave as _wave
            import numpy as _np

            n_total = max(1, int(round(total_duration * sample_rate)))
            mix = _np.zeros(n_total, dtype=_np.float32)
            cache: dict[str, _np.ndarray] = {}

            for ev in sfx_events:
                path = ev.get("path", "")
                if not path or not os.path.exists(path):
                    continue
                if path not in cache:
                    with _wave.open(path, "rb") as wf:
                        raw = wf.readframes(wf.getnframes())
                        ch = wf.getnchannels()
                        arr = _np.frombuffer(raw, dtype=_np.int16).astype(_np.float32) / 32768.0
                        if ch > 1:
                            arr = arr.reshape(-1, ch).mean(axis=1)
                        cache[path] = arr
                clip = cache[path]
                if len(clip) == 0:
                    continue
                t0 = max(0.0, float(ev.get("time", 0.0)))
                vol = max(0.0, min(1.5, float(ev.get("volume", 0.7))))
                start_idx = int(round(t0 * sample_rate))
                if start_idx >= n_total:
                    continue
                end_idx = min(n_total, start_idx + len(clip))
                mix[start_idx:end_idx] += clip[: end_idx - start_idx] * vol

            peak = float(_np.max(_np.abs(mix))) if len(mix) else 0.0
            if peak > 0.40:
                mix = mix * (0.40 / peak)

            pcm = _np.clip(mix * 32767.0, -32768, 32767).astype(_np.int16).tobytes()
            os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)
            with _wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(pcm)
            return True
        except Exception as exc:
            logger.warning("build_composite_sfx_track failed: %s", exc)
            return False

    def add_silence(self, duration: float, output_path: str) -> bool:
        """Generate a silent WAV file of *duration* seconds."""
        cmd = [
            self.ffmpeg_path, "-y",
            "-f", "lavfi",
            "-i", f"anullsrc=r=44100:cl=mono",
            "-t", f"{duration:.4f}",
            "-c:a", "pcm_s16le",
            output_path,
        ]
        return self._run(cmd, f"silence {duration:.1f}s → {os.path.basename(output_path)}")

    def pad_audio_to_duration(self, input_path: str, output_path: str, target_duration: float) -> bool:
        """Extend *input_path* with silence so the output is at least *target_duration* seconds.

        This prevents FFmpeg from truncating video when audio is shorter than visual frames.
        If the input is already long enough, it is copied as-is.
        """
        current_dur = self.get_duration(input_path)
        if current_dur >= target_duration - 0.05:
            # Already long enough — just copy
            import shutil as _shutil
            try:
                _shutil.copy2(input_path, output_path)
                return True
            except Exception as exc:
                logger.error("pad_audio_to_duration copy failed: %s", exc)
                return False

        pad_secs = max(0.1, target_duration - current_dur + 0.3)
        cmd = [
            self.ffmpeg_path, "-y",
            "-i", input_path,
            "-af", f"apad=pad_dur={pad_secs:.4f}",
            "-t", f"{target_duration + 0.3:.4f}",
            "-c:a", "pcm_s16le",
            "-ar", "44100",
            "-ac", "1",
            output_path,
        ]
        return self._run(cmd, f"pad_audio {current_dur:.1f}s→{target_duration:.1f}s")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _run(self, cmd: list[str], label: str) -> bool:
        """Run an FFmpeg command, logging stderr on failure."""
        logger.debug("FFmpeg [%s]: %s", label, " ".join(cmd))
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                timeout=300,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode != 0:
                stderr = result.stderr.decode("utf-8", errors="replace")
                logger.error("FFmpeg '%s' failed (rc=%d):\n%s", label, result.returncode, stderr)
                return False
            return True
        except FileNotFoundError:
            logger.error(
                "FFmpeg not found at '%s'. Install FFmpeg and ensure it is on PATH.",
                self.ffmpeg_path,
            )
            return False
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg '%s' timed out after 300 s", label)
            return False
        except Exception as exc:
            logger.error("FFmpeg '%s' exception: %s", label, exc, exc_info=True)
            return False
