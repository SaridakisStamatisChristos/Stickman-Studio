"""
Settings Dialog - Application settings with tabs for AI Model, Output, TTS,
Performance, and About. Wired directly to LLMManager, TTSManager, and SystemInfo.
"""
from __future__ import annotations

import platform
import sys
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from utils.system_info import get_system_summary

DIALOG_STYLE = """
QDialog { background: #1a1a2e; color: #e8e8e8; }
QWidget { background: #1a1a2e; color: #e8e8e8; font-family: 'Segoe UI'; font-size: 12px; }
QTabWidget::pane { border: 1px solid #0f3460; background: #16213e; border-radius: 6px; }
QTabBar::tab { background: #0d1b2a; color: #888; padding: 8px 18px; }
QTabBar::tab:selected { background: #16213e; color: #e8e8e8; border-bottom: 2px solid #e94560; }
QGroupBox { border: 1px solid #0f3460; border-radius: 8px; margin-top: 12px; color: #4FC3F7; font-weight: bold; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; }
QPushButton { background: #0f3460; color: white; border: none; border-radius: 6px; padding: 7px 16px; }
QPushButton:hover { background: #1a4a8a; }
QPushButton:pressed { background: #0d2d50; }
QPushButton:disabled { background: #1c2236; color: #666; }
QLineEdit, QPlainTextEdit { background: #0d1b2a; border: 1px solid #0f3460; border-radius: 6px; color: #e8e8e8; padding: 6px; }
QComboBox { background: #0f3460; border: 1px solid #1a4a8a; border-radius: 6px; color: white; padding: 6px 12px; }
QComboBox QAbstractItemView { background: #16213e; color: #e8e8e8; }
QSlider::groove:horizontal { background: #0f3460; height: 4px; border-radius: 2px; }
QSlider::handle:horizontal { background: #e94560; width: 16px; height: 16px; border-radius: 8px; margin: -6px 0; }
QSlider::sub-page:horizontal { background: #e94560; height: 4px; border-radius: 2px; }
QCheckBox { color: #e8e8e8; spacing: 8px; }
QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #0f3460; border-radius: 4px; background: #0d1b2a; }
QCheckBox::indicator:checked { background: #e94560; border-color: #e94560; }
QLabel { background: transparent; color: #e8e8e8; }
QProgressBar { background: #0d1b2a; border: none; border-radius: 4px; height: 8px; }
QProgressBar::chunk { background: #e94560; border-radius: 4px; }
QScrollArea { border: none; }
"""

# Strictly lightweight local models tailored to 8 GB RAM / 4 GB VRAM
AVAILABLE_MODELS = [
    ("auto",         "Auto",     "Select fastest reliable model for this laptop"),
    ("qwen3.5:0.8b", "~550 MB",  "Fast mode (recommended for 8 GB RAM)"),
    ("qwen3.5:2b",   "~1.4 GB",  "Better quality mode (fits 4 GB VRAM)"),
    ("qwen2.5:0.5b", "~395 MB",  "Ultra-light fallback"),
    ("qwen2.5:1.5b", "~934 MB",  "Balanced fallback"),
]

TTS_ENGINES = [
    ("kokoro", "Kokoro-82M (ONNX)", "~338 MB — High-quality neural English & Hindi TTS"),
    ("piper",  "Piper TTS",         "~60 MB/voice — Lightweight offline neural voices"),
]


class _ModelPullThread(QThread):
    progress = Signal(str, int)
    finished_ok = Signal(bool, str)

    def __init__(self, llm_manager, model_name: str) -> None:
        super().__init__()
        self.llm = llm_manager
        self.model_name = model_name

    def run(self) -> None:
        ok = self.llm.pull_model(
            self.model_name,
            progress_callback=lambda s, p: self.progress.emit(s, p),
        )
        self.finished_ok.emit(ok, self.model_name)


class _BenchmarkThread(QThread):
    done = Signal(dict)

    def __init__(self, llm_manager, model_name: Optional[str]) -> None:
        super().__init__()
        self.llm = llm_manager
        self.model_name = model_name

    def run(self) -> None:
        res = self.llm.benchmark_model(self.model_name)
        self.done.emit(res)


class _KokoroDownloadThread(QThread):
    progress = Signal(str, int)
    finished_ok = Signal(bool)

    def __init__(self, tts_manager) -> None:
        super().__init__()
        self.tts = tts_manager

    def run(self) -> None:
        ok = self.tts.download_kokoro_models(
            progress_callback=lambda s, p: self.progress.emit(s, p)
        )
        self.finished_ok.emit(ok)


