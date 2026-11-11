"""
Main Window - Primary application window for Stickman Studio.
Clean, modern, dark-themed UI optimized for one-click offline video creation.
"""
from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QColorDialog,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.scene_planner import ScenePlanner
from styles.style_packs import resolve_style_pack
from ui.preview_player import PreviewPlayer
from ui.progress_dialog import ProgressDialog
from ui.settings_dialog import SettingsDialog
from ui.style_cards import StyleSelector
from ui.voice_panel import VoicePanel
from utils.system_info import get_system_summary

logger = logging.getLogger(__name__)

PREMIUM_STYLESHEET = """
/* ── Base ── */
QMainWindow { background: #0F1117; }
QWidget {
    background: #0F1117;
    color: #E6EDF3;
    font-family: 'Segoe UI';
    font-size: 13px;
}

/* ── Cards / Frames ── */
QFrame#card {
    background: #1C2333;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 14px;
}

/* ── Buttons – default ── */
QPushButton {
    background: #21262D;
    color: #C9D1D9;
    border: 1px solid #30363D;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background: #2D333B;
    border-color: #58A6FF;
    color: #E6EDF3;
}
QPushButton:pressed { background: #161B22; }
QPushButton:disabled { background: #161B22; color: #484F58; border-color: #21262D; }

/* ── Primary CTA ── */
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C3AED, stop:1 #6D28D9);
    color: white;
    border: none;
    border-radius: 10px;
    padding: 14px 28px;
    font-size: 15px;
    font-weight: bold;
    min-height: 52px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8B5CF6, stop:1 #7C3AED);
}
QPushButton#primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6D28D9, stop:1 #5B21B6);
}
QPushButton#primary:disabled {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #3D2065, stop:1 #2D1B4E);
    color: #7B72A8;
}

/* ── Secondary ── */
QPushButton#secondary {
    background: #161B22;
    border: 1px solid #06B6D4;
    color: #06B6D4;
    font-weight: bold;
    padding: 10px 18px;
    border-radius: 8px;
}
QPushButton#secondary:hover {
    background: #0D2030;
    border-color: #22D3EE;
    color: #22D3EE;
}

/* ── Pill Toggle buttons ── */
QPushButton#pill {
    background: #1C2333;
    color: #8B949E;
    border: 1px solid #30363D;
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton#pill:hover { background: #2D333B; color: #C9D1D9; }
QPushButton#pill:checked {
    background: #7C3AED;
    color: white;
    border-color: #7C3AED;
    font-weight: bold;
}

/* ── Inputs ── */
QTextEdit, QLineEdit, QSpinBox {
    background: #0D1117;
    border: 1px solid #30363D;
    border-radius: 8px;
    color: #E6EDF3;
    padding: 10px;
    selection-background-color: #7C3AED;
}
QTextEdit:focus, QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #7C3AED;
    background: #0D1117;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #21262D;
    border: none;
    width: 18px;
}

/* ── ComboBox ── */
QComboBox {
    background: #21262D;
    border: 1px solid #30363D;
    border-radius: 8px;
    color: #E6EDF3;
    padding: 7px 12px;
}
QComboBox:hover { border-color: #58A6FF; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background: #161B22;
    color: #E6EDF3;
    border: 1px solid #30363D;
    border-radius: 6px;
    selection-background-color: #7C3AED;
    outline: none;
}

/* ── Sliders ── */
QSlider::groove:horizontal {
    background: #21262D;
    height: 5px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #7C3AED;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
    border: 2px solid #A78BFA;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C3AED, stop:1 #06B6D4);
    height: 5px;
    border-radius: 3px;
}

/* ── Labels ── */
QLabel#header {
    font-size: 22px;
    font-weight: bold;
    color: #E6EDF3;
}
QLabel#section {
    font-size: 13px;
    font-weight: bold;
    color: #06B6D4;
    margin-top: 6px;
}

/* ── Scroll ── */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #0D1117;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #30363D;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #484F58; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #30363D;
    background: #161B22;
    border-radius: 10px;
    padding: 8px;
}
QTabBar::tab {
    background: #0D1117;
    color: #8B949E;
    padding: 10px 20px;
    border-top-left-radius: 8px;
    border-top-right-radius: 8px;
    margin-right: 3px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #1C2333;
    color: #E6EDF3;
    border-bottom: 2px solid #7C3AED;
    font-weight: bold;
}
QTabBar::tab:hover:!selected { background: #161B22; color: #C9D1D9; }

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #30363D;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    color: #8B949E;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    color: #8B949E;
}

/* ── Radio Button (legacy, kept for compat) ── */
QRadioButton { color: #C9D1D9; spacing: 6px; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #30363D; }
QRadioButton::indicator:checked { background: #7C3AED; border-color: #7C3AED; }

/* ── Status Bar ── */
QStatusBar {
    background: #0D1117;
    color: #8B949E;
    border-top: 1px solid #21262D;
    font-size: 11px;
}

/* ── Splitter ── */
QSplitter::handle { background: #21262D; }
QSplitter::handle:hover { background: #7C3AED; }
"""


class GenerationThread(QThread):
    """Runs VideoPipeline.generate_video() in a background thread."""

    stage_updated = Signal(str, int)
    log_added = Signal(str)
    completed = Signal(bool, str)

    def __init__(self, pipeline, params: dict) -> None:
        super().__init__()
        self.pipeline = pipeline
        self.params = params

    def run(self) -> None:
        try:
            out = self.pipeline.generate_video(
                self.params,
                progress_callback=lambda stage, pct: self.stage_updated.emit(stage, pct),
                log_callback=lambda msg: self.log_added.emit(msg),
            )
            if out and os.path.exists(out):
                self.completed.emit(True, out)
            else:
                self.completed.emit(False, "")
        except Exception as exc:
            logger.exception("GenerationThread error: %s", exc)
            self.log_added.emit(f"Fatal error: {exc}")
            self.completed.emit(False, "")


class ScriptWorkerThread(QThread):
    """Runs LLM script generation / improvement / shortening without freezing UI."""

    finished_text = Signal(str)

    def __init__(self, fn) -> None:
        super().__init__()
        self.fn = fn

    def run(self) -> None:
        try:
            res = self.fn()
            self.finished_text.emit(res or "")
        except Exception as exc:
            logger.error("ScriptWorkerThread error: %s", exc)
            self.finished_text.emit("")


