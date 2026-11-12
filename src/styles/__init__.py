"""Style packs registry for Stickman Studio (11 Director & Autopilot styles)."""

from .style_packs import (
    ALL_STYLE_IDS,
    AUTO_STYLE_IDS,
    AUTOPILOT_STYLE_IDS,
    DIRECTOR_STYLE_IDS,
    LEGACY_STYLE_MAP,
    STYLE_PACKS,
    StylePack,
    get_style_choices,
    resolve_style_pack,
    synthesize_auto_style_for_scene,
)

__all__ = [
    "StylePack",
    "STYLE_PACKS",
    "AUTO_STYLE_IDS",
    "DIRECTOR_STYLE_IDS",
    "AUTOPILOT_STYLE_IDS",
    "ALL_STYLE_IDS",
    "LEGACY_STYLE_MAP",
    "resolve_style_pack",
    "synthesize_auto_style_for_scene",
    "get_style_choices",
]
