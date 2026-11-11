"""
Style Gallery Widget - Complete 12-Style Modern Collection (S1-S6 Creator & S7-S12 Artistic)
selector with REAL SceneComposer-rendered preview thumbnails and inline variation pickers.

Created by Atharv Hatwar.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont, QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from animation.scene_composer import SceneComposer
from styles.style_packs import (
    ARTISTIC_STYLE_IDS,
    AUTOPILOT_STYLE_IDS,
    CREATOR_STYLE_IDS,
    DIRECTOR_STYLE_IDS,
    STYLE_PACKS,
    resolve_style_pack,
)

_PREVIEW_CACHE_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
) / "OfflineStickmanStudio" / "style_previews_v5"


def _sample_scene_for_style(style_id: str) -> dict[str, Any]:
    """Return a characteristic 1-scene mini storyboard showcasing this style's identity."""
    pack, _ = resolve_style_pack(style_id)
    sid = pack.id

    if sid == "s1_rsa_whiteboard":
        return {
            "id": 1,
            "background": "STAGE",
            "camera": "MEDIUM",
            "emotion": "HAPPY",
            "narration": "Clear ideas cut through noise.",
            "characters": [{"id": "PERSON_A", "action": "POINT_UP", "start_x": 0.42, "end_x": 0.42, "y": 0.62, "scale": 1.48, "facing": "right", "speaking": True}],
            "objects": [{"asset": "LIGHTBULB", "x": 0.62, "y": 0.22, "width": 0.18, "height": 0.18}],
        }
    if sid == "s2_cyberpunk_neon":
        return {
            "id": 1,
            "background": "CITY",
            "camera": "MEDIUM",
            "emotion": "EXCITED",
            "narration": "Future terminal active.",
            "characters": [{"id": "PERSON_A", "action": "TYPING_LAPTOP", "start_x": 0.38, "end_x": 0.38, "y": 0.62, "scale": 1.44, "facing": "right", "speaking": True}],
            "objects": [{"asset": "LAPTOP", "x": 0.58, "y": 0.42, "width": 0.28, "height": 0.22}],
        }
    if sid == "s3_retro_pop_comic":
        return {
            "id": 1,
            "background": "ABSTRACT",
            "camera": "MEDIUM",
            "emotion": "EXCITED",
            "narration": "POW! Ideas strike fast.",
            "characters": [{"id": "PERSON_A", "action": "CELEBRATE", "start_x": 0.40, "end_x": 0.40, "y": 0.62, "scale": 1.46, "facing": "right", "speaking": True}],
            "objects": [{"asset": "STAR", "x": 0.64, "y": 0.24, "width": 0.20, "height": 0.20}],
        }
    if sid == "s4_notion_startup":
        return {
            "id": 1,
            "background": "OFFICE",
            "camera": "MEDIUM",
            "emotion": "HAPPY",
            "narration": "Clean minimalist system.",
            "characters": [{"id": "PERSON_A", "action": "PRESENT_CHART", "start_x": 0.36, "end_x": 0.36, "y": 0.62, "scale": 1.44, "facing": "right", "speaking": True}],
            "objects": [{"asset": "GLASS_CARD", "x": 0.52, "y": 0.26, "width": 0.36, "height": 0.26}],
        }
    if sid == "s5_dark_gold_wealth":
        return {
            "id": 1,
            "background": "OFFICE",
            "camera": "MEDIUM",
            "emotion": "HAPPY",
            "narration": "Compounding financial wealth.",
            "characters": [{"id": "PERSON_A", "action": "COUNT_MONEY", "start_x": 0.40, "end_x": 0.40, "y": 0.62, "scale": 1.44, "facing": "right", "speaking": True}],
            "objects": [{"asset": "MONEY", "x": 0.62, "y": 0.32, "width": 0.22, "height": 0.16}],
        }
    if sid == "s6_chalkboard_academy":
        return {
            "id": 1,
            "background": "CLASSROOM",
            "camera": "MEDIUM",
            "emotion": "EXCITED",
            "narration": "Mathematics proven step by step.",
            "characters": [{"id": "PERSON_A", "action": "PRESENT_CHART", "start_x": 0.36, "end_x": 0.36, "y": 0.62, "scale": 1.44, "facing": "right", "speaking": True}],
            "objects": [{"asset": "LINE_CHART", "x": 0.56, "y": 0.32, "width": 0.32, "height": 0.26}],
        }
    if sid == "s7_ghibli_watercolor":
        return {
            "id": 1,
            "background": "CAFE",
            "camera": "MEDIUM",
            "emotion": "HAPPY",
            "narration": "Slow mornings change everything.",
            "characters": [{"id": "PERSON_A", "action": "SIT", "start_x": 0.36, "end_x": 0.36, "y": 0.62, "scale": 1.44, "facing": "right"}],
            "objects": [{"asset": "COFFEE_CUP", "x": 0.56, "y": 0.48, "width": 0.13, "height": 0.13}],
        }
    if sid == "s8_shonen_manga":
        return {
            "id": 1,
            "background": "STAGE",
            "camera": "PUNCH_IN",
            "emotion": "EXCITED",
            "narration": "Break beyond all limits!",
            "characters": [{"id": "PERSON_A", "action": "TRIUMPH_FIST", "start_x": 0.44, "end_x": 0.44, "y": 0.62, "scale": 1.48, "facing": "right", "speaking": True}],
            "objects": [{"asset": "STAR", "x": 0.66, "y": 0.20, "width": 0.18, "height": 0.18}],
        }
    if sid == "s9_retro_arcade":
        return {
            "id": 1,
            "background": "STAGE",
            "camera": "MEDIUM",
            "emotion": "HAPPY",
            "narration": "Player One Press Start.",
            "characters": [{"id": "PERSON_A", "action": "CELEBRATE", "start_x": 0.42, "end_x": 0.42, "y": 0.62, "scale": 1.44, "facing": "right"}],
            "objects": [{"asset": "STAR", "x": 0.64, "y": 0.24, "width": 0.18, "height": 0.18}],
        }
    if sid == "s10_blueprint_cad":
        return {
            "id": 1,
            "background": "OFFICE",
            "camera": "MEDIUM",
            "emotion": "NEUTRAL",
            "narration": "Precision structural schematic.",
            "characters": [{"id": "PERSON_A", "action": "PRESENT_CHART", "start_x": 0.38, "end_x": 0.38, "y": 0.62, "scale": 1.44, "facing": "right"}],
            "objects": [{"asset": "BAR_CHART", "x": 0.58, "y": 0.34, "width": 0.30, "height": 0.24}],
        }
    if sid == "s11_graffiti_punk":
        return {
            "id": 1,
            "background": "STREET",
            "camera": "MEDIUM",
            "emotion": "EXCITED",
            "narration": "Raw urban creative velocity.",
            "characters": [{"id": "PERSON_A", "action": "SPRINT_FAST", "start_x": 0.36, "end_x": 0.36, "y": 0.62, "scale": 1.44, "facing": "right"}],
            "objects": [{"asset": "ARROW", "x": 0.60, "y": 0.26, "width": 0.22, "height": 0.10}],
        }
    if sid == "s12_cinematic_noir":
        return {
            "id": 1,
            "background": "CITY",
            "camera": "CLOSE",
            "emotion": "CONFUSED",
            "narration": "Shadows in the dark city.",
            "characters": [{"id": "PERSON_A", "action": "CROSS_ARMS", "start_x": 0.44, "end_x": 0.44, "y": 0.62, "scale": 1.46, "facing": "right"}],
            "objects": [{"asset": "QUESTION_MARK", "x": 0.66, "y": 0.24, "width": 0.14, "height": 0.16}],
        }
    if sid == "s14_chameleon_adaptive":
        return {
            "id": 1,
            "background": "STAGE",
            "camera": "DYNAMIC_CUT",
            "emotion": "EXCITED",
            "narration": "Adaptive visual storytelling.",
            "characters": [{"id": "PERSON_A", "action": "WAVE", "start_x": 0.38, "end_x": 0.38, "y": 0.62, "scale": 1.46, "facing": "right", "speaking": True}],
            "objects": [{"asset": "STAR", "x": 0.64, "y": 0.22, "width": 0.20, "height": 0.20}],
        }
    # s13_cinematic_storyteller (Created by Atharv Hatwar)
    return {
        "id": 1,
        "background": "MOUNTAIN",
        "camera": "SLOW_ZOOM_IN",
        "emotion": "HAPPY",
        "narration": "Every legend begins with a single step.",
        "characters": [
            {"id": "PERSON_A", "action": "WALK_RIGHT", "start_x": 0.32, "end_x": 0.32, "y": 0.62, "scale": 1.46, "facing": "right"},
        ],
        "objects": [{"asset": "STAR", "x": 0.68, "y": 0.22, "width": 0.18, "height": 0.18}],
    }


