"""
Style Packs Registry - High-End Creative Video Presets (12 Modern Pro Styles)
=============================================================================
Replaces legacy outdated presets with 12 modern, high-demand animation styles
crafted specifically for viral YouTube Shorts, Reels, TikTok, and explainer channels.

Collections:
1. VIRAL CREATOR & EXPLAINER (S1 - S6):
   - S1 RSA Whiteboard Explainer (MinutePhysics / AsapSCIENCE)
   - S2 Cyberpunk Neon Terminal (Tech / AI / Crypto)
   - S3 Pop Art & Retro Comic (High-Energy Comic Action)
   - S4 Notion & Tech Minimalist (Corporate Startup Polish)
   - S5 Luxury Gold & Finance (Billionaire Mindset & Wealth)
   - S6 Academic Chalkboard Lecture (Harvard / MIT Math & Science)

2. ARTISTIC & STORYTELLING (S7 - S12):
   - S7 Cozy Ghibli Storybook (Warm Pastel Watercolor)
   - S8 Shonen Manga Action (High-Contrast Anime B&W)
   - S9 8-Bit Retro Arcade CRT (Gaming Nostalgia)
   - S10 Blueprint CAD Engineering (Technical Schematics)
   - S11 Urban Street Art & Graffiti (Edgy Neon Punk)
   - S12 1940s Detective Film Noir (Moody Dramatic Mystery)

Created by Atharv Hatwar.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class StylePack:
    """Complete self-contained visual & storytelling identity for a video style."""

    id: str
    code: str
    collection: str  # "creator" | "artistic"
    name: str
    short_desc: str
    # Canvas & core palette
    bg: str
    bg_secondary: str
    fg: str
    accent: str
    accent_secondary: str
    character_palette: tuple[str, ...]
    head_fill: str
    filled_head: bool = False
    # Proportions & linework
    line_width: float = 4.2
    head_radius: float = 19.0
    limb_taper: float = 0.25
    line_technique: str = "crisp"  # crisp | hand_drawn | bold_ink | glowing_crt | noir_rim | chalk
    wobble_px: float = 0.0
    # Costumes & character identity
    primary_outfit: str = "minimalist"
    secondary_outfit: str = "minimal_cap"
    default_accessory: str = "none"
    character_rim_color: str = ""
    cheek_blush: bool = False
    # Backgrounds & overlays
    bg_theme: str = "studio_clean"
    lighting_mode: str = "clean"
    vignette_strength: float = 0.0
    paper_grain: float = 0.0
    scanlines: bool = False
    headline_banner: bool = False
    presenter_pip: bool = False
    default_background: str = "STAGE"
    preferred_backgrounds: tuple[str, ...] = ("STAGE", "OFFICE", "CITY", "ABSTRACT")
    # Animation & camera behaviour
    motion_feel: str = "smooth"
    ease_overshoot: float = 0.0
    tremble_amp: float = 0.0
    pacing_multiplier: float = 1.0
    preferred_transition: str = "FADE"
    preferred_camera: str = "MEDIUM"
    # Typography & captions
    caption_font: str = "Segoe UI Bold"
    caption_text_color: str = "#FFFFFF"
    caption_stroke_color: str = "#111111"
    caption_bg_color: str = "#000000"
    caption_highlight_color: str = "#FFD700"
    caption_pill_alpha: int = 175
    # Audio hints
    preferred_music: str = "calm"
    preferred_sfx: str = "pop"
    # Optional variations
    variations: tuple[tuple[str, str, dict[str, Any]], ...] = field(default_factory=tuple)

    def to_params(self, variant: Optional[str] = None) -> dict[str, Any]:
        """Materialize flat style dictionary with optional variation overrides."""
        data: dict[str, Any] = {
            "id": self.id,
            "code": self.code,
            "collection": self.collection,
            "name": self.name,
            "variant": variant or (self.variations[0][0] if self.variations else "default"),
            "bg": self.bg,
            "bg_secondary": self.bg_secondary,
            "fg": self.fg,
            "accent": self.accent,
            "accent_secondary": self.accent_secondary,
            "character_palette": list(self.character_palette),
            "head_fill": self.head_fill,
            "filled_head": self.filled_head,
            "line_width": self.line_width,
            "head_radius": self.head_radius,
            "limb_taper": self.limb_taper,
            "line_technique": self.line_technique,
            "wobble_px": self.wobble_px,
            "primary_outfit": self.primary_outfit,
            "secondary_outfit": self.secondary_outfit,
            "default_accessory": self.default_accessory,
            "character_rim_color": self.character_rim_color,
            "cheek_blush": self.cheek_blush,
            "bg_theme": self.bg_theme,
            "lighting_mode": self.lighting_mode,
            "vignette_strength": self.vignette_strength,
            "paper_grain": self.paper_grain,
            "scanlines": self.scanlines,
            "headline_banner": self.headline_banner,
            "presenter_pip": self.presenter_pip,
            "default_background": self.default_background,
            "preferred_backgrounds": list(self.preferred_backgrounds),
            "motion_feel": self.motion_feel,
            "ease_overshoot": self.ease_overshoot,
            "tremble_amp": self.tremble_amp,
            "pacing_multiplier": self.pacing_multiplier,
            "preferred_transition": self.preferred_transition,
            "preferred_camera": self.preferred_camera,
            "caption_font": self.caption_font,
            "caption_text_color": self.caption_text_color,
            "caption_stroke_color": self.caption_stroke_color,
            "caption_bg_color": self.caption_bg_color,
            "caption_highlight_color": self.caption_highlight_color,
            "caption_pill_alpha": self.caption_pill_alpha,
            "preferred_music": self.preferred_music,
            "preferred_sfx": self.preferred_sfx,
        }
        if variant and self.variations:
            for v_id, _v_label, overrides in self.variations:
                if v_id == variant:
                    data.update(overrides)
                    data["variant"] = v_id
                    break
        return data


# ===========================================================================
# THE 12 MODERN PRO STYLES
# ===========================================================================

STYLE_PACKS: dict[str, StylePack] = {
    # -----------------------------------------------------------------------
    # 1. VIRAL CREATOR & EXPLAINER STYLES (S1 - S6)
    # -----------------------------------------------------------------------
    "s1_rsa_whiteboard": StylePack(
        id="s1_rsa_whiteboard",
        code="S1",
        collection="creator",
        name="S1 RSA Whiteboard Explainer",
        short_desc="Organic hand-drawn sketchy ink on textured paper with bright red & cyan marker highlights",
        bg="#FFFFFF",
        bg_secondary="#F8FAFC",
        fg="#18181B",
        accent="#EF4444",
        accent_secondary="#0284C7",
        character_palette=("#18181B", "#EF4444", "#0284C7"),
        head_fill="#FFFFFF",
        line_width=4.5,
        head_radius=19.0,
        limb_taper=0.22,
        line_technique="hand_drawn",
        wobble_px=1.2,
        paper_grain=0.18,
        lighting_mode="paper_grain",
        motion_feel="bouncy_sketch",
        ease_overshoot=0.22,
        preferred_transition="SLIDE_LEFT",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#18181B",
        caption_bg_color="#18181B",
        caption_highlight_color="#EF4444",
        caption_pill_alpha=220,
        preferred_music="calm",
        preferred_sfx="pop",
        variations=(
            ("white_paper", "White Sketchbook", {}),
            ("grid_notebook", "Grid Notebook Paper", {"paper_grain": 0.25}),
        ),
    ),
    "s2_cyberpunk_neon": StylePack(
        id="s2_cyberpunk_neon",
        code="S2",
        collection="creator",
        name="S2 Cyberpunk Neon Terminal",
        short_desc="Obsidian dark mode canvas with glowing cyan & electric pink neon strokes and tech grid",
        bg="#090D16",
        bg_secondary="#111827",
        fg="#00F0FF",
        accent="#FF0055",
        accent_secondary="#A855F7",
        character_palette=("#00F0FF", "#FF0055", "#A855F7"),
        head_fill="#090D16",
        line_width=3.8,
        head_radius=18.5,
        limb_taper=0.18,
        line_technique="glowing_crt",
        scanlines=True,
        lighting_mode="tech_grid",
        character_rim_color="#FF0055",
        default_background="CITY",
        preferred_backgrounds=("CITY", "OFFICE", "ABSTRACT"),
        motion_feel="snappy_pop",
        ease_overshoot=0.18,
        preferred_transition="SNAP_CUT",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#030712",
        caption_bg_color="#030712",
        caption_highlight_color="#00F0FF",
        caption_pill_alpha=230,
        preferred_music="energetic",
        preferred_sfx="notification",
        variations=(
            ("matrix_cyan", "Cyan & Pink Matrix", {}),
            ("purple_glow", "Deep Purple & Violet", {
                "fg": "#C084FC",
                "accent": "#F43F5E",
                "character_rim_color": "#F43F5E",
                "caption_highlight_color": "#C084FC",
            }),
        ),
    ),
    "s3_retro_pop_comic": StylePack(
        id="s3_retro_pop_comic",
        code="S3",
        collection="creator",
        name="S3 Pop Art & Retro Comic",
        short_desc="Vintage comic book dots, bold black ink borders, primary yellow & red action bursts",
        bg="#FFFBEB",
        bg_secondary="#FEF3C7",
        fg="#111827",
        accent="#EF4444",
        accent_secondary="#FACC15",
        character_palette=("#111827", "#EF4444", "#FACC15"),
        head_fill="#FFFFFF",
        line_width=5.2,
        head_radius=19.5,
        limb_taper=0.28,
        line_technique="bold_ink",
        primary_outfit="beanie_tee",
        motion_feel="heavy_comic",
        ease_overshoot=0.25,
        preferred_transition="SLIDE_LEFT",
        preferred_camera="MEDIUM",
        caption_font="Arial Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#111827",
        caption_bg_color="#111827",
        caption_highlight_color="#FACC15",
        caption_pill_alpha=225,
        preferred_music="energetic",
        preferred_sfx="boing",
    ),
    "s4_notion_startup": StylePack(
        id="s4_notion_startup",
        code="S4",
        collection="creator",
        name="S4 Notion & Tech Minimalist",
        short_desc="Modern tech explainer with clean rounded lines, warm off-white paper, and royal indigo accents",
        bg="#FBFBFA",
        bg_secondary="#F4F4F5",
        fg="#18181B",
        accent="#6366F1",
        accent_secondary="#10B981",
        character_palette=("#18181B", "#6366F1", "#10B981"),
        head_fill="#FFFFFF",
        line_width=4.0,
        head_radius=19.0,
        limb_taper=0.20,
        line_technique="crisp",
        default_background="OFFICE",
        preferred_backgrounds=("OFFICE", "STAGE", "CITY", "ABSTRACT"),
        motion_feel="smooth",
        ease_overshoot=0.12,
        preferred_transition="FADE",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#18181B",
        caption_bg_color="#18181B",
        caption_highlight_color="#6366F1",
        caption_pill_alpha=215,
        preferred_music="calm",
        preferred_sfx="pop",
        variations=(
            ("indigo_light", "Indigo Minimalist Light", {}),
            ("emerald_dark", "Emerald Dark Mode", {
                "bg": "#0F172A",
                "bg_secondary": "#1E293B",
                "fg": "#F8FAFC",
                "accent": "#10B981",
                "head_fill": "#0F172A",
                "caption_highlight_color": "#10B981",
            }),
        ),
    ),
    "s5_dark_gold_wealth": StylePack(
        id="s5_dark_gold_wealth",
        code="S5",
        collection="creator",
        name="S5 Luxury Gold & Finance",
        short_desc="Deep matte black canvas, metallic gold foil lines, and emerald indicators for finance & mindset",
        bg="#090A0F",
        bg_secondary="#131722",
        fg="#F59E0B",
        accent="#10B981",
        accent_secondary="#FBBF24",
        character_palette=("#F59E0B", "#10B981", "#FFFFFF"),
        head_fill="#090A0F",
        line_width=4.2,
        head_radius=19.0,
        limb_taper=0.24,
        line_technique="noir_rim",
        character_rim_color="#F59E0B",
        vignette_strength=0.45,
        lighting_mode="amber_noir",
        default_background="CITY",
        preferred_backgrounds=("CITY", "STAGE", "OFFICE", "ABSTRACT"),
        motion_feel="theatrical",
        ease_overshoot=0.16,
        preferred_transition="SLIDE_LEFT",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#090A0F",
        caption_bg_color="#090A0F",
        caption_highlight_color="#F59E0B",
        caption_pill_alpha=230,
        preferred_music="dramatic",
        preferred_sfx="coin_clink",
    ),
    "s6_chalkboard_academy": StylePack(
        id="s6_chalkboard_academy",
        code="S6",
        collection="creator",
        name="S6 Academic Chalkboard Lecture",
        short_desc="Dark green chalkboard slate, powdery chalk linework, formulas, and yellow chalk highlights",
        bg="#19231E",
        bg_secondary="#131C18",
        fg="#F8FAFC",
        accent="#FDE047",
        accent_secondary="#86EFAC",
        character_palette=("#F8FAFC", "#FDE047", "#86EFAC"),
        head_fill="#19231E",
        line_width=4.4,
        head_radius=19.0,
        limb_taper=0.20,
        line_technique="chalk",
        wobble_px=1.0,
        default_background="CLASSROOM",
        preferred_backgrounds=("CLASSROOM", "STAGE", "LIBRARY", "ABSTRACT"),
        motion_feel="snappy_pop",
        ease_overshoot=0.15,
        preferred_transition="FADE",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#19231E",
        caption_bg_color="#19231E",
        caption_highlight_color="#FDE047",
        caption_pill_alpha=220,
        preferred_music="calm",
        preferred_sfx="pencil_scratch",
    ),

    # -----------------------------------------------------------------------
    # 2. ARTISTIC & STORYTELLING STYLES (S7 - S12)
    # -----------------------------------------------------------------------
    "s7_ghibli_watercolor": StylePack(
        id="s7_ghibli_watercolor",
        code="S7",
        collection="artistic",
        name="S7 Cozy Ghibli Storybook",
        short_desc="Warm cream watercolor wash, soft charcoal outlines, matcha green & terracotta tones",
        bg="#FAF8F5",
        bg_secondary="#F3EDE2",
        fg="#292524",
        accent="#D97706",
        accent_secondary="#15803D",
        character_palette=("#292524", "#D97706", "#15803D"),
        head_fill="#FAF8F5",
        line_width=3.8,
        head_radius=19.0,
        limb_taper=0.22,
        line_technique="hand_drawn",
        cheek_blush=True,
        primary_outfit="cozy_sweater",
        default_accessory="scarf",
        paper_grain=0.15,
        lighting_mode="warm_rays",
        default_background="CAFE",
        preferred_backgrounds=("CAFE", "PARK", "HOME", "ABSTRACT"),
        motion_feel="gentle_slow",
        ease_overshoot=0.08,
        preferred_transition="FADE",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#292524",
        caption_bg_color="#292524",
        caption_highlight_color="#D97706",
        caption_pill_alpha=200,
        preferred_music="cozy",
        preferred_sfx="chime_soft",
    ),
    "s8_shonen_manga": StylePack(
        id="s8_shonen_manga",
        code="S8",
        collection="artistic",
        name="S8 Shonen Manga Action",
        short_desc="High-contrast dynamic B&W manga ink, dramatic crosshatching, speed lines, and intense shonen eyes",
        bg="#FFFFFF",
        bg_secondary="#F3F4F6",
        fg="#000000",
        accent="#DC2626",
        accent_secondary="#4B5563",
        character_palette=("#000000", "#DC2626", "#4B5563"),
        head_fill="#FFFFFF",
        line_width=5.6,
        head_radius=19.5,
        limb_taper=0.32,
        line_technique="bold_ink",
        default_background="STAGE",
        preferred_backgrounds=("STAGE", "CITY", "MOUNTAIN", "ABSTRACT"),
        motion_feel="snappy_pop",
        ease_overshoot=0.30,
        preferred_transition="SNAP_CUT",
        preferred_camera="PUNCH_IN",
        caption_font="Arial Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#000000",
        caption_bg_color="#000000",
        caption_highlight_color="#DC2626",
        caption_pill_alpha=230,
        preferred_music="energetic",
        preferred_sfx="impact",
    ),
    "s9_retro_arcade": StylePack(
        id="s9_retro_arcade",
        code="S9",
        collection="artistic",
        name="S9 8-Bit Retro Arcade CRT",
        short_desc="Phosphor screen glow, emerald green vector lines, pixel health bars, and arcade badges",
        bg="#051008",
        bg_secondary="#081C0E",
        fg="#22C55E",
        accent="#EAB308",
        accent_secondary="#38BDF8",
        character_palette=("#22C55E", "#EAB308", "#38BDF8"),
        head_fill="#051008",
        line_width=4.2,
        head_radius=18.0,
        limb_taper=0.15,
        line_technique="glowing_crt",
        scanlines=True,
        default_background="STAGE",
        preferred_backgrounds=("STAGE", "CITY", "ABSTRACT"),
        motion_feel="snappy_pop",
        ease_overshoot=0.20,
        preferred_transition="SLIDE_LEFT",
        preferred_camera="MEDIUM",
        caption_font="Arial Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#051008",
        caption_bg_color="#051008",
        caption_highlight_color="#22C55E",
        caption_pill_alpha=225,
        preferred_music="energetic",
        preferred_sfx="boing",
    ),
    "s10_blueprint_cad": StylePack(
        id="s10_blueprint_cad",
        code="S10",
        collection="artistic",
        name="S10 Blueprint CAD Engineering",
        short_desc="Deep engineering blueprint cyan with pure white technical CAD lines and measurement markings",
        bg="#0B2545",
        bg_secondary="#081C34",
        fg="#FFFFFF",
        accent="#38BDF8",
        accent_secondary="#F59E0B",
        character_palette=("#FFFFFF", "#38BDF8", "#F59E0B"),
        head_fill="#0B2545",
        line_width=3.6,
        head_radius=18.5,
        limb_taper=0.18,
        line_technique="crisp",
        lighting_mode="tech_grid",
        default_background="OFFICE",
        preferred_backgrounds=("OFFICE", "STAGE", "ABSTRACT"),
        motion_feel="smooth",
        ease_overshoot=0.10,
        preferred_transition="FADE",
        preferred_camera="MEDIUM",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#0B2545",
        caption_bg_color="#0B2545",
        caption_highlight_color="#38BDF8",
        caption_pill_alpha=220,
        preferred_music="calm",
        preferred_sfx="notification",
    ),
    "s11_graffiti_punk": StylePack(
        id="s11_graffiti_punk",
        code="S11",
        collection="artistic",
        name="S11 Urban Street Art & Graffiti",
        short_desc="Dark asphalt canvas, vibrant neon spray-paint splatter, and punchy urban marker energy",
        bg="#18181B",
        bg_secondary="#27272A",
        fg="#F43F5E",
        accent="#FACC15",
        accent_secondary="#06B6D4",
        character_palette=("#F43F5E", "#FACC15", "#06B6D4"),
        head_fill="#18181B",
        line_width=5.0,
        head_radius=19.5,
        limb_taper=0.26,
        line_technique="bold_ink",
        default_background="STREET",
        preferred_backgrounds=("STREET", "CITY", "STAGE"),
        motion_feel="bouncy_sketch",
        ease_overshoot=0.25,
        preferred_transition="SLIDE_LEFT",
        preferred_camera="PUNCH_IN",
        caption_font="Arial Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#18181B",
        caption_bg_color="#18181B",
        caption_highlight_color="#FACC15",
        caption_pill_alpha=225,
        preferred_music="energetic",
        preferred_sfx="impact",
    ),
    "s12_cinematic_noir": StylePack(
        id="s12_cinematic_noir",
        code="S12",
        collection="artistic",
        name="S12 1940s Detective Film Noir",
        short_desc="High-contrast chiaroscuro shadow play, Venetian blind light beams, trench coats, and mystery thriller",
        bg="#0C0A09",
        bg_secondary="#1C1917",
        fg="#F5F5F4",
        accent="#D97706",
        accent_secondary="#78716C",
        character_palette=("#F5F5F4", "#D97706", "#78716C"),
        head_fill="#0C0A09",
        line_width=4.2,
        head_radius=19.0,
        limb_taper=0.25,
        line_technique="noir_rim",
        character_rim_color="#D97706",
        vignette_strength=0.65,
        lighting_mode="amber_noir",
        default_background="CITY",
        preferred_backgrounds=("CITY", "STREET", "OFFICE"),
        motion_feel="theatrical",
        ease_overshoot=0.14,
        preferred_transition="FADE",
        preferred_camera="CLOSE",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#0C0A09",
        caption_bg_color="#0C0A09",
        caption_highlight_color="#D97706",
        caption_pill_alpha=230,
        preferred_music="dramatic",
        preferred_sfx="whoosh",
    ),
    "s13_cinematic_storyteller": StylePack(
        id="s13_cinematic_storyteller",
        code="S13",
        collection="artistic",
        name="S13 Cinematic Storyteller",
        short_desc="Warm golden-hour narrative lighting, antique parchment texture, epic fable staging, and expressive character acting",
        bg="#FBF8F1",
        bg_secondary="#F5EFE0",
        fg="#1C1917",
        accent="#D97706",
        accent_secondary="#059669",
        character_palette=("#1C1917", "#D97706", "#059669", "#DC2626"),
        head_fill="#FBF8F1",
        line_width=4.4,
        head_radius=19.2,
        limb_taper=0.25,
        line_technique="hand_drawn",
        primary_outfit="cloak_hood",
        default_accessory="satchel",
        paper_grain=0.20,
        vignette_strength=0.35,
        lighting_mode="golden_hour",
        default_background="MOUNTAIN",
        preferred_backgrounds=("MOUNTAIN", "PARK", "CAFE", "LIBRARY", "STAGE"),
        motion_feel="theatrical",
        ease_overshoot=0.18,
        preferred_transition="FADE",
        preferred_camera="SLOW_ZOOM_IN",
        caption_font="Georgia Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#1C1917",
        caption_bg_color="#1C1917",
        caption_highlight_color="#F59E0B",
        caption_pill_alpha=220,
        preferred_music="cinematic_story",
        preferred_sfx="chime_soft",
    ),
    "s14_chameleon_adaptive": StylePack(
        id="s14_chameleon_adaptive",
        code="S14",
        collection="creator",
        name="S14 Chameleon Dynamic (Adaptive Story Mix)",
        short_desc="Adapts linework, palettes, and atmosphere dynamically per scene based on script topic.",
        bg="#FFFFFF",
        bg_secondary="#F8FAFC",
        fg="#0F172A",
        accent="#6366F1",
        accent_secondary="#EC4899",
        character_palette=("#0F172A", "#6366F1", "#10B981", "#F59E0B", "#EF4444"),
        head_fill="#FFFFFF",
        filled_head=False,
        line_width=4.2,
        head_radius=19.0,
        limb_taper=0.20,
        line_technique="crisp",
        primary_outfit="minimalist",
        secondary_outfit="minimal_cap",
        bg_theme="studio_clean",
        lighting_mode="clean",
        default_background="STAGE",
        preferred_backgrounds=("STAGE", "OFFICE", "CITY", "MIND", "BEDROOM", "MOUNTAIN"),
        motion_feel="dynamic_adaptive",
        ease_overshoot=0.18,
        preferred_transition="DYNAMIC",
        preferred_camera="DYNAMIC_CUT",
        caption_font="Segoe UI Bold",
        caption_text_color="#FFFFFF",
        caption_stroke_color="#0F172A",
        caption_bg_color="#0F172A",
        caption_highlight_color="#F59E0B",
        caption_pill_alpha=200,
        preferred_music="epic_hype",
        preferred_sfx="pop",
        variations=(
            ("auto", "Full Adaptive Mix", {}),
            ("vibrant", "High-Energy Pop & Neon", {}),
            ("cinematic", "Moody Noir & Storybook", {}),
        ),
    ),
}

CREATOR_STYLE_IDS: tuple[str, ...] = (
    "s1_rsa_whiteboard",
    "s2_cyberpunk_neon",
    "s3_retro_pop_comic",
    "s4_notion_startup",
    "s5_dark_gold_wealth",
    "s6_chalkboard_academy",
    "s14_chameleon_adaptive",
)

ARTISTIC_STYLE_IDS: tuple[str, ...] = (
    "s7_ghibli_watercolor",
    "s8_shonen_manga",
    "s9_retro_arcade",
    "s10_blueprint_cad",
    "s11_graffiti_punk",
    "s12_cinematic_noir",
    "s13_cinematic_storyteller",
)

# For backward compatibility with existing code and tests
DIRECTOR_STYLE_IDS: tuple[str, ...] = CREATOR_STYLE_IDS
AUTOPILOT_STYLE_IDS: tuple[str, ...] = ARTISTIC_STYLE_IDS
ALL_STYLE_IDS: tuple[str, ...] = CREATOR_STYLE_IDS + ARTISTIC_STYLE_IDS

# Backwards-compatible mapping from previous style names to new modern packs
LEGACY_STYLE_MAP: dict[str, tuple[str, Optional[str]]] = {
    # Chameleon Adaptive mapping
    "adaptive":              ("s14_chameleon_adaptive", None),
    "mixed":                 ("s14_chameleon_adaptive", None),
    "chameleon":             ("s14_chameleon_adaptive", None),
    # Previous A1-A6 Director mapping
    "a1_classic_bw":        ("s4_notion_startup", "indigo_light"),
    "a2_modern_pop":         ("s3_retro_pop_comic", None),
    "a3_prehistoric_cave":   ("s7_ghibli_watercolor", None),
    "a4_cozy_storytelling":  ("s7_ghibli_watercolor", None),
    "a5_historical_cartoon": ("s3_retro_pop_comic", None),
    "a6_amber_noir":         ("s12_cinematic_noir", None),
    # Previous B1-B5 Autopilot mapping
    "b1_minimal_line_art":   ("s1_rsa_whiteboard", "white_paper"),
    "b2_colorful_hand_drawn":("s1_rsa_whiteboard", "grid_notebook"),
    "b3_retro_tv":           ("s9_retro_arcade", None),
    "b4_survival_thriller":  ("s2_cyberpunk_neon", None),
    "b5_character_explainer":("s4_notion_startup", None),
    # Original 8 legacy mapping
    "minimal_bw":            ("s1_rsa_whiteboard", None),
    "colorful":              ("s3_retro_pop_comic", None),
    "modern_explainer":      ("s4_notion_startup", None),
    "retro_comic":           ("s3_retro_pop_comic", None),
    "whiteboard":            ("s1_rsa_whiteboard", None),
    "dark_cinematic":        ("s5_dark_gold_wealth", None),
    "chalkboard":            ("s6_chalkboard_academy", None),
    "minimal_infographic":   ("s4_notion_startup", None),
}


def resolve_style_pack(
    style_id: str,
    variant: Optional[str] = None,
) -> tuple[StylePack, dict[str, Any]]:
    """Resolve any style ID (including legacy names) to (StylePack, params_dict)."""
    key = (style_id or "s1_rsa_whiteboard").strip().lower()
    if key in LEGACY_STYLE_MAP:
        mapped_id, mapped_var = LEGACY_STYLE_MAP[key]
        pack = STYLE_PACKS[mapped_id]
        return pack, pack.to_params(variant or mapped_var)

    pack = STYLE_PACKS.get(key) or STYLE_PACKS["s1_rsa_whiteboard"]
    return pack, pack.to_params(variant)


def get_style_choices() -> list[dict[str, Any]]:
    """Return ordered metadata dicts for all 12 styles for UI presentation."""
    items: list[dict[str, Any]] = []
    for sid in ALL_STYLE_IDS:
        pack = STYLE_PACKS[sid]
        items.append({
            "id": pack.id,
            "code": pack.code,
            "collection": pack.collection,
            "name": pack.name,
            "desc": pack.short_desc,
            "variations": [(vid, vlabel) for vid, vlabel, _ in pack.variations],
            "preferred_music": pack.preferred_music,
        })
    return items


def get_adaptive_style_for_scene(narration: str = "", emotion: str = "", action: str = "") -> str:
    """
    Selects the most impactful, tone-aligned style for a scene when using S14 Chameleon Adaptive.
    Created by Atharv Hatwar.
    """
    text = (narration or "").lower()
    emo = (emotion or "").upper()
    act = (action or "").upper()

    # 1. High energy / battle / conflict / sprint / shock
    if act in ("RUN", "SPRINT_FAST", "FIGHT", "JUMP") or emo in ("SURPRISED", "ANGRY", "CRINGE") or any(w in text for w in ("fight", "run", "chase", "explode", "battle", "crush", "warning", "fast", "sprint", "danger")):
        return "s8_shonen_manga" if any(w in text for w in ("action", "fight", "battle", "anime", "power", "clash")) else "s3_retro_pop_comic"

    # 2. Tech / Coding / Future / AI / Cyber / Terminal
    if any(w in text for w in ("code", "tech", "ai", "software", "terminal", "algorithm", "crypto", "data", "system", "hacker", "future", "matrix")):
        return "s2_cyberpunk_neon"

    # 3. Wealth / Finance / Money / Luxury
    if act == "COUNT_MONEY" or any(w in text for w in ("money", "wealth", "dollar", "cash", "rich", "invest", "millionaire", "gold", "profit", "asset")):
        return "s5_dark_gold_wealth"

    # 4. Mystery / Doubt / Question / Dark / Noir
    if any(w in text for w in ("why", "mystery", "secret", "shadow", "detective", "hidden", "truth", "crime", "dark", "unknown", "whisper")):
        return "s12_cinematic_noir"

    # 5. Cozy / Heartfelt / Nature / Sleep / Relax
    if act in ("BED_REST", "BED_SHOCK", "SIT") or emo in ("CALM", "SAD") or any(w in text for w in ("peace", "cozy", "bed", "sleep", "dream", "nature", "forest", "morning", "gentle", "friend", "love", "memory")):
        return "s7_ghibli_watercolor"

    # 6. Teaching / Lecture / Science / Math
    if any(w in text for w in ("math", "formula", "science", "physics", "chalk", "professor", "lecture", "study", "exam", "theory")):
        return "s6_chalkboard_academy"

    # 7. Modern Startup / Desk / Productivity / Organization
    if act in ("TYPING_LAPTOP", "PRESENT_CHART") or any(w in text for w in ("startup", "work", "office", "minimal", "plan", "clean", "task", "project", "discipline", "habit")):
        return "s4_notion_startup"

    # Default versatile explainer
    return "s1_rsa_whiteboard"
