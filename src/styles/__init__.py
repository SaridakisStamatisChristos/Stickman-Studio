"""Style packs registry for Stickman Studio (11 Director & Autopilot styles)."""

from .style_packs import (
    ALL_STYLE_IDS,
    AUTOPILOT_STYLE_IDS,
    DIRECTOR_STYLE_IDS,
    LEGACY_STYLE_MAP,
    STYLE_PACKS,
    StylePack,
    get_style_choices,
    resolve_style_pack,
)

__all__ = [
    "StylePack",
    "STYLE_PACKS",
    "DIRECTOR_STYLE_IDS",
    "AUTOPILOT_STYLE_IDS",
    "ALL_STYLE_IDS",
    "LEGACY_STYLE_MAP",
    "resolve_style_pack",
    "get_style_choices",
]