def render_style_preview_pixmap(style_id: str, variant: Optional[str] = None, w: int = 160, h: int = 212) -> QPixmap:
    """Render an authentic single-frame thumbnail directly through SceneComposer."""
    pack, sp = resolve_style_pack(style_id, variant)
    var_key = sp.get("variant", "default")
    _PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    cache_path = _PREVIEW_CACHE_DIR / f"{pack.id}_{var_key}_{w}x{h}.png"

    if cache_path.exists():
        px = QPixmap(str(cache_path))
        if not px.isNull():
            return px

    try:
        composer = SceneComposer(pack.id, width=w, height=h, fps=24, style_variant=var_key)
        scene = _sample_scene_for_style(pack.id)
        frame = None
        for idx, fr in enumerate(composer.compose_scene_stream(scene, 0.7)):
            frame = fr
            if idx >= 10:
                break
        if frame is not None:
            rgb = frame.convert("RGBA")
            try:
                rgb.save(str(cache_path), format="PNG")
            except Exception:
                pass
            raw = rgb.tobytes("raw", "RGBA")
            qimg = QImage(raw, w, h, w * 4, QImage.Format_RGBA8888)
            return QPixmap.fromImage(qimg.copy())
    except Exception:
        pass

    fallback = QPixmap(w, h)
    fallback.fill(Qt.black)
    return fallback


