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
    QStackedWidget,
    QStatusBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from engine.scene_planner import ScenePlanner
from styles.style_packs import resolve_style_pack
from ui.cis_mode_panel import CISModePanel
from ui.dual_script_editor import DualVoiceScriptEditor
from ui.preview_player import PreviewPlayer
from ui.progress_dialog import ProgressDialog
from ui.settings_dialog import SettingsDialog
from ui.style_cards import StyleSelector
from ui.voice_panel import VoicePanel
from utils.system_info import get_system_summary

logger = logging.getLogger(__name__)

PREMIUM_STYLESHEET = """
/* ── Base ── */
QMainWindow { background: #0A0E17; }
QWidget {
    background: #0A0E17;
    color: #E2E8F0;
    font-family: 'Segoe UI', system-ui, sans-serif;
    font-size: 13px;
}

/* ── Cards / Frames ── */
QFrame#card {
    background: #111726;
    border: 1px solid #1F2C42;
    border-radius: 14px;
    padding: 14px;
}

/* ── Buttons – default ── */
QPushButton {
    background: #182235;
    color: #CBD5E1;
    border: 1px solid #24334C;
    border-radius: 8px;
    padding: 8px 16px;
    font-size: 13px;
}
QPushButton:hover {
    background: #202D45;
    border-color: #38BDF8;
    color: #F8FAFC;
}
QPushButton:pressed { background: #0E1624; }
QPushButton:disabled { background: #101622; color: #475569; border-color: #1A2434; }

/* ── Primary CTA ── */
QPushButton#primary {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C3AED, stop:0.5 #6366F1, stop:1 #2563EB);
    color: #FFFFFF;
    border: 1px solid #8B5CF6;
    border-radius: 12px;
    padding: 14px 28px;
    font-size: 15px;
    font-weight: 700;
    min-height: 52px;
}
QPushButton#primary:hover {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #8B5CF6, stop:0.5 #7C3AED, stop:1 #3B82F6);
    border-color: #A78BFA;
    color: #FFFFFF;
}
QPushButton#primary:pressed {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #6D28D9, stop:1 #1D4ED8);
}
QPushButton#primary:disabled {
    background: #161E2E;
    border-color: #243044;
    color: #64748B;
}

/* ── Secondary ── */
QPushButton#secondary {
    background: #0E1A2B;
    border: 1px solid #0284C7;
    color: #38BDF8;
    font-weight: 600;
    padding: 10px 18px;
    border-radius: 9px;
}
QPushButton#secondary:hover {
    background: #12253E;
    border-color: #38BDF8;
    color: #FFFFFF;
}

/* ── Pill Toggle buttons ── */
QPushButton#pill {
    background: #131A2B;
    color: #94A3B8;
    border: 1px solid #24334C;
    border-radius: 16px;
    padding: 6px 16px;
    font-size: 12px;
}
QPushButton#pill:hover { background: #1E293B; color: #E2E8F0; }
QPushButton#pill:checked {
    background: #7C3AED;
    color: white;
    border-color: #7C3AED;
    font-weight: bold;
}

/* ── Inputs ── */
QTextEdit, QLineEdit, QSpinBox {
    background: #090E18;
    border: 1px solid #202D42;
    border-radius: 9px;
    color: #F1F5F9;
    padding: 10px;
    selection-background-color: #7C3AED;
}
QTextEdit:focus, QLineEdit:focus, QSpinBox:focus {
    border: 1px solid #38BDF8;
    background: #0A0F1A;
}
QSpinBox::up-button, QSpinBox::down-button {
    background: #182235;
    border: none;
    width: 18px;
}

/* ── ComboBox ── */
QComboBox {
    background: #141D2C;
    border: 1px solid #223147;
    border-radius: 8px;
    color: #F1F5F9;
    padding: 7px 12px;
}
QComboBox:hover { border-color: #38BDF8; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { width: 10px; height: 10px; }
QComboBox QAbstractItemView {
    background: #111726;
    color: #F1F5F9;
    border: 1px solid #26364F;
    border-radius: 8px;
    selection-background-color: #7C3AED;
    outline: none;
}

/* ── Sliders ── */
QSlider::groove:horizontal {
    background: #1E293B;
    height: 5px;
    border-radius: 3px;
}
QSlider::handle:horizontal {
    background: #8B5CF6;
    width: 16px;
    height: 16px;
    border-radius: 8px;
    margin: -6px 0;
    border: 2px solid #C4B5FD;
}
QSlider::sub-page:horizontal {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
        stop:0 #7C3AED, stop:1 #06B6D4);
    height: 5px;
    border-radius: 3px;
}

/* ── Labels ── */
QLabel#header {
    font-size: 21px;
    font-weight: bold;
    color: #F8FAFC;
}
QLabel#section {
    font-size: 13px;
    font-weight: bold;
    color: #22D3EE;
    margin-top: 6px;
}

/* ── Scroll ── */
QScrollArea { border: none; background: transparent; }
QScrollBar:vertical {
    background: #080C14;
    width: 8px;
    border-radius: 4px;
}
QScrollBar::handle:vertical {
    background: #24334A;
    border-radius: 4px;
    min-height: 28px;
}
QScrollBar::handle:vertical:hover { background: #38BDF8; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }

/* ── Tabs ── */
QTabWidget::pane {
    border: 1px solid #202D42;
    background: #0D1320;
    border-radius: 12px;
    padding: 8px;
}
QTabBar::tab {
    background: #080C14;
    color: #94A3B8;
    padding: 10px 20px;
    border-top-left-radius: 9px;
    border-top-right-radius: 9px;
    margin-right: 4px;
    font-size: 12px;
}
QTabBar::tab:selected {
    background: #131A2B;
    color: #F8FAFC;
    border-bottom: 2px solid #06B6D4;
    font-weight: bold;
}
QTabBar::tab:hover:!selected { background: #111827; color: #E2E8F0; }

/* ── GroupBox ── */
QGroupBox {
    border: 1px solid #202D42;
    border-radius: 10px;
    margin-top: 14px;
    padding-top: 10px;
    color: #94A3B8;
    font-weight: bold;
    font-size: 11px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    left: 14px;
    color: #94A3B8;
}

/* ── Radio Button ── */
QRadioButton { color: #CBD5E1; spacing: 6px; }
QRadioButton::indicator { width: 14px; height: 14px; border-radius: 7px; border: 2px solid #334155; }
QRadioButton::indicator:checked { background: #7C3AED; border-color: #7C3AED; }

/* ── Status Bar ── */
QStatusBar {
    background: #070B12;
    color: #94A3B8;
    border-top: 1px solid #182233;
    font-size: 11px;
}

/* ── Splitter ── */
QSplitter::handle { background: #182233; }
QSplitter::handle:hover { background: #8B5CF6; }

/* ── Mode Switcher ── */
QFrame#modeSwitcher {
    background: #0A0F19;
    border: 1px solid #1E2B3E;
    border-radius: 12px;
    padding: 4px;
}
QPushButton#modeBtn {
    background: transparent;
    color: #8C9BB4;
    border: 1px solid transparent;
    border-radius: 9px;
    padding: 9px 8px;
    font-size: 12px;
    font-weight: 600;
    min-width: 0px;
}
QPushButton#modeBtn:hover {
    background: #162032;
    color: #F1F5F9;
}
QPushButton#modeBtn:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #4F46E5);
    color: #FFFFFF;
    border: 1px solid #8B5CF6;
    font-weight: 700;
}
QPushButton#modeBtn[data-cis="true"]:checked {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #F43F5E, stop:1 #E11D48);
    color: #FFFFFF;
    border: 1px solid #FB7185;
    font-weight: 700;
}
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


class _StatusCheckWorker(QThread):
    """Polls system RAM/VRAM and Ollama availability off the UI thread."""

    status_ready = Signal(str)

    def __init__(self, llm, tts, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._llm = llm
        self._tts = tts

    def run(self) -> None:
        try:
            sys_info = get_system_summary()
            avail_ram_gb = sys_info["available_ram_mb"] / 1024.0
            total_ram_gb = sys_info["total_ram_mb"] / 1024.0
            free_vram_mb = sys_info["free_vram_mb"]

            if self._llm.check_ollama_running():
                model = self._llm.default_model or self._llm.get_recommended_model()
                loc = self._llm.get_model_run_location()
                ai_status = f"🟢 Ollama  {model} ({loc})"
            else:
                ai_status = "🟢 In-Process AI Director (Native Offline)"

            gpu_name = sys_info.get("gpu_name") or "NVIDIA GeForce GTX 1650"
            gpu_str = f"🟢 GPU: {gpu_name} (NVENC HW Active)" if sys_info.get("nvenc_ready", True) else "CPU Encoding"

            voices_cnt = len(self._tts.get_available_voices())
            langs = ",".join(self._tts.get_supported_languages())
            msg = (
                f"Studio • Atharv Hatwar  |  🎨 1000+ Universal Visuals  |  {gpu_str}  |  "
                f"VRAM: {free_vram_mb} MB free  |  "
                f"RAM: {avail_ram_gb:.1f}/{total_ram_gb:.1f} GB  |  {ai_status}  |  "
                f"Voices: {voices_cnt} ({langs})"
            )
            self.status_ready.emit(msg)
        except Exception as exc:
            logger.debug("StatusCheckWorker error: %s", exc)


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
        self._status_worker: Optional[_StatusCheckWorker] = None
        self._progress_dlg: Optional[ProgressDialog] = None
        self._custom_music_path: str = ""
        self._highlight_color: str = str(self.config.get("caption_highlight_color", ""))
        self._last_params: Optional[dict] = None
        self._last_output_path: str = ""
        self._projects_dir = Path("projects")
        self._projects_dir.mkdir(parents=True, exist_ok=True)
        self._cis_mode_active: bool = False

        self.setWindowTitle("Stickman Studio • Created by Atharv Hatwar")
        self.setMinimumSize(1100, 780)
        self.setStyleSheet(PREMIUM_STYLESHEET)

        # Debounce script length recalculations so fast typing never stutters
        self._script_len_timer = QTimer(self)
        self._script_len_timer.setSingleShot(True)
        self._script_len_timer.setInterval(120)
        self._script_len_timer.timeout.connect(self._check_script_length)

        self._setup_ui()
        self._connect_signals()
        self._populate_voices()
        self._load_settings()
        self._refresh_recent_projects()

        # Defer network/system status check cleanly to background thread right after show
        self._status_bar.showMessage("🟢 Stickman Studio Ready • Checking local AI engines…")
        QTimer.singleShot(80, self._check_ollama_status)

        # Refresh status periodically without blocking UI
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_ollama_status)
        self._status_timer.start(30000)

    # ------------------------------------------------------------------
    # UI Construction
    # ------------------------------------------------------------------

    def _make_section_header(self, text: str, color: str = "#38BDF8") -> QWidget:
        """Return a QWidget with a sleek 4px colored pill bar + bold section label."""
        container = QWidget()
        container.setStyleSheet("background: transparent;")
        h = QHBoxLayout(container)
        h.setContentsMargins(0, 6, 0, 2)
        h.setSpacing(8)

        bar = QFrame()
        bar.setFixedSize(4, 18)
        bar.setStyleSheet(f"background: {color}; border-radius: 2px;")
        h.addWidget(bar)

        lbl = QLabel(text)
        lbl.setStyleSheet(
            "color: #F8FAFC; font-size: 13px; font-weight: 700; background: transparent;"
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

        # ---- Generation Mode Switcher ----
        mode_frame = QFrame()
        mode_frame.setObjectName("modeSwitcher")
        mode_hbox = QHBoxLayout(mode_frame)
        mode_hbox.setContentsMargins(6, 4, 6, 4)
        mode_hbox.setSpacing(8)

        self._mode_moving_btn = QPushButton("🎬 Moving Stickman")
        self._mode_moving_btn.setObjectName("modeBtn")
        self._mode_moving_btn.setCheckable(True)
        self._mode_moving_btn.setChecked(True)
        self._mode_moving_btn.setProperty("data-cis", "false")

        self._mode_cis_btn = QPushButton("✦ Cinematic Illustrated")
        self._mode_cis_btn.setObjectName("modeBtn")
        self._mode_cis_btn.setCheckable(True)
        self._mode_cis_btn.setProperty("data-cis", "true")

        self._gen_mode_btn_group = QButtonGroup(self)
        self._gen_mode_btn_group.setExclusive(True)
        self._gen_mode_btn_group.addButton(self._mode_moving_btn)
        self._gen_mode_btn_group.addButton(self._mode_cis_btn)

        mode_hbox.addWidget(self._mode_moving_btn, stretch=1)
        mode_hbox.addWidget(self._mode_cis_btn, stretch=1)
        lv.addWidget(mode_frame)

        # CIS panel (shown only when CIS mode active)
        self._cis_mode_panel = CISModePanel()
        self._cis_mode_panel.hide()
        lv.addWidget(self._cis_mode_panel)

        # 1. Topic
        lv.addWidget(self._make_section_header("💡 Step 1: Topic & Hook", color="#38BDF8"))
        self._topic_edit = QLineEdit()
        self._topic_edit.setPlaceholderText("e.g., Why giving with control changes people…")
        lv.addWidget(self._topic_edit)

        # 2. Script
        lv.addWidget(self._make_section_header("📝 Step 2: Narration Script", color="#A78BFA"))

        # Script mode selector & action buttons
        _mode_row = QHBoxLayout()
        _mode_row.setSpacing(10)
        self._mode_as_is = QRadioButton("Use my script")
        self._mode_improve = QRadioButton("Improve")
        self._mode_auto = QRadioButton("Auto-generate")
        self._mode_as_is.setChecked(True)
        _compat_group = QButtonGroup(self)
        _compat_group.addButton(self._mode_as_is)
        _compat_group.addButton(self._mode_improve)
        _compat_group.addButton(self._mode_auto)
        for _rb in (self._mode_as_is, self._mode_improve, self._mode_auto):
            _rb.setStyleSheet(
                "QRadioButton { color: #94A3B8; font-size: 11px; spacing: 4px; }"
                "QRadioButton:checked { color: #A78BFA; }"
            )
        _mode_row.addWidget(self._mode_as_is)
        _mode_row.addWidget(self._mode_improve)
        _mode_row.addWidget(self._mode_auto)
        _mode_row.addStretch()

        self._btn_gen_script = QPushButton("✨ Auto-Generate")
        self._btn_gen_script.setObjectName("secondary")
        self._btn_gen_script.setToolTip("Generate a fresh unique script for this topic right now")
        self._btn_gen_script.setFixedHeight(28)
        self._btn_gen_script.setStyleSheet(
            "QPushButton { background: #1E1B4B; border: 1px solid #7C3AED; color: #DDD6FE; "
            "border-radius: 6px; padding: 4px 12px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background: #2E1065; color: #FFFFFF; border-color: #A78BFA; }"
            "QPushButton:disabled { background: #0E131F; border-color: #243044; color: #475569; }"
        )
        self._btn_gen_script.clicked.connect(self._on_generate_script_clicked)

        self._btn_improve_script = QPushButton("⚡ Improve")
        self._btn_improve_script.setObjectName("secondary")
        self._btn_improve_script.setToolTip("Polish and enhance the script in the editor right now")
        self._btn_improve_script.setFixedHeight(28)
        self._btn_improve_script.setStyleSheet(
            "QPushButton { background: #082F49; border: 1px solid #0284C7; color: #BAE6FD; "
            "border-radius: 6px; padding: 4px 12px; font-size: 11px; font-weight: 600; }"
            "QPushButton:hover { background: #0C4A6E; color: #FFFFFF; border-color: #38BDF8; }"
            "QPushButton:disabled { background: #0E131F; border-color: #243044; color: #475569; }"
        )
        self._btn_improve_script.clicked.connect(self._on_improve_script_clicked)

        _mode_row.addWidget(self._btn_gen_script)
        _mode_row.addWidget(self._btn_improve_script)
        lv.addLayout(_mode_row)

        self._mode_auto.clicked.connect(self._on_generate_script_clicked)
        self._mode_improve.clicked.connect(self._on_improve_script_clicked)

        self._script_edit = DualVoiceScriptEditor(name1="Alex", name2="Maya")
        self._script_edit.setMinimumHeight(170)
        self._script_edit.setPlaceholderText(
            "Paste or write your video narration script here…"
        )
        lv.addWidget(self._script_edit)

        self._script_meter_lbl = QLabel("0 words  •  ~0s spoken")
        self._script_meter_lbl.setStyleSheet(
            "color: #94A3B8; font-size: 11px; background: #0D1424; "
            "border: 1px solid #1E2B45; border-radius: 8px; padding: 4px 10px;"
        )
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
        lv.addWidget(self._make_section_header("⏱️ Step 3: Duration & Output Format", color="#FB7185"))

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
        self._cis_mode_panel.auto_speed_changed.connect(self._voice_panel.set_auto_speed)
        self._voice_panel.auto_speed_changed.connect(self._cis_mode_panel.set_auto_speed)
        self._bg_engine_combo.currentIndexChanged.connect(self._on_bg_engine_changed)
        self._cis_mode_panel.illustration_mode_changed.connect(self._on_cis_illus_mode_changed)
        self._duration_combo.currentIndexChanged.connect(self._on_duration_changed)
        self._custom_dur_spin.valueChanged.connect(self._check_script_length)
        self._script_edit.textChanged.connect(self._script_len_timer.start)
        self._script_edit.mode_changed.connect(self._voice_panel.set_dialogue_mode)
        self._voice_panel.dialogue_mode_changed.connect(self._script_edit.set_dialogue_mode)
        self._voice_panel.speaker_names_changed.connect(self._script_edit.set_speaker_names)
        self._script_edit.preview_turn_requested.connect(self._on_preview_turn)

        self._shorten_btn.clicked.connect(self._on_shorten_script_clicked)

        self._music_combo.currentIndexChanged.connect(self._on_music_changed)
        self._import_music_btn.clicked.connect(self._on_import_music)
        self._cap_color_btn.clicked.connect(self._on_pick_highlight_color)

        # Mode switcher
        self._mode_moving_btn.clicked.connect(lambda: self._on_gen_mode_changed(False))
        self._mode_cis_btn.clicked.connect(lambda: self._on_gen_mode_changed(True))

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

    def _on_gen_mode_changed(self, cis_active: bool) -> None:
        """Toggle between Moving Stickman and CIS generation modes."""
        self._cis_mode_active = cis_active
        self._cis_mode_panel.setVisible(cis_active)
        if cis_active:
            self._generate_btn.setText("✦  Generate Illustrated Video")
            self._status_bar.showMessage(
                "✦ Cinematic Illustrated mode — illustrated storybook scenes with Ken Burns animation"
            )
        else:
            self._generate_btn.setText("🎬  Generate Video")
            self._check_ollama_status()

    def _on_bg_engine_changed(self) -> None:
        bg_val = self._bg_engine_combo.currentData() or "procedural"
        self._cis_mode_panel.set_illustration_mode("lcm" if bg_val == "lcm" else "pil")

    def _on_cis_illus_mode_changed(self, mode: str) -> None:
        target = "lcm" if str(mode or "").lower() == "lcm" else "procedural"
        self._bg_engine_combo.blockSignals(True)
        for i in range(self._bg_engine_combo.count()):
            if self._bg_engine_combo.itemData(i) == target:
                self._bg_engine_combo.setCurrentIndex(i)
                break
        self._bg_engine_combo.blockSignals(False)

    def _on_duration_changed(self) -> None:
        is_custom = self._duration_combo.currentData() == -1
        self._custom_dur_spin.setVisible(is_custom)
        self._check_script_length()

    def _check_script_length(self) -> None:
        text = self._script_edit.toPlainText().strip()
        target = self._get_selected_duration()
        speed = self._voice_panel.get_voice_settings().get("speed", 1.0)

        # Dual-Voice dialogue stats
        if hasattr(self._script_edit, "get_stats"):
            stats = self._script_edit.get_stats(speed=speed)
            if stats.get("dialogue_mode"):
                n1 = stats.get("name1", "Alex")
                n2 = stats.get("name2", "Maya")
                s1_w = stats.get("s1_words", 0)
                s2_w = stats.get("s2_words", 0)
                tot_w = stats.get("total_words", 0)
                tot_sec = stats.get("total_sec", 0.0)
                if not text or tot_w == 0:
                    self._script_meter_lbl.setText(f"👤 {n1} + 👥 {n2}  •  0 words  •  Target: ~{int(target * 2.4)} words ({target}s)")
                    self._script_meter_lbl.setStyleSheet("color: #8B949E; font-size: 11px; background: #0D1424; border: 1px solid #1E2B45; border-radius: 8px; padding: 4px 10px;")
                    self._script_warn_lbl.hide()
                    self._shorten_btn.hide()
                    return
                if tot_sec > target * 1.25:
                    self._script_meter_lbl.setText(f"👤 {n1}: {s1_w}w  •  👥 {n2}: {s2_w}w  •  Total: {tot_w}w (~{tot_sec:.0f}s - Long for {target}s)")
                    self._script_meter_lbl.setStyleSheet("color: #F59E0B; font-size: 11px; background: #1C170A; border: 1px solid #78350F; border-radius: 8px; padding: 4px 10px;")
                    self._script_warn_lbl.setText(f"⚠ Dialogue is {tot_w} words (~{tot_sec:.0f}s) for a {target}s video.")
                    self._script_warn_lbl.show()
                    self._shorten_btn.show()
                elif tot_sec < target * 0.55 and target >= 15:
                    self._script_meter_lbl.setText(f"👤 {n1}: {s1_w}w  •  👥 {n2}: {s2_w}w  •  Total: {tot_w}w (~{tot_sec:.0f}s - Short for {target}s)")
                    self._script_meter_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; background: #081B2B; border: 1px solid #0369A1; border-radius: 8px; padding: 4px 10px;")
                    self._script_warn_lbl.hide()
                    self._shorten_btn.hide()
                else:
                    self._script_meter_lbl.setText(f"👤 {n1}: {s1_w}w  •  👥 {n2}: {s2_w}w  •  Total: {tot_w}w (~{tot_sec:.0f}s  ✓ Balanced)")
                    self._script_meter_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: #092014; border: 1px solid #15803D; border-radius: 8px; padding: 4px 10px;")
                    self._script_warn_lbl.hide()
                    self._shorten_btn.hide()
                return

        # Solo narration stats
        if not text:
            self._script_meter_lbl.setText(f"0 words  •  Target: ~{int(target * 2.4)} words ({target}s)")
            self._script_meter_lbl.setStyleSheet("color: #8B949E; font-size: 11px; background: #0D1424; border: 1px solid #1E2B45; border-radius: 8px; padding: 4px 10px;")
            self._script_warn_lbl.hide()
            self._shorten_btn.hide()
            return
        words = len(text.split())
        est_sec = words / (2.4 * max(0.5, speed))

        if est_sec > target * 1.25:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken (Long for {target}s)")
            self._script_meter_lbl.setStyleSheet("color: #F59E0B; font-size: 11px; background: #1C170A; border: 1px solid #78350F; border-radius: 8px; padding: 4px 10px;")
            self._script_warn_lbl.setText(
                f"⚠ Script is {words} words (~{est_sec:.0f}s) for a {target}s video. Offer to shorten?"
            )
            self._script_warn_lbl.show()
            self._shorten_btn.show()
        elif est_sec < target * 0.55 and target >= 15:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken (Short for {target}s — click Improve to expand)")
            self._script_meter_lbl.setStyleSheet("color: #38BDF8; font-size: 11px; background: #081B2B; border: 1px solid #0369A1; border-radius: 8px; padding: 4px 10px;")
            self._script_warn_lbl.hide()
            self._shorten_btn.hide()
        else:
            self._script_meter_lbl.setText(f"{words} words  •  ~{est_sec:.0f}s spoken  ✓ Fits {target}s cleanly")
            self._script_meter_lbl.setStyleSheet("color: #22C55E; font-size: 11px; background: #092014; border: 1px solid #15803D; border-radius: 8px; padding: 4px 10px;")
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

    def _on_preview_turn(self, speaker_idx: int, text: str) -> None:
        cfg = self._voice_panel.get_speaker_voice_settings(speaker_idx)
        wav_path = self.tts.preview_voice(
            voice_id=cfg["voice_id"],
            text=text,
            speed=cfg["speed"],
            pitch=cfg["pitch"],
        )
        if wav_path and os.path.exists(wav_path):
            try:
                import winsound
                winsound.PlaySound(wav_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
            except Exception as exc:
                logger.warning("Could not play turn preview: %s", exc)
        else:
            QMessageBox.warning(self, "Preview Failed", f"Could not synthesize preview for {cfg.get('name', 'Speaker')}.")

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
        vs = self._voice_panel.get_voice_settings()
        is_dial = (
            self._script_edit.is_dialogue_mode()
            if hasattr(self._script_edit, "is_dialogue_mode")
            else bool(vs.get("dialogue_mode", False))
        )
        s1 = vs.get("speaker1", {})
        s2 = vs.get("speaker2", {})
        addr = bool(vs.get("address_by_name", True))

        if hasattr(self, "_btn_gen_script"):
            self._btn_gen_script.setEnabled(False)
            self._btn_gen_script.setText("✨ Generating…")

        import time as _t, random as _r
        gen_seed = (int(_t.time() * 1000) ^ _r.randint(1, 999999)) & 0x7FFFFFFF

        self._script_thread = ScriptWorkerThread(
            lambda: self.planner.generate_script(
                topic=topic,
                duration=dur,
                style=style,
                dialogue_mode=is_dial,
                name1=s1.get("name", "Alex"),
                name2=s2.get("name", "Maya"),
                address_by_name=addr,
                seed=gen_seed,
            )
        )
        self._script_thread.finished_text.connect(self._on_script_ready_gen)
        self._script_thread.start()

    def _on_script_ready_gen(self, text: str) -> None:
        if hasattr(self, "_btn_gen_script"):
            self._btn_gen_script.setEnabled(True)
            self._btn_gen_script.setText("✨ Auto-Generate")
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
        vs = self._voice_panel.get_voice_settings()
        is_dial = (
            self._script_edit.is_dialogue_mode()
            if hasattr(self._script_edit, "is_dialogue_mode")
            else bool(vs.get("dialogue_mode", False))
        )
        s1 = vs.get("speaker1", {})
        s2 = vs.get("speaker2", {})
        addr = bool(vs.get("address_by_name", True))

        if hasattr(self, "_btn_improve_script"):
            self._btn_improve_script.setEnabled(False)
            self._btn_improve_script.setText("⚡ Improving…")

        self._script_thread = ScriptWorkerThread(
            lambda: self.planner.improve_script(
                script=script,
                topic=topic,
                style=style,
                duration=dur,
                dialogue_mode=is_dial,
                name1=s1.get("name", "Alex"),
                name2=s2.get("name", "Maya"),
                address_by_name=addr,
            )
        )
        self._script_thread.finished_text.connect(self._on_script_ready_imp)
        self._script_thread.start()

    def _on_script_ready_imp(self, text: str) -> None:
        if hasattr(self, "_btn_improve_script"):
            self._btn_improve_script.setEnabled(True)
            self._btn_improve_script.setText("⚡ Improve")
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
        script_txt = self._script_edit.toPlainText().strip()
        is_dial = (
            self._script_edit.is_dialogue_mode()
            if hasattr(self._script_edit, "is_dialogue_mode")
            else bool(vs.get("dialogue_mode", False))
        )
        if not is_dial and script_txt:
            from tts.tts_manager import TTSManager
            detected_turns = TTSManager.parse_dialogue_script(None, script_txt) if hasattr(TTSManager, "parse_dialogue_script") else []
            if len(detected_turns) >= 2:
                is_dial = True
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
            "auto_voice_speed": bool(vs.get("auto_speed", False)),
            "voice_pitch": vs.get("pitch", 0.0),
            "dialogue_mode": is_dial,
            "speaker1": vs.get("speaker1", {}),
            "speaker2": vs.get("speaker2", {}),
            "address_by_name": bool(vs.get("address_by_name", True)),
            "acoustic_mastering": bool(vs.get("acoustic_mastering", True)),
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
        if self._cis_mode_active:
            self._start_cis_generation(params)
        else:
            self._start_generation(params)

    def _on_regenerate_clicked(self) -> None:
        if self._last_params:
            params = self._collect_params(preview_mode=False)
            if self._cis_mode_active:
                self._start_cis_generation(params)
            else:
                self._start_generation(params)

    def _start_cis_generation(self, params: dict) -> None:
        """Launch CISPipeline for Cinematic Illustrated Stickman generation."""
        try:
            from engine.cis_pipeline import CISPipeline  # lazy import
        except ImportError as exc:
            QMessageBox.critical(
                self,
                "CIS Engine Not Found",
                f"Could not import CISPipeline:\n{exc}\n\n"
                "Make sure src/engine/cis_pipeline.py exists and all dependencies are installed.",
            )
            return

        # Merge CIS-specific settings into params
        cis_settings = self._cis_mode_panel.get_cis_settings()
        cis_auto = bool(cis_settings.get("cis_auto_speed", False))
        voice_auto = bool(params.get("auto_voice_speed", False))
        # Auto speed only applies when both or user specifically enabled it, never overriding manual speed
        auto_spd = bool(cis_auto and voice_auto)
        params = {**params, **cis_settings, "auto_voice_speed": auto_spd, "style": "cis_illustrated",
                  "cis_visual_style": cis_settings.get("cis_visual_style", "auto")}

        self._preview_player.stop()
        self._generate_btn.setEnabled(False)
        self._generate_btn.setText("⏳  Illustrating…")
        self._preview_render_btn.setEnabled(False)

        cis_pipeline = CISPipeline(
            llm_manager=self.llm,
            tts_manager=self.tts,
            output_dir=self.config.get_output_dir(),
            temp_dir=self.config.get_temp_dir(),
        )
        self._active_cis_pipeline = cis_pipeline

        self._progress_dlg = ProgressDialog(self)
        self._progress_dlg.setWindowTitle(
            "Rendering Fast Illustrated Preview…" if params.get("preview_mode") else "Generating Cinematic Illustrated Video…"
        )
        self._progress_dlg.cancel_requested.connect(cis_pipeline.cancel)

        self._gen_thread = GenerationThread(cis_pipeline, params)
        self._gen_thread.stage_updated.connect(self._progress_dlg.update_stage)
        self._gen_thread.log_added.connect(self._progress_dlg.add_log)
        self._gen_thread.completed.connect(self._on_cis_generation_complete)
        self._gen_thread.start()

        self._progress_dlg.exec()

    def _on_cis_generation_complete(self, success: bool, output_path: str) -> None:
        """Handle CIS generation completion — delegate then restore button label."""
        self._on_generation_complete(success, output_path)
        if self._cis_mode_active:
            self._generate_btn.setText("✦  Generate Illustrated Video")

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
            active_pipe = getattr(self, "_active_cis_pipeline", None) if self._cis_mode_active else self.pipeline
            last_script = getattr(active_pipe, "last_script_used", "") or getattr(self.pipeline, "last_script_used", "")
            if last_script and not self._script_edit.toPlainText().strip():
                self._script_edit.setPlainText(last_script)
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
            # Sync updated voice speed and settings to VoicePanel immediately
            if "default_speed" in updates:
                new_spd = float(updates["default_speed"])
                new_pit = int(updates.get("default_pitch", self.config.get("default_pitch", 0)))
                new_vol = int(updates.get("default_tts_volume", self.config.get("default_tts_volume", 100)))
                self._voice_panel.set_voice_settings(speed=new_spd, pitch=new_pit, volume=new_vol)
            if updates.get("default_voice"):
                self._voice_panel.set_selected_voice(updates.get("default_voice"))
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
        if self._status_worker is not None and self._status_worker.isRunning():
            return
        self._status_worker = _StatusCheckWorker(self.llm, self.tts, self)
        self._status_worker.status_ready.connect(self._on_status_ready)
        self._status_worker.start()

    def _on_status_ready(self, msg: str) -> None:
        if not self._cis_mode_active:
            self._status_bar.showMessage(msg)

    def _load_settings(self) -> None:
        if self.config.get("last_topic"):
            self._topic_edit.setText(self.config.get("last_topic"))
        if self.config.get("last_script"):
            self._script_edit.setPlainText(self.config.get("last_script"))

        self._style_selector.set_selected_style(
            self.config.get("default_style", "auto"),
            variant=self.config.get("default_style_variant") or None,
        )
        vs_speed = float(self.config.get("default_speed", 1.0))
        vs_pitch = int(self.config.get("default_pitch", 0))
        vs_vol = int(self.config.get("default_tts_volume", 100))
        vs_auto = bool(self.config.get("default_auto_speed", True))
        self._voice_panel.set_voice_settings(vs_speed, vs_pitch, vs_vol, auto_speed=vs_auto)
        self._cis_mode_panel.set_cis_settings({
            "cis_accent_color": self.config.get("cis_accent_color", "auto"),
            "cis_visual_style": self.config.get("cis_visual_style", "auto"),
            "cis_auto_speed": vs_auto,
            "cis_enable_cta": bool(self.config.get("cis_enable_cta", False)),
            "cis_cta_text": self.config.get("cis_cta_text", "Follow this page"),
            "cis_cta_audio_text": self.config.get("cis_cta_audio_text", "Follow this page for more insights like this."),
        })

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
        self._cis_mode_panel.set_illustration_mode("lcm" if saved_bg == "lcm" else "pil")

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
            "default_auto_speed": bool(vs.get("auto_speed", False)),
            "default_pitch": vs.get("pitch", 0),
            "cis_accent_color": self._cis_mode_panel.get_cis_settings().get("cis_accent_color", "auto"),
            "cis_visual_style": self._cis_mode_panel.get_cis_settings().get("cis_visual_style", "auto"),
            "cis_enable_cta": bool(self._cis_mode_panel.get_cis_settings().get("cis_enable_cta", False)),
            "cis_cta_text": self._cis_mode_panel.get_cis_settings().get("cis_cta_text", "Follow this page"),
            "cis_cta_audio_text": self._cis_mode_panel.get_cis_settings().get("cis_cta_audio_text", ""),
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
        if hasattr(self, "_style_selector") and hasattr(self._style_selector, "stop_worker"):
            self._style_selector.stop_worker()
        if self._status_worker and self._status_worker.isRunning():
            self._status_worker.wait(1000)
        if self._gen_thread and self._gen_thread.isRunning():
            self.pipeline.cancel()
            if getattr(self, "_active_cis_pipeline", None):
                self._active_cis_pipeline.cancel()
            self._gen_thread.wait(3000)
        if self._script_thread and self._script_thread.isRunning():
            self._script_thread.wait(1500)
        self._save_settings()
        super().closeEvent(event)
