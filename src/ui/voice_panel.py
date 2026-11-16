"""
Voice Panel - Voice selection, preview, and audio settings.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

# ---------------------------------------------------------------------------
# Voice card
# ---------------------------------------------------------------------------

GENDER_ICONS: dict[str, str] = {
    "male": "♂",
    "female": "♀",
    "neutral": "⚥",
}


_VOICE_PANEL_QSS = """
QFrame#voiceCard {
    background: #131A2B;
    border: 1px solid #263248;
    border-radius: 10px;
}
QFrame#voiceCard:hover {
    background: #192238;
    border-color: #3B4970;
}
QFrame#voiceCard[selected="true"] {
    background: #1E2540;
    border: 2px solid #8B5CF6;
}
QPushButton#voicePrevBtn {
    background: #1E293B;
    color: #38BDF8;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
    font-weight: bold;
}
QPushButton#voicePrevBtn:hover {
    background: #0D293A;
    border-color: #38BDF8;
    color: #FFFFFF;
}
"""


class VoiceCard(QFrame):
    """Compact card representing a single voice option."""

    selected = Signal(str)   # voice_id
    preview = Signal(str)    # voice_id

    def __init__(self, voice: dict, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._voice_id: str = voice.get("id", "")
        self._voice_data: dict = voice
        self._is_selected: bool = False
        self.setObjectName("voiceCard")
        self.setProperty("selected", "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)

        # Gender icon
        gender = voice.get("gender", "neutral").lower()
        icon_lbl = QLabel(GENDER_ICONS.get(gender, "⚥"))
        icon_lbl.setFont(QFont("Segoe UI", 16))
        icon_lbl.setFixedWidth(28)
        icon_lbl.setStyleSheet("background: transparent;")
        h.addWidget(icon_lbl)

        # Name + tags
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(voice.get("name", self._voice_id))
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
        name_lbl.setStyleSheet("color: #F1F5F9; background: transparent;")
        info.addWidget(name_lbl)

        tags = voice.get("tags", [])
        if isinstance(tags, list) and tags:
            tags_str = "  ".join(f"#{t}" for t in tags[:3])
        else:
            lang = voice.get("language", "en")
            pers = voice.get("personality", "natural")
            backend = voice.get("backend", "local")
            tags_str = f"#{lang}  #{pers}  #{backend}"
        tag_lbl = QLabel(tags_str)
        tag_lbl.setFont(QFont("Segoe UI", 8))
        tag_lbl.setStyleSheet("color: #38BDF8; background: transparent;")
        info.addWidget(tag_lbl)
        h.addLayout(info, stretch=1)

        # Preview button
        prev_btn = QPushButton("▶ Preview")
        prev_btn.setObjectName("voicePrevBtn")
        prev_btn.setFixedWidth(82)
        prev_btn.clicked.connect(lambda: self.preview.emit(self._voice_id))
        h.addWidget(prev_btn)

    # ------------------------------------------------------------------
    @property
    def voice_id(self) -> str:
        return self._voice_id

    def set_selected(self, selected: bool) -> None:
        if self._is_selected == selected:
            return
        self._is_selected = selected
        self.setProperty("selected", "true" if selected else "false")
        st = self.style()
        if st:
            st.unpolish(self)
            st.polish(self)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.selected.emit(self._voice_id)
        super().mousePressEvent(event)


# ---------------------------------------------------------------------------
# Voice Panel
# ---------------------------------------------------------------------------

class VoicePanel(QWidget):
    """Left: scrollable voice list. Right: audio settings."""

    voice_changed = Signal(str)           # voice_id
    preview_requested = Signal(str, str)  # voice_id, preview_text
    auto_speed_changed = Signal(bool)     # auto_speed enabled
    dialogue_mode_changed = Signal(bool)  # dialogue_mode enabled
    speaker_names_changed = Signal(str, str)  # name1, name2

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, VoiceCard] = {}
        self._selected_voice_id: str = ""
        self._preview_callback: Optional[Callable[[str, str], None]] = None
        self.setStyleSheet(_VOICE_PANEL_QSS)
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle { background: #1E293B; }")

        # ---- Left: voice list ----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(4)

        voices_label = QLabel("Available Voices")
        voices_label.setObjectName("section")
        voices_label.setFont(QFont("Segoe UI", 12, QFont.Bold))
        left_layout.addWidget(voices_label)

        # Search + language / gender / personality filters
        filter_row = QHBoxLayout()
        filter_row.setSpacing(6)
        self._search_edit = QLineEdit()
        self._search_edit.setPlaceholderText("🔍  Search voices…")
        self._search_edit.textChanged.connect(lambda: self._filter_voices(self._search_edit.text()))
        filter_row.addWidget(self._search_edit, stretch=1)

        self._lang_combo = QComboBox()
        self._lang_combo.addItem("All Languages", "all")
        self._lang_combo.currentIndexChanged.connect(lambda: self._filter_voices(self._search_edit.text()))
        filter_row.addWidget(self._lang_combo)
        left_layout.addLayout(filter_row)

        sub_filter_row = QHBoxLayout()
        sub_filter_row.setSpacing(6)
        self._gender_combo = QComboBox()
        self._gender_combo.addItem("All Genders", "all")
        self._gender_combo.addItem("Female", "female")
        self._gender_combo.addItem("Male", "male")
        self._gender_combo.currentIndexChanged.connect(lambda: self._filter_voices(self._search_edit.text()))
        sub_filter_row.addWidget(self._gender_combo)

        self._pers_combo = QComboBox()
        self._pers_combo.addItem("All Personalities", "all")
        self._pers_combo.addItem("Natural", "natural")
        self._pers_combo.addItem("Calm", "calm")
        self._pers_combo.addItem("Energetic", "energetic")
        self._pers_combo.addItem("Deep", "deep")
        self._pers_combo.addItem("Fast", "fast")
        self._pers_combo.currentIndexChanged.connect(lambda: self._filter_voices(self._search_edit.text()))
        sub_filter_row.addWidget(self._pers_combo)
        left_layout.addLayout(sub_filter_row)

        # Scroll area for cards
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._scroll.setStyleSheet("QScrollArea { border: none; }")

        self._list_container = QWidget()
        self._list_container.setStyleSheet("background: transparent;")
        self._list_layout = QVBoxLayout(self._list_container)
        self._list_layout.setAlignment(Qt.AlignTop)
        self._list_layout.setSpacing(6)
        self._list_layout.setContentsMargins(2, 2, 2, 2)
        self._scroll.setWidget(self._list_container)
        left_layout.addWidget(self._scroll, stretch=1)

        splitter.addWidget(left_widget)

        # ---- Right: settings ----
        right_widget = QWidget()
        right_widget.setMinimumWidth(320)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 4, 8, 4)
        right_layout.setSpacing(8)

        # Header: Mode Switcher (Solo vs Two-Voice Dialogue)
        header_row = QHBoxLayout()
        settings_lbl = QLabel("Voice Engine")
        settings_lbl.setObjectName("section")
        settings_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        header_row.addWidget(settings_lbl)
        header_row.addStretch()

        self._mode_solo_btn = QPushButton("👤 Solo Voice")
        self._mode_solo_btn.setCheckable(True)
        self._mode_solo_btn.setChecked(True)
        self._mode_solo_btn.setStyleSheet("""
            QPushButton { background: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-weight: bold; }
            QPushButton:checked { background: #0284C7; color: #FFFFFF; border-color: #38BDF8; }
        """)
        self._mode_dialogue_btn = QPushButton("👥 Two-Voice Dialogue")
        self._mode_dialogue_btn.setCheckable(True)
        self._mode_dialogue_btn.setStyleSheet("""
            QPushButton { background: #1E293B; color: #94A3B8; border: 1px solid #334155; border-radius: 6px; padding: 4px 10px; font-weight: bold; }
            QPushButton:checked { background: #8B5CF6; color: #FFFFFF; border-color: #C084FC; }
        """)
        self._mode_solo_btn.clicked.connect(lambda: self._set_dialogue_ui_active(False))
        self._mode_dialogue_btn.clicked.connect(lambda: self._set_dialogue_ui_active(True))
        header_row.addWidget(self._mode_solo_btn)
        header_row.addWidget(self._mode_dialogue_btn)
        right_layout.addLayout(header_row)

        # --- Container 1: Solo Voice Settings ---
        self._solo_container = QWidget()
        solo_v = QVBoxLayout(self._solo_container)
        solo_v.setContentsMargins(0, 0, 0, 0)
        solo_v.setSpacing(8)

        speed_group = self._make_slider_group(
            "Speed", "speed", 5, 20, 10, lambda v: f"{v / 10:.1f}×"
        )
        self._auto_speed_chk = QCheckBox("Auto")
        self._auto_speed_chk.setToolTip("Automatically adjust speaking speed to match your script and target video duration")
        self._auto_speed_chk.setStyleSheet("QCheckBox { color: #58A6FF; font-size: 11px; font-weight: bold; }")
        self._auto_speed_chk.toggled.connect(self._on_auto_speed_toggled)
        speed_header = speed_group.layout().itemAt(0).layout()
        speed_header.insertWidget(1, self._auto_speed_chk)
        self._speed_slider.valueChanged.connect(self._on_master_speed_changed)
        solo_v.addWidget(speed_group)

        solo_v.addWidget(self._make_slider_group(
            "Pitch", "pitch", -5, 5, 0, lambda v: f"{v:+d} st"
        ))
        solo_v.addWidget(self._make_slider_group(
            "Volume", "volume", 0, 100, 85, lambda v: f"{v}%"
        ))

        preview_group = QGroupBox("Solo Preview")
        preview_group.setStyleSheet(
            "QGroupBox { border: 1px solid #0f3460; border-radius: 6px; margin-top: 6px; color: #4FC3F7; font-weight: bold; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        pg_layout = QVBoxLayout(preview_group)
        self._preview_text = QLineEdit("The quick brown fox jumps over the lazy dog.")
        self._preview_text.setPlaceholderText("Enter preview text…")
        pg_layout.addWidget(self._preview_text)
        self._preview_btn = QPushButton("▶  Preview Selected Voice")
        self._preview_btn.clicked.connect(self._on_preview_clicked)
        pg_layout.addWidget(self._preview_btn)
        solo_v.addWidget(preview_group)

        self._selected_info_lbl = QLabel("No voice selected")
        self._selected_info_lbl.setStyleSheet("color: #888; font-style: italic;")
        self._selected_info_lbl.setWordWrap(True)
        solo_v.addWidget(self._selected_info_lbl)
        right_layout.addWidget(self._solo_container)

        # --- Container 2: Two-Voice Dialogue Settings ---
        self._dialogue_container = QWidget()
        self._dialogue_container.setVisible(False)
        dial_v = QVBoxLayout(self._dialogue_container)
        dial_v.setContentsMargins(0, 0, 0, 0)
        dial_v.setSpacing(8)

        # Speaker 1 Box
        s1_box = QGroupBox("Speaker 1 (e.g. Question / Seeker)")
        s1_box.setStyleSheet(
            "QGroupBox { border: 1px solid #2563EB; border-radius: 8px; margin-top: 6px; color: #60A5FA; font-weight: bold; padding: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        s1_layout = QVBoxLayout(s1_box)
        s1_layout.setSpacing(4)
        s1_name_row = QHBoxLayout()
        s1_name_lbl = QLabel("Name:")
        s1_name_lbl.setStyleSheet("color: #E2E8F0; font-weight: normal;")
        self._s1_name_edit = QLineEdit("Alex")
        self._s1_name_edit.setPlaceholderText("Character 1 name (e.g. Alex)")
        self._s1_name_edit.textChanged.connect(self._emit_speaker_names)
        s1_name_row.addWidget(s1_name_lbl)
        s1_name_row.addWidget(self._s1_name_edit, stretch=1)
        s1_layout.addLayout(s1_name_row)

        self._s1_voice_combo = QComboBox()
        s1_layout.addWidget(self._s1_voice_combo)

        s1_ctrl_row = QHBoxLayout()
        s1_ctrl_row.addWidget(self._make_slider_group("Speed", "s1_speed", 5, 20, 10, lambda v: f"{v / 10:.1f}×"))
        s1_ctrl_row.addWidget(self._make_slider_group("Pitch", "s1_pitch", -5, 5, 0, lambda v: f"{v:+d} st"))
        s1_layout.addLayout(s1_ctrl_row)

        self._s1_prev_btn = QPushButton("▶ Preview Speaker 1")
        self._s1_prev_btn.clicked.connect(self._preview_speaker1)
        s1_layout.addWidget(self._s1_prev_btn)
        dial_v.addWidget(s1_box)

        # Speaker 2 Box
        s2_box = QGroupBox("Speaker 2 (e.g. Guide / Emotional Clarity)")
        s2_box.setStyleSheet(
            "QGroupBox { border: 1px solid #7C3AED; border-radius: 8px; margin-top: 6px; color: #C084FC; font-weight: bold; padding: 6px; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        s2_layout = QVBoxLayout(s2_box)
        s2_layout.setSpacing(4)
        s2_name_row = QHBoxLayout()
        s2_name_lbl = QLabel("Name:")
        s2_name_lbl.setStyleSheet("color: #E2E8F0; font-weight: normal;")
        self._s2_name_edit = QLineEdit("Maya")
        self._s2_name_edit.setPlaceholderText("Character 2 name (e.g. Maya)")
        self._s2_name_edit.textChanged.connect(self._emit_speaker_names)
        s2_name_row.addWidget(s2_name_lbl)
        s2_name_row.addWidget(self._s2_name_edit, stretch=1)
        s2_layout.addLayout(s2_name_row)

        self._s2_voice_combo = QComboBox()
        s2_layout.addWidget(self._s2_voice_combo)

        s2_ctrl_row = QHBoxLayout()
        s2_ctrl_row.addWidget(self._make_slider_group("Speed", "s2_speed", 5, 20, 10, lambda v: f"{v / 10:.1f}×"))
        s2_ctrl_row.addWidget(self._make_slider_group("Pitch", "s2_pitch", -5, 5, 0, lambda v: f"{v:+d} st"))
        s2_layout.addLayout(s2_ctrl_row)

        self._s2_prev_btn = QPushButton("▶ Preview Speaker 2")
        self._s2_prev_btn.clicked.connect(self._preview_speaker2)
        s2_layout.addWidget(self._s2_prev_btn)
        dial_v.addWidget(s2_box)

        # Dialogue Options
        self._address_by_name_chk = QCheckBox("Characters address each other by name in script")
        self._address_by_name_chk.setChecked(True)
        self._address_by_name_chk.setStyleSheet("QCheckBox { color: #38BDF8; font-size: 11px; font-weight: bold; }")
        dial_v.addWidget(self._address_by_name_chk)

        self._acoustic_mastering_chk = QCheckBox("Studio Acoustic Mastering (Chest Warmth + De-harshing)")
        self._acoustic_mastering_chk.setChecked(True)
        self._acoustic_mastering_chk.setStyleSheet("QCheckBox { color: #34D399; font-size: 11px; font-weight: bold; }")
        dial_v.addWidget(self._acoustic_mastering_chk)

        right_layout.addWidget(self._dialogue_container)

        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([320, 280])

        root.addWidget(splitter)

    # ------------------------------------------------------------------
    def _make_slider_group(
        self,
        label: str,
        attr_name: str,
        minimum: int,
        maximum: int,
        default: int,
        fmt: Callable[[int], str],
    ) -> QWidget:
        """Return a widget containing a labelled slider with a value display."""
        group = QWidget()
        v = QVBoxLayout(group)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(2)

        h = QHBoxLayout()
        h.setContentsMargins(0, 0, 0, 0)
        lbl = QLabel(label)
        lbl.setFont(QFont("Segoe UI", 10))
        val_lbl = QLabel(fmt(default))
        val_lbl.setFont(QFont("Segoe UI", 10))
        val_lbl.setFixedWidth(50)
        val_lbl.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        h.addWidget(lbl)
        h.addStretch()
        h.addWidget(val_lbl)
        v.addLayout(h)

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(minimum)
        slider.setMaximum(maximum)
        slider.setValue(default)
        slider.valueChanged.connect(lambda val, lbl=val_lbl, f=fmt: lbl.setText(f(val)))
        v.addWidget(slider)

        # Store references
        setattr(self, f"_{attr_name}_slider", slider)
        setattr(self, f"_{attr_name}_val_lbl", val_lbl)
        return group

    def _on_auto_speed_toggled(self, checked: bool) -> None:
        self._speed_slider.setEnabled(not checked)
        if checked:
            self._speed_val_lbl.setText("Auto")
        else:
            self._speed_val_lbl.setText(f"{self._speed_slider.value() / 10:.1f}×")
        self.auto_speed_changed.emit(bool(checked))

    def _on_master_speed_changed(self, val: int) -> None:
        # Keep Speaker 1 and Speaker 2 in sync with master voice speed unless manually decoupled
        if hasattr(self, "_s1_speed_slider"):
            self._s1_speed_slider.blockSignals(True)
            self._s1_speed_slider.setValue(val)
            self._s1_speed_slider.blockSignals(False)
            if hasattr(self, "_s1_speed_val_lbl"):
                self._s1_speed_val_lbl.setText(f"{val / 10:.1f}×")
        if hasattr(self, "_s2_speed_slider"):
            self._s2_speed_slider.blockSignals(True)
            self._s2_speed_slider.setValue(val)
            self._s2_speed_slider.blockSignals(False)
            if hasattr(self, "_s2_speed_val_lbl"):
                self._s2_speed_val_lbl.setText(f"{val / 10:.1f}×")

    def set_auto_speed(self, enabled: bool) -> None:
        self._auto_speed_chk.setChecked(bool(enabled))

    # ------------------------------------------------------------------
    def _on_preview_clicked(self) -> None:
        text = self._preview_text.text().strip()
        if not text:
            text = "Hello, this is a voice preview."
        self.preview_requested.emit(self._selected_voice_id, text)
        if self._preview_callback:
            self._preview_callback(self._selected_voice_id, text)

    # ------------------------------------------------------------------
    def _filter_voices(self, query: str) -> None:
        q = query.lower().strip()
        lang_filter = self._lang_combo.currentData() if hasattr(self, "_lang_combo") else "all"
        gen_filter = self._gender_combo.currentData() if hasattr(self, "_gender_combo") else "all"
        pers_filter = self._pers_combo.currentData() if hasattr(self, "_pers_combo") else "all"
        self._list_container.setUpdatesEnabled(False)
        try:
            for vid, card in self._cards.items():
                vd = card._voice_data
                haystack = " ".join([
                    vid,
                    str(vd.get("name", "")),
                    str(vd.get("gender", "")),
                    str(vd.get("personality", "")),
                    str(vd.get("language", "")),
                    str(vd.get("backend", "")),
                    " ".join(vd.get("tags", [])),
                ]).lower()
                lang_ok = (lang_filter == "all") or (str(vd.get("language", "en")).lower() == lang_filter)
                gen_ok = (gen_filter == "all") or (str(vd.get("gender", "")).lower() == gen_filter)
                pers_ok = (pers_filter == "all") or (pers_filter in str(vd.get("personality", "")).lower())
                card.setVisible((not q or q in haystack) and lang_ok and gen_ok and pers_ok)
        finally:
            self._list_container.setUpdatesEnabled(True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_voices(self, voices: list[dict]) -> None:
        """Populate the voice list from genuinely installed local voices."""
        self._list_container.setUpdatesEnabled(False)
        try:
            for card in self._cards.values():
                self._list_layout.removeWidget(card)
                card.deleteLater()
            self._cards.clear()

            # Refresh genuinely supported languages in dropdown across all installed models
            if hasattr(self, "_lang_combo"):
                self._lang_combo.blockSignals(True)
                self._lang_combo.clear()
                self._lang_combo.addItem("All Languages", "all")
                langs = sorted({str(v.get("language", "en")).lower() for v in voices})
                lang_names = {
                    "en": "English (en)",
                    "hi": "Hindi / Hinglish (hi)",
                    "es": "Spanish (es)",
                    "fr": "French (fr)",
                    "it": "Italian (it)",
                    "ja": "Japanese (ja)",
                    "pt": "Portuguese (pt)",
                    "zh": "Mandarin Chinese (zh)",
                }
                for lc in langs:
                    self._lang_combo.addItem(lang_names.get(lc, lc.upper()), lc)
                self._lang_combo.blockSignals(False)

            # Populate Speaker 1 and Speaker 2 dropdowns
            if hasattr(self, "_s1_voice_combo") and hasattr(self, "_s2_voice_combo"):
                self._s1_voice_combo.blockSignals(True)
                self._s2_voice_combo.blockSignals(True)
                self._s1_voice_combo.clear()
                self._s2_voice_combo.clear()

                for v in voices:
                    v_name = v.get("name", v["id"])
                    self._s1_voice_combo.addItem(f"{v_name}", v["id"])
                    self._s2_voice_combo.addItem(f"{v_name}", v["id"])

                # Pick smart defaults (Male Seeker for Speaker 1, Female Warm for Speaker 2)
                s1_default_idx = 0
                s2_default_idx = 0
                for idx, v in enumerate(voices):
                    vid = v.get("id", "")
                    if "blend:male_introspective" in vid or vid == "am_michael" or (s1_default_idx == 0 and v.get("gender") == "male"):
                        s1_default_idx = idx
                    if "blend:female_warm" in vid or vid == "af_heart" or (s2_default_idx == 0 and v.get("gender") == "female"):
                        s2_default_idx = idx

                self._s1_voice_combo.setCurrentIndex(s1_default_idx)
                self._s2_voice_combo.setCurrentIndex(s2_default_idx)
                self._s1_voice_combo.blockSignals(False)
                self._s2_voice_combo.blockSignals(False)

            for voice in voices:
                card = VoiceCard(voice)
                card.selected.connect(self._on_voice_selected)
                card.preview.connect(self._on_card_preview)
                self._list_layout.addWidget(card)
                self._cards[voice["id"]] = card
        finally:
            self._list_container.setUpdatesEnabled(True)

        if voices:
            self._on_voice_selected(voices[0]["id"])

    def _set_dialogue_ui_active(self, active: bool) -> None:
        active = bool(active)
        if hasattr(self, "_mode_dialogue_btn") and self._mode_dialogue_btn.isChecked() == active and self._dialogue_container.isVisible() == active:
            return
        self._mode_solo_btn.setChecked(not active)
        self._mode_dialogue_btn.setChecked(active)
        self._solo_container.setVisible(not active)
        self._dialogue_container.setVisible(active)
        self.dialogue_mode_changed.emit(active)

    def set_dialogue_mode(self, active: bool) -> None:
        self._set_dialogue_ui_active(bool(active))

    def _emit_speaker_names(self) -> None:
        n1 = self._s1_name_edit.text().strip() or "Alex" if hasattr(self, "_s1_name_edit") else "Alex"
        n2 = self._s2_name_edit.text().strip() or "Maya" if hasattr(self, "_s2_name_edit") else "Maya"
        self.speaker_names_changed.emit(n1, n2)

    def get_speaker_names(self) -> tuple[str, str]:
        n1 = self._s1_name_edit.text().strip() or "Alex" if hasattr(self, "_s1_name_edit") else "Alex"
        n2 = self._s2_name_edit.text().strip() or "Maya" if hasattr(self, "_s2_name_edit") else "Maya"
        return n1, n2

    def get_speaker_voice_settings(self, speaker_idx: int = 1) -> dict:
        master_speed = self._speed_slider.value() / 10.0 if hasattr(self, "_speed_slider") else 1.0
        if speaker_idx == 1:
            vid = self._s1_voice_combo.currentData() if hasattr(self, "_s1_voice_combo") else self._selected_voice_id
            sp = (self._s1_speed_slider.value() / 10.0) if hasattr(self, "_s1_speed_slider") else master_speed
            pt = float(self._s1_pitch_slider.value()) if hasattr(self, "_s1_pitch_slider") else 0.0
            name = self._s1_name_edit.text().strip() or "Alex" if hasattr(self, "_s1_name_edit") else "Alex"
        else:
            vid = self._s2_voice_combo.currentData() if hasattr(self, "_s2_voice_combo") else self._selected_voice_id
            sp = (self._s2_speed_slider.value() / 10.0) if hasattr(self, "_s2_speed_slider") else master_speed
            pt = float(self._s2_pitch_slider.value()) if hasattr(self, "_s2_pitch_slider") else 0.0
            name = self._s2_name_edit.text().strip() or "Maya" if hasattr(self, "_s2_name_edit") else "Maya"
        return {
            "name": name,
            "voice_id": vid or self._selected_voice_id,
            "speed": max(0.5, min(2.0, sp)),
            "pitch": pt,
        }

    def is_dialogue_mode(self) -> bool:
        return self._mode_dialogue_btn.isChecked() if hasattr(self, "_mode_dialogue_btn") else False

    def _preview_speaker1(self) -> None:
        vid = self._s1_voice_combo.currentData() if hasattr(self, "_s1_voice_combo") else self._selected_voice_id
        n1 = self._s1_name_edit.text().strip() or "Alex"
        n2 = self._s2_name_edit.text().strip() or "Maya"
        text = f"Have you ever noticed something strange, {n2}? It is darker than you think."
        self.preview_requested.emit(vid, text)
        if self._preview_callback:
            self._preview_callback(vid, text)

    def _preview_speaker2(self) -> None:
        vid = self._s2_voice_combo.currentData() if hasattr(self, "_s2_voice_combo") else self._selected_voice_id
        n1 = self._s1_name_edit.text().strip() or "Alex"
        text = f"And the worst part, {n1}? You know they are confusing you."
        self.preview_requested.emit(vid, text)
        if self._preview_callback:
            self._preview_callback(vid, text)

    def _on_card_preview(self, voice_id: str) -> None:
        self._on_voice_selected(voice_id)
        text = self._preview_text.text().strip() or "Hello, this is a voice preview."
        self.preview_requested.emit(voice_id, text)
        if self._preview_callback:
            self._preview_callback(voice_id, text)

    def _on_voice_selected(self, voice_id: str) -> None:
        for vid, card in self._cards.items():
            card.set_selected(vid == voice_id)
        self._selected_voice_id = voice_id
        card = self._cards.get(voice_id)
        label = card._voice_data.get("name", voice_id) if card else voice_id
        self._selected_info_lbl.setText(f"Selected: {label}")
        self.voice_changed.emit(voice_id)

    def set_selected_voice(self, voice_id: str) -> None:
        if voice_id in self._cards:
            self._on_voice_selected(voice_id)

    def set_voice_settings(
        self,
        speed: float = 1.0,
        pitch: int = 0,
        volume: int = 100,
        auto_speed: bool = False,
        dialogue_mode: bool = False,
        speaker1_name: str = "Alex",
        speaker2_name: str = "Maya",
        address_by_name: bool = True,
        acoustic_mastering: bool = True,
    ) -> None:
        val = max(5, min(20, int(round(speed * 10))))
        self._speed_slider.setValue(val)
        if hasattr(self, "_s1_speed_slider"):
            self._s1_speed_slider.setValue(val)
        if hasattr(self, "_s2_speed_slider"):
            self._s2_speed_slider.setValue(val)
        self._pitch_slider.setValue(max(-5, min(5, int(pitch))))
        self._volume_slider.setValue(max(0, min(100, int(volume))))
        self._auto_speed_chk.setChecked(bool(auto_speed))
        if hasattr(self, "_set_dialogue_ui_active"):
            self._set_dialogue_ui_active(bool(dialogue_mode))
        if hasattr(self, "_s1_name_edit") and speaker1_name:
            self._s1_name_edit.setText(speaker1_name)
        if hasattr(self, "_s2_name_edit") and speaker2_name:
            self._s2_name_edit.setText(speaker2_name)
        if hasattr(self, "_address_by_name_chk"):
            self._address_by_name_chk.setChecked(bool(address_by_name))
        if hasattr(self, "_acoustic_mastering_chk"):
            self._acoustic_mastering_chk.setChecked(bool(acoustic_mastering))

    def get_selected_voice_id(self) -> str:
        return self._selected_voice_id

    def get_voice_settings(self) -> dict:
        is_dial = self.is_dialogue_mode()
        s1_name = self._s1_name_edit.text().strip() if hasattr(self, "_s1_name_edit") else "Alex"
        s2_name = self._s2_name_edit.text().strip() if hasattr(self, "_s2_name_edit") else "Maya"
        s1_vid = self._s1_voice_combo.currentData() if hasattr(self, "_s1_voice_combo") else self._selected_voice_id
        s2_vid = self._s2_voice_combo.currentData() if hasattr(self, "_s2_voice_combo") else "blend:female_warm"

        # Smart differentiation: Ensure Speaker 1 and Speaker 2 never share the same voice
        if not s1_vid:
            s1_vid = "am_adam" if "am_adam" in self._cards else (self._selected_voice_id or "blend:male_introspective")
        if not s2_vid or s2_vid == s1_vid:
            if "female" in str(s1_vid).lower() or str(s1_vid).startswith("af_"):
                s2_vid = "am_adam" if "am_adam" in self._cards else "blend:male_introspective"
            else:
                s2_vid = "af_heart" if "af_heart" in self._cards else "blend:female_warm"

        master_speed = self._speed_slider.value() / 10.0
        s1_spd = self._s1_speed_slider.value() / 10.0 if hasattr(self, "_s1_speed_slider") else master_speed
        s1_pit = self._s1_pitch_slider.value() if hasattr(self, "_s1_pitch_slider") else 0
        s2_spd = self._s2_speed_slider.value() / 10.0 if hasattr(self, "_s2_speed_slider") else master_speed
        s2_pit = self._s2_pitch_slider.value() if hasattr(self, "_s2_pitch_slider") else 0

        return {
            "voice_id": self._selected_voice_id,
            "speed": self._speed_slider.value() / 10.0,
            "auto_speed": self._auto_speed_chk.isChecked(),
            "pitch": self._pitch_slider.value(),
            "volume": self._volume_slider.value(),
            # Two-voice dialogue parameters
            "dialogue_mode": is_dial,
            "speaker1": {
                "name": s1_name or "Alex",
                "voice_id": s1_vid or self._selected_voice_id,
                "speed": s1_spd,
                "pitch": s1_pit,
            },
            "speaker2": {
                "name": s2_name or "Maya",
                "voice_id": s2_vid or "blend:female_warm",
                "speed": s2_spd,
                "pitch": s2_pit,
            },
            "address_by_name": self._address_by_name_chk.isChecked() if hasattr(self, "_address_by_name_chk") else True,
            "acoustic_mastering": self._acoustic_mastering_chk.isChecked() if hasattr(self, "_acoustic_mastering_chk") else True,
        }

    def set_preview_callback(self, callback: Callable[[str, str], None]) -> None:
        self._preview_callback = callback