class StyleCard(QFrame):
    """Clickable style card displaying a real engine preview, badge, name, and variation toggle."""

    clicked = Signal(str)
    variant_selected = Signal(str, str)

    def __init__(self, style_id: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.pack = STYLE_PACKS[style_id]
        self._style_id = self.pack.id
        self._selected = False
        self._current_variant: Optional[str] = self.pack.variations[0][0] if self.pack.variations else None

        self.setObjectName("styleCard")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(190)
        self.setFixedHeight(285 if self.pack.variations else 258)
        self.setFrameShape(QFrame.StyledPanel)
        self._apply_style(False)

        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)

        # Top header bar: Code pill + Name
        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        code_badge = QLabel(self.pack.code)
        code_badge.setFixedWidth(30)
        code_badge.setAlignment(Qt.AlignCenter)
        code_badge.setStyleSheet(
            "background: #e94560; color: white; font-weight: bold; border-radius: 5px; padding: 2px 4px; font-size: 11px;"
            if self.pack.collection == "director"
            else "background: #0284c7; color: white; font-weight: bold; border-radius: 5px; padding: 2px 4px; font-size: 11px;"
        )
        top_row.addWidget(code_badge)

        name_lbl = QLabel(self.pack.name.replace(f"{self.pack.code} ", "", 1))
        name_lbl.setFont(QFont("Segoe UI", 10, QFont.Bold))
        name_lbl.setStyleSheet("color: #f1f5f9; background: transparent;")
        top_row.addWidget(name_lbl, stretch=1)
        layout.addLayout(top_row)

        # Real engine-rendered preview thumbnail
        self._preview_lbl = QLabel()
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setFixedSize(136, 166)
        self._preview_lbl.setStyleSheet("border: 1px solid #1e293b; border-radius: 6px; background: #0f172a;")
        self._refresh_preview()
        layout.addWidget(self._preview_lbl, alignment=Qt.AlignHCenter)

        # Concise description
        desc_lbl = QLabel(self.pack.short_desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setFont(QFont("Segoe UI", 8))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #94a3b8; background: transparent;")
        layout.addWidget(desc_lbl)

        # Variation selector if style offers multiple looks (A1 Light/Dark, A2 Minimal Tech / Colorful Story)
        self._var_combo: Optional[QComboBox] = None
        if self.pack.variations:
            self._var_combo = QComboBox()
            self._var_combo.setStyleSheet(
                "QComboBox { background: #0f172a; color: #38bdf8; border: 1px solid #334155; border-radius: 5px; padding: 3px 6px; font-size: 11px; }"
            )
            for vid, vlabel, _ in self.pack.variations:
                self._var_combo.addItem(vlabel, vid)
            self._var_combo.currentIndexChanged.connect(self._on_variant_combo_changed)
            layout.addWidget(self._var_combo)

    def _refresh_preview(self) -> None:
        px = render_style_preview_pixmap(self._style_id, variant=self._current_variant, w=136, h=166)
        self._preview_lbl.setPixmap(px)

    def _on_variant_combo_changed(self) -> None:
        if self._var_combo is None:
            return
        self._current_variant = self._var_combo.currentData()
        self._refresh_preview()
        self.clicked.emit(self._style_id)
        if self._current_variant:
            self.variant_selected.emit(self._style_id, self._current_variant)

    def get_variant(self) -> Optional[str]:
        return self._current_variant

    def set_variant(self, variant: Optional[str]) -> None:
        if self._var_combo is None or not variant:
            return
        for i in range(self._var_combo.count()):
            if self._var_combo.itemData(i) == variant:
                self._var_combo.blockSignals(True)
                self._var_combo.setCurrentIndex(i)
                self._var_combo.blockSignals(False)
                self._current_variant = variant
                self._refresh_preview()
                break

    @property
    def style_id(self) -> str:
        return self._style_id

    def set_selected(self, selected: bool) -> None:
        self._selected = selected
        self._apply_style(selected)

    def _apply_style(self, selected: bool) -> None:
        if selected:
            self.setStyleSheet(
                "QFrame#styleCard { background: #1e293b; border: 2px solid #e94560; border-radius: 10px; }"
            )
        else:
            self.setStyleSheet(
                "QFrame#styleCard { background: #16213e; border: 1px solid #0f3460; border-radius: 10px; }"
            )

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._style_id)
        super().mousePressEvent(event)


