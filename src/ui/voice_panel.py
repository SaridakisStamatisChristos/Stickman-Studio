"""
Voice Panel - Voice selection, preview, and audio settings.
"""
from __future__ import annotations

from typing import Callable, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
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
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(68)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self._apply_style(False)

        h = QHBoxLayout(self)
        h.setContentsMargins(10, 6, 10, 6)
        h.setSpacing(8)

        # Gender icon
        gender = voice.get("gender", "neutral").lower()
        icon_lbl = QLabel(GENDER_ICONS.get(gender, "⚥"))
        icon_lbl.setFont(QFont("Segoe UI", 16))
        icon_lbl.setFixedWidth(28)
        h.addWidget(icon_lbl)

        # Name + tags
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(voice.get("name", self._voice_id))
        name_lbl.setFont(QFont("Segoe UI", 11, QFont.Bold))
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
        tag_lbl.setStyleSheet("color: #4FC3F7;")
        info.addWidget(tag_lbl)
        h.addLayout(info, stretch=1)

        # Preview button
        prev_btn = QPushButton("▶ Preview")
        prev_btn.setFixedWidth(80)
        prev_btn.setStyleSheet(
            "QPushButton { background: #0f3460; color: white; border-radius: 4px; padding: 4px 8px; font-size: 11px; }"
            "QPushButton:hover { background: #1a4a8a; }"
        )
        prev_btn.clicked.connect(lambda: self.preview.emit(self._voice_id))
        h.addWidget(prev_btn)

    # ------------------------------------------------------------------
    @property
    def voice_id(self) -> str:
        return self._voice_id

    def set_selected(self, selected: bool) -> None:
        self._is_selected = selected
        self._apply_style(selected)

    def _apply_style(self, selected: bool) -> None:
        base = "QFrame#voiceCard { border-radius: 8px; "
        if selected:
            self.setStyleSheet(base + "background: #1a2a4a; border: 2px solid #e94560; }")
        else:
            self.setStyleSheet(base + "background: #16213e; border: 1px solid #0f3460; }")

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

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, VoiceCard] = {}
        self._selected_voice_id: str = ""
        self._preview_callback: Optional[Callable[[str, str], None]] = None
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(4)
        splitter.setStyleSheet("QSplitter::handle { background: #0f3460; }")

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
        right_widget.setMinimumWidth(240)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(12, 4, 4, 4)
        right_layout.setSpacing(10)

        settings_lbl = QLabel("Audio Settings")
        settings_lbl.setObjectName("section")
        settings_lbl.setFont(QFont("Segoe UI", 12, QFont.Bold))
        right_layout.addWidget(settings_lbl)

        # Speed
        right_layout.addWidget(self._make_slider_group(
            "Speed", "speed", 5, 20, 10, lambda v: f"{v / 10:.1f}×"
        ))

        # Pitch
        right_layout.addWidget(self._make_slider_group(
            "Pitch", "pitch", -5, 5, 0, lambda v: f"{v:+d} st"
        ))

        # Volume
        right_layout.addWidget(self._make_slider_group(
            "Volume", "volume", 0, 100, 85, lambda v: f"{v}%"
        ))

        # Preview text
        preview_group = QGroupBox("Preview")
        preview_group.setStyleSheet(
            "QGroupBox { border: 1px solid #0f3460; border-radius: 6px; margin-top: 10px; color: #4FC3F7; font-weight: bold; }"
            "QGroupBox::title { subcontrol-origin: margin; left: 10px; }"
        )
        pg_layout = QVBoxLayout(preview_group)
        self._preview_text = QLineEdit("The quick brown fox jumps over the lazy dog.")
        self._preview_text.setPlaceholderText("Enter preview text…")
        pg_layout.addWidget(self._preview_text)

        self._preview_btn = QPushButton("▶  Preview Voice")
        self._preview_btn.clicked.connect(self._on_preview_clicked)
        pg_layout.addWidget(self._preview_btn)
        right_layout.addWidget(preview_group)

        # Selected voice info
        self._selected_info_lbl = QLabel("No voice selected")
        self._selected_info_lbl.setStyleSheet("color: #888; font-style: italic;")
        self._selected_info_lbl.setWordWrap(True)
        right_layout.addWidget(self._selected_info_lbl)

        right_layout.addStretch()
        splitter.addWidget(right_widget)
        splitter.setSizes([320, 240])

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
        return group

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

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_voices(self, voices: list[dict]) -> None:
        """Populate the voice list from genuinely installed local voices."""
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

        for voice in voices:
            card = VoiceCard(voice)
            card.selected.connect(self._on_voice_selected)
            card.preview.connect(self._on_card_preview)
            self._list_layout.addWidget(card)
            self._cards[voice["id"]] = card

        if voices:
            self._on_voice_selected(voices[0]["id"])

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

    def set_voice_settings(self, speed: float = 1.0, pitch: int = 0, volume: int = 100) -> None:
        self._speed_slider.setValue(max(5, min(20, int(round(speed * 10)))))
        self._pitch_slider.setValue(max(-5, min(5, int(pitch))))
        self._volume_slider.setValue(max(0, min(100, int(volume))))

    def get_selected_voice_id(self) -> str:
        return self._selected_voice_id

    def get_voice_settings(self) -> dict:
        return {
            "voice_id": self._selected_voice_id,
            "speed": self._speed_slider.value() / 10.0,
            "pitch": self._pitch_slider.value(),
            "volume": self._volume_slider.value(),
        }

    def set_preview_callback(self, callback: Callable[[str, str], None]) -> None:
        self._preview_callback = callback