class MainWindow(QMainWindow):
    """Primary desktop interface for Stickman Studio."""

    def __init__(
        self,
        config_manager,
        llm_manager,
        tts_manager,
        pipeline,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.config = config_manager
        self.llm = llm_manager
        self.tts = tts_manager
        self.pipeline = pipeline
        self.planner = ScenePlanner(llm_manager)

        self._gen_thread: Optional[GenerationThread] = None
        self._script_thread: Optional[ScriptWorkerThread] = None
        self._progress_dlg: Optional[ProgressDialog] = None
        self._custom_music_path: str = ""
        self._highlight_color: str = str(self.config.get("caption_highlight_color", ""))
        self._last_params: Optional[dict] = None
        self._last_output_path: str = ""
        self._projects_dir = Path("projects")
        self._projects_dir.mkdir(parents=True, exist_ok=True)

        self.setWindowTitle("Stickman Studio • Created by Atharv Hatwar")
        self.setMinimumSize(1100, 780)
        self.setStyleSheet(PREMIUM_STYLESHEET)

        self._setup_ui()
        self._connect_signals()
        self._populate_voices()
        self._load_settings()
        self._refresh_recent_projects()
        self._check_ollama_status()

        # Refresh status periodically without blocking UI
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_ollama_status)
        self._status_timer.start(30000)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _make_section_header(self, text: str, color: str = "#06B6D4") -> QWidget:
        """Return a QWidget with a 3px colored left bar + bold section label."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 6, 0, 2)
        h.setSpacing(8)

        bar = QFrame()
        bar.setFixedSize(3, 20)
        bar.setStyleSheet(f"background: {color}; border-radius: 1px;")
        h.addWidget(bar)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {color}; font-size: 13px; font-weight: bold; background: transparent;"
        )
        h.addWidget(lbl)
        h.addStretch()
        return container

    def _setup_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 8)
        root.setSpacing(10)

        # ---- Top Header Bar ----
        header_row = QHBoxLayout()
        title_lbl = QLabel("🎬  Stickman Studio")
        title_lbl.setObjectName("header")
        header_row.addWidget(title_lbl)

        creator_badge = QLabel("Created by Atharv Hatwar")
        creator_badge.setStyleSheet(
            "background: #1C2333; color: #A78BFA; border: 1px solid #7C3AED; "
            "border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;"
        )
        header_row.addWidget(creator_badge)

        badge = QLabel("100% Local  •  No Cloud  •  Free")
        badge.setStyleSheet(
            "background: #161B22; color: #06B6D4; border: 1px solid #30363D; "
            "border-radius: 12px; padding: 4px 14px; font-size: 11px;"
        )
        header_row.addWidget(badge)
        header_row.addStretch()

        header_row.addWidget(QLabel("Recent:"))
        self._recent_combo = QComboBox()
        self._recent_combo.setMinimumWidth(200)
        self._recent_combo.addItem("— Select recent project —", "")
        header_row.addWidget(self._recent_combo)

        self._settings_btn = QPushButton("⚙️  Settings")
        header_row.addWidget(self._settings_btn)

        self._about_btn = QPushButton("ℹ️  About")
        self._about_btn.setStyleSheet(
            "QPushButton { background: #1C2333; color: #A78BFA; border: 1px solid #7C3AED; "
            "border-radius: 6px; padding: 6px 12px; font-weight: bold; } "
            "QPushButton:hover { background: #7C3AED; color: white; }"
        )
        self._about_btn.clicked.connect(self._show_about_dialog)
        header_row.addWidget(self._about_btn)

        root.addLayout(header_row)

        # Thin separator
        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setStyleSheet("color: #21262D; background: #21262D; max-height: 1px;")
        root.addWidget(sep)

        # ---- Main Split Body ----
        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(5)

        # Left Panel (Scrollable Creation Controls)
        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(370)
        left_scroll.setMaximumWidth(460)

        left_card = QFrame()
        left_card.setObjectName("card")
        lv = QVBoxLayout(left_card)
        lv.setSpacing(10)
        lv.setContentsMargins(14, 14, 14, 14)

        # 1. Topic
        lv.addWidget(self._make_section_header("1. Topic"))
        self._topic_edit = QLineEdit()
        self._topic_edit.setPlaceholderText("e.g., Why giving with control changes people…")
        lv.addWidget(self._topic_edit)

        # 2. Script
        lv.addWidget(self._make_section_header("2. Script"))

        # Hidden radio button for script mode compatibility (defaults to clean 'use_as_is')
        self._mode_as_is = QRadioButton("Use my script")
        self._mode_improve = QRadioButton("Improve")
        self._mode_auto = QRadioButton("Auto-generate")
        self._mode_as_is.setChecked(True)
        _compat_group = QButtonGroup(self)
        _compat_group.addButton(self._mode_as_is)
        _compat_group.addButton(self._mode_improve)
        _compat_group.addButton(self._mode_auto)
        self._mode_as_is.hide()
        self._mode_improve.hide()
        self._mode_auto.hide()
        lv.addWidget(self._mode_as_is)
        lv.addWidget(self._mode_improve)
        lv.addWidget(self._mode_auto)

        self._script_edit = QTextEdit()
        self._script_edit.setMinimumHeight(155)
        self._script_edit.setPlaceholderText(
            "Paste or write your video narration script here…"
        )
        lv.addWidget(self._script_edit)

        self._script_meter_lbl = QLabel("0 words  •  ~0s spoken")
        self._script_meter_lbl.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
        lv.addWidget(self._script_meter_lbl)

        # Script length warning + Shorten offer
        warn_row = QHBoxLayout()
        self._script_warn_lbl = QLabel("")
        self._script_warn_lbl.setWordWrap(True)
        self._script_warn_lbl.setStyleSheet(
            "color: #F59E0B; font-size: 11px; background: #1C1A0A; "
            "border: 1px solid #78350F; border-radius: 6px; padding: 6px; "
        )
        self._script_warn_lbl.hide()
        warn_row.addWidget(self._script_warn_lbl, stretch=1)
        self._shorten_btn = QPushButton("✂ Shorten")
        self._shorten_btn.setStyleSheet(
            "background: #78350F; color: #FDE68A; border: 1px solid #92400E; "
            "padding: 6px 12px; font-size: 11px; border-radius: 6px;"
        )
        self._shorten_btn.hide()
        warn_row.addWidget(self._shorten_btn)
        lv.addLayout(warn_row)

        # 3. Duration & Format
        lv.addWidget(self._make_section_header("3. Duration & Format"))

        dur_grid = QGridLayout()
        dur_grid.setSpacing(8)
        dur_lbl = QLabel("Duration:")
        dur_lbl.setStyleSheet("color: #8B949E; font-size: 12px; background: transparent;")
        dur_grid.addWidget(dur_lbl, 0, 0)
        self._duration_combo = QComboBox()
        self._duration_combo.addItem("15 seconds", 15)
        self._duration_combo.addItem("30 seconds", 30)
        self._duration_combo.addItem("45 seconds", 45)
        self._duration_combo.addItem("60 seconds", 60)
        self._duration_combo.addItem("90 seconds", 90)
        self._duration_combo.addItem("Custom…", -1)
        self._duration_combo.setCurrentIndex(1)  # 30s default
        dur_grid.addWidget(self._duration_combo, 0, 1)

        self._custom_dur_spin = QSpinBox()
        self._custom_dur_spin.setRange(5, 300)
        self._custom_dur_spin.setValue(30)
        self._custom_dur_spin.setSuffix(" s")
        self._custom_dur_spin.hide()
        dur_grid.addWidget(self._custom_dur_spin, 0, 2)

        fmt_lbl = QLabel("Format:")
        fmt_lbl.setStyleSheet("color: #8B949E; font-size: 12px; background: transparent;")
        dur_grid.addWidget(fmt_lbl, 1, 0)
        self._format_combo = QComboBox()
        self._format_combo.addItem("9:16  (Instagram Reels / Shorts)", "9:16")
        self._format_combo.addItem("16:9  (Landscape YouTube)", "16:9")
        self._format_combo.addItem("1:1   (Square)", "1:1")
        dur_grid.addWidget(self._format_combo, 1, 1, 1, 2)

        exp_lbl = QLabel("Export:")
        exp_lbl.setStyleSheet("color: #8B949E; font-size: 12px; background: transparent;")
        dur_grid.addWidget(exp_lbl, 2, 0)
        self._res_combo = QComboBox()
        self._res_combo.addItem("1080p (Full HD)", "1080")
        self._res_combo.addItem("720p  (Lightweight)", "720")
        dur_grid.addWidget(self._res_combo, 2, 1)

        self._fps_combo = QComboBox()
        self._fps_combo.addItem("24 FPS", 24)
        self._fps_combo.addItem("30 FPS", 30)
        dur_grid.addWidget(self._fps_combo, 2, 2)

        bg_ai_lbl = QLabel("Background AI:")
        bg_ai_lbl.setStyleSheet("color: #8B949E; font-size: 12px; background: transparent;")
        dur_grid.addWidget(bg_ai_lbl, 3, 0)
        self._bg_engine_combo = QComboBox()
        self._bg_engine_combo.addItem("🎨 Procedural Vector AI (Instant • 0% CPU)", "procedural")
        self._bg_engine_combo.addItem("✨ LCM DreamShaper AI (Cinematic Diffusion)", "lcm")
        dur_grid.addWidget(self._bg_engine_combo, 3, 1, 1, 2)
        lv.addLayout(dur_grid)

        lv.addStretch()

        # Primary CTA Buttons
        self._preview_render_btn = QPushButton("⚡  Fast Low-Res Preview")
        self._preview_render_btn.setObjectName("secondary")
        lv.addWidget(self._preview_render_btn)

        self._generate_btn = QPushButton("🎬  Generate Video")
        self._generate_btn.setObjectName("primary")
        lv.addWidget(self._generate_btn)

        left_scroll.setWidget(left_card)
        splitter.addWidget(left_scroll)

        # ---- Right Panel (Tabs) ----
        self._tabs = QTabWidget()

        # Tab 1: Style cards
        self._style_selector = StyleSelector()
        self._tabs.addTab(self._style_selector, "🎨  Animation Style")

        # Tab 2: Voice selection
        self._voice_panel = VoicePanel()
        self._tabs.addTab(self._voice_panel, "🎙️  Voice & Speech")

        # Tab 3: Audio & Captions
        self._tabs.addTab(self._build_audio_captions_tab(), "🎵  Audio & Captions")

        # Tab 4: Preview & Export
        preview_tab = QWidget()
        pt_v = QVBoxLayout(preview_tab)
        pt_v.setContentsMargins(6, 6, 6, 6)
        self._preview_player = PreviewPlayer(ffmpeg_path=getattr(self.pipeline, "ffmpeg_path", None))
        pt_v.addWidget(self._preview_player, stretch=1)

        regen_row = QHBoxLayout()
        self._output_path_lbl = QLabel("Ready — click Generate Video to create an MP4.")
        self._output_path_lbl.setStyleSheet(
            "color: #8B949E; font-size: 11px; background: transparent;"
        )
        regen_row.addWidget(self._output_path_lbl, stretch=1)
        self._regen_btn = QPushButton("🔄  Regenerate")
        self._regen_btn.setEnabled(False)
        regen_row.addWidget(self._regen_btn)
        pt_v.addLayout(regen_row)
        self._tabs.addTab(preview_tab, "▶  Preview & Export")

        splitter.addWidget(self._tabs)
        splitter.setSizes([400, 800])
        root.addWidget(splitter, stretch=1)

        # Status Bar
        self._status_bar = QStatusBar()
        self._status_bar.setStyleSheet(
            "background: #0D1117; border-top: 1px solid #21262D; color: #8B949E; font-size: 11px;"
        )
        self.setStatusBar(self._status_bar)

    def _build_audio_captions_tab(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        inner = QWidget()
        v = QVBoxLayout(inner)
        v.setSpacing(14)

        # ---- Music & Mixing Group ----
        music_grp = QGroupBox("Background Music & Sound Mixing (100% Royalty-Free Local Audio)")
        mg = QVBoxLayout(music_grp)
        mg.setSpacing(10)

        m_row = QHBoxLayout()
        ml = QLabel("Music Style:")
        ml.setStyleSheet("color: #8B949E; font-size: 12px;")
        m_row.addWidget(ml)
        self._music_combo = QComboBox()
        self._music_combo.addItem("Auto (Match Animation Style)", "auto")
        self._music_combo.addItem("None", "none")
        self._music_combo.addItem("Calm Background", "calm")
        self._music_combo.addItem("Cozy Lo-Fi Rhodes", "lofi")
        self._music_combo.addItem("Feudal Pentatonic", "feudal")
        self._music_combo.addItem("Tribal Cave Pulse", "tribal")
        self._music_combo.addItem("Noir Jazz", "noir_jazz")
        self._music_combo.addItem("Dark Ambient", "dark_ambient")
        self._music_combo.addItem("Emotional", "emotional")
        self._music_combo.addItem("Tension", "tension")
        self._music_combo.addItem("Energetic", "energetic")
        self._music_combo.addItem("Custom MP3 / WAV File…", "custom")
        self._music_combo.setCurrentIndex(0)
        m_row.addWidget(self._music_combo, stretch=1)

        self._import_music_btn = QPushButton("📂 Import Audio")
        self._import_music_btn.hide()
        m_row.addWidget(self._import_music_btn)
        mg.addLayout(m_row)

        self._custom_music_lbl = QLabel("")
        self._custom_music_lbl.setStyleSheet(
            "color: #06B6D4; font-size: 11px; background: transparent;"
        )
        self._custom_music_lbl.hide()
        mg.addWidget(self._custom_music_lbl)

        # Sliders for voice, music, sfx, fade-in, fade-out
        self._voice_vol_slider, _ = self._add_labeled_slider(mg, "Voice Volume", 20, 150, 100, "{}%")
        self._music_vol_slider, _ = self._add_labeled_slider(mg, "Music Volume", 0, 100, 25, "{}%")
        self._sfx_vol_slider, _   = self._add_labeled_slider(mg, "Sound Effects Volume", 0, 100, 65, "{}%")
        self._fade_in_slider, _   = self._add_labeled_slider(mg, "Audio Fade-In", 0, 30, 5, lambda x: f"{x/10:.1f}s")
        self._fade_out_slider, _  = self._add_labeled_slider(mg, "Audio Fade-Out", 0, 30, 5, lambda x: f"{x/10:.1f}s")
        v.addWidget(music_grp)

        # ---- Captions Group ----
        cap_grp = QGroupBox("Captions & Subtitles (Instagram Safe Area)")
        cg = QGridLayout(cap_grp)
        cg.setSpacing(10)

        def _glbl(t: str) -> QLabel:
            l = QLabel(t)
            l.setStyleSheet("color: #8B949E; font-size: 12px;")
            return l

        cg.addWidget(_glbl("Caption Style:"), 0, 0)
        self._cap_style_combo = QComboBox()
        self._cap_style_combo.addItem("Bold Social Media", "bold_social")
        self._cap_style_combo.addItem("Word Highlight", "word_highlight")
        self._cap_style_combo.addItem("Karaoke Sweep", "karaoke")
        self._cap_style_combo.addItem("Normal Subtitles", "normal")
        self._cap_style_combo.addItem("Minimal Subtitles", "minimal")
        self._cap_style_combo.addItem("No Captions", "none")
        cg.addWidget(self._cap_style_combo, 0, 1)

        cg.addWidget(_glbl("Font:"), 1, 0)
        self._cap_font_combo = QComboBox()
        self._cap_font_combo.addItems(["Arial Bold", "Segoe UI Bold", "Verdana Bold", "Calibri Bold", "Tahoma"])
        cg.addWidget(self._cap_font_combo, 1, 1)

        cg.addWidget(_glbl("Font Size:"), 2, 0)
        self._cap_size_spin = QSpinBox()
        self._cap_size_spin.setRange(20, 72)
        self._cap_size_spin.setValue(38)
        self._cap_size_spin.setSuffix(" px")
        cg.addWidget(self._cap_size_spin, 2, 1)

        cg.addWidget(_glbl("Position:"), 3, 0)
        self._cap_pos_combo = QComboBox()
        self._cap_pos_combo.addItem("Auto (Smart Safe Position)", "auto")
        self._cap_pos_combo.addItem("Bottom (Safe Area)", "bottom")
        self._cap_pos_combo.addItem("Center", "center")
        self._cap_pos_combo.addItem("Top", "top")
        cg.addWidget(self._cap_pos_combo, 3, 1)

        cg.addWidget(_glbl("Highlight Color:"), 4, 0)
        hl_row = QHBoxLayout()
        self._cap_color_btn = QPushButton("Auto (Style Match)")
        self._cap_color_auto_btn = QPushButton("Reset Auto")
        self._cap_color_auto_btn.setFixedWidth(90)
        self._cap_color_auto_btn.clicked.connect(self._on_reset_highlight_color)
        hl_row.addWidget(self._cap_color_btn, stretch=1)
        hl_row.addWidget(self._cap_color_auto_btn)
        self._update_color_button()
        cg.addLayout(hl_row, 4, 1)

        v.addWidget(cap_grp)
        v.addStretch()
        scroll.setWidget(inner)
        return scroll

    @staticmethod
    def _add_labeled_slider(
        parent_layout: QVBoxLayout,
        title: str,
        minimum: int,
        maximum: int,
        default: int,
        fmt: Any,
    ) -> tuple[QSlider, QLabel]:
        row = QHBoxLayout()
        lbl = QLabel(title)
        lbl.setStyleSheet("color: #8B949E; font-size: 12px;")
        row.addWidget(lbl)
        fmt_fn = fmt if callable(fmt) else (lambda val, s=fmt: s.format(val))
        val_lbl = QLabel(fmt_fn(default))
        val_lbl.setFixedWidth(52)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        val_lbl.setStyleSheet("color: #E6EDF3; font-size: 12px;")
        row.addStretch()
        row.addWidget(val_lbl)
        parent_layout.addLayout(row)

        slider = QSlider(Qt.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(default)
        slider.valueChanged.connect(lambda val, lbl=val_lbl, fn=fmt_fn: lbl.setText(fn(val)))
        parent_layout.addWidget(slider)
        return slider, val_lbl

    # ------------------------------------------------------------------
    # Signals & Event Handlers
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self._duration_combo.currentIndexChanged.connect(self._on_duration_changed)
        self._custom_dur_spin.valueChanged.connect(self._check_script_length)
        self._script_edit.textChanged.connect(self._check_script_length)

        self._shorten_btn.clicked.connect(self._on_shorten_script_clicked)

        self._music_combo.currentIndexChanged.connect(self._on_music_changed)
        self._import_music_btn.clicked.connect(self._on_import_music)
        self._cap_color_btn.clicked.connect(self._on_pick_highlight_color)

        self._voice_panel.set_preview_callback(self._on_preview_voice)
        self._settings_btn.clicked.connect(self.show_settings)
        self._recent_combo.currentIndexChanged.connect(self._on_load_recent_project)

        self._preview_render_btn.clicked.connect(lambda: self._on_generate_clicked(preview_mode=True))
        self._generate_btn.clicked.connect(lambda: self._on_generate_clicked(preview_mode=False))
        self._regen_btn.clicked.connect(self._on_regenerate_clicked)

    def _populate_voices(self) -> None:
        voices = self.tts.get_available_voices()
        self._voice_panel.set_voices(voices)
        saved_voice = self.config.get("default_voice", "")
        if saved_voice:
            self._voice_panel.set_selected_voice(saved_voice)

    def _get_selected_duration(self) -> int:
        val = self._duration_combo.currentData()
        if val == -1:
            return self._custom_dur_spin.value()
        return int(val or 30)

    def _on_duration_changed(self) -> None:
        is_custom = self._duration_combo.currentData() == -1
        self._custom_dur_spin.setVisible(is_custom)
        self._check_script_length()

    def _check_script_length(self) -> None:
        text = self._script_edit.toPlainText().strip()
        target = self._get_selected_duration()
        if not text:
            self._script_meter_lbl.setText(f"0 words  •  Target: ~{int(target * 2.4)} words ({target}s)")
            self._script_meter_lbl.setStyleSheet("color: #8B949E; font-size: 11px; background: transparent;")
            self._script_warn_lbl.hide()
            self._shorten_btn.hide()
            return
        words = len(text.split())
        speed = self._voice_panel.get_voice_settings().get("speed", 1.0)
        est_sec = words / (2.4 * max(0.5, speed))

        if est_sec > target * 1.25:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken (Long for {target}s)")
            self._script_meter_lbl.setStyleSheet("color: #F59E0B; font-size: 11px; background: transparent;")
            self._script_warn_lbl.setText(
                f"⚠ Script is {words} words (~{est_sec:.0f}s) for a {target}s video. Offer to shorten?"
            )
            self._script_warn_lbl.show()
            self._shorten_btn.show()
        elif est_sec < target * 0.55 and target >= 15:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken (Short for {target}s — click Improve to expand)")
            self._script_meter_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; background: transparent;")
            self._script_warn_lbl.hide()
            self._shorten_btn.hide()
        else:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken  ✓ Fits {target}s cleanly")
            self._script_meter_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: transparent;")
            self._script_warn_lbl.hide()
            self._shorten_btn.hide()

    def _on_music_changed(self) -> None:
        is_custom = self._music_combo.currentData() == "custom"
        self._import_music_btn.setVisible(is_custom)
        self._custom_music_lbl.setVisible(is_custom and bool(self._custom_music_path))

    def _on_import_music(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Background Music",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.m4a);;All Files (*)",
        )
        if path:
            self._custom_music_path = path
            self._custom_music_lbl.setText(f"Selected: {os.path.basename(path)}")
            self._custom_music_lbl.show()

    def _on_pick_highlight_color(self) -> None:
        initial = QColor(self._highlight_color or "#FFD700")
        col = QColorDialog.getColor(initial, self, "Select Highlight Color")
        if col.isValid():
            self._highlight_color = col.name().upper()
            self._update_color_button()

    def _on_reset_highlight_color(self) -> None:
        self._highlight_color = ""
        self._update_color_button()

    def _update_color_button(self) -> None:
        if not self._highlight_color:
            self._cap_color_btn.setText("🎨  Auto (Style Match)")
            self._cap_color_btn.setStyleSheet(
                "background: #21262D; color: #06B6D4; font-weight: bold; "
                "border: 1px solid #30363D; border-radius: 8px;"
            )
        else:
            self._cap_color_btn.setText(f"■  {self._highlight_color}")
            self._cap_color_btn.setStyleSheet(
                f"background: #21262D; color: {self._highlight_color}; font-weight: bold; "
                "border: 1px solid #30363D; border-radius: 8px;"
            )

    def _on_preview_voice(self, voice_id: str, preview_text: str) -> None:
        vs = self._voice_panel.get_voice_settings()
        wav_path = self.tts.preview_voice(
            voice_id=voice_id,
            text=preview_text,
            speed=vs.get("speed", 1.0),
            pitch=vs.get("pitch", 0.0),
        )
        if wav_path and os.path.exists(wav_path):
            try:
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as exc:
                logger.warning("Could not play preview audio: %s", exc)
        else:
            QMessageBox.warning(self, "Preview Failed", "Could not synthesize voice preview.")

    # ------------------------------------------------------------------
    # Script AI Helpers
    # ------------------------------------------------------------------

    def _script_busy(self) -> bool:
        return self._script_thread is not None and self._script_thread.isRunning()

    def _on_generate_script_clicked(self) -> None:
        if self._script_busy():
            return
        topic = self._topic_edit.text().strip()
        if not topic:
            QMessageBox.information(self, "Enter Topic", "Please enter a video topic first.")
            return
        dur = self._get_selected_duration()
        style = self._style_selector.get_selected_style()

        self._script_thread = ScriptWorkerThread(
            lambda: self.planner.generate_script(topic=topic, duration=dur, style=style)
        )
        self._script_thread.finished_text.connect(self._on_script_ready_gen)
        self._script_thread.start()

    def _on_script_ready_gen(self, text: str) -> None:
        if text:
            self._script_edit.setPlainText(text)
            self._mode_as_is.setChecked(True)

    def _on_improve_script_clicked(self) -> None:
        if self._script_busy():
            return
        script = self._script_edit.toPlainText().strip()
        if not script:
            QMessageBox.information(self, "No Script", "Paste a script first or generate one from topic.")
            return
        topic = self._topic_edit.text().strip()
        dur = self._get_selected_duration()
        style = self._style_selector.get_selected_style()

        self._script_thread = ScriptWorkerThread(
            lambda: self.planner.improve_script(script=script, topic=topic, style=style, duration=dur)
        )
        self._script_thread.finished_text.connect(self._on_script_ready_imp)
        self._script_thread.start()

    def _on_script_ready_imp(self, text: str) -> None:
        if text:
            self._script_edit.setPlainText(text)

    def _on_shorten_script_clicked(self) -> None:
        if self._script_busy():
            return
        script = self._script_edit.toPlainText().strip()
        if not script:
            return
        topic = self._topic_edit.text().strip()
        dur = self._get_selected_duration()
        style = self._style_selector.get_selected_style()
        self._shorten_btn.setEnabled(False)
        self._script_thread = ScriptWorkerThread(
            lambda: self.planner.shorten_script(script=script, target_duration=dur, topic=topic, style=style)
        )
        self._script_thread.finished_text.connect(self._on_script_shortened)
        self._script_thread.start()

    def _on_script_shortened(self, text: str) -> None:
        self._shorten_btn.setEnabled(True)
        if text:
            self._script_edit.setPlainText(text)

    # ------------------------------------------------------------------
    # Video Generation
    # ------------------------------------------------------------------

    def _validate_inputs(self) -> tuple[bool, str]:
        topic = self._topic_edit.text().strip()
        script = self._script_edit.toPlainText().strip()
        if not topic and not script:
            return False, "Please enter a topic or paste a script."
        if not script and not self._mode_auto.isChecked():
            return False, "Please paste a script or choose 'Auto-generate' mode."
        if self._music_combo.currentData() == "custom" and not self._custom_music_path:
            return False, "You selected Custom music — please import an MP3/WAV file or choose another music style."
        return True, ""

    def _collect_params(self, preview_mode: bool = False) -> dict:
        vs = self._voice_panel.get_voice_settings()
        if self._mode_auto.isChecked():
            script_mode = "auto_generate"
        elif self._mode_improve.isChecked():
            script_mode = "improve"
        else:
            script_mode = "use_as_is"

        voice_vol = (self._voice_vol_slider.value() / 100.0) * (vs.get("volume", 100) / 100.0)
        sel_style = self._style_selector.get_selected_style()
        sel_variant = self._style_selector.get_selected_variant()
        pack, _ = resolve_style_pack(sel_style, sel_variant or None)
        raw_music = self._music_combo.currentData() or "auto"
        eff_music = pack.preferred_music if raw_music == "auto" else raw_music

        return {
            "topic": self._topic_edit.text().strip() or "Stickman Story",
            "script": self._script_edit.toPlainText().strip(),
            "script_mode": script_mode,
            "duration": self._get_selected_duration(),
            "style": sel_style,
            "style_variant": sel_variant,
            "voice_id": vs.get("voice_id", ""),
            "voice_speed": vs.get("speed", 1.0),
            "voice_pitch": vs.get("pitch", 0.0),
            "format": self._format_combo.currentData() or "9:16",
            "resolution": self._res_combo.currentData() or "1080",
            "fps": int(self._fps_combo.currentData() or 24),
            "use_lcm": self._bg_engine_combo.currentData() == "lcm",
            "preview_mode": preview_mode,
            "use_hardware_encoding": bool(self.config.get("use_hardware_encoding", True)),
            "unload_llm": bool(self.config.get("unload_llm_after_planning", True)),
            "music_style": eff_music,
            "custom_music_path": self._custom_music_path,
            "voice_volume": voice_vol,
            "music_volume": self._music_vol_slider.value() / 100.0,
            "sfx_volume": self._sfx_vol_slider.value() / 100.0,
            "fade_in": self._fade_in_slider.value() / 10.0,
            "fade_out": self._fade_out_slider.value() / 10.0,
            "caption_style": self._cap_style_combo.currentData() or "bold_social",
            "caption_font_name": self._cap_font_combo.currentText(),
            "caption_font_size": self._cap_size_spin.value(),
            "caption_position": self._cap_pos_combo.currentData() or "auto",
            "caption_highlight_color": self._highlight_color,
        }

    def _on_generate_clicked(self, preview_mode: bool = False) -> None:
        valid, err = self._validate_inputs()
        if not valid:
            QMessageBox.warning(self, "Missing Input", err)
            return

        # Warn cleanly if script is significantly longer than chosen duration
        if not preview_mode and self._script_warn_lbl.isVisible():
            resp = QMessageBox.question(
                self,
                "Script Longer Than Duration",
                self._script_warn_lbl.text() + "\n\nClick Yes to shorten automatically first, or No to keep full script and adjust pacing.",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel,
            )
            if resp == QMessageBox.Cancel:
                return
            if resp == QMessageBox.Yes:
                shortened = self.planner.shorten_script(
                    self._script_edit.toPlainText().strip(),
                    self._get_selected_duration(),
                    topic=self._topic_edit.text().strip(),
                    style=self._style_selector.get_selected_style(),
                )
                self._script_edit.setPlainText(shortened)

        params = self._collect_params(preview_mode=preview_mode)
        self._last_params = params
        self._save_settings()
        self._start_generation(params)

    def _on_regenerate_clicked(self) -> None:
        if self._last_params:
            params = self._collect_params(preview_mode=False)
            self._start_generation(params)

    def _start_generation(self, params: dict) -> None:
        self._preview_player.stop()
        self._generate_btn.setEnabled(False)
        self._generate_btn.setText("⏳  Generating…")
        self._preview_render_btn.setEnabled(False)

        self._progress_dlg = ProgressDialog(self)
        self._progress_dlg.setWindowTitle(
            "Rendering Fast Preview…" if params.get("preview_mode") else "Generating MP4 Video…"
        )
        self._progress_dlg.cancel_requested.connect(self.pipeline.cancel)

        self._gen_thread = GenerationThread(self.pipeline, params)
        self._gen_thread.stage_updated.connect(self._progress_dlg.update_stage)
        self._gen_thread.log_added.connect(self._progress_dlg.add_log)
        self._gen_thread.completed.connect(self._on_generation_complete)
        self._gen_thread.start()

        self._progress_dlg.exec()

    def _on_generation_complete(self, success: bool, output_path: str) -> None:
        self._generate_btn.setEnabled(True)
        self._generate_btn.setText("🎬  Generate Video")
        self._preview_render_btn.setEnabled(True)

        if self._progress_dlg:
            self._progress_dlg.mark_complete(success, output_path)

        if success and output_path:
            self._last_output_path = output_path
            self._regen_btn.setEnabled(True)
            if getattr(self.pipeline, "last_script_used", "") and not self._script_edit.toPlainText().strip():
                self._script_edit.setPlainText(self.pipeline.last_script_used)
            # Styled success path label
            fname = os.path.basename(output_path)
            self._output_path_lbl.setText(f"✅  Saved: {fname}")
            self._output_path_lbl.setStyleSheet(
                "color: #22C55E; font-size: 11px; background: #0D2010; "
                "border: 1px solid #166534; border-radius: 6px; padding: 4px 10px;"
            )
            self._output_path_lbl.setToolTip(output_path)
            self._preview_player.load_video(output_path)
            self._tabs.setCurrentIndex(3)  # Switch to Preview & Export tab

            if not (self._last_params or {}).get("preview_mode"):
                self._save_project_record(self._last_params or {}, output_path)

    # ------------------------------------------------------------------
    # Projects, Settings, Status
    # ------------------------------------------------------------------

    def _save_project_record(self, params: dict, output_path: str) -> None:
        try:
            self.config.add_recent_topic(params.get("topic", ""))
            if params.get("script"):
                self.config.add_recent_script(params["script"])
            stamp = int(time.time())
            proj = {
                "timestamp": stamp,
                "topic": params.get("topic", ""),
                "script": params.get("script", ""),
                "duration": params.get("duration", 30),
                "style": params.get("style", "s1_rsa_whiteboard"),
                "style_variant": params.get("style_variant", ""),
                "format": params.get("format", "9:16"),
                "voice_id": params.get("voice_id", ""),
                "output_path": output_path,
            }
            fname = self._projects_dir / f"project_{stamp}.json"
            with open(fname, "w", encoding="utf-8") as fh:
                json.dump(proj, fh, indent=2)
            self._refresh_recent_projects()
        except Exception as exc:
            logger.debug("Could not save project record: %s", exc)

    def _refresh_recent_projects(self) -> None:
        self._recent_combo.blockSignals(True)
        self._recent_combo.clear()
        self._recent_combo.addItem("— Select recent project —", "")
        files = sorted(self._projects_dir.glob("project_*.json"), reverse=True)[:12]
        for f in files:
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    data = json.load(fh)
                label = f"{data.get('topic', 'Untitled')[:28]} ({data.get('duration', 30)}s)"
                self._recent_combo.addItem(label, str(f))
            except Exception:
                continue
        self._recent_combo.blockSignals(False)

    def _on_load_recent_project(self, idx: int) -> None:
        path = self._recent_combo.itemData(idx)
        if not path or not os.path.exists(path):
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            self._topic_edit.setText(data.get("topic", ""))
            self._script_edit.setPlainText(data.get("script", ""))
            self._style_selector.set_selected_style(
                data.get("style", "s1_rsa_whiteboard"),
                variant=data.get("style_variant") or None,
            )
            if data.get("voice_id"):
                self._voice_panel.set_selected_voice(data["voice_id"])
            out = data.get("output_path", "")
            if out and os.path.exists(out):
                self._output_path_lbl.setText(f"Project video: {os.path.basename(out)}")
                self._output_path_lbl.setStyleSheet(
                    "color: #8B949E; font-size: 11px; background: transparent;"
                )
                self._output_path_lbl.setToolTip(out)
                self._preview_player.load_video(out)
        except Exception as exc:
            logger.warning("Failed to load recent project: %s", exc)

    def show_settings(self) -> None:
        dlg = SettingsDialog(self, llm_manager=self.llm, tts_manager=self.tts)
        dlg.voices_updated.connect(self._populate_voices)
        dlg.load_settings(self.config.get_all())
        if dlg.exec():
            updates = dlg.get_settings()
            self.config.update(updates)
            # Apply updated runtime config
            if updates.get("llm_model") == "auto":
                self.llm.default_model = self.llm.get_recommended_model()
            else:
                self.llm.default_model = updates.get("llm_model")
            self.llm.context_window = int(updates.get("llm_context_window", 2048))
            if updates.get("output_dir"):
                self.pipeline.output_dir = Path(self.config.get_output_dir())
            self._check_ollama_status()

    def _show_about_dialog(self) -> None:
        license_html = (
            "<div style='background:#0D1117; border:1px solid #30363D; border-radius:6px; padding:10px; margin-top:8px; font-size:11px; color:#C9D1D9; font-family:Consolas, monospace;'>"
            "<b style='color:#58A6FF;'>MIT License</b><br><br>"
            "Copyright (c) 2026 Atharv Hatwar<br><br>"
            "Permission is hereby granted, free of charge, to any person obtaining a copy "
            "of this software and associated documentation files (the 'Software'), to deal "
            "in the Software without restriction, including without limitation the rights "
            "to use, copy, modify, merge, publish, distribute, sublicense, and/or sell "
            "copies of the Software, and to permit persons to whom the Software is "
            "furnished to do so.<br><br>"
            "THE SOFTWARE IS PROVIDED 'AS IS', WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED.<br><br>"
            "<i style='color:#8B949E;'>Open Source • Released under the MIT License</i>"
            "</div>"
        )
        QMessageBox.about(
            self,
            "About Stickman Studio",
            "<h2 style='color:#A78BFA; margin-bottom:2px;'>🎬 Stickman Studio</h2>"
            "<p><b style='font-size:14px; color:#38BDF8;'>Created by Atharv Hatwar</b><br>"
            "<a style='color:#A78BFA;' href='https://github.com/atharv01h'>GitHub Profile (@atharv01h)</a> &bull; "
            "<a style='color:#38BDF8;' href='https://github.com/atharv01h/Stickman-Studio'>Repository</a></p>"
            "<p>A professional, 100% offline, local automated video generation suite.</p>"
            "<hr style='border:1px solid #30363D;'>"
            "<p><b>Core Capabilities:</b></p>"
            "<ul style='margin-left:-15px; color:#E2E8F0;'>"
            "<li><b>13 Style Packs</b> — S1-S6 Creator & S7-S13 Artistic & Storyteller</li>"
            "<li><b>Embedded In-Process AI Director</b> — Native Python scene planning (Zero Ollama required)</li>"
            "<li><b>Procedural Script-to-Scene Metaphor Engine</b> — Topic-aligned environments</li>"
            "<li><b>Dynamic Character & Animal Kinematics</b> — Real physics, props & pets</li>"
            "<li><b>AI Backgrounds & Objects</b> — Contextual scenery tailored to every script</li>"
            "<li><b>Smart Video Director</b> — Dynamic camera cuts, kinetic callouts & sound effects</li>"
            "<li><b>Local Neural Voices & Sound Stems</b> — Sidechain ducking & crisp audio</li>"
            "</ul>"
            + license_html
        )

    def _check_ollama_status(self) -> None:
        sys_info = get_system_summary()
        avail_ram_gb = sys_info["available_ram_mb"] / 1024.0
        total_ram_gb = sys_info["total_ram_mb"] / 1024.0
        free_vram_mb = sys_info["free_vram_mb"]

        if self.llm.check_ollama_running():
            model = self.llm.default_model or self.llm.get_recommended_model()
            loc = self.llm.get_model_run_location()
            ai_status = f"🟢 Ollama  {model} ({loc})"
        else:
            ai_status = "🟢 In-Process AI Director (Native Offline)"

        voices_cnt = len(self.tts.get_available_voices())
        langs = ",".join(self.tts.get_supported_languages())
        self._status_bar.showMessage(
            f"Stickman Studio • Atharv Hatwar  |  "
            f"RAM: {avail_ram_gb:.1f}/{total_ram_gb:.1f} GB free  |  "
            f"VRAM free: {free_vram_mb} MB  |  {ai_status}  |  "
            f"Voices: {voices_cnt} ({langs})"
        )

    def _load_settings(self) -> None:
        if self.config.get("last_topic"):
            self._topic_edit.setText(self.config.get("last_topic"))
        if self.config.get("last_script"):
            self._script_edit.setPlainText(self.config.get("last_script"))

        self._style_selector.set_selected_style(
            self.config.get("default_style", "s1_rsa_whiteboard"),
            variant=self.config.get("default_style_variant") or None,
        )
        vs_speed = float(self.config.get("default_speed", 1.0))
        vs_pitch = int(self.config.get("default_pitch", 0))
        vs_vol = int(self.config.get("default_tts_volume", 100))
        self._voice_panel.set_voice_settings(vs_speed, vs_pitch, vs_vol)

        saved_dur = int(self.config.get("default_duration", 30))
        matched_dur = False
        for i in range(self._duration_combo.count()):
            if self._duration_combo.itemData(i) == saved_dur:
                self._duration_combo.setCurrentIndex(i)
                matched_dur = True
                break
        if not matched_dur:
            self._duration_combo.setCurrentIndex(self._duration_combo.count() - 1)
            self._custom_dur_spin.setValue(saved_dur)
            self._custom_dur_spin.show()

        saved_fmt = self.config.get("default_format", "9:16")
        for i in range(self._format_combo.count()):
            if self._format_combo.itemData(i) == saved_fmt:
                self._format_combo.setCurrentIndex(i)
                break

        saved_res = self.config.get("default_resolution", "1080p")
        self._res_combo.setCurrentIndex(1 if "720" in str(saved_res) else 0)
        self._fps_combo.setCurrentIndex(1 if int(self.config.get("default_fps", 24)) == 30 else 0)

        saved_bg = self.config.get("default_bg_engine", "procedural")
        for i in range(self._bg_engine_combo.count()):
            if self._bg_engine_combo.itemData(i) == saved_bg:
                self._bg_engine_combo.setCurrentIndex(i)
                break

        saved_music = self.config.get("default_music_style", "auto")
        for i in range(self._music_combo.count()):
            if self._music_combo.itemData(i) == saved_music:
                self._music_combo.setCurrentIndex(i)
                break

        self._voice_vol_slider.setValue(int(self.config.get("default_voice_volume", 100)))
        self._music_vol_slider.setValue(int(self.config.get("default_music_volume", 25)))
        self._sfx_vol_slider.setValue(int(self.config.get("default_sfx_volume", 65)))
        self._fade_in_slider.setValue(int(self.config.get("audio_fade_in_ds", 5)))
        self._fade_out_slider.setValue(int(self.config.get("audio_fade_out_ds", 5)))

        self._mode_as_is.setChecked(True)

        saved_cap = self.config.get("default_caption_style", "bold_social")
        for i in range(self._cap_style_combo.count()):
            if self._cap_style_combo.itemData(i) == saved_cap:
                self._cap_style_combo.setCurrentIndex(i)
                break
        saved_font = self.config.get("caption_font_name", "Arial Bold")
        idx_font = self._cap_font_combo.findText(saved_font)
        if idx_font >= 0:
            self._cap_font_combo.setCurrentIndex(idx_font)
        saved_pos = self.config.get("caption_position", "auto")
        for i in range(self._cap_pos_combo.count()):
            if self._cap_pos_combo.itemData(i) == saved_pos:
                self._cap_pos_combo.setCurrentIndex(i)
                break
        self._cap_size_spin.setValue(int(self.config.get("caption_font_size", 38)))
        self._check_script_length()

    def _save_settings(self) -> None:
        vs = self._voice_panel.get_voice_settings()
        mode = "auto_generate" if self._mode_auto.isChecked() else ("improve" if self._mode_improve.isChecked() else "use_as_is")
        self.config.update({
            "last_topic": self._topic_edit.text().strip(),
            "last_script": self._script_edit.toPlainText().strip(),
            "script_mode": mode,
            "default_style": self._style_selector.get_selected_style(),
            "default_style_variant": self._style_selector.get_selected_variant(),
            "default_voice": vs.get("voice_id", ""),
            "default_speed": vs.get("speed", 1.0),
            "default_pitch": vs.get("pitch", 0),
            "default_tts_volume": vs.get("volume", 100),
            "default_duration": self._get_selected_duration(),
            "default_format": self._format_combo.currentData() or "9:16",
            "default_resolution": "720p" if "720" in str(self._res_combo.currentData()) else "1080p",
            "default_fps": int(self._fps_combo.currentData() or 24),
            "default_bg_engine": self._bg_engine_combo.currentData() or "procedural",
            "default_music_style": self._music_combo.currentData() or "auto",
            "default_voice_volume": self._voice_vol_slider.value(),
            "default_music_volume": self._music_vol_slider.value(),
            "default_sfx_volume": self._sfx_vol_slider.value(),
            "audio_fade_in_ds": self._fade_in_slider.value(),
            "audio_fade_out_ds": self._fade_out_slider.value(),
            "default_caption_style": self._cap_style_combo.currentData() or "bold_social",
            "caption_font_name": self._cap_font_combo.currentText(),
            "caption_font_size": self._cap_size_spin.value(),
            "caption_position": self._cap_pos_combo.currentData() or "auto",
            "caption_highlight_color": self._highlight_color,
            "window_width": self.width(),
            "window_height": self.height(),
            "window_x": self.x(),
            "window_y": self.y(),
        })

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._preview_player.stop()
        if self._gen_thread and self._gen_thread.isRunning():
            self.pipeline.cancel()
            self._gen_thread.wait(3000)
        if self._script_thread and self._script_thread.isRunning():
            self._script_thread.wait(1500)
        self._save_settings()
        super().closeEvent(event)