class _SemanticBrainDownloadThread(QThread):
    progress = Signal(str, int)
    finished_ok = Signal(bool)

    def run(self) -> None:
        from engine.semantic_scene_brain import SemanticSceneBrain
        ok = SemanticSceneBrain.download_model(
            progress_callback=lambda s, p: self.progress.emit(s, p)
        )
        self.finished_ok.emit(ok)


def _make_slider_row(
    label: str,
    minimum: int,
    maximum: int,
    default: int,
    fmt: Any = "{}",
    step: int = 1,
) -> tuple[QWidget, QSlider]:
    w = QWidget()
    v = QVBoxLayout(w)
    v.setContentsMargins(0, 0, 0, 0)
    v.setSpacing(2)

    format_fn = fmt if callable(fmt) else (lambda val, f=fmt: f.format(val))

    h = QHBoxLayout()
    h.setContentsMargins(0, 0, 0, 0)
    lbl = QLabel(label)
    val_lbl = QLabel(format_fn(default))
    val_lbl.setFixedWidth(78)
    val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
    h.addWidget(lbl)
    h.addStretch()
    h.addWidget(val_lbl)
    v.addLayout(h)

    slider = QSlider(Qt.Horizontal)
    slider.setMinimum(minimum)
    slider.setMaximum(maximum)
    slider.setValue(default)
    slider.setSingleStep(step)
    slider.valueChanged.connect(lambda val, lbl=val_lbl, fn=format_fn: lbl.setText(fn(val)))
    v.addWidget(slider)
    return w, slider


