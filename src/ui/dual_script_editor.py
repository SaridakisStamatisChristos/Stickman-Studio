"""
Dual-Voice Script Editor - Advanced interactive script and dialogue editor for Stickman Studio.
Provides seamless switching between Solo narration and Two-Voice conversational dialogue
with per-character turn cards, live audio previews, syntax tags, and timing meters.
"""
from __future__ import annotations

import logging
import re
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class DialogueTurnCard(QFrame):
    """
    An individual conversational turn card in the two-voice dialogue editor.
    Allows toggling speaker, editing dialogue line, previewing Kokoro voice, and reordering.
    """

    deleted = Signal(object)
    changed = Signal()
    move_up = Signal(object)
    move_down = Signal(object)
    preview_requested = Signal(int, str)  # (speaker_idx: 1 or 2, text: str)

    def __init__(
        self,
        index: int,
        speaker: int = 1,
        text: str = "",
        name1: str = "Alex",
        name2: str = "Maya",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._index = index
        self._speaker = 1 if speaker == 1 else 2
        self._name1 = name1 or "Alex"
        self._name2 = name2 or "Maya"

        self.setObjectName("turnCard")
        self._setup_ui(text)
        self._apply_speaker_style()

    def _setup_ui(self, initial_text: str) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(6)

        # Header: Index Badge + Speaker Toggle Pill + Action Buttons
        header_row = QHBoxLayout()
        header_row.setSpacing(6)

        self._badge_lbl = QLabel(f"#{self._index:02d}")
        self._badge_lbl.setStyleSheet(
            "color: #94A3B8; font-size: 11px; font-weight: bold; background: transparent;"
        )
        header_row.addWidget(self._badge_lbl)

        # Speaker switcher button (1 click toggles Alex <-> Maya)
        self._speaker_btn = QPushButton()
        self._speaker_btn.setFixedHeight(26)
        self._speaker_btn.setCursor(Qt.PointingHandCursor)
        self._speaker_btn.clicked.connect(self._toggle_speaker)
        header_row.addWidget(self._speaker_btn)

        header_row.addStretch()

        # Mini preview button
        self._prev_btn = QPushButton("▶ Play")
        self._prev_btn.setToolTip("Hear this line with this character's Kokoro voice")
        self._prev_btn.setFixedHeight(24)
        self._prev_btn.setCursor(Qt.PointingHandCursor)
        self._prev_btn.setStyleSheet("""
            QPushButton {
                background: #1E293B; color: #38BDF8; border: 1px solid #0284C7;
                border-radius: 5px; padding: 2px 8px; font-size: 10px; font-weight: bold;
            }
            QPushButton:hover { background: #0369A1; color: white; }
        """)
        self._prev_btn.clicked.connect(self._on_preview_clicked)
        header_row.addWidget(self._prev_btn)

        # Move Up button
        self._up_btn = QPushButton("▲")
        self._up_btn.setFixedSize(24, 24)
        self._up_btn.setToolTip("Move turn earlier")
        self._up_btn.setStyleSheet("QPushButton { background: #131A2B; color: #94A3B8; border: 1px solid #263248; border-radius: 4px; font-size: 9px; } QPushButton:hover { color: white; background: #263248; }")
        self._up_btn.clicked.connect(lambda: self.move_up.emit(self))
        header_row.addWidget(self._up_btn)

        # Move Down button
        self._down_btn = QPushButton("▼")
        self._down_btn.setFixedSize(24, 24)
        self._down_btn.setToolTip("Move turn later")
        self._down_btn.setStyleSheet("QPushButton { background: #131A2B; color: #94A3B8; border: 1px solid #263248; border-radius: 4px; font-size: 9px; } QPushButton:hover { color: white; background: #263248; }")
        self._down_btn.clicked.connect(lambda: self.move_down.emit(self))
        header_row.addWidget(self._down_btn)

        # Delete button
        self._del_btn = QPushButton("✕")
        self._del_btn.setFixedSize(24, 24)
        self._del_btn.setToolTip("Remove this dialogue turn")
        self._del_btn.setStyleSheet("QPushButton { background: #2A1215; color: #F87171; border: 1px solid #7F1D1D; border-radius: 4px; font-size: 10px; font-weight: bold; } QPushButton:hover { background: #991B1B; color: white; }")
        self._del_btn.clicked.connect(lambda: self.deleted.emit(self))
        header_row.addWidget(self._del_btn)

        layout.addLayout(header_row)

        # Spoken dialogue text
        self._text_edit = QTextEdit()
        self._text_edit.setPlainText(initial_text)
        self._text_edit.setPlaceholderText("Enter dialogue line…")
        self._text_edit.setFixedHeight(54)
        self._text_edit.setStyleSheet("""
            QTextEdit {
                background: #080C14;
                border: 1px solid #263248;
                border-radius: 6px;
                color: #F8FAFC;
                padding: 6px 8px;
                font-size: 12px;
            }
            QTextEdit:focus {
                border-color: #38BDF8;
            }
        """)
        self._text_edit.textChanged.connect(self.changed.emit)
        layout.addWidget(self._text_edit)

    def _toggle_speaker(self) -> None:
        self._speaker = 2 if self._speaker == 1 else 1
        self._apply_speaker_style()
        self.changed.emit()

    def _apply_speaker_style(self) -> None:
        if self._speaker == 1:
            name = self._name1 or "Alex"
            self._speaker_btn.setText(f"👤  {name}  (S1)")
            self._speaker_btn.setStyleSheet("""
                QPushButton {
                    background: #0C2338;
                    color: #38BDF8;
                    border: 1px solid #0284C7;
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #0369A1;
                    color: white;
                }
            """)
            self.setStyleSheet("""
                QFrame#turnCard {
                    background: #0E1626;
                    border: 1px solid #1E3A5F;
                    border-left: 4px solid #0284C7;
                    border-radius: 8px;
                }
            """)
        else:
            name = self._name2 or "Maya"
            self._speaker_btn.setText(f"👥  {name}  (S2)")
            self._speaker_btn.setStyleSheet("""
                QPushButton {
                    background: #2D1022;
                    color: #F43F5E;
                    border: 1px solid #E11D48;
                    border-radius: 12px;
                    padding: 2px 10px;
                    font-size: 11px;
                    font-weight: bold;
                }
                QPushButton:hover {
                    background: #BE123C;
                    color: white;
                }
            """)
            self.setStyleSheet("""
                QFrame#turnCard {
                    background: #191220;
                    border: 1px solid #4C1D3A;
                    border-left: 4px solid #F43F5E;
                    border-radius: 8px;
                }
            """)

    def _on_preview_clicked(self) -> None:
        text = self.get_text().strip()
        if text:
            self.preview_requested.emit(self._speaker, text)

    def update_names(self, name1: str, name2: str) -> None:
        self._name1 = name1 or "Alex"
        self._name2 = name2 or "Maya"
        self._apply_speaker_style()

    def set_index(self, idx: int) -> None:
        self._index = idx
        self._badge_lbl.setText(f"#{idx:02d}")

    def get_speaker(self) -> int:
        return self._speaker

    def set_speaker(self, speaker: int) -> None:
        self._speaker = 1 if speaker == 1 else 2
        self._apply_speaker_style()

    def get_text(self) -> str:
        return self._text_edit.toPlainText().strip()

    def set_text(self, text: str) -> None:
        self._text_edit.setPlainText(text)


class DualVoiceScriptEditor(QWidget):
    """
    State-of-the-art script editor supporting both Solo and Dual-Voice Dialogue modes.
    Direct drop-in replacement for the standard script box with full backwards-compatibility.
    """

    textChanged = Signal()
    mode_changed = Signal(bool)  # True = Dialogue mode, False = Solo mode
    preview_turn_requested = Signal(int, str)  # (speaker: 1 or 2, text: str)

    def __init__(
        self,
        name1: str = "Alex",
        name2: str = "Maya",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._name1 = name1 or "Alex"
        self._name2 = name2 or "Maya"
        self._is_dialogue_mode = False
        self._cards: list[DialogueTurnCard] = []

        self._debounce_timer = QTimer(self)
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.setInterval(120)
        self._debounce_timer.timeout.connect(self._on_internal_change)

        self._setup_ui()

    def _setup_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(6)

        # ── Top Mode Selection Toolbar ──
        mode_bar = QHBoxLayout()
        mode_bar.setSpacing(6)

        self._solo_mode_btn = QPushButton("👤 Solo Script")
        self._solo_mode_btn.setCheckable(True)
        self._solo_mode_btn.setChecked(True)
        self._solo_mode_btn.setCursor(Qt.PointingHandCursor)
        self._solo_mode_btn.setStyleSheet("""
            QPushButton {
                background: #131A2B; color: #94A3B8; border: 1px solid #263248;
                border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;
            }
            QPushButton:checked {
                background: #0284C7; color: white; border-color: #38BDF8;
            }
            QPushButton:hover { background: #1E293B; }
        """)
        self._solo_mode_btn.clicked.connect(lambda: self.set_dialogue_mode(False))
        mode_bar.addWidget(self._solo_mode_btn)

        self._dual_mode_btn = QPushButton("👥 Two-Voice Dialogue")
        self._dual_mode_btn.setCheckable(True)
        self._dual_mode_btn.setCursor(Qt.PointingHandCursor)
        self._dual_mode_btn.setStyleSheet("""
            QPushButton {
                background: #131A2B; color: #94A3B8; border: 1px solid #263248;
                border-radius: 12px; padding: 4px 12px; font-size: 11px; font-weight: bold;
            }
            QPushButton:checked {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7C3AED, stop:1 #F43F5E);
                color: white; border-color: #C084FC;
            }
            QPushButton:hover { background: #1E293B; }
        """)
        self._dual_mode_btn.clicked.connect(lambda: self.set_dialogue_mode(True))
        mode_bar.addWidget(self._dual_mode_btn)

        mode_bar.addStretch()

        # Dual mode view switcher (Cards vs Raw Script)
        self._view_cards_btn = QPushButton("💬 Cards")
        self._view_cards_btn.setCheckable(True)
        self._view_cards_btn.setChecked(True)
        self._view_cards_btn.setVisible(False)
        self._view_cards_btn.setCursor(Qt.PointingHandCursor)
        self._view_cards_btn.setStyleSheet("""
            QPushButton {
                background: #131A2B; color: #94A3B8; border: 1px solid #263248;
                border-radius: 8px; padding: 3px 8px; font-size: 10px; font-weight: bold;
            }
            QPushButton:checked { background: #334155; color: #38BDF8; border-color: #0284C7; }
        """)
        self._view_cards_btn.clicked.connect(lambda: self._set_dual_view(0))
        mode_bar.addWidget(self._view_cards_btn)

        self._view_raw_btn = QPushButton("📜 Text")
        self._view_raw_btn.setCheckable(True)
        self._view_raw_btn.setVisible(False)
        self._view_raw_btn.setCursor(Qt.PointingHandCursor)
        self._view_raw_btn.setStyleSheet("""
            QPushButton {
                background: #131A2B; color: #94A3B8; border: 1px solid #263248;
                border-radius: 8px; padding: 3px 8px; font-size: 10px; font-weight: bold;
            }
            QPushButton:checked { background: #334155; color: #38BDF8; border-color: #0284C7; }
        """)
        self._view_raw_btn.clicked.connect(lambda: self._set_dual_view(1))
        mode_bar.addWidget(self._view_raw_btn)

        main_layout.addLayout(mode_bar)

        # ── Stacked Container ──
        self._stack = QStackedWidget()

        # View 0: Solo Text Editor
        self._solo_edit = QTextEdit()
        self._solo_edit.setMinimumHeight(155)
        self._solo_edit.setPlaceholderText("Paste or write your video narration script here…")
        self._solo_edit.textChanged.connect(self._schedule_change)
        self._stack.addWidget(self._solo_edit)

        # View 1: Dialogue Interactive Turn Cards
        self._dialogue_cards_container = QWidget()
        cards_outer = QVBoxLayout(self._dialogue_cards_container)
        cards_outer.setContentsMargins(0, 0, 0, 0)
        cards_outer.setSpacing(6)

        self._scroll_area = QScrollArea()
        self._scroll_area.setWidgetResizable(True)
        self._scroll_area.setMinimumHeight(180)
        self._scroll_area.setStyleSheet("QScrollArea { border: 1px solid #263248; border-radius: 8px; background: #080C14; }")

        self._cards_list_widget = QWidget()
        self._cards_layout = QVBoxLayout(self._cards_list_widget)
        self._cards_layout.setContentsMargins(6, 6, 6, 6)
        self._cards_layout.setSpacing(6)
        self._cards_layout.addStretch()
        self._scroll_area.setWidget(self._cards_list_widget)
        cards_outer.addWidget(self._scroll_area)

        # Quick Turn Add & Swap Bar
        action_bar = QHBoxLayout()
        action_bar.setSpacing(6)

        self._add_s1_btn = QPushButton(f"+ Add {self._name1}")
        self._add_s1_btn.setCursor(Qt.PointingHandCursor)
        self._add_s1_btn.setStyleSheet("""
            QPushButton {
                background: #0C2338; color: #38BDF8; border: 1px solid #0284C7;
                border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #0369A1; color: white; }
        """)
        self._add_s1_btn.clicked.connect(lambda: self.add_turn(1, ""))
        action_bar.addWidget(self._add_s1_btn)

        self._add_s2_btn = QPushButton(f"+ Add {self._name2}")
        self._add_s2_btn.setCursor(Qt.PointingHandCursor)
        self._add_s2_btn.setStyleSheet("""
            QPushButton {
                background: #2D1022; color: #F43F5E; border: 1px solid #E11D48;
                border-radius: 6px; padding: 4px 10px; font-size: 11px; font-weight: bold;
            }
            QPushButton:hover { background: #BE123C; color: white; }
        """)
        self._add_s2_btn.clicked.connect(lambda: self.add_turn(2, ""))
        action_bar.addWidget(self._add_s2_btn)

        self._swap_all_btn = QPushButton("🔄 Swap Speakers")
        self._swap_all_btn.setToolTip("Invert all Speaker 1 & Speaker 2 assignments")
        self._swap_all_btn.setStyleSheet("""
            QPushButton {
                background: #1B2336; color: #CBD5E1; border: 1px solid #334155;
                border-radius: 6px; padding: 4px 8px; font-size: 11px;
            }
            QPushButton:hover { background: #243049; color: white; }
        """)
        self._swap_all_btn.clicked.connect(self._swap_all_turns)
        action_bar.addWidget(self._swap_all_btn)

        action_bar.addStretch()

        self._clear_turns_btn = QPushButton("🧹 Clear")
        self._clear_turns_btn.setStyleSheet("""
            QPushButton {
                background: transparent; color: #94A3B8; border: none; font-size: 11px;
            }
            QPushButton:hover { color: #F87171; }
        """)
        self._clear_turns_btn.clicked.connect(self.clear_turns)
        action_bar.addWidget(self._clear_turns_btn)

        cards_outer.addLayout(action_bar)
        self._stack.addWidget(self._dialogue_cards_container)

        # View 2: Dialogue Raw Text Editor (e.g. Alex: ... \n Maya: ...)
        self._dual_raw_edit = QTextEdit()
        self._dual_raw_edit.setMinimumHeight(180)
        self._dual_raw_edit.setPlaceholderText(
            f"{self._name1}: Have you ever noticed something strange?\n\n"
            f"{self._name2}: And the worst part? You know they're confusing you.\n\n"
            f"{self._name1}: But why does this happen?"
        )
        self._dual_raw_edit.textChanged.connect(self._schedule_change)
        self._stack.addWidget(self._dual_raw_edit)

        main_layout.addWidget(self._stack)

    def _schedule_change(self) -> None:
        self._debounce_timer.start()

    def _on_internal_change(self) -> None:
        self.textChanged.emit()

    def set_dialogue_mode(self, active: bool) -> None:
        """Switch between Solo narration and Two-Voice dialogue mode."""
        active = bool(active)
        if self._is_dialogue_mode == active:
            return

        self._is_dialogue_mode = active
        self._solo_mode_btn.setChecked(not self._is_dialogue_mode)
        self._dual_mode_btn.setChecked(self._is_dialogue_mode)

        self._view_cards_btn.setVisible(self._is_dialogue_mode)
        self._view_raw_btn.setVisible(self._is_dialogue_mode)

        if not self._is_dialogue_mode:
            self._stack.setCurrentIndex(0)
        else:
            # If transitioning to dialogue mode with solo text, parse into turns
            if not self._cards and self._solo_edit.toPlainText().strip():
                self._load_text_into_turns(self._solo_edit.toPlainText().strip())
            current_sub = 0 if self._view_cards_btn.isChecked() else 1
            self._set_dual_view(current_sub)

        self.mode_changed.emit(self._is_dialogue_mode)
        self.textChanged.emit()

    def is_dialogue_mode(self) -> bool:
        return self._is_dialogue_mode

    def _set_dual_view(self, view_idx: int) -> None:
        """Switch between Cards view (0) and Raw text view (1)."""
        if view_idx == 0:
            self._view_cards_btn.setChecked(True)
            self._view_raw_btn.setChecked(False)
            # Sync raw text into cards
            raw_txt = self._dual_raw_edit.toPlainText().strip()
            if raw_txt:
                self._load_text_into_turns(raw_txt)
            self._stack.setCurrentIndex(1)
        else:
            self._view_cards_btn.setChecked(False)
            self._view_raw_btn.setChecked(True)
            # Sync cards into raw text
            formatted = self._format_turns_to_text()
            self._dual_raw_edit.blockSignals(True)
            self._dual_raw_edit.setPlainText(formatted)
            self._dual_raw_edit.blockSignals(False)
            self._stack.setCurrentIndex(2)

    def add_turn(self, speaker: int, text: str = "") -> DialogueTurnCard:
        """Add a new dialogue turn card."""
        idx = len(self._cards) + 1
        card = DialogueTurnCard(
            index=idx,
            speaker=speaker,
            text=text,
            name1=self._name1,
            name2=self._name2,
            parent=self._cards_list_widget,
        )
        card.changed.connect(self._schedule_change)
        card.deleted.connect(self._remove_turn)
        card.move_up.connect(self._move_turn_up)
        card.move_down.connect(self._move_turn_down)
        card.preview_requested.connect(self.preview_turn_requested.emit)

        # Insert before stretch item
        self._cards.append(card)
        self._cards_layout.insertWidget(len(self._cards) - 1, card)
        self._schedule_change()
        return card

    def _remove_turn(self, card: DialogueTurnCard) -> None:
        if card in self._cards:
            self._cards.remove(card)
            self._cards_layout.removeWidget(card)
            card.deleteLater()
            self._reindex_cards()
            self._schedule_change()

    def _move_turn_up(self, card: DialogueTurnCard) -> None:
        idx = self._cards.index(card)
        if idx > 0:
            self._cards[idx], self._cards[idx - 1] = self._cards[idx - 1], self._cards[idx]
            self._rebuild_layout_order()
            self._schedule_change()

    def _move_turn_down(self, card: DialogueTurnCard) -> None:
        idx = self._cards.index(card)
        if idx < len(self._cards) - 1:
            self._cards[idx], self._cards[idx + 1] = self._cards[idx + 1], self._cards[idx]
            self._rebuild_layout_order()
            self._schedule_change()

    def _rebuild_layout_order(self) -> None:
        for card in self._cards:
            self._cards_layout.removeWidget(card)
        for i, card in enumerate(self._cards):
            card.set_index(i + 1)
            self._cards_layout.insertWidget(i, card)

    def _reindex_cards(self) -> None:
        for i, card in enumerate(self._cards):
            card.set_index(i + 1)

    def _swap_all_turns(self) -> None:
        for card in self._cards:
            card.set_speaker(2 if card.get_speaker() == 1 else 1)
        self._schedule_change()

    def clear_turns(self) -> None:
        for card in list(self._cards):
            self._cards_layout.removeWidget(card)
            card.deleteLater()
        self._cards.clear()
        self._dual_raw_edit.clear()
        self._schedule_change()

    def set_speaker_names(self, name1: str, name2: str) -> None:
        """Update speaker labels and buttons across all turn cards and UI."""
        n1 = (name1 or "Alex").strip()
        n2 = (name2 or "Maya").strip()
        if self._name1 == n1 and self._name2 == n2:
            return
        self._name1 = n1
        self._name2 = n2
        self._add_s1_btn.setText(f"+ Add {self._name1}")
        self._add_s2_btn.setText(f"+ Add {self._name2}")
        for card in self._cards:
            card.update_names(self._name1, self._name2)

    def _load_text_into_turns(self, text: str) -> None:
        """Parse structured or raw text into dialogue turn cards."""
        self.clear_turns()
        if not text or not str(text).strip():
            return

        from tts.tts_manager import TTSManager
        turns = TTSManager.parse_dialogue_script(
            text, name1=self._name1, name2=self._name2
        ) if hasattr(TTSManager, "parse_dialogue_script") else []

        if not turns:
            # Fallback simple parser if TTSManager not available
            lines = [l.strip() for l in (text or "").splitlines() if l.strip()]
            curr_spk = 1
            for l in lines:
                if l.startswith("#"):
                    continue
                self.add_turn(curr_spk, l)
                curr_spk = 2 if curr_spk == 1 else 1
            return

        for t in turns:
            spk = 1 if t.get("speaker") == 1 else 2
            txt = t.get("text", "").strip()
            if txt:
                self.add_turn(spk, txt)

    def _format_turns_to_text(self) -> str:
        """Format current turn cards into standard speaker text."""
        out = []
        for card in self._cards:
            t = card.get_text()
            if not t:
                continue
            name = self._name1 if card.get_speaker() == 1 else self._name2
            out.append(f"{name}: {t}\n")
        return "\n".join(out).strip()

    # ──────────────────────────────────────────────────────────────────
    # Backwards-compatible QTextEdit API
    # ──────────────────────────────────────────────────────────────────

    def toPlainText(self) -> str:
        """Return the script text formatted for pipeline and synthesis."""
        if not self._is_dialogue_mode:
            return self._solo_edit.toPlainText().strip()

        # In dialogue mode:
        if self._stack.currentIndex() == 2:
            # Raw view
            return self._dual_raw_edit.toPlainText().strip()
        return self._format_turns_to_text()

    def setPlainText(self, text: str) -> None:
        """Set script text into both solo editor and dual dialogue cards."""
        text = text or ""
        self._solo_edit.blockSignals(True)
        self._solo_edit.setPlainText(text)
        self._solo_edit.blockSignals(False)

        # Check if text contains dialogue tags or if already in dialogue mode
        n1 = self._name1.lower()
        n2 = self._name2.lower()
        has_tags = any(
            re.search(rf"\b({re.escape(n1)}|{re.escape(n2)}|speaker\s*1|speaker\s*2|male|female)\s*:", l, re.IGNORECASE)
            for l in text.splitlines()
        )

        if has_tags and not self._is_dialogue_mode:
            self.set_dialogue_mode(True)

        if self._is_dialogue_mode or has_tags:
            self._load_text_into_turns(text)
            self._dual_raw_edit.blockSignals(True)
            self._dual_raw_edit.setPlainText(text)
            self._dual_raw_edit.blockSignals(False)

        self.textChanged.emit()

    def setPlaceholderText(self, text: str) -> None:
        self._solo_edit.setPlaceholderText(text)

    def setMinimumHeight(self, h: int) -> None:
        self._solo_edit.setMinimumHeight(h)
        self._scroll_area.setMinimumHeight(h)
        self._dual_raw_edit.setMinimumHeight(h)

    def get_stats(self, speed: float = 1.0) -> dict:
        """Calculate word count and spoken time breakdown for UI meters."""
        if not self._is_dialogue_mode:
            txt = self._solo_edit.toPlainText().strip()
            words = len(txt.split()) if txt else 0
            est_sec = words / (2.4 * max(0.5, speed))
            return {
                "dialogue_mode": False,
                "total_words": words,
                "total_sec": est_sec,
            }

        # Dialogue mode stats
        s1_words = 0
        s2_words = 0
        if self._stack.currentIndex() == 2:
            # Parse from raw view
            raw = self._dual_raw_edit.toPlainText()
            for line in raw.splitlines():
                line = line.strip()
                if not line:
                    continue
                if line.lower().startswith(self._name1.lower() + ":"):
                    s1_words += len(line.split()[1:])
                elif line.lower().startswith(self._name2.lower() + ":"):
                    s2_words += len(line.split()[1:])
                else:
                    s1_words += len(line.split())
        else:
            for card in self._cards:
                cnt = len(card.get_text().split())
                if card.get_speaker() == 1:
                    s1_words += cnt
                else:
                    s2_words += cnt

        total_words = s1_words + s2_words
        wps = 2.4 * max(0.5, speed)
        return {
            "dialogue_mode": True,
            "name1": self._name1,
            "name2": self._name2,
            "s1_words": s1_words,
            "s1_sec": s1_words / wps,
            "s2_words": s2_words,
            "s2_sec": s2_words / wps,
            "total_words": total_words,
            "total_sec": total_words / wps,
        }
