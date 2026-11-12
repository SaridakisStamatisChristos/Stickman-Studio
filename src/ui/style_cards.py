"""
Style Gallery Widget - Hero AI Auto Director + Complete Modern Style Collection
with non-blocking async preview rendering, shared QSS styling, and inline variations.

Created by Atharv Hatwar.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Optional

from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QImage, QLinearGradient, QPainter, QPixmap
from PySide6.QtWidgets import (
    QApplication,
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
    AUTO_STYLE_IDS,
    CREATOR_STYLE_IDS,
    STYLE_PACKS,
    resolve_style_pack,
)

_PREVIEW_CACHE_DIR = Path(
    os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))
) / "OfflineStickmanStudio" / "style_previews_v6"

_GALLERY_QSS = """
QScrollArea { border: none; background: transparent; }
QFrame#styleCard {
    background: #131A2B;
    border: 1px solid #263248;
    border-radius: 12px;
}
QFrame#styleCard:hover {
    background: #192238;
    border-color: #475569;
}
QFrame#styleCard[selected="true"] {
    background: #1B243B;
    border: 2px solid #8B5CF6;
}
QFrame#styleCard[isAuto="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #181B33, stop:1 #112233);
    border: 1px solid #3B4970;
}
QFrame#styleCard[isAuto="true"]:hover {
    border-color: #38BDF8;
}
QFrame#styleCard[isAuto="true"][selected="true"] {
    background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #201D42, stop:1 #132A3E);
    border: 2px solid #06B6D4;
}
QComboBox#cardVarCombo {
    background: #0B0F19;
    color: #38BDF8;
    border: 1px solid #293548;
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 11px;
}
QComboBox#cardVarCombo:hover {
    border-color: #06B6D4;
}
"""


def _sample_scene_for_style(style_id: str) -> dict[str, Any]:
    """Return a characteristic 1-scene mini storyboard showcasing this style's identity."""
    pack, _ = resolve_style_pack(style_id)
    sid = pack.id

    if sid == "auto":
        return {
            "id": 1,
            "background": "STAGE",
            "camera": "MEDIUM",
            "emotion": "EXCITED",
            "topic": "Creative Ideas",
            "narration": "Every story adapts visually to match your message.",
            "characters": [{"id": "PERSON_A", "action": "POINT_UP", "start_x": 0.38, "end_x": 0.38, "y": 0.62, "scale": 1.48, "facing": "right", "speaking": True}],
            "objects": [{"asset": "LIGHTBULB", "x": 0.64, "y": 0.22, "width": 0.20, "height": 0.20}],
        }
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
    if sid == "s15_minimalist_accent":
        return {
            "id": 1,
            "background": "ABSTRACT",
            "camera": "MEDIUM",
            "emotion": "NEUTRAL",
            "narration": "Truth doesn't scream. It breaks the illusion.",
            "characters": [{"id": "PERSON_A", "action": "STAND", "start_x": 0.38, "end_x": 0.38, "y": 0.62, "scale": 1.48, "facing": "right", "speaking": True}],
            "objects": [{"asset": "TETHER_THREAD", "x": 0.40, "y": 0.48, "width": 0.38, "height": 0.16}, {"asset": "DOORWAY_SUNLIGHT", "x": 0.12, "y": 0.28, "width": 0.26, "height": 0.48}],
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


def _make_placeholder_pixmap(pack, w: int = 136, h: int = 166) -> QPixmap:
    """Instant zero-lag gradient card placeholder drawn in <1ms before async preview finishes."""
    px = QPixmap(w, h)
    px.fill(Qt.transparent)
    painter = QPainter(px)
    grad = QLinearGradient(0, 0, w, h)
    grad.setColorAt(0.0, QColor(pack.bg))
    grad.setColorAt(1.0, QColor(pack.bg_secondary))
    painter.fillRect(0, 0, w, h, grad)
    painter.setPen(QColor(pack.accent))
    painter.setFont(QFont("Segoe UI", 16, QFont.Bold))
    painter.drawText(px.rect(), Qt.AlignCenter, pack.code)
    painter.end()
    return px


def _cached_preview_path(style_id: str, variant: Optional[str], w: int, h: int) -> Path:
    pack, sp = resolve_style_pack(style_id, variant)
    var_key = sp.get("variant", "default")
    _PREVIEW_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return _PREVIEW_CACHE_DIR / f"{pack.id}_{var_key}_{w}x{h}.png"


def render_style_preview_qimage(style_id: str, variant: Optional[str] = None, w: int = 136, h: int = 166) -> Optional[QImage]:
    """Render and cache a preview QImage (thread-safe for background QThread use)."""
    pack, sp = resolve_style_pack(style_id, variant)
    var_key = sp.get("variant", "default")
    cache_path = _cached_preview_path(pack.id, var_key, w, h)
    if cache_path.exists():
        img = QImage(str(cache_path))
        if not img.isNull():
            return img

    try:
        composer = SceneComposer(pack.id, width=w, height=h, fps=24, style_variant=var_key)
        scene = _sample_scene_for_style(pack.id)
        frame = None
        for idx, fr in enumerate(composer.compose_scene_stream(scene, 0.7)):
            frame = fr
            if idx >= 8:
                break
        if frame is not None:
            rgb = frame.convert("RGBA")
            try:
                rgb.save(str(cache_path), format="PNG")
            except Exception:
                pass
            raw = rgb.tobytes("raw", "RGBA")
            qimg = QImage(raw, w, h, w * 4, QImage.Format_RGBA8888)
            return qimg.copy()
    except Exception:
        pass
    return None


def render_style_preview_pixmap(style_id: str, variant: Optional[str] = None, w: int = 160, h: int = 212) -> QPixmap:
    """Synchronous helper returning cached or freshly rendered QPixmap."""
    qimg = render_style_preview_qimage(style_id, variant=variant, w=w, h=h)
    if qimg is not None and not qimg.isNull():
        return QPixmap.fromImage(qimg)
    pack, _ = resolve_style_pack(style_id, variant)
    return _make_placeholder_pixmap(pack, w, h)


class _PreviewRenderWorker(QThread):
    """Renders uncached card thumbnails off the GUI thread for instant startup."""

    preview_ready = Signal(str, str, QImage)

    def __init__(self, jobs: list[tuple[str, str, int, int]], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._jobs = list(jobs)
        self._stop = False

    def stop(self) -> None:
        self._stop = True

    def run(self) -> None:
        for style_id, variant, w, h in self._jobs:
            if self._stop or self.isInterruptionRequested():
                break
            img = render_style_preview_qimage(style_id, variant=variant, w=w, h=h)
            if self._stop or self.isInterruptionRequested():
                break
            if img is not None and not img.isNull():
                self.preview_ready.emit(style_id, variant, img)


class StyleCard(QFrame):
    """Clickable style card displaying a cached/async engine preview, badge, name, and variation toggle."""

    clicked = Signal(str)
    variant_selected = Signal(str, str)

    def __init__(self, style_id: str, hero: bool = False, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.pack = STYLE_PACKS[style_id]
        self._style_id = self.pack.id
        self._hero = hero
        self._selected = False
        self._current_variant: Optional[str] = self.pack.variations[0][0] if self.pack.variations else None
        self._thumb_w = 132 if hero else 136
        self._thumb_h = 152 if hero else 160

        self.setObjectName("styleCard")
        self.setProperty("selected", "false")
        self.setProperty("isAuto", "true" if hero else "false")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumWidth(190)
        if hero:
            self.setFixedHeight(192)
        else:
            self.setFixedHeight(282 if self.pack.variations else 252)
        self.setFrameShape(QFrame.StyledPanel)

        if hero:
            self._build_hero_layout()
        else:
            self._build_grid_layout()

        self._load_cached_or_placeholder()

    def _build_hero_layout(self) -> None:
        h = QHBoxLayout(self)
        h.setSpacing(14)
        h.setContentsMargins(14, 12, 14, 12)

        self._preview_lbl = QLabel()
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setFixedSize(self._thumb_w, self._thumb_h)
        self._preview_lbl.setStyleSheet("border: 1px solid #38BDF8; border-radius: 8px; background: #0B0F19;")
        h.addWidget(self._preview_lbl)

        col = QVBoxLayout()
        col.setSpacing(6)
        top_row = QHBoxLayout()
        top_row.setSpacing(8)
        badge = QLabel("✦ BEST • AUTO AI")
        badge.setStyleSheet(
            "background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 #7C3AED, stop:1 #06B6D4); "
            "color: white; font-weight: bold; border-radius: 6px; padding: 3px 9px; font-size: 11px;"
        )
        top_row.addWidget(badge)
        title = QLabel("Auto — AI Script Director")
        title.setFont(QFont("Segoe UI", 12, QFont.Bold))
        title.setStyleSheet("color: #F8FAFC; background: transparent;")
        top_row.addWidget(title, stretch=1)
        col.addLayout(top_row)

        desc = QLabel(
            "Matches every scene's emotion & script topic: mixes all styles (S1–S15) AND synthesizes custom studio palettes, lighting & motion dynamically."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #CBD5E1; font-size: 11px; background: transparent;")
        col.addWidget(desc, stretch=1)

        self._var_combo: Optional[QComboBox] = QComboBox()
        self._var_combo.setObjectName("cardVarCombo")
        for vid, vlabel, _ in self.pack.variations:
            self._var_combo.addItem(vlabel, vid)
        self._var_combo.currentIndexChanged.connect(self._on_variant_combo_changed)
        col.addWidget(self._var_combo)
        h.addLayout(col, stretch=1)

    def _build_grid_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.setSpacing(5)
        layout.setContentsMargins(8, 8, 8, 8)

        top_row = QHBoxLayout()
        top_row.setSpacing(6)
        code_badge = QLabel(self.pack.code)
        code_badge.setFixedWidth(32)
        code_badge.setAlignment(Qt.AlignCenter)
        code_badge.setStyleSheet(
            "background: #F43F5E; color: white; font-weight: bold; border-radius: 5px; padding: 2px 4px; font-size: 10px;"
            if self.pack.collection == "creator"
            else "background: #0284C7; color: white; font-weight: bold; border-radius: 5px; padding: 2px 4px; font-size: 10px;"
        )
        top_row.addWidget(code_badge)

        name_lbl = QLabel(self.pack.name.replace(f"{self.pack.code} ", "", 1))
        name_lbl.setFont(QFont("Segoe UI", 9, QFont.Bold))
        name_lbl.setStyleSheet("color: #F1F5F9; background: transparent;")
        top_row.addWidget(name_lbl, stretch=1)
        layout.addLayout(top_row)

        self._preview_lbl = QLabel()
        self._preview_lbl.setAlignment(Qt.AlignCenter)
        self._preview_lbl.setFixedSize(self._thumb_w, self._thumb_h)
        self._preview_lbl.setStyleSheet("border: 1px solid #1E293B; border-radius: 8px; background: #0B0F19;")
        layout.addWidget(self._preview_lbl, alignment=Qt.AlignHCenter)

        desc_lbl = QLabel(self.pack.short_desc)
        desc_lbl.setAlignment(Qt.AlignCenter)
        desc_lbl.setFont(QFont("Segoe UI", 8))
        desc_lbl.setWordWrap(True)
        desc_lbl.setStyleSheet("color: #94A3B8; background: transparent;")
        layout.addWidget(desc_lbl)

        self._var_combo = None
        if self.pack.variations:
            self._var_combo = QComboBox()
            self._var_combo.setObjectName("cardVarCombo")
            for vid, vlabel, _ in self.pack.variations:
                self._var_combo.addItem(vlabel, vid)
            self._var_combo.currentIndexChanged.connect(self._on_variant_combo_changed)
            layout.addWidget(self._var_combo)

    def _load_cached_or_placeholder(self) -> Optional[tuple[str, str, int, int]]:
        """Load disk-cached preview immediately or set fast placeholder and return render job."""
        var_key = self._current_variant or "default"
        cache_path = _cached_preview_path(self._style_id, var_key, self._thumb_w, self._thumb_h)
        if cache_path.exists():
            px = QPixmap(str(cache_path))
            if not px.isNull():
                self._preview_lbl.setPixmap(px)
                return None
        self._preview_lbl.setPixmap(_make_placeholder_pixmap(self.pack, self._thumb_w, self._thumb_h))
        return (self._style_id, var_key, self._thumb_w, self._thumb_h)

    def apply_rendered_image(self, image: QImage) -> None:
        if not image.isNull():
            self._preview_lbl.setPixmap(QPixmap.fromImage(image))

    def _on_variant_combo_changed(self) -> None:
        if self._var_combo is None:
            return
        self._current_variant = self._var_combo.currentData()
        job = self._load_cached_or_placeholder()
        if job:
            px = render_style_preview_pixmap(self._style_id, variant=self._current_variant, w=self._thumb_w, h=self._thumb_h)
            self._preview_lbl.setPixmap(px)
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
                if self._load_cached_or_placeholder():
                    self._preview_lbl.setPixmap(
                        render_style_preview_pixmap(self._style_id, variant=variant, w=self._thumb_w, h=self._thumb_h)
                    )
                break

    @property
    def style_id(self) -> str:
        return self._style_id

    def set_selected(self, selected: bool) -> None:
        if self._selected == selected:
            return
        self._selected = selected
        self.setProperty("selected", "true" if selected else "false")
        st = self.style()
        if st:
            st.unpolish(self)
            st.polish(self)

    def mousePressEvent(self, event) -> None:  # type: ignore[override]
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self._style_id)
        super().mousePressEvent(event)


class StyleSelector(QWidget):
    """Displays flagship AI Auto style + Creator & Artistic Style Packs cleanly without UI blocking."""

    style_changed = Signal(str)
    variant_changed = Signal(str)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._cards: dict[str, StyleCard] = {}
        self._selected_id: str = AUTO_STYLE_IDS[0]
        self._worker: Optional[_PreviewRenderWorker] = None
        self.setStyleSheet(_GALLERY_QSS)
        self._setup_ui()
        self.set_selected_style(self._selected_id)

        app = QApplication.instance()
        if app is not None:
            app.aboutToQuit.connect(self.stop_worker)

    def stop_worker(self) -> None:
        if self._worker is not None and self._worker.isRunning():
            self._worker.stop()
            self._worker.requestInterruption()
            self._worker.wait(1500)

    def _setup_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        container.setStyleSheet("background: transparent;")
        root_v = QVBoxLayout(container)
        root_v.setSpacing(12)
        root_v.setContentsMargins(10, 10, 10, 10)

        pending_jobs: list[tuple[str, str, int, int]] = []

        # ---- HERO: AI AUTO DIRECTOR (Recommended Best Option) ----
        auto_lbl = QLabel("✨  AI AUTO DIRECTOR  (Mixes All Styles + Custom Studio Presets)")
        auto_lbl.setStyleSheet("color: #22D3EE; font-size: 12px; font-weight: bold; padding-left: 2px; background: transparent;")
        root_v.addWidget(auto_lbl)

        for sid in AUTO_STYLE_IDS:
            card = StyleCard(sid, hero=True)
            card.clicked.connect(self._on_card_clicked)
            card.variant_selected.connect(self._on_variant_changed)
            self._cards[sid] = card
            job = card._load_cached_or_placeholder()
            if job:
                pending_jobs.append(job)
            root_v.addWidget(card)

        # ---- VIRAL CREATOR & EXPLAINER STYLES (S1-S6 + S14-S15) ----
        dir_lbl = QLabel("🔥  VIRAL CREATOR & EXPLAINER STYLES")
        dir_lbl.setStyleSheet("color: #FB7185; font-size: 12px; font-weight: bold; padding-top: 6px; padding-left: 2px; background: transparent;")
        root_v.addWidget(dir_lbl)

        dir_grid = QGridLayout()
        dir_grid.setSpacing(10)
        for idx, sid in enumerate(CREATOR_STYLE_IDS):
            card = StyleCard(sid)
            card.clicked.connect(self._on_card_clicked)
            card.variant_selected.connect(self._on_variant_changed)
            self._cards[sid] = card
            job = card._load_cached_or_placeholder()
            if job:
                pending_jobs.append(job)
            row, col = divmod(idx, 3)
            dir_grid.addWidget(card, row, col)
        root_v.addLayout(dir_grid)

        # ---- ARTISTIC & STORYTELLING STYLES (S7-S13) ----
        auto_grp_lbl = QLabel("🎨  ARTISTIC & STORYTELLING STYLES")
        auto_grp_lbl.setStyleSheet("color: #38BDF8; font-size: 12px; font-weight: bold; padding-top: 6px; padding-left: 2px; background: transparent;")
        root_v.addWidget(auto_grp_lbl)

        auto_grid = QGridLayout()
        auto_grid.setSpacing(10)
        for idx, sid in enumerate(ARTISTIC_STYLE_IDS):
            card = StyleCard(sid)
            card.clicked.connect(self._on_card_clicked)
            card.variant_selected.connect(self._on_variant_changed)
            self._cards[sid] = card
            job = card._load_cached_or_placeholder()
            if job:
                pending_jobs.append(job)
            row, col = divmod(idx, 3)
            auto_grid.addWidget(card, row, col)
        root_v.addLayout(auto_grid)

        footer_lbl = QLabel("✨ Stickman Studio • Designed & Engineered by Atharv Hatwar")
        footer_lbl.setAlignment(Qt.AlignCenter)
        footer_lbl.setStyleSheet("color: #64748B; font-size: 11px; padding-top: 8px; font-style: italic; background: transparent;")
        root_v.addWidget(footer_lbl)
        root_v.addStretch()

        scroll.setWidget(container)
        outer.addWidget(scroll)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        if pending_jobs:
            self._worker = _PreviewRenderWorker(pending_jobs, self)
            self._worker.preview_ready.connect(self._on_async_preview_ready)
            self._worker.start()

    def _on_async_preview_ready(self, style_id: str, variant: str, image: QImage) -> None:
        card = self._cards.get(style_id)
        if card and (card.get_variant() or "default") == variant:
            card.apply_rendered_image(image)

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
        pack, _ = resolve_style_pack(style_id, variant)
        resolved = pack.id
        for sid, card in self._cards.items():
            card.set_selected(sid == resolved)
        if variant and resolved in self._cards:
            self._cards[resolved].set_variant(variant)
        self._selected_id = resolved
