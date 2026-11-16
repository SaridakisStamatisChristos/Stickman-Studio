"""
Video Encoder - Encodes frames to H.264 MP4 using FFmpeg.
Supports NVENC hardware encoding on NVIDIA GTX 1650.
"""

import io
import logging
import shutil
import subprocess
from pathlib import Path
from typing import Callable, Optional

from PIL import Image

logger = logging.getLogger(__name__)


class VideoEncoder:
    """Encodes PIL Image frames to an H.264 MP4 file via FFmpeg.

    Automatically detects NVIDIA NVENC support and falls back to libx264
    software encoding when hardware encoding is unavailable.

    Args:
        ffmpeg_path: Path or name of the ffmpeg executable.
        use_hardware: Whether to attempt NVENC hardware encoding.
    """

    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        use_hardware: bool = True,
    ) -> None:
        self.ffmpeg_path = ffmpeg_path
        self.use_hardware = use_hardware
        self._nvenc_available: Optional[bool] = None  # lazily detected

    # ------------------------------------------------------------------
    # NVENC detection
    # ------------------------------------------------------------------

    def check_nvenc_support(self) -> bool:
        """Test whether NVENC hardware encoding actually initializes on this GPU."""
        if self._nvenc_available is not None:
            return self._nvenc_available

        if not self.use_hardware:
            self._nvenc_available = False
            return False

        try:
            probe = subprocess.run(
                [
                    self.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
                    "-f", "lavfi", "-i", "color=c=black:s=256x256:d=0.05",
                    "-frames:v", "1", "-c:v", "h264_nvenc", "-f", "null", "-",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            self._nvenc_available = (probe.returncode == 0)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            logger.warning("Could not probe NVENC support; assuming unavailable.")
            self._nvenc_available = False

        if self._nvenc_available:
            logger.info("NVENC hardware encoding verified and enabled.")
        else:
            logger.info("NVENC not available; using libx264 software encoding.")

        return self._nvenc_available

    # ------------------------------------------------------------------
    # Encoding process management
    # ------------------------------------------------------------------

    def start_encoding(
        self,
        output_path: str,
        width: int,
        height: int,
        fps: int,
        audio_path: Optional[str] = None,
        crf: int = 23,
        preset: str = "fast",
    ) -> subprocess.Popen:
        """Start an FFmpeg process that reads raw RGB frames from stdin.

        Args:
            output_path: Destination MP4 file path.
            width: Frame width in pixels.
            height: Frame height in pixels.
            fps: Frames per second.
            audio_path: Optional path to an audio file to mux into the video.
            crf: Constant Rate Factor for libx264 (lower = higher quality).

        Returns:
            subprocess.Popen object; write raw RGB24 frames to its stdin.
        """
        # Ensure output directory exists
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)

        cmd: list[str] = [
            self.ffmpeg_path,
            "-y",                          # overwrite output
            "-hide_banner",
            "-loglevel", "warning",
            # Video input from pipe
            "-f", "rawvideo",
            "-pix_fmt", "rgb24",
            "-s", f"{width}x{height}",
            "-r", str(fps),
            "-i", "pipe:0",
        ]

        # Optional audio input
        if audio_path and Path(audio_path).exists():
            cmd += ["-i", audio_path]
            map_flags = ["-map", "0:v", "-map", "1:a", "-shortest"]
            audio_codec = ["-c:a", "aac", "-b:a", "128k"]
        else:
            map_flags = ["-map", "0:v"]
            audio_codec = []

        cmd += map_flags

        # Video codec selection - always utilize NVIDIA NVENC when available
        if self.check_nvenc_support():
            nvenc_preset = "p1" if preset == "ultrafast" else "p4"
            bitrate = "2.5M" if preset == "ultrafast" else "4.5M"
            maxrate = "4M" if preset == "ultrafast" else "6M"
            bufsize = "4M" if preset == "ultrafast" else "8M"
            cmd += [
                "-c:v", "h264_nvenc",
                "-b:v", bitrate,
                "-maxrate", maxrate,
                "-bufsize", bufsize,
                "-preset", nvenc_preset,
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
            ]
        else:
            cmd += [
                "-c:v", "libx264",
                "-crf", str(crf),
                "-preset", preset,
                "-profile:v", "high",
                "-pix_fmt", "yuv420p",
            ]

        cmd += audio_codec
        cmd += ["-movflags", "+faststart", output_path]

        logger.debug("FFmpeg command: %s", " ".join(cmd))

        try:
            process = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
        except FileNotFoundError:
            raise RuntimeError(
                f"FFmpeg executable not found at '{self.ffmpeg_path}'. "
                "Please install FFmpeg and ensure it is on PATH."
            )

        return process

    def write_frame(
        self,
        process: subprocess.Popen,
        frame: Image.Image,
    ) -> bool:
        """Write a single PIL Image frame as raw RGB24 bytes to the FFmpeg process.

        Args:
            process: Running FFmpeg Popen object.
            frame: PIL Image (any mode; converted to RGB internally).

        Returns:
            True on success, False if the process stdin is closed.
        """
        if process.stdin is None or process.stdin.closed:
            logger.error("FFmpeg stdin is not available.")
            return False

        try:
            rgb_frame = frame.convert("RGB")
            process.stdin.write(rgb_frame.tobytes())
            return True
        except (BrokenPipeError, OSError) as exc:
            logger.error("Error writing frame to FFmpeg: %s", exc)
            return False

    def finish_encoding(self, process: subprocess.Popen) -> bool:
        """Signal end of input, wait for FFmpeg to finish, and return success status.

        Args:
            process: Running FFmpeg Popen object.

        Returns:
            True if FFmpeg exited with return code 0, False otherwise.
        """
        if process.stdin and not process.stdin.closed:
            try:
                process.stdin.close()
            except OSError:
                pass

        try:
            _, stderr = process.communicate(timeout=120)
        except subprocess.TimeoutExpired:
            logger.error("FFmpeg timed out during finalization; killing process.")
            process.kill()
            process.communicate()
            return False

        if process.returncode != 0:
            stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""
            logger.error(
                "FFmpeg exited with code %d:\n%s",
                process.returncode,
                stderr_text[-2000:],  # last 2 KB of error output
            )
            return False

        logger.info("FFmpeg encoding completed successfully.")
        return True

    # ------------------------------------------------------------------
    # High-level convenience method
    # ------------------------------------------------------------------

    def encode_from_frames(
        self,
        frames: list[Image.Image],
        output_path: str,
        audio_path: Optional[str] = None,
        fps: int = 24,
        width: int = 1080,
        height: int = 1920,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
        """Encode a list of PIL Images to an MP4 file.

        Args:
            frames: Ordered list of PIL Image frames to encode.
            output_path: Destination MP4 file path.
            audio_path: Optional audio file to mux in.
            fps: Output frame rate.
            width: Frame width (frames will be resized if mismatched).
            height: Frame height (frames will be resized if mismatched).
            progress_callback: Optional callable(stage: str, percent: int).

        Returns:
            True on success, False on failure.
        """
        if not frames:
            logger.error("encode_from_frames called with empty frame list.")
            return False

        total = len(frames)
        logger.info(
            "Encoding %d frames at %dx%d @%d fps → %s",
            total, width, height, fps, output_path,
        )

        if progress_callback:
            progress_callback("Rendering video", 0)

        try:
            process = self.start_encoding(
                output_path=output_path,
                width=width,
                height=height,
                fps=fps,
                audio_path=audio_path,
            )
        except RuntimeError as exc:
            logger.error("Failed to start encoder: %s", exc)
            return False

        for idx, frame in enumerate(frames):
            # Resize frame if dimensions mismatch (defensive)
            if frame.size != (width, height):
                frame = frame.resize((width, height), Image.LANCZOS)

            ok = self.write_frame(process, frame)
            if not ok:
                logger.error("Frame write failed at index %d; aborting.", idx)
                process.kill()
                return False

            if progress_callback and idx % max(1, total // 20) == 0:
                pct = int((idx / total) * 100)
                progress_callback("Rendering video", pct)

        success = self.finish_encoding(process)

        if progress_callback:
            progress_callback("Rendering video", 100 if success else -1)

        return success
