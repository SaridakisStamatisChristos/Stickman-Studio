"""
Preview Player - Frame-based video preview widget using ffmpeg + QTimer.
Supports load, play, pause, stop, scrubbing, and file export actions.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QIcon, QPixmap
try:
    from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
    _HAS_QT_MEDIA = True
except Exception:
    _HAS_QT_MEDIA = False
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

PLAYER_STYLE = """
QWidget { background: #0d1b2a; color: #e8e8e8; }
QPushButton {
    background: #0f3460; color: white; border: none;
    border-radius: 6px; padding: 7px 14px; font-size: 12px;
}
QPushButton:hover { background: #1a4a8a; }
QPushButton:disabled { background: #1a1a2e; color: #444; }
QSlider::groove:horizontal { background: #1a2a3a; height: 5px; border-radius: 3px; }
QSlider::handle:horizontal {
    background: #e94560; width: 14px; height: 14px;
    border-radius: 7px; margin: -5px 0;
}
QSlider::sub-page:horizontal { background: #e94560; height: 5px; border-radius: 3px; }
QLabel { background: transparent; }
"""

_FFMPEG_TIMEOUT = 60  # seconds for frame extraction


def _find_ffmpeg(preferred: Optional[str] = None) -> Optional[str]:
    """Return path to ffmpeg executable, checking common Windows locations."""
    if preferred and os.path.isfile(preferred):
        return preferred
    candidates = [
        shutil.which("ffmpeg"),
        os.path.join(os.getcwd(), "ffmpeg", "ffmpeg.exe"),
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _find_ffprobe(ffmpeg_path: Optional[str] = None) -> Optional[str]:
    if ffmpeg_path:
        sibling = os.path.join(os.path.dirname(ffmpeg_path), "ffprobe.exe")
        if os.path.isfile(sibling):
            return sibling
    return shutil.which("ffprobe") or (r"C:\ffmpeg\bin\ffprobe.exe" if os.path.isfile(r"C:\ffmpeg\bin\ffprobe.exe") else None)


def _get_video_duration(path: str, ffmpeg_path: Optional[str] = None) -> float:
    """Return video duration in seconds using ffprobe."""
    ffprobe = _find_ffprobe(ffmpeg_path)
    if not ffprobe:
        return 0.0
    try:
        result = subprocess.run(
            [
                ffprobe, "-v", "quiet", "-print_format", "json",
                "-show_format", path,
            ],
            capture_output=True, text=True, timeout=10,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        import json
        data = json.loads(result.stdout)
        return float(data.get("format", {}).get("duration", 0))
    except Exception:
        return 0.0


def _fmt_time(seconds: float) -> str:
    s = int(seconds)
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02d}:{s:02d}"
    return f"{m}:{s:02d}"


class PreviewPlayer(QWidget):
    """
    Simple frame-based video player.
    Uses ffmpeg to extract frames to a temp directory on demand,
    then cycles through them with a QTimer.
    """

    playback_finished = Signal()

    def __init__(self, parent: Optional[QWidget] = None, ffmpeg_path: Optional[str] = None) -> None:
        super().__init__(parent)
        self.setStyleSheet(PLAYER_STYLE)

        self._video_path: str = ""
        self._audio_wav_path: str = ""
        self._temp_dir: Optional[tempfile.TemporaryDirectory] = None
        self._frame_paths: list[str] = []
        self._current_frame: int = 0
        self._total_frames: int = 0
        self._fps: float = 10.0
        self._duration: float = 0.0
        self._playing: bool = False
        self._ffmpeg: Optional[str] = _find_ffmpeg(ffmpeg_path)
        self._audio_player = None
        self._audio_output = None
        if _HAS_QT_MEDIA:
            try:
                self._audio_output = QAudioOutput(self)
                self._audio_output.setVolume(0.9)
                self._audio_player = QMediaPlayer(self)
                self._audio_player.setAudioOutput(self._audio_output)
            except Exception:
                self._audio_player = None
                self._audio_output = None

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance_frame)

        self._setup_ui()

    def set_ffmpeg_path(self, ffmpeg_path: str) -> None:
        self._ffmpeg = _find_ffmpeg(ffmpeg_path) or self._ffmpeg

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Video display
        self._display = QLabel()
        self._display.setAlignment(Qt.AlignCenter)
        self._display.setMinimumHeight(300)
        self._display.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self._display.setStyleSheet(
            "QLabel { background: #050508; border: 1px solid #0f3460; border-radius: 6px; color: #444; font-size: 16px; }"
        )
        self._display.setText("No video loaded")
        root.addWidget(self._display, stretch=1)

        # Progress slider
        self._seek_slider = QSlider(Qt.Horizontal)
        self._seek_slider.setRange(0, 1000)
        self._seek_slider.setValue(0)
        self._seek_slider.sliderMoved.connect(self._on_seek)
        self._seek_slider.setEnabled(False)
        root.addWidget(self._seek_slider)

        # Time display
        time_row = QHBoxLayout()
        self._time_lbl = QLabel("0:00")
        self._total_lbl = QLabel("0:00")
        self._time_lbl.setStyleSheet("color: #4FC3F7; font-family: Consolas;")
        self._total_lbl.setStyleSheet("color: #4FC3F7; font-family: Consolas;")
        time_row.addWidget(self._time_lbl)
        time_row.addStretch()
        time_row.addWidget(self._total_lbl)
        root.addLayout(time_row)

        # Controls
        ctrl_row = QHBoxLayout()
        ctrl_row.setSpacing(6)

        self._play_btn = QPushButton("▶  Play")
        self._play_btn.clicked.connect(self._toggle_play)
        self._play_btn.setEnabled(False)
        ctrl_row.addWidget(self._play_btn)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.clicked.connect(self.stop)
        self._stop_btn.setEnabled(False)
        ctrl_row.addWidget(self._stop_btn)

        ctrl_row.addStretch()

        self._explorer_btn = QPushButton("📁  Open in Explorer")
        self._explorer_btn.clicked.connect(self._open_in_explorer)
        self._explorer_btn.setEnabled(False)
        ctrl_row.addWidget(self._explorer_btn)

        self._export_btn = QPushButton("💾  Export Copy")
        self._export_btn.clicked.connect(self._export_copy)
        self._export_btn.setEnabled(False)
        ctrl_row.addWidget(self._export_btn)

        root.addLayout(ctrl_row)

    # ------------------------------------------------------------------
    # Frame extraction
    # ------------------------------------------------------------------

    def _extract_frames(self) -> bool:
        """Extract frames from the loaded video into a temp directory."""
        if not self._ffmpeg:
            self._display.setText("ffmpeg not found.\nInstall ffmpeg and add it to PATH.")
            return False
        if not self._video_path or not os.path.isfile(self._video_path):
            return False

        # Clean up previous temp dir
        self._cleanup_temp()
        self._temp_dir = tempfile.TemporaryDirectory(prefix="stickman_preview_")
        out_pattern = os.path.join(self._temp_dir.name, "frame_%05d.jpg")

        try:
            subprocess.run(
                [
                    self._ffmpeg, "-y",
                    "-i", self._video_path,
                    "-vf", "fps=10,scale=854:-2",   # 10 fps preview, up to 480p-ish
                    "-q:v", "4",
                    out_pattern,
                ],
                capture_output=True,
                timeout=_FFMPEG_TIMEOUT,
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            self._display.setText(f"ffmpeg error:\n{exc.stderr.decode(errors='replace')[:300]}")
            return False
        except subprocess.TimeoutExpired:
            self._display.setText("ffmpeg timed out during frame extraction.")
            return False

        frames = sorted(Path(self._temp_dir.name).glob("frame_*.jpg"), key=lambda p: p.name)
        self._frame_paths = [str(f) for f in frames]
        self._total_frames = len(self._frame_paths)
        self._fps = 10.0  # preview fps

        # Also extract audio WAV for synchronized offline playback via winsound
        self._audio_wav_path = os.path.join(self._temp_dir.name, "preview_audio.wav")
        try:
            subprocess.run(
                [self._ffmpeg, "-y", "-i", self._video_path, "-vn", "-ar", "22050", "-ac", "1", "-c:a", "pcm_s16le", self._audio_wav_path],
                capture_output=True, timeout=30,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if not os.path.exists(self._audio_wav_path):
                self._audio_wav_path = ""
        except Exception:
            self._audio_wav_path = ""

        return self._total_frames > 0

    def _cleanup_temp(self) -> None:
        self._timer.stop()
        if self._audio_player is not None:
            try:
                self._audio_player.stop()
                self._audio_player.setSource(QUrl())
            except Exception:
                pass
        if self._temp_dir is not None:
            try:
                self._temp_dir.cleanup()
            except Exception:
                pass
            self._temp_dir = None
        self._audio_wav_path = ""
        self._frame_paths = []
        self._current_frame = 0
        self._total_frames = 0

    # ------------------------------------------------------------------
    # Playback
    # ------------------------------------------------------------------

    def _advance_frame(self) -> None:
        if self._current_frame >= self._total_frames:
            self._current_frame = 0
            self.stop()
            self.playback_finished.emit()
            return
        self._show_frame(self._current_frame)
        self._current_frame += 1
        self._update_time_ui()

    def _show_frame(self, index: int) -> None:
        if 0 <= index < len(self._frame_paths):
            px = QPixmap(self._frame_paths[index])
            if not px.isNull():
                scaled = px.scaled(
                    self._display.size(),
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation,
                )
                self._display.setPixmap(scaled)

    def _update_time_ui(self) -> None:
        current_sec = self._current_frame / self._fps if self._fps else 0
        self._time_lbl.setText(_fmt_time(current_sec))
        if self._total_frames > 0:
            self._seek_slider.setValue(int(self._current_frame / self._total_frames * 1000))

    def _on_seek(self, slider_value: int) -> None:
        if self._total_frames > 0:
            self._current_frame = min(self._total_frames - 1, int(slider_value / 1000 * self._total_frames))
            self._show_frame(self._current_frame)
            self._update_time_ui()
            if self._audio_player is not None:
                try:
                    pos_ms = int((self._current_frame / max(1.0, self._fps)) * 1000)
                    self._audio_player.setPosition(pos_ms)
                except Exception:
                    pass

    # ------------------------------------------------------------------
    # Action slots
    # ------------------------------------------------------------------

    def _toggle_play(self) -> None:
        if self._playing:
            self.pause()
        else:
            self.play()

    def _open_in_explorer(self) -> None:
        if self._video_path and os.path.isfile(self._video_path):
            subprocess.Popen(["explorer", "/select,", os.path.normpath(self._video_path)])

    def _export_copy(self) -> None:
        if not self._video_path:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Export Video Copy",
            os.path.basename(self._video_path),
            "MP4 Video (*.mp4);;All Files (*)",
        )
        if dest:
            try:
                shutil.copy2(self._video_path, dest)
                QMessageBox.information(self, "Exported", f"Saved to:\n{dest}")
            except OSError as exc:
                QMessageBox.warning(self, "Export Failed", str(exc))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_video(self, path: str) -> None:
        """Load a video file and extract preview frames."""
        self.stop()
        self._video_path = path
        self._duration = _get_video_duration(path, self._ffmpeg)
        self._total_lbl.setText(_fmt_time(self._duration))
        self._display.setText(f"Extracting preview frames…\n{os.path.basename(path)}")

        success = self._extract_frames()
        if success:
            if self._audio_player is not None and self._audio_wav_path and os.path.exists(self._audio_wav_path):
                try:
                    self._audio_player.setSource(QUrl.fromLocalFile(self._audio_wav_path))
                except Exception:
                    pass
            self._show_frame(0)
            self._seek_slider.setEnabled(True)
            self._play_btn.setEnabled(True)
            self._stop_btn.setEnabled(True)
            self._explorer_btn.setEnabled(True)
            self._export_btn.setEnabled(True)
            self._update_time_ui()
        else:
            if not self._ffmpeg:
                pass  # message already set
            else:
                self._display.setText("Failed to extract frames.")

    def play(self) -> None:
        if not self._frame_paths:
            return
        if self._current_frame >= self._total_frames:
            self._current_frame = 0
        self._playing = True
        interval_ms = max(1, int(1000 / self._fps))
        self._timer.start(interval_ms)
        self._play_btn.setText("⏸  Pause")
        self._stop_btn.setEnabled(True)
        if self._audio_player is not None and self._audio_wav_path and os.path.exists(self._audio_wav_path):
            try:
                pos_ms = int((self._current_frame / max(1.0, self._fps)) * 1000)
                self._audio_player.setPosition(pos_ms)
                self._audio_player.play()
                return
            except Exception:
                pass
        if self._current_frame == 0 and self._audio_wav_path and os.path.exists(self._audio_wav_path):
            try:
                import winsound
                winsound.PlaySound(self._audio_wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception:
                pass

    def pause(self) -> None:
        self._playing = False
        self._timer.stop()
        self._play_btn.setText("▶  Play")
        if self._audio_player is not None:
            try:
                self._audio_player.pause()
            except Exception:
                pass
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass

    def stop(self) -> None:
        self._playing = False
        self._timer.stop()
        if self._audio_player is not None:
            try:
                self._audio_player.stop()
                self._audio_player.setPosition(0)
            except Exception:
                pass
        try:
            import winsound
            winsound.PlaySound(None, 0)
        except Exception:
            pass
        self._current_frame = 0
        self._play_btn.setText("▶  Play")
        if self._frame_paths:
            self._show_frame(0)
        self._seek_slider.setValue(0)
        self._time_lbl.setText("0:00")

    def get_current_time(self) -> float:
        return self._current_frame / self._fps if self._fps else 0.0

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._cleanup_temp()
        super().closeEvent(event)