class SettingsDialog(QDialog):
    """Multi-tab application settings dialog."""

    voices_updated = Signal()

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        llm_manager: Any = None,
        tts_manager: Any = None,
    ) -> None:
        super().__init__(parent)
        self._llm = llm_manager
        self._tts = tts_manager
        self._pull_thread: Optional[_ModelPullThread] = None
        self._bench_thread: Optional[_BenchmarkThread] = None
        self._kokoro_thread: Optional[_KokoroDownloadThread] = None

        self.setWindowTitle("Settings — Stickman Studio")
        self.setMinimumSize(640, 560)
        self.setStyleSheet(DIALOG_STYLE)
        self._setup_ui()
        self._refresh_runtime_statuses()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._tabs = QTabWidget()
        self._tabs.addTab(self._build_ai_tab(), "🤖  AI Model")
        self._tabs.addTab(self._build_output_tab(), "🎬  Output")
        self._tabs.addTab(self._build_tts_tab(), "🔊  TTS")
        self._tabs.addTab(self._build_perf_tab(), "⚙️  Performance")
        self._tabs.addTab(self._build_about_tab(), "ℹ️  About")
        root.addWidget(self._tabs)

        btns = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        btns.button(QDialogButtonBox.Save).setText("Save Settings")
        btns.button(QDialogButtonBox.Save).setStyleSheet(
            "QPushButton { background: #e94560; font-weight: bold; padding: 9px 24px; }"
            "QPushButton:hover { background: #ff5a7a; }"
        )
        btns.accepted.connect(self._on_save)
        btns.rejected.connect(self.reject)
        root.addWidget(btns)

    # ------------------------------------------------------------------
    # Tab builders
    # ------------------------------------------------------------------

    def _build_ai_tab(self) -> QWidget:
        tab = self._scrollable_tab()
        layout = tab.layout()

        # 1. In-Process Neural Semantic Brain (Primary AI Engine)
        brain_group = QGroupBox("In-Process AI Neural Semantic Brain (100% Offline • 0 MB VRAM • Zero Ollama)")
        bg = QVBoxLayout(brain_group)
        bg.setSpacing(8)

        brain_top = QHBoxLayout()
        self._brain_dot = QLabel("●")
        self._brain_dot.setStyleSheet("color: #4CAF50; font-size: 18px;")
        brain_top.addWidget(self._brain_dot)
        self._brain_status_lbl = QLabel("Checking Neural Brain…")
        brain_top.addWidget(self._brain_status_lbl, stretch=1)

        self._brain_test_btn = QPushButton("⚡ Test Brain")
        self._brain_test_btn.clicked.connect(self._on_test_semantic_brain)
        brain_top.addWidget(self._brain_test_btn)

        self._brain_dl_btn = QPushButton("⬇ Download / Verify Brain")
        self._brain_dl_btn.clicked.connect(self._on_download_semantic_brain)
        brain_top.addWidget(self._brain_dl_btn)
        bg.addLayout(brain_top)

        self._brain_desc_lbl = QLabel(
            "Deep neural embedding transformer (MiniLM-L6 · 22.9 MB). Runs in-process in <10ms to map narration to "
            "60+ physical visual metaphors, posture kinetics, and emotion choreography with zero external daemons."
        )
        self._brain_desc_lbl.setWordWrap(True)
        self._brain_desc_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        bg.addWidget(self._brain_desc_lbl)

        self._brain_test_res_lbl = QLabel("")
        self._brain_test_res_lbl.setStyleSheet("color: #81C784; font-size: 11px; font-weight: bold;")
        self._brain_test_res_lbl.hide()
        bg.addWidget(self._brain_test_res_lbl)

        self._brain_progress_bar = QProgressBar()
        self._brain_progress_bar.setRange(0, 100)
        self._brain_progress_bar.hide()
        bg.addWidget(self._brain_progress_bar)

        layout.addWidget(brain_group)

        # 2. External Ollama LLM (Optional)
        status_group = QGroupBox("External Ollama LLM (Optional — Not Required for Production)")
        sg = QVBoxLayout(status_group)
        top_row = QHBoxLayout()
        self._ollama_dot = QLabel("●")
        self._ollama_dot.setStyleSheet("color: #FF9800; font-size: 18px;")
        top_row.addWidget(self._ollama_dot)
        self._ollama_status_lbl = QLabel("Checking Ollama…")
        top_row.addWidget(self._ollama_status_lbl, stretch=1)
        test_btn = QPushButton("Test Connection")
        test_btn.clicked.connect(self._test_ollama)
        top_row.addWidget(test_btn)
        self._bench_btn = QPushButton("⚡ Benchmark")
        self._bench_btn.clicked.connect(self._on_benchmark)
        top_row.addWidget(self._bench_btn)
        sg.addLayout(top_row)

        self._bench_lbl = QLabel("Benchmark: not run yet")
        self._bench_lbl.setStyleSheet("color: #aaa; font-size: 11px;")
        sg.addWidget(self._bench_lbl)

        ollama_note = QLabel(
            "Note: Stickman Studio works 100% offline out-of-the-box using the In-Process Neural Semantic Brain above. "
            "Ollama is an optional fallback for open-ended text expansion."
        )
        ollama_note.setWordWrap(True)
        ollama_note.setStyleSheet("color: #777; font-size: 10px; font-style: italic;")
        sg.addWidget(ollama_note)

        layout.addWidget(status_group)

        # Model selection
        model_group = QGroupBox("Ollama Model Selection (If Using Ollama)")
        mg = QVBoxLayout(model_group)
        mg.setSpacing(8)

        self._model_combo = QComboBox()
        for m_id, size, desc in AVAILABLE_MODELS:
            self._model_combo.addItem(f"{m_id}  ({size})  — {desc}", m_id)
        self._model_combo.currentIndexChanged.connect(self._update_model_size_label)
        mg.addWidget(self._model_combo)

        size_row = QHBoxLayout()
        self._model_size_lbl = QLabel("Auto-selects fastest model for your hardware")
        self._model_size_lbl.setStyleSheet("color: #4FC3F7;")
        size_row.addWidget(self._model_size_lbl, stretch=1)
        self._download_btn = QPushButton("⬇  Download Model")
        self._download_btn.clicked.connect(self._on_download_model)
        size_row.addWidget(self._download_btn)
        mg.addLayout(size_row)

        self._pull_bar = QProgressBar()
        self._pull_bar.setRange(0, 100)
        self._pull_bar.hide()
        mg.addWidget(self._pull_bar)

        layout.addWidget(model_group)

        # Parameters
        param_group = QGroupBox("Inference Parameters")
        pg = QVBoxLayout(param_group)
        pg.setSpacing(10)

        ctx_w, self._ctx_slider = _make_slider_row("Context Window", 512, 4096, 2048, "{} tokens", 256)
        pg.addWidget(ctx_w)
        temp_w, self._temp_slider = _make_slider_row(
            "Temperature", 1, 10, 7, lambda v: f"{v / 10:.1f}"
        )
        pg.addWidget(temp_w)
        layout.addWidget(param_group)

        layout.addStretch()
        return tab

    def _build_output_tab(self) -> QWidget:
        tab = self._scrollable_tab()
        layout = tab.layout()

        dir_group = QGroupBox("Default Output Directory")
        dg = QHBoxLayout(dir_group)
        self._output_dir_edit = QLineEdit()
        self._output_dir_edit.setPlaceholderText("output")
        dg.addWidget(self._output_dir_edit, stretch=1)
        browse_btn = QPushButton("Browse…")
        browse_btn.clicked.connect(self._browse_output_dir)
        dg.addWidget(browse_btn)
        layout.addWidget(dir_group)

        vid_group = QGroupBox("Video Defaults")
        vg = QVBoxLayout(vid_group)

        self._res_combo = QComboBox()
        self._res_combo.addItems(["1080p (Full HD)", "720p (Fast / Lightweight)"])
        vg.addWidget(QLabel("Resolution"))
        vg.addWidget(self._res_combo)

        self._fps_combo = QComboBox()
        self._fps_combo.addItems(["24 FPS (Recommended)", "30 FPS"])
        vg.addWidget(QLabel("Frame Rate"))
        vg.addWidget(self._fps_combo)

        self._format_combo = QComboBox()
        self._format_combo.addItems(["9:16  (Instagram / Shorts)", "16:9  (Landscape)", "1:1  (Square)"])
        vg.addWidget(QLabel("Aspect Ratio"))
        vg.addWidget(self._format_combo)

        self._hw_encode_check = QCheckBox("Use NVIDIA Hardware Encoding (NVENC on GTX 1650)")
        self._hw_encode_check.setChecked(True)
        vg.addWidget(self._hw_encode_check)
        layout.addWidget(vid_group)

        layout.addStretch()
        return tab

    def _build_tts_tab(self) -> QWidget:
        tab = self._scrollable_tab()
        layout = tab.layout()

        for engine_id, engine_name, engine_desc in TTS_ENGINES:
            grp = QGroupBox(engine_name)
            g = QVBoxLayout(grp)
            desc_lbl = QLabel(engine_desc)
            desc_lbl.setStyleSheet("color: #aaa;")
            g.addWidget(desc_lbl)

            status_row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet("color: #FF9800; font-size: 16px;")
            status_row.addWidget(dot)
            status_lbl = QLabel("Checking…")
            status_row.addWidget(status_lbl, stretch=1)
            action_btn = QPushButton("Download Models (~338 MB)" if engine_id == "kokoro" else "Open Voices Folder")
            action_btn.clicked.connect(lambda _, eid=engine_id: self._install_tts(eid))
            status_row.addWidget(action_btn)
            g.addLayout(status_row)

            setattr(self, f"_{engine_id}_dot", dot)
            setattr(self, f"_{engine_id}_status_lbl", status_lbl)
            setattr(self, f"_{engine_id}_btn", action_btn)
            layout.addWidget(grp)

        self._tts_dl_bar = QProgressBar()
        self._tts_dl_bar.hide()
        layout.addWidget(self._tts_dl_bar)

        default_grp = QGroupBox("Default Voice")
        dg = QVBoxLayout(default_grp)
        self._default_voice_combo = QComboBox()
        dg.addWidget(self._default_voice_combo)
        layout.addWidget(default_grp)

        speed_w, self._tts_speed_slider = _make_slider_row(
            "Default Speed", 5, 20, 10, lambda v: f"{v / 10:.1f}×"
        )
        layout.addWidget(speed_w)
        pitch_w, self._tts_pitch_slider = _make_slider_row(
            "Default Pitch", -5, 5, 0, lambda v: f"{v:+d} st"
        )
        layout.addWidget(pitch_w)

        layout.addStretch()
        return tab

    def _build_perf_tab(self) -> QWidget:
        tab = self._scrollable_tab()
        layout = tab.layout()

        ram_w, self._ram_slider = _make_slider_row("Max RAM Budget", 1, 6, 3, "{} GB")
        layout.addWidget(ram_w)

        batch_w, self._batch_slider = _make_slider_row("Frame Batch Size", 1, 48, 24, "{} frames")
        layout.addWidget(batch_w)

        self._unload_llm_check = QCheckBox("Unload LLM from VRAM/RAM right after scene planning (recommended for 8 GB RAM)")
        self._unload_llm_check.setChecked(True)
        layout.addWidget(self._unload_llm_check)

        layout.addStretch()
        return tab

    def _build_about_tab(self) -> QWidget:
        tab = self._scrollable_tab()
        layout = tab.layout()

        about_group = QGroupBox("Stickman Studio")
        ag = QVBoxLayout(about_group)

        lines = [
            ("Version", "1.0.0"),
            ("Creator", "Atharv Hatwar"),
            ("Profile", "https://github.com/atharv01h"),
            ("Repository", "https://github.com/atharv01h/Stickman-Studio"),
            ("License", "MIT License — Copyright (c) 2026 Atharv Hatwar"),
            ("Python", sys.version.split()[0]),
            ("Platform", platform.platform(aliased=True)),
        ]
        for key, val in lines:
            row = QHBoxLayout()
            k_lbl = QLabel(key)
            k_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
            k_lbl.setFixedWidth(90)
            v_lbl = QLabel(val)
            v_lbl.setStyleSheet("color: #4FC3F7;")
            row.addWidget(k_lbl)
            row.addWidget(v_lbl, stretch=1)
            ag.addLayout(row)

        layout.addWidget(about_group)

        sys_group = QGroupBox("Detected Laptop Hardware")
        sg = QVBoxLayout(sys_group)
        sys_text = QPlainTextEdit()
        sys_text.setReadOnly(True)
        sys_text.setMaximumHeight(170)
        sys_text.setPlainText(self._collect_system_info())
        sg.addWidget(sys_text)
        layout.addWidget(sys_group)

        layout.addStretch()
        return tab

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _scrollable_tab(self) -> QWidget:
        outer = QWidget()
        outer_layout = QVBoxLayout(outer)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet("background: #16213e;")
        inner_layout = QVBoxLayout(inner)
        inner_layout.setContentsMargins(14, 14, 14, 14)
        inner_layout.setSpacing(12)

        scroll.setWidget(inner)
        outer_layout.addWidget(scroll)

        outer._inner_layout = inner_layout  # type: ignore[attr-defined]
        outer.layout = lambda: outer._inner_layout  # type: ignore[assignment]
        return outer

    def _collect_system_info(self) -> str:
        info = get_system_summary()
        lines = [
            f"CPU: {info['cpu_name']}",
            f"GPU: {info['gpu_name']}",
            f"RAM: {info['available_ram_mb']} MB free / {info['total_ram_mb']} MB total",
            f"VRAM: {info['free_vram_mb']} MB free / {info['total_vram_mb']} MB total",
            f"Recommended Local AI: {info['recommended_model']}",
            f"Python: {sys.version.split()[0]}",
        ]
        return "\n".join(lines)

    def _refresh_runtime_statuses(self) -> None:
        self._refresh_semantic_brain_status()
        self._test_ollama()
        self._refresh_tts_status()

    def _refresh_semantic_brain_status(self) -> None:
        try:
            from engine.semantic_scene_brain import SemanticSceneBrain
            if SemanticSceneBrain.is_model_available():
                brain = SemanticSceneBrain.get_instance()
                if brain._initialized:
                    self._brain_dot.setStyleSheet("color: #4CAF50; font-size: 18px;")
                    self._brain_status_lbl.setText("Active (MiniLM-L6 Neural Semantic Engine · 22.9 MB · <10ms inference)")
                    self._brain_dl_btn.setText("✓ Brain Verified")
                    self._brain_dl_btn.setEnabled(False)
                    self._brain_test_btn.setEnabled(True)
                    return
            self._brain_dot.setStyleSheet("color: #FF9800; font-size: 18px;")
            self._brain_status_lbl.setText("Model files not downloaded (~22.9 MB required)")
            self._brain_dl_btn.setText("⬇ Download Brain (23 MB)")
            self._brain_dl_btn.setEnabled(True)
            self._brain_test_btn.setEnabled(False)
        except Exception as exc:
            self._brain_dot.setStyleSheet("color: #e94560; font-size: 18px;")
            self._brain_status_lbl.setText(f"Brain status check error: {exc}")

    def _on_download_semantic_brain(self) -> None:
        self._brain_dl_btn.setEnabled(False)
        self._brain_progress_bar.setValue(0)
        self._brain_progress_bar.show()

        self._brain_thread = _SemanticBrainDownloadThread()
        self._brain_thread.progress.connect(self._on_semantic_progress)
        self._brain_thread.finished_ok.connect(self._on_semantic_done)
        self._brain_thread.start()

    def _on_semantic_progress(self, status: str, pct: int) -> None:
        self._brain_status_lbl.setText(status)
        if pct >= 0:
            self._brain_progress_bar.setValue(pct)

    def _on_semantic_done(self, ok: bool) -> None:
        self._brain_progress_bar.hide()
        self._refresh_semantic_brain_status()
        if ok:
            QMessageBox.information(
                self,
                "Neural Brain Ready",
                "The In-Process AI Neural Semantic Brain (MiniLM-L6) is downloaded and fully active!\n"
                "All future script interpretations and visual scene generations will now use deep neural semantic matching.",
            )
        else:
            QMessageBox.warning(
                self,
                "Download Failed",
                "Could not download the Neural Semantic Brain from Hugging Face.\n"
                "Stickman Studio will continue using the high-performance procedural keyword fallback.",
            )

    def _on_test_semantic_brain(self) -> None:
        try:
            from engine.semantic_scene_brain import SemanticSceneBrain
            brain = SemanticSceneBrain.get_instance()
            sample = "He realized all the sacrifices in silence were finally turning into gold."
            met, m_score = brain.match_best_metaphor(sample)
            emo, e_score = brain.match_best_emotion(sample)
            act, a_score = brain.match_best_action(sample)
            res_txt = f"✓ Neural Test: \"{sample[:35]}...\"\n  ➜ Metaphor: {met} (conf: {m_score:.2f})  |  Pose: {act}  |  Emotion: {emo}"
            self._brain_test_res_lbl.setText(res_txt)
            self._brain_test_res_lbl.show()
        except Exception as exc:
            self._brain_test_res_lbl.setText(f"Test failed: {exc}")
            self._brain_test_res_lbl.show()

    def _refresh_tts_status(self) -> None:
        if not self._tts:
            return

        kokoro_ok = self._tts.is_kokoro_available()
        kokoro_pkg = self._tts.is_kokoro_package_installed()
        if kokoro_ok:
            self._kokoro_dot.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self._kokoro_status_lbl.setText("Installed & ready (offline ONNX models present)")
            self._kokoro_btn.setEnabled(False)
            self._kokoro_btn.setText("✓ Installed")
        elif kokoro_pkg:
            self._kokoro_dot.setStyleSheet("color: #FF9800; font-size: 16px;")
            self._kokoro_status_lbl.setText("Package installed — model files needed (~338 MB)")
            self._kokoro_btn.setEnabled(True)
        else:
            self._kokoro_dot.setStyleSheet("color: #e94560; font-size: 16px;")
            self._kokoro_status_lbl.setText("Run pip install kokoro-onnx first")
            self._kokoro_btn.setEnabled(False)

        piper_voices = self._tts._discover_piper_models()
        if piper_voices:
            self._piper_dot.setStyleSheet("color: #4CAF50; font-size: 16px;")
            self._piper_status_lbl.setText(f"Ready ({len(piper_voices)} local .onnx voice(s) found)")
        elif self._tts.is_piper_package_installed():
            self._piper_dot.setStyleSheet("color: #FF9800; font-size: 16px;")
            self._piper_status_lbl.setText("Package ready — place .onnx voice models in voices folder")
        else:
            self._piper_dot.setStyleSheet("color: #e94560; font-size: 16px;")
            self._piper_status_lbl.setText("Not installed")

        # Populate genuinely available voices in Default Voice dropdown
        self._default_voice_combo.clear()
        for v in self._tts.get_available_voices():
            self._default_voice_combo.addItem(f"{v['name']} [{v['backend']}]", v["id"])

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _test_ollama(self) -> None:
        if self._llm and self._llm.check_ollama_running():
            installed = [m.get("name", "") for m in self._llm.get_installed_models()]
            loc = self._llm.get_model_run_location()
            self._ollama_dot.setStyleSheet("color: #4CAF50; font-size: 18px;")
            count_txt = f"{len(installed)} model(s) installed" if installed else "no models downloaded yet"
            self._ollama_status_lbl.setText(f"Connected ({loc}) — {count_txt}")
            # Add any additional installed Ollama models to combo
            known = {self._model_combo.itemData(i) for i in range(self._model_combo.count())}
            for name in installed:
                if name and name not in known:
                    self._model_combo.addItem(f"{name}  (Installed)", name)
        else:
            self._ollama_dot.setStyleSheet("color: #e94560; font-size: 18px;")
            self._ollama_status_lbl.setText("Offline / not running — deterministic planner active")

    def _on_benchmark(self) -> None:
        if not self._llm or not self._llm.check_ollama_running():
            QMessageBox.warning(self, "Ollama Not Running", "Start Ollama (`ollama serve`) to benchmark a model.")
            return
        model_id = self._model_combo.currentData()
        if model_id == "auto":
            model_id = self._llm.get_recommended_model()
        if not self._llm.is_model_downloaded(model_id):
            QMessageBox.information(self, "Model Not Downloaded", f"Download {model_id} first before benchmarking.")
            return

        self._bench_btn.setEnabled(False)
        self._bench_lbl.setText(f"Benchmarking {model_id}…")
        self._bench_thread = _BenchmarkThread(self._llm, model_id)
        self._bench_thread.done.connect(self._on_benchmark_done)
        self._bench_thread.start()

    def _on_benchmark_done(self, res: dict) -> None:
        self._bench_btn.setEnabled(True)
        if res.get("ok"):
            self._bench_lbl.setText(
                f"Benchmark ({res['model']}): {res['tokens_per_sec']} tok/s | "
                f"Startup: {res['startup_ms']} ms | Device: {res['run_location']}"
            )
        else:
            self._bench_lbl.setText("Benchmark failed — ensure model is downloaded and Ollama is responsive.")

    def _update_model_size_label(self, idx: int) -> None:
        m_id = self._model_combo.itemData(idx)
        if not m_id or m_id == "auto":
            rec = self._llm.get_recommended_model() if self._llm else "qwen3.5:0.8b"
            est = self._llm.get_model_size_estimate(rec) if self._llm else "~550 MB"
            self._model_size_lbl.setText(f"Auto selects {rec} ({est})")
            self._download_btn.setEnabled(False)
            return

        est = self._llm.get_model_size_estimate(m_id) if self._llm else "Unknown"
        downloaded = self._llm.is_model_downloaded(m_id) if self._llm else False
        if downloaded:
            self._model_size_lbl.setText(f"{m_id} ({est}) — ✓ Downloaded")
            self._download_btn.setText("✓ Installed")
            self._download_btn.setEnabled(False)
        else:
            self._model_size_lbl.setText(f"Download size: {est} (requires internet once)")
            self._download_btn.setText("⬇  Download Model")
            self._download_btn.setEnabled(True)

    def _on_download_model(self) -> None:
        if not self._llm or not self._llm.check_ollama_running():
            QMessageBox.warning(self, "Ollama Not Running", "Start Ollama first (`ollama serve`), then try downloading.")
            return
        m_id = self._model_combo.currentData()
        if not m_id or m_id == "auto":
            return
        est = self._llm.get_model_size_estimate(m_id)
        reply = QMessageBox.question(
            self,
            "Confirm Model Download",
            f"Download {m_id} (approx. {est}) via Ollama?\n\n"
            "Internet is only needed for this one-time download.",
        )
        if reply != QMessageBox.Yes:
            return

        self._download_btn.setEnabled(False)
        self._download_btn.setText("Downloading…")
        self._pull_bar.setValue(0)
        self._pull_bar.show()
        self._pull_thread = _ModelPullThread(self._llm, m_id)
        self._pull_thread.progress.connect(self._on_pull_progress)
        self._pull_thread.finished_ok.connect(self._on_pull_finished)
        self._pull_thread.start()

    def _on_pull_progress(self, status: str, pct: int) -> None:
        self._model_size_lbl.setText(status[:60])
        if pct >= 0:
            self._pull_bar.setRange(0, 100)
            self._pull_bar.setValue(pct)
        else:
            self._pull_bar.setRange(0, 0)

    def _on_pull_finished(self, ok: bool, model_name: str) -> None:
        self._pull_bar.hide()
        self._test_ollama()
        self._update_model_size_label(self._model_combo.currentIndex())
        if ok:
            QMessageBox.information(self, "Model Ready", f"{model_name} downloaded and ready offline.")
        else:
            QMessageBox.warning(self, "Download Failed", f"Failed to download {model_name}.")

    def _browse_output_dir(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "Select Output Directory")
        if path:
            self._output_dir_edit.setText(path)

    def _install_tts(self, engine_id: str) -> None:
        if not self._tts:
            return
        if engine_id == "kokoro":
            reply = QMessageBox.question(
                self,
                "Download Kokoro-ONNX Models",
                "Download kokoro-v1.0.onnx + voices-v1.0.bin (~338 MB total) for natural offline voices?",
            )
            if reply != QMessageBox.Yes:
                return
            self._kokoro_btn.setEnabled(False)
            self._tts_dl_bar.setRange(0, 100)
            self._tts_dl_bar.setValue(0)
            self._tts_dl_bar.show()
            self._kokoro_thread = _KokoroDownloadThread(self._tts)
            self._kokoro_thread.progress.connect(lambda s, p: (self._kokoro_status_lbl.setText(s), self._tts_dl_bar.setValue(p)))
            self._kokoro_thread.finished_ok.connect(self._on_kokoro_done)
            self._kokoro_thread.start()
        elif engine_id == "piper":
            import os
            import subprocess
            piper_dir = os.path.join(self._tts.models_dir, "piper")
            os.makedirs(piper_dir, exist_ok=True)
            subprocess.Popen(["explorer", os.path.normpath(piper_dir)])
            QMessageBox.information(
                self,
                "Piper Voices Folder",
                f"Place any downloaded Piper `.onnx` + `.onnx.json` files (English or Hindi `hi_IN-*`) into:\n\n{piper_dir}\n\nThey will automatically appear in your voice list.",
            )

    def _on_kokoro_done(self, ok: bool) -> None:
        self._tts_dl_bar.hide()
        self._refresh_tts_status()
        if ok:
            self.voices_updated.emit()
            QMessageBox.information(self, "Kokoro Ready", "Kokoro-ONNX voice models installed and ready offline.")
        else:
            QMessageBox.warning(self, "Download Failed", "Could not download Kokoro models. Check your internet connection.")

    def _on_save(self) -> None:
        self._stop_worker_threads()
        self.accept()

    def reject(self) -> None:
        self._stop_worker_threads()
        super().reject()

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self._stop_worker_threads()
        super().closeEvent(event)

    def _stop_worker_threads(self) -> None:
        for attr in ("_pull_thread", "_bench_thread", "_kokoro_thread", "_brain_thread"):
            th = getattr(self, attr, None)
            if th is not None and th.isRunning():
                th.wait(1500)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_settings(self, settings: dict) -> None:
        s = settings
        model = s.get("llm_model", "auto")
        for i in range(self._model_combo.count()):
            if self._model_combo.itemData(i) == model:
                self._model_combo.setCurrentIndex(i)
                break
        self._update_model_size_label(self._model_combo.currentIndex())

        self._ctx_slider.setValue(int(s.get("llm_context_window", 2048)))
        self._temp_slider.setValue(max(1, min(10, int(round(float(s.get("llm_temperature", 0.7)) * 10)))))

        self._output_dir_edit.setText(s.get("output_dir", ""))
        self._res_combo.setCurrentIndex(1 if "720" in str(s.get("default_resolution", "1080p")) else 0)
        self._fps_combo.setCurrentIndex(1 if int(s.get("default_fps", 24)) == 30 else 0)
        fmt_map = {"9:16": 0, "16:9": 1, "1:1": 2}
        self._format_combo.setCurrentIndex(fmt_map.get(s.get("default_format", "9:16"), 0))
        self._hw_encode_check.setChecked(bool(s.get("use_hardware_encoding", True)))

        def_voice = s.get("default_voice", "")
        for i in range(self._default_voice_combo.count()):
            if self._default_voice_combo.itemData(i) == def_voice:
                self._default_voice_combo.setCurrentIndex(i)
                break
        self._tts_speed_slider.setValue(max(5, min(20, int(round(float(s.get("default_speed", 1.0)) * 10)))))
        self._tts_pitch_slider.setValue(max(-5, min(5, int(s.get("default_pitch", 0)))))

        self._ram_slider.setValue(int(s.get("max_render_ram_gb", 3)))
        self._batch_slider.setValue(int(s.get("frame_batch_size", 24)))
        self._unload_llm_check.setChecked(bool(s.get("unload_llm_after_planning", True)))

    def get_settings(self) -> dict:
        res_labels = ["1080p", "720p"]
        fps_values = [24, 30]
        fmt_labels = ["9:16", "16:9", "1:1"]
        return {
            "llm_model": self._model_combo.currentData() or "auto",
            "llm_context_window": self._ctx_slider.value(),
            "llm_temperature": round(self._temp_slider.value() / 10.0, 2),
            "output_dir": self._output_dir_edit.text().strip(),
            "default_resolution": res_labels[self._res_combo.currentIndex()],
            "default_fps": fps_values[self._fps_combo.currentIndex()],
            "default_format": fmt_labels[self._format_combo.currentIndex()],
            "use_hardware_encoding": self._hw_encode_check.isChecked(),
            "default_voice": self._default_voice_combo.currentData() or "",
            "default_speed": round(self._tts_speed_slider.value() / 10.0, 2),
            "default_pitch": self._tts_pitch_slider.value(),
            "max_render_ram_gb": self._ram_slider.value(),
            "frame_batch_size": self._batch_slider.value(),
            "unload_llm_after_planning": self._unload_llm_check.isChecked(),
        }
