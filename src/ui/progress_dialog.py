"""
Progress Dialog - Displays generation pipeline progress with stage tracking,
animated spinner for the current stage, log details, and cancel support.
"""
from __future__ import annotations

from typing import Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

STAGES: list[str] = [
    "Understanding script",
    "Planning scenes",
    "Generating narration",
    "Mixing audio",
    "Creating animations",
    "Adding captions",
    "Rendering video",
    "Validating output",
    "Complete",
]

SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


class StageRow(QWidget):
    """Single row in the stage list."""

    def __init__(self, stage_name: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._stage_name = stage_name
        self._state: str = "pending"   # pending | active | done | error

        h = QHBoxLayout(self)
        h.setContentsMargins(8, 4, 8, 4)
        h.setSpacing(10)

        self._icon_lbl = QLabel("○")
        self._icon_lbl.setFont(QFont("Segoe UI", 13))
        self._icon_lbl.setFixedWidth(22)
        self._icon_lbl.setAlignment(Qt.AlignCenter)
        h.addWidget(self._icon_lbl)

        self._name_lbl = QLabel(stage_name)
        self._name_lbl.setFont(QFont("Segoe UI", 11))
        h.addWidget(self._name_lbl, stretch=1)

        self._refresh_style()

    # ------------------------------------------------------------------
    def set_state(self, state: str, spinner_frame: str = "⠋") -> None:
        """state: 'pending' | 'active' | 'done' | 'error'"""
        self._state = state
        if state == "done":
            self._icon_lbl.setText("✓")
        elif state == "active":
            self._icon_lbl.setText(spinner_frame)
        elif state == "error":
            self._icon_lbl.setText("✗")
        else:
            self._icon_lbl.setText("○")
        self._refresh_style()

    def update_spinner(self, frame: str) -> None:
        if self._state == "active":
            self._icon_lbl.setText(frame)

    def _refresh_style(self) -> None:
        colours = {
            "done":    ("#4CAF50", "#c8e6c9"),
            "active":  ("#4FC3F7", "#e1f5fe"),
            "error":   ("#e94560", "#ffcdd2"),
            "pending": ("#555555", "#888888"),
        }
        icon_color, text_color = colours.get(self._state, ("#555555", "#888888"))
        self._icon_lbl.setStyleSheet(f"color: {icon_color};")
        self._name_lbl.setStyleSheet(f"color: {text_color};")


class ProgressDialog(QDialog):
    """Modal dialog tracking multi-stage video generation progress."""

    cancel_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Generating Video…")
        self.setMinimumWidth(480)
        self.setMinimumHeight(400)
        self.setModal(True)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setStyleSheet(
            "QDialog { background: #1a1a2e; color: #e8e8e8; }"
            "QLabel { color: #e8e8e8; background: transparent; }"
            "QPushButton { background: #0f3460; color: white; border: none; border-radius: 6px; padding: 8px 16px; }"
            "QPushButton:hover { background: #1a4a8a; }"
            "QProgressBar { background: #0d1b2a; border: none; border-radius: 4px; height: 10px; }"
            "QProgressBar::chunk { background: #e94560; border-radius: 4px; }"
            "QPlainTextEdit { background: #0d1b2a; color: #c0c0c0; border: 1px solid #0f3460; border-radius: 4px; font-family: Consolas; font-size: 11px; }"
            "QScrollArea { border: none; }"
        )

        self._current_stage_index: int = -1
        self._spinner_tick: int = 0
        self._stage_rows: dict[str, StageRow] = {}
        self._cancellable: bool = True

        self._setup_ui()
        self._spinner_timer = QTimer(self)
        self._spinner_timer.timeout.connect(self._tick_spinner)
        self._spinner_timer.start(80)

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setSpacing(12)
        root.setContentsMargins(20, 20, 20, 20)

        # Stage name (large, centered)
        self._stage_name_lbl = QLabel("Initialising…")
        self._stage_name_lbl.setAlignment(Qt.AlignCenter)
        self._stage_name_lbl.setFont(QFont("Segoe UI", 17, QFont.Bold))
        self._stage_name_lbl.setStyleSheet("color: #e94560;")
        root.addWidget(self._stage_name_lbl)

        # Progress bar
        self._progress_bar = QProgressBar()
        self._progress_bar.setRange(0, 100)
        self._progress_bar.setValue(0)
        self._progress_bar.setTextVisible(True)
        self._progress_bar.setFormat("%p%")
        root.addWidget(self._progress_bar)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("border: 1px solid #0f3460;")
        root.addWidget(sep)

        # Stage list
        stage_scroll = QScrollArea()
        stage_scroll.setWidgetResizable(True)
        stage_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        stage_scroll.setMaximumHeight(240)

        stage_container = QWidget()
        stage_container.setStyleSheet("background: #16213e; border-radius: 8px;")
        stage_v = QVBoxLayout(stage_container)
        stage_v.setSpacing(2)
        stage_v.setContentsMargins(4, 4, 4, 4)

        for stage in STAGES:
            row = StageRow(stage)
            self._stage_rows[stage] = row
            stage_v.addWidget(row)

        stage_scroll.setWidget(stage_container)
        root.addWidget(stage_scroll)

        # Details toggle + cancel row
        btn_row = QHBoxLayout()
        self._details_btn = QPushButton("▼ Show Details")
        self._details_btn.setCheckable(True)
        self._details_btn.setStyleSheet(
            "QPushButton { background: transparent; color: #4FC3F7; border: none; padding: 4px; }"
            "QPushButton:hover { color: #81D4FA; }"
        )
        self._details_btn.toggled.connect(self._toggle_details)
        btn_row.addWidget(self._details_btn)
        btn_row.addStretch()
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: #3a1a2e; color: #e94560; border: 1px solid #e94560; border-radius: 6px; padding: 8px 20px; }"
            "QPushButton:hover { background: #5a1a3e; }"
            "QPushButton:disabled { color: #555; border-color: #333; }"
        )
        self._cancel_btn.clicked.connect(self._on_cancel)
        btn_row.addWidget(self._cancel_btn)
        root.addLayout(btn_row)

        # Log area (hidden by default)
        self._log_area = QPlainTextEdit()
        self._log_area.setReadOnly(True)
        self._log_area.setMaximumBlockCount(2000)
        self._log_area.setFixedHeight(140)
        self._log_area.hide()
        root.addWidget(self._log_area)

    # ------------------------------------------------------------------
    def _tick_spinner(self) -> None:
        self._spinner_tick = (self._spinner_tick + 1) % len(SPINNER_FRAMES)
        frame = SPINNER_FRAMES[self._spinner_tick]
        for row in self._stage_rows.values():
            row.update_spinner(frame)

    # ------------------------------------------------------------------
    def _toggle_details(self, checked: bool) -> None:
        if checked:
            self._details_btn.setText("▲ Hide Details")
            self._log_area.show()
        else:
            self._details_btn.setText("▼ Show Details")
            self._log_area.hide()
        self.adjustSize()

    # ------------------------------------------------------------------
    def _on_cancel(self) -> None:
        if self._cancellable:
            self.cancel_requested.emit()
            self._cancel_btn.setEnabled(False)
            self._cancel_btn.setText("Cancelling…")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _normalize_stage(self, stage_name: str) -> str:
        s = stage_name.strip()
        if s in STAGES:
            return s
        low = s.lower().rstrip("….").strip()
        if any(k in low for k in ("understanding", "script")):
            return "Understanding script"
        if any(k in low for k in ("plan", "storyboard")):
            return "Planning scenes"
        if any(k in low for k in ("synthesiz", "voice", "narration")):
            return "Generating narration"
        if any(k in low for k in ("mix", "score", "ambient", "sfx")):
            return "Mixing audio"
        if any(k in low for k in ("art", "illustrat", "animat", "sprite", "scene")):
            return "Creating animations"
        if any(k in low for k in ("caption", "subtitle", "manifest")):
            return "Adding captions"
        if any(k in low for k in ("render", "encod", "autopilot", "ffmpeg", "preview sample", "cinematic video")):
            return "Rendering video"
        if any(k in low for k in ("validat", "qc", "check", "inspect")):
            return "Validating output"
        if any(k in low for k in ("complete", "done", "finish")):
            return "Complete"
        return s

    def update_stage(self, stage_name: str, percentage: int) -> None:
        """Move progress to stage_name at the given percentage."""
        canonical = self._normalize_stage(stage_name)
        self._stage_name_lbl.setText(stage_name)
        self._progress_bar.setValue(max(0, min(100, percentage)))

        target_idx = STAGES.index(canonical) if canonical in STAGES else -1
        if target_idx != -1:
            self._current_stage_index = target_idx

        for idx, name in enumerate(STAGES):
            row = self._stage_rows.get(name)
            if not row:
                continue
            if idx == self._current_stage_index:
                row.set_state("active")
            elif idx < self._current_stage_index:
                row.set_state("done")
            else:
                row.set_state("pending")

    def add_log(self, message: str) -> None:
        """Append a log line."""
        self._log_area.appendPlainText(message)
        # Scroll to bottom
        sb = self._log_area.verticalScrollBar()
        sb.setValue(sb.maximum())

    def set_cancellable(self, enabled: bool) -> None:
        self._cancellable = enabled
        self._cancel_btn.setEnabled(enabled)

    def mark_complete(self, success: bool, output_path: str = "") -> None:
        """Call when generation finishes."""
        self._spinner_timer.stop()
        self._progress_bar.setValue(100)

        if success:
            self._stage_name_lbl.setText("✓ Complete!")
            self._stage_name_lbl.setStyleSheet("color: #4CAF50; font-size: 20px; font-weight: bold;")
            for row in self._stage_rows.values():
                row.set_state("done")
            if output_path:
                self.add_log(f"Output saved: {output_path}")
        else:
            self._stage_name_lbl.setText("✗ Generation Failed")
            self._stage_name_lbl.setStyleSheet("color: #e94560; font-size: 20px; font-weight: bold;")
            # Mark current stage as error
            if 0 <= self._current_stage_index < len(STAGES):
                self._stage_rows[STAGES[self._current_stage_index]].set_state("error")

        self._cancel_btn.setText("Close")
        self._cancel_btn.setEnabled(True)
        self._cancel_btn.setStyleSheet(
            "QPushButton { background: #0f3460; color: white; border: none; border-radius: 6px; padding: 8px 20px; }"
            "QPushButton:hover { background: #1a4a8a; }"
        )
        # Reconnect close behaviour
        try:
            self._cancel_btn.clicked.disconnect()
        except RuntimeError:
            pass
        self._cancel_btn.clicked.connect(self.accept)
