"""
CIS Mode Panel - Settings panel for Cinematic Illustrated Stickman mode.
Created by Atharv Hatwar.
100% Free, Local & Offline. No paid APIs required.
"""
from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

_CIS_PANEL_STYLE = """
QFrame#cisCard {
    background: #0D1424;
    border: 1px solid #1E2B45;
    border-radius: 14px;
    padding: 2px;
}
QLabel#cisTitle {
    color: #FB7185;
    font-size: 13px;
    font-weight: 800;
    background: transparent;
}
QLabel#cisBadge {
    background: #2D1525;
    color: #FDA4AF;
    border: 1px solid #E11D48;
    border-radius: 6px;
    padding: 2px 6px;
    font-size: 10px;
    font-weight: bold;
}
QLabel#cisInfo {
    color: #94A3B8;
    font-size: 11px;
    line-height: 1.4;
    background: #070B14;
    border: 1px solid #162034;
    border-radius: 8px;
    padding: 8px 10px;
}
QLabel#cisSectionLabel {
    color: #38BDF8;
    font-size: 11px;
    font-weight: 700;
    background: transparent;
    margin-top: 4px;
}
QLabel#cisSubLabel {
    color: #94A3B8;
    font-size: 10px;
    background: transparent;
}
QPushButton#cisAccentBtn {
    border: 1px solid #202D44;
    border-radius: 8px;
    padding: 6px 4px;
    font-size: 11px;
    font-weight: 600;
    color: white;
    min-width: 0px;
}
QPushButton#cisAccentBtn:checked {
    border: 2px solid #FFFFFF;
}
QPushButton#cisAccentBtn:hover {
    border-color: #E2E8F0;
}
QComboBox, QLineEdit {
    background: #111A2E;
    border: 1px solid #202E48;
    border-radius: 8px;
    color: #E2E8F0;
    padding: 6px 10px;
    font-size: 11px;
    min-width: 0px;
}
QComboBox:hover, QLineEdit:focus { border-color: #FB7185; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #0D1424;
    color: #E2E8F0;
    border: 1px solid #202B45;
    border-radius: 8px;
    selection-background-color: #F43F5E;
    outline: none;
}
QCheckBox {
    color: #E6EDF3;
    font-size: 11px;
    font-weight: bold;
    background: transparent;
    min-width: 0px;
}
QFrame#cisCtaBox {
    background: #090E1A;
    border: 1px solid #182236;
    border-radius: 10px;
    padding: 2px;
}
"""

_ACCENT_OPTIONS = [
    ("#E94560", "🔴 Red"),
    ("#00897B", "🟢 Teal"),
    ("#F5A623", "🟡 Gold"),
    ("auto",    "✨ Auto"),
]

_CTA_PRESETS = [
    ("Follow this page", "Follow this page for more insights like this."),
    ("Follow for more", "Follow for more daily breakdowns."),
    ("Follow me", "Follow me if this resonated with you today."),
    ("Save & Follow", "Save this reminder and follow for part two."),
    ("Custom…", ""),
]