class StyleSelector(QWidget):
    """Displays all 11 Director & Autopilot Style Packs with real engine previews."""

    style_changed = Signal(str)
    variant_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, StyleCard] = {}
        self._selected_id: str = DIRECTOR_STYLE_IDS[0]
        self._setup_ui()
        self.set_selected_style(self._selected_id)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        root_v = QVBoxLayout(container)
        root_v.setSpacing(12)
        root_v.setContentsMargins(8, 8, 8, 8)

        # ---- VIRAL CREATOR & EXPLAINER STYLES (S1-S6) ----
        dir_lbl = QLabel("🔥  VIRAL CREATOR & EXPLAINER STYLES  (S1 – S6)")
        dir_lbl.setStyleSheet("color: #f43f5e; font-size: 13px; font-weight: bold; padding-left: 2px;")
        root_v.addWidget(dir_lbl)

        dir_grid = QGridLayout()
        dir_grid.setSpacing(10)
        for idx, sid in enumerate(CREATOR_STYLE_IDS):
            card = StyleCard(sid)
            card.clicked.connect(self._on_card_clicked)
            card.variant_selected.connect(self._on_variant_changed)
            self._cards[sid] = card
            row, col = divmod(idx, 3)
            dir_grid.addWidget(card, row, col)
        root_v.addLayout(dir_grid)

        # ---- ARTISTIC & STORYTELLING STYLES (S7-S13) ----
        auto_lbl = QLabel("🎨  ARTISTIC & STORYTELLING STYLES  (S7 – S13)")
        auto_lbl.setStyleSheet("color: #38bdf8; font-size: 13px; font-weight: bold; padding-top: 6px; padding-left: 2px;")
        root_v.addWidget(auto_lbl)

        auto_grid = QGridLayout()
        auto_grid.setSpacing(10)
        for idx, sid in enumerate(ARTISTIC_STYLE_IDS):
            card = StyleCard(sid)
            card.clicked.connect(self._on_card_clicked)
            card.variant_selected.connect(self._on_variant_changed)
            self._cards[sid] = card
            row, col = divmod(idx, 3)
            auto_grid.addWidget(card, row, col)
        root_v.addLayout(auto_grid)

        # Creator Attribution Credit Footer
        footer_lbl = QLabel("✨ Stickman Studio • Designed & Engineered by Atharv Hatwar")
        footer_lbl.setAlignment(Qt.AlignCenter)
        footer_lbl.setStyleSheet("color: #64748b; font-size: 11px; padding-top: 10px; font-style: italic;")
        root_v.addWidget(footer_lbl)
        root_v.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def _on_card_clicked(self, style_id: str) -> None:
        self.set_selected_style(style_id)
        self.style_changed.emit(style_id)
        var = self.get_selected_variant()
        if var:
            self.variant_changed.emit(var)

    def _on_variant_changed(self, style_id: str, variant: str) -> None:
        self.set_selected_style(style_id, variant=variant)
        self.style_changed.emit(style_id)
        self.variant_changed.emit(variant)

    def get_selected_style(self) -> str:
        return self._selected_id

    def get_selected_variant(self) -> str:
        card = self._cards.get(self._selected_id)
        return (card.get_variant() or "") if card else ""

    def set_selected_style(self, style_id: str, variant: Optional[str] = None) -> None:
        pack, sp = resolve_style_pack(style_id, variant)
        resolved = pack.id
        for sid, card in self._cards.items():
            card.set_selected(sid == resolved)
        if variant and resolved in self._cards:
            self._cards[resolved].set_variant(variant)
        self._selected_id = resolved