class CISModePanel(QWidget):
    """Settings panel shown when Cinematic Illustrated Stickman mode is active."""

    settings_changed = Signal(dict)
    auto_speed_changed = Signal(bool)
    illustration_mode_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._accent_color: str = "auto"
        self._illustration_mode: str = "pil"
        self._scene_density: str = "balanced"
        self._setup_ui()

    def _setup_ui(self) -> None:
        self.setStyleSheet(_CIS_PANEL_STYLE)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        card = QFrame()
        card.setObjectName("cisCard")
        v = QVBoxLayout(card)
        v.setSpacing(8)
        v.setContentsMargins(8, 8, 8, 8)

        # Title row
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        icon_lbl = QLabel("✦")
        icon_lbl.setStyleSheet(
            "color: #E94560; font-size: 15px; font-weight: bold; background: transparent;"
        )
        title_row.addWidget(icon_lbl)
        title_lbl = QLabel("Cinematic Illustrated Mode")
        title_lbl.setObjectName("cisTitle")
        title_row.addWidget(title_lbl)

        badge_lbl = QLabel("1,000+ Vectors")
        badge_lbl.setObjectName("cisBadge")
        title_row.addWidget(badge_lbl)

        title_row.addStretch()
        v.addLayout(title_row)

        # Info banner
        info_lbl = QLabel(
            "✦ Full-screen genre-aware B1 stickman storytelling with multi-layer camera & vector "
            "animations unique to each script. 100% local, free & offline."
        )
        info_lbl.setObjectName("cisInfo")
        info_lbl.setWordWrap(True)
        v.addWidget(info_lbl)

        # Accent color selector
        accent_lbl = QLabel("Accent Highlight")
        accent_lbl.setObjectName("cisSectionLabel")
        v.addWidget(accent_lbl)

        accent_row = QHBoxLayout()
        accent_row.setSpacing(4)
        accent_row.setContentsMargins(0, 0, 0, 0)
        self._accent_btn_group = QButtonGroup(self)
        self._accent_btn_group.setExclusive(True)
        self._accent_btns: dict[str, QPushButton] = {}

        for color, label in _ACCENT_OPTIONS:
            btn = QPushButton(label)
            btn.setObjectName("cisAccentBtn")
            btn.setCheckable(True)
            btn.setMinimumWidth(0)
            if color == "auto":
                btn.setStyleSheet(
                    "QPushButton#cisAccentBtn { background: #21262D; color: #E6EDF3; }"
                    "QPushButton#cisAccentBtn:checked { background: #30363D; border-color: #A78BFA; }"
                )
            else:
                btn.setStyleSheet(
                    f"QPushButton#cisAccentBtn {{ background: {color}; }}"
                    f"QPushButton#cisAccentBtn:checked {{ border-color: white; }}"
                )
            btn.clicked.connect(lambda _, c=color: self._on_accent_selected(c))
            self._accent_btn_group.addButton(btn)
            self._accent_btns[color] = btn
            accent_row.addWidget(btn, stretch=1)

        # Default: Auto (adapts per reel genre)
        self._accent_btns["auto"].setChecked(True)
        v.addLayout(accent_row)

        # Visual World / Animation Style combo
        style_lbl = QLabel("Visual World & Style")
        style_lbl.setObjectName("cisSectionLabel")
        v.addWidget(style_lbl)

        self._visual_style_combo = QComboBox()
        self._visual_style_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._visual_style_combo.addItem("✨ Auto (1000+ Multi-Domain Visuals)", "auto")
        self._visual_style_combo.addItem("💼 Wealth, Finance & Business", "wealth_business")
        self._visual_style_combo.addItem("💻 Tech, Coding & AI Systems", "tech_coding_ai")
        self._visual_style_combo.addItem("🏋️ Fitness, Health & Athletics", "fitness_health_bio")
        self._visual_style_combo.addItem("🏛️ Stoicism, Philosophy & History", "stoicism_philosophy_history")
        self._visual_style_combo.addItem("⚡ Habits, Focus & Productivity", "habits_productivity_focus")
        self._visual_style_combo.addItem("🚀 Motivation & Mental Toughness", "motivation_mindset_leadership")
        self._visual_style_combo.addItem("🌌 Science, Space & Cosmos", "science_space_nature")
        self._visual_style_combo.addItem("🎭 Relatable Daily Life & Comedy", "comedy_daily_relatable")
        self._visual_style_combo.addItem("🧠 Dark Psychology & Behavior", "psychology_human_behavior")
        self._visual_style_combo.addItem("📓 Classic White Sketchbook (B1 Ink)", "B1")
        self._visual_style_combo.addItem("📰 Warm Editorial (B2 Cream)", "B2")
        self._visual_style_combo.addItem("🌌 Obsidian Dark Chalkboard (B3 Neon)", "B3")
        self._visual_style_combo.setCurrentIndex(0)
        self._visual_style_combo.currentIndexChanged.connect(self._on_settings_changed)
        v.addWidget(self._visual_style_combo)

        # Illustration engine combo
        illus_lbl = QLabel("Illustration Engine")
        illus_lbl.setObjectName("cisSectionLabel")
        v.addWidget(illus_lbl)

        self._illus_combo = QComboBox()
        self._illus_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._illus_combo.addItem("✏️ Hand-Drawn B1 (Offline & Free)", "pil")
        self._illus_combo.addItem("🎨 Local Diffusion (LCM DreamShaper)", "lcm")
        self._illus_combo.setCurrentIndex(0)
        self._illus_combo.currentIndexChanged.connect(self._on_illus_mode_changed)
        v.addWidget(self._illus_combo)

        # Scene pacing & Voice Speed row
        pacing_lbl = QLabel("Scene Pacing & Voice Speed")
        pacing_lbl.setObjectName("cisSectionLabel")
        v.addWidget(pacing_lbl)

        self._density_combo = QComboBox()
        self._density_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._density_combo.addItem("⬜ Balanced Scenes (Default)", "balanced")
        self._density_combo.addItem("⬛ Fast Paced (More scenes)", "detailed")
        self._density_combo.addItem("▦ Slow & Deep (Fewer scenes)", "compact")
        self._density_combo.setCurrentIndex(0)
        self._density_combo.currentIndexChanged.connect(self._on_settings_changed)
        v.addWidget(self._density_combo)

        self._speed_mode_combo = QComboBox()
        self._speed_mode_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self._speed_mode_combo.addItem("✨ Voice Speed: Auto (Smart Fit)", "auto")
        self._speed_mode_combo.addItem("🎚️ Voice Speed: Manual Slider", "manual")
        self._speed_mode_combo.setCurrentIndex(0)
        self._speed_mode_combo.currentIndexChanged.connect(self._on_speed_mode_changed)
        v.addWidget(self._speed_mode_combo)

        # Optional Ending Follow / CTA Screen section
        cta_box = QFrame()
        cta_box.setObjectName("cisCtaBox")
        cta_v = QVBoxLayout(cta_box)
        cta_v.setContentsMargins(8, 8, 8, 8)
        cta_v.setSpacing(6)

        self._cta_enable_chk = QCheckBox("Ending Follow / CTA Screen")
        self._cta_enable_chk.setChecked(False)
        self._cta_enable_chk.toggled.connect(self._on_cta_toggled)
        cta_v.addWidget(self._cta_enable_chk)

        self._cta_fields_widget = QWidget()
        cf_v = QVBoxLayout(self._cta_fields_widget)
        cf_v.setContentsMargins(0, 2, 0, 0)
        cf_v.setSpacing(5)

        preset_lbl = QLabel("Quick Preset")
        preset_lbl.setObjectName("cisSubLabel")
        cf_v.addWidget(preset_lbl)

        self._cta_preset_combo = QComboBox()
        self._cta_preset_combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        for screen_txt, audio_txt in _CTA_PRESETS:
            self._cta_preset_combo.addItem(screen_txt, (screen_txt, audio_txt))
        self._cta_preset_combo.currentIndexChanged.connect(self._on_cta_preset_changed)
        cf_v.addWidget(self._cta_preset_combo)

        screen_lbl = QLabel("Last Screen Text")
        screen_lbl.setObjectName("cisSubLabel")
        cf_v.addWidget(screen_lbl)

        self._cta_text_edit = QLineEdit("Follow this page")
        self._cta_text_edit.setMinimumWidth(0)
        self._cta_text_edit.setPlaceholderText("e.g. Follow me / Follow this page")
        self._cta_text_edit.textChanged.connect(lambda _: self._on_settings_changed())
        cf_v.addWidget(self._cta_text_edit)

        audio_lbl = QLabel("Last Spoken Audio Text")
        audio_lbl.setObjectName("cisSubLabel")
        cf_v.addWidget(audio_lbl)

        self._cta_audio_edit = QLineEdit("Follow this page for more insights like this.")
        self._cta_audio_edit.setMinimumWidth(0)
        self._cta_audio_edit.setPlaceholderText("Blank = speak screen text")
        self._cta_audio_edit.textChanged.connect(lambda _: self._on_settings_changed())
        cf_v.addWidget(self._cta_audio_edit)

        self._cta_fields_widget.setVisible(False)
        cta_v.addWidget(self._cta_fields_widget)
        v.addWidget(cta_box)

        outer.addWidget(card)

    def _on_accent_selected(self, color: str) -> None:
        self._accent_color = color
        self._on_settings_changed()

    def _on_speed_mode_changed(self) -> None:
        is_auto = (self._speed_mode_combo.currentData() == "auto")
        self.auto_speed_changed.emit(is_auto)
        self._on_settings_changed()

    def _on_illus_mode_changed(self) -> None:
        mode = self._illus_combo.currentData() or "pil"
        self._illustration_mode = mode
        self.illustration_mode_changed.emit(mode)
        self._on_settings_changed()

    def set_illustration_mode(self, mode: str) -> None:
        target = "lcm" if str(mode or "").lower() == "lcm" else "pil"
        self._illus_combo.blockSignals(True)
        for i in range(self._illus_combo.count()):
            if self._illus_combo.itemData(i) == target:
                self._illus_combo.setCurrentIndex(i)
                break
        self._illus_combo.blockSignals(False)
        self._illustration_mode = target

    def _on_cta_toggled(self, checked: bool) -> None:
        self._cta_fields_widget.setVisible(bool(checked))
        self._on_settings_changed()

    def _on_cta_preset_changed(self, _idx: int) -> None:
        data = self._cta_preset_combo.currentData()
        if not data:
            return
        screen_txt, audio_txt = data
        if screen_txt != "Custom…":
            self._cta_text_edit.blockSignals(True)
            self._cta_text_edit.setText(screen_txt)
            self._cta_text_edit.blockSignals(False)
            self._cta_audio_edit.blockSignals(True)
            self._cta_audio_edit.setText(audio_txt)
            self._cta_audio_edit.blockSignals(False)
        self._on_settings_changed()

    def set_auto_speed(self, enabled: bool) -> None:
        target = "auto" if enabled else "manual"
        self._speed_mode_combo.blockSignals(True)
        for i in range(self._speed_mode_combo.count()):
            if self._speed_mode_combo.itemData(i) == target:
                self._speed_mode_combo.setCurrentIndex(i)
                break
        self._speed_mode_combo.blockSignals(False)

    def set_cis_settings(self, settings: dict) -> None:
        """Restore persisted CIS panel settings cleanly."""
        if not settings:
            return
        acc = settings.get("cis_accent_color")
        if acc in self._accent_btns:
            self._accent_btns[acc].setChecked(True)
            self._accent_color = acc
        if "cis_visual_style" in settings:
            target_vs = str(settings["cis_visual_style"] or "auto")
            self._visual_style_combo.blockSignals(True)
            for i in range(self._visual_style_combo.count()):
                if self._visual_style_combo.itemData(i) == target_vs:
                    self._visual_style_combo.setCurrentIndex(i)
                    break
            self._visual_style_combo.blockSignals(False)
        if "cis_illustration_mode" in settings:
            self.set_illustration_mode(str(settings["cis_illustration_mode"] or "pil"))
        if "cis_auto_speed" in settings:
            self.set_auto_speed(bool(settings["cis_auto_speed"]))
        if "cis_enable_cta" in settings:
            self._cta_enable_chk.setChecked(bool(settings["cis_enable_cta"]))
        if settings.get("cis_cta_text"):
            self._cta_text_edit.setText(str(settings["cis_cta_text"]))
        if "cis_cta_audio_text" in settings:
            self._cta_audio_edit.setText(str(settings["cis_cta_audio_text"] or ""))

    def _on_settings_changed(self) -> None:
        self._illustration_mode = self._illus_combo.currentData() or "pil"
        self._scene_density = self._density_combo.currentData() or "balanced"
        self.settings_changed.emit(self.get_cis_settings())

    def get_cis_settings(self) -> dict:
        """Return the current CIS-specific settings dict."""
        return {
            "cis_accent_color": self._accent_color,
            "cis_visual_style": self._visual_style_combo.currentData() or "auto",
            "cis_illustration_mode": self._illus_combo.currentData() or "pil",
            "cis_scene_density": self._density_combo.currentData() or "balanced",
            "cis_auto_speed": (self._speed_mode_combo.currentData() == "auto"),
            "cis_enable_cta": self._cta_enable_chk.isChecked(),
            "cis_cta_text": self._cta_text_edit.text().strip() or "Follow this page",
            "cis_cta_audio_text": self._cta_audio_edit.text().strip(),
        }
