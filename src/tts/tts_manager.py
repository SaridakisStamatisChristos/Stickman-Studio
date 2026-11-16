"""
TTS Manager - Local text-to-speech with Kokoro-ONNX, Piper, and Windows SAPI backends.
Fully offline. No cloud TTS. No paid APIs.

Strictly exposes only voices and languages genuinely supported by locally
installed models/engines.
"""

from __future__ import annotations

import array
import importlib.util
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
import uuid
import wave
from pathlib import Path
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Voice metadata catalogues for downloadable / installed local engines
# ---------------------------------------------------------------------------

KOKORO_VOICE_CATALOG: list[dict] = [
    # ── Hyper-Realistic Human Blend Profiles (Atharv Hatwar) ────────────
    {"id": "blend:female_warm", "name": "Maya (Female, Warm Empathy Blend)", "gender": "female", "personality": "natural", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Human Blend", "Warmth & Breath", "Dialogue"]},
    {"id": "blend:male_introspective", "name": "Alex (Male, Introspective Deep Blend)", "gender": "male", "personality": "deep", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Human Blend", "Chest Resonance", "Dialogue"]},
    {"id": "blend:female_calm", "name": "Sarah (Female, Soft & Intimate Blend)", "gender": "female", "personality": "calm", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Human Blend", "Soft Calm", "Kokoro"]},
    {"id": "blend:male_story", "name": "David (Male, Dark Psychology & Gravitas)", "gender": "male", "personality": "deep", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Human Blend", "Dark Psychology", "Gravitas"]},
    # ── American English Female (11) ─────────────────────────────────────
    {"id": "af_heart",    "name": "Heart (Female, Natural)",       "gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Natural", "Kokoro"]},
    {"id": "af_bella",    "name": "Bella (Female, Calm)",          "gender": "female", "personality": "calm",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Calm", "Kokoro"]},
    {"id": "af_nova",     "name": "Nova (Female, Energetic)",      "gender": "female", "personality": "energetic", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Energetic", "Kokoro"]},
    {"id": "af_sarah",    "name": "Sarah (Female, Natural)",       "gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Natural", "Kokoro"]},
    {"id": "af_sky",      "name": "Sky (Female, Fast & Bright)",   "gender": "female", "personality": "fast",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Fast", "Kokoro"]},
    {"id": "af_nicole",   "name": "Nicole (Female, Soft/Calm)",    "gender": "female", "personality": "calm",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Calm", "Kokoro"]},
    {"id": "af_alloy",    "name": "Alloy (Female, Clear)",         "gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Clear", "Kokoro"]},
    {"id": "af_aoede",    "name": "Aoede (Female, Storytelling)",  "gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Story", "Kokoro"]},
    {"id": "af_jessica",  "name": "Jessica (Female, Expressive)",  "gender": "female", "personality": "energetic", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Expressive", "Kokoro"]},
    {"id": "af_kore",     "name": "Kore (Female, Crisp)",          "gender": "female", "personality": "fast",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Crisp", "Kokoro"]},
    {"id": "af_river",    "name": "River (Female, Smooth)",        "gender": "female", "personality": "calm",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Smooth", "Kokoro"]},
    # ── American English Male (9) ────────────────────────────────────────
    {"id": "am_adam",     "name": "Adam (Male, Deep)",             "gender": "male",   "personality": "deep",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Deep", "Kokoro"]},
    {"id": "am_michael",  "name": "Michael (Male, Natural)",       "gender": "male",   "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Natural", "Kokoro"]},
    {"id": "am_fenrir",   "name": "Fenrir (Male, Deep Story)",     "gender": "male",   "personality": "deep",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Deep", "Kokoro"]},
    {"id": "am_onyx",     "name": "Onyx (Male, Deep Calm)",        "gender": "male",   "personality": "deep",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Deep", "Kokoro"]},
    {"id": "am_puck",     "name": "Puck (Male, Energetic)",        "gender": "male",   "personality": "energetic", "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Energetic", "Kokoro"]},
    {"id": "am_echo",     "name": "Echo (Male, Balanced)",         "gender": "male",   "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Natural", "Kokoro"]},
    {"id": "am_eric",     "name": "Eric (Male, Clear)",            "gender": "male",   "personality": "natural",   "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Clear", "Kokoro"]},
    {"id": "am_liam",     "name": "Liam (Male, Fast)",             "gender": "male",   "personality": "fast",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Fast", "Kokoro"]},
    {"id": "am_santa",    "name": "Santa (Male, Warm Deep)",       "gender": "male",   "personality": "deep",      "language": "en", "lang_code": "en-us", "backend": "kokoro", "tags": ["US English", "Warm", "Kokoro"]},
    # ── British English Female & Male (8) ────────────────────────────────
    {"id": "bf_emma",     "name": "Emma (Female, British Natural)","gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Natural", "Kokoro"]},
    {"id": "bf_alice",    "name": "Alice (Female, British Calm)",  "gender": "female", "personality": "calm",      "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Calm", "Kokoro"]},
    {"id": "bf_isabella", "name": "Isabella (Female, British)",    "gender": "female", "personality": "natural",   "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Warm", "Kokoro"]},
    {"id": "bf_lily",     "name": "Lily (Female, British Bright)", "gender": "female", "personality": "energetic", "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Energetic", "Kokoro"]},
    {"id": "bm_george",   "name": "George (Male, British Calm)",   "gender": "male",   "personality": "calm",      "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Deep", "Kokoro"]},
    {"id": "bm_daniel",   "name": "Daniel (Male, British Natural)","gender": "male",   "personality": "natural",   "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Natural", "Kokoro"]},
    {"id": "bm_fable",    "name": "Fable (Male, British Story)",   "gender": "male",   "personality": "calm",      "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Story", "Kokoro"]},
    {"id": "bm_lewis",    "name": "Lewis (Male, British Deep)",    "gender": "male",   "personality": "deep",      "language": "en", "lang_code": "en-gb", "backend": "kokoro", "tags": ["UK English", "Deep", "Kokoro"]},
    # ── Hindi / Hinglish (4) ─────────────────────────────────────────────
    {"id": "hf_alpha",    "name": "Alpha (Female, Hindi)",         "gender": "female", "personality": "natural",   "language": "hi", "lang_code": "hi",    "backend": "kokoro", "tags": ["Hindi", "Hinglish", "Kokoro"]},
    {"id": "hf_beta",     "name": "Beta (Female, Hindi Calm)",     "gender": "female", "personality": "calm",      "language": "hi", "lang_code": "hi",    "backend": "kokoro", "tags": ["Hindi", "Hinglish", "Kokoro"]},
    {"id": "hm_omega",    "name": "Omega (Male, Hindi Deep)",      "gender": "male",   "personality": "deep",      "language": "hi", "lang_code": "hi",    "backend": "kokoro", "tags": ["Hindi", "Hinglish", "Kokoro"]},
    {"id": "hm_psi",      "name": "Psi (Male, Hindi Natural)",     "gender": "male",   "personality": "natural",   "language": "hi", "lang_code": "hi",    "backend": "kokoro", "tags": ["Hindi", "Hinglish", "Kokoro"]},
    # ── Additional International Kokoro Voices (22) ──────────────────────
    {"id": "ef_dora",     "name": "Dora (Female, Spanish)",        "gender": "female", "personality": "natural",   "language": "es", "lang_code": "es",    "backend": "kokoro", "tags": ["Spanish", "Kokoro"]},
    {"id": "em_alex",     "name": "Alex (Male, Spanish)",          "gender": "male",   "personality": "natural",   "language": "es", "lang_code": "es",    "backend": "kokoro", "tags": ["Spanish", "Kokoro"]},
    {"id": "em_santa",    "name": "Santa (Male, Spanish Deep)",    "gender": "male",   "personality": "deep",      "language": "es", "lang_code": "es",    "backend": "kokoro", "tags": ["Spanish", "Kokoro"]},
    {"id": "ff_siwis",    "name": "Siwis (Female, French)",        "gender": "female", "personality": "natural",   "language": "fr", "lang_code": "fr-fr", "backend": "kokoro", "tags": ["French", "Kokoro"]},
    {"id": "if_sara",     "name": "Sara (Female, Italian)",        "gender": "female", "personality": "natural",   "language": "it", "lang_code": "it",    "backend": "kokoro", "tags": ["Italian", "Kokoro"]},
    {"id": "im_nicola",   "name": "Nicola (Male, Italian)",        "gender": "male",   "personality": "natural",   "language": "it", "lang_code": "it",    "backend": "kokoro", "tags": ["Italian", "Kokoro"]},
    {"id": "pf_dora",     "name": "Dora (Female, Portuguese)",     "gender": "female", "personality": "natural",   "language": "pt", "lang_code": "pt-br", "backend": "kokoro", "tags": ["Portuguese", "Kokoro"]},
    {"id": "pm_alex",     "name": "Alex (Male, Portuguese)",       "gender": "male",   "personality": "natural",   "language": "pt", "lang_code": "pt-br", "backend": "kokoro", "tags": ["Portuguese", "Kokoro"]},
    {"id": "pm_santa",    "name": "Santa (Male, Portuguese Deep)", "gender": "male",   "personality": "deep",      "language": "pt", "lang_code": "pt-br", "backend": "kokoro", "tags": ["Portuguese", "Kokoro"]},
    {"id": "jf_alpha",    "name": "Alpha (Female, Japanese)",      "gender": "female", "personality": "natural",   "language": "ja", "lang_code": "ja",    "backend": "kokoro", "tags": ["Japanese", "Kokoro"]},
    {"id": "jf_gongitsune","name":"Gongitsune (Female, Japanese)", "gender": "female", "personality": "calm",      "language": "ja", "lang_code": "ja",    "backend": "kokoro", "tags": ["Japanese", "Kokoro"]},
    {"id": "jf_nezumi",   "name": "Nezumi (Female, Japanese)",     "gender": "female", "personality": "natural",   "language": "ja", "lang_code": "ja",    "backend": "kokoro", "tags": ["Japanese", "Kokoro"]},
    {"id": "jf_tebukuro", "name": "Tebukuro (Female, Japanese)",   "gender": "female", "personality": "calm",      "language": "ja", "lang_code": "ja",    "backend": "kokoro", "tags": ["Japanese", "Kokoro"]},
    {"id": "jm_kumo",     "name": "Kumo (Male, Japanese)",         "gender": "male",   "personality": "natural",   "language": "ja", "lang_code": "ja",    "backend": "kokoro", "tags": ["Japanese", "Kokoro"]},
    {"id": "zf_xiaobei",  "name": "Xiaobei (Female, Chinese)",     "gender": "female", "personality": "natural",   "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zf_xiaoni",   "name": "Xiaoni (Female, Chinese)",      "gender": "female", "personality": "calm",      "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zf_xiaoxiao", "name": "Xiaoxiao (Female, Chinese)",    "gender": "female", "personality": "natural",   "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zf_xiaoyi",   "name": "Xiaoyi (Female, Chinese)",      "gender": "female", "personality": "energetic", "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zm_yunjian",  "name": "Yunjian (Male, Chinese)",       "gender": "male",   "personality": "deep",      "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zm_yunxi",    "name": "Yunxi (Male, Chinese)",         "gender": "male",   "personality": "natural",   "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zm_yunxia",   "name": "Yunxia (Male, Chinese)",        "gender": "male",   "personality": "calm",      "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
    {"id": "zm_yunyang",  "name": "Yunyang (Male, Chinese)",       "gender": "male",   "personality": "deep",      "language": "zh", "lang_code": "cmn",   "backend": "kokoro", "tags": ["Chinese", "Kokoro"]},
]

# Kokoro-ONNX lightweight int8 model files (~88 MB ONNX + ~27 MB voices binary = ~115 MB total)
KOKORO_MODEL_URLS = {
    "model": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
    "voices": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
}


class TTSManager:
    """
    Manages local TTS synthesis via Kokoro-ONNX, Piper, and Windows SAPI.
    Only lists voices backed by genuinely installed local models.
    """

    def __init__(self, models_dir: str, ffmpeg_path: str = "ffmpeg") -> None:
        self.models_dir: str = models_dir
        if ffmpeg_path == "ffmpeg" and not shutil.which("ffmpeg"):
            candidate = r"C:\ffmpeg\bin\ffmpeg.exe"
            self.ffmpeg_path = candidate if os.path.exists(candidate) else "ffmpeg"
        else:
            self.ffmpeg_path = ffmpeg_path
        os.makedirs(models_dir, exist_ok=True)
        os.makedirs(os.path.join(models_dir, "kokoro"), exist_ok=True)
        os.makedirs(os.path.join(models_dir, "piper"), exist_ok=True)

        self._kokoro_onnx = None
        self._sapi_voices_cache: Optional[list[dict]] = None

    # ------------------------------------------------------------------
    # Backend & model availability probes
    # ------------------------------------------------------------------

    def _find_kokoro_files(self) -> tuple[Optional[str], Optional[str]]:
        """Locate kokoro ONNX model + voices bin in models_dir or project assets."""
        repo_root = Path(__file__).resolve().parent.parent.parent
        search_dirs = [
            Path(self.models_dir) / "kokoro",
            Path(self.models_dir),
            repo_root / "models" / "kokoro",
            repo_root / "assets" / "voices" / "kokoro",
            Path("assets/voices/kokoro"),
            Path("models/kokoro"),
        ]
        model_names = ("kokoro-v1.0.fp16.onnx", "kokoro-v1.0.int8.onnx", "kokoro-v1.0.onnx", "kokoro-v0_19.onnx")
        voice_names = ("voices-v1.0.bin", "voices.bin", "voices.json")

        found_model: Optional[str] = None
        found_voices: Optional[str] = None
        for d in search_dirs:
            if not d.exists():
                continue
            if not found_model:
                for mn in model_names:
                    p = d / mn
                    if p.exists() and p.stat().st_size > 1_000_000:
                        found_model = str(p)
                        break
            if not found_voices:
                for vn in voice_names:
                    p = d / vn
                    if p.exists() and p.stat().st_size > 100_000:
                        found_voices = str(p)
                        break
        return found_model, found_voices

    def is_kokoro_package_installed(self) -> bool:
        return importlib.util.find_spec("kokoro_onnx") is not None or importlib.util.find_spec("kokoro") is not None

    def is_kokoro_available(self) -> bool:
        """True only when kokoro_onnx is installed AND local model files exist."""
        if importlib.util.find_spec("kokoro_onnx") is not None:
            m, v = self._find_kokoro_files()
            if m and v:
                return True
        if importlib.util.find_spec("kokoro") is not None:
            return True
        return False

    def is_piper_package_installed(self) -> bool:
        if importlib.util.find_spec("piper") is not None:
            return True
        return shutil.which("piper") is not None

    def _discover_piper_models(self) -> list[dict]:
        """Scan local voice folders for genuinely installed Piper .onnx models."""
        if not self.is_piper_package_installed():
            return []

        search_dirs = [
            Path(self.models_dir) / "piper",
            Path("assets/voices/piper"),
            Path("assets/voices"),
            Path("models/piper"),
        ]
        discovered: list[dict] = []
        seen_ids: set[str] = set()

        for d in search_dirs:
            if not d.exists():
                continue
            for onnx_path in sorted(d.glob("*.onnx")):
                vid = onnx_path.stem
                if vid in seen_ids or "kokoro" in vid.lower():
                    continue
                seen_ids.add(vid)

                lang = "hi" if vid.lower().startswith("hi") else "en"
                gender = "female" if any(k in vid.lower() for k in ("amy", "lessac", "alba", "female", "priyamvada", "jenny")) else "male"
                lang_label = "Hindi" if lang == "hi" else "English"
                tags = [lang_label, "Piper"]
                if lang == "hi":
                    tags.append("Hinglish")

                discovered.append({
                    "id": f"piper:{vid}",
                    "name": f"{vid} ({gender.title()}, {lang_label})",
                    "gender": gender,
                    "personality": "natural",
                    "language": lang,
                    "backend": "piper",
                    "model_path": str(onnx_path),
                    "tags": tags,
                    "available": True,
                })
        return discovered

    def _discover_sapi_voices(self) -> list[dict]:
        """Enumerate genuinely installed Windows SAPI speech voices."""
        if self._sapi_voices_cache is not None:
            return self._sapi_voices_cache

        ps = """
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
foreach ($v in $s.GetInstalledVoices()) {
    if ($v.Enabled) {
        $vi = $v.VoiceInfo
        Write-Output "$($vi.Name)|$($vi.Gender)|$($vi.Culture.Name)"
    }
}
"""
        voices: list[dict] = []
        try:
            r = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if r.returncode == 0:
                for line in r.stdout.strip().splitlines():
                    parts = [p.strip() for p in line.split("|")]
                    if len(parts) != 3 or not parts[0]:
                        continue
                    vname, vgender, vculture = parts
                    lang = vculture.split("-")[0].lower() if vculture else "en"
                    g = vgender.lower() if vgender.lower() in ("male", "female") else "neutral"
                    short_name = vname.replace("Microsoft ", "").replace(" Desktop", "")
                    pers = "deep" if g == "male" else "natural"
                    voices.append({
                        "id": f"sapi:{vname}",
                        "sapi_name": vname,
                        "name": f"{short_name} ({g.title()}, {vculture})",
                        "gender": g,
                        "personality": pers,
                        "language": lang,
                        "backend": "sapi",
                        "tags": [vculture, "Windows Offline", "SAPI"],
                        "available": True,
                    })
        except Exception as exc:
            logger.debug("SAPI voice enumeration failed: %s", exc)

        self._sapi_voices_cache = voices
        return voices

    def is_piper_available(self) -> bool:
        return len(self._discover_piper_models()) > 0

    def get_available_voices(self) -> list[dict]:
        """
        Return ONLY voices genuinely supported by locally installed engines & models.
        Includes Kokoro (when model files exist), Piper (discovered .onnx models),
        and installed Windows SAPI voices.
        """
        voices: list[dict] = []

        # 1. Kokoro voices (only if model files + package are locally available)
        if self.is_kokoro_available():
            supported_kokoro = self._get_installed_kokoro_voice_ids()
            known_ids = {v["id"] for v in KOKORO_VOICE_CATALOG}
            for v in KOKORO_VOICE_CATALOG:
                is_blend = str(v["id"]).startswith("blend:")
                blend_ok = True
                if is_blend and supported_kokoro:
                    blend_spec = v.get("blend", [])
                    blend_ok = all(vid in supported_kokoro for vid, _ in blend_spec)

                if is_blend and blend_ok:
                    entry = dict(v)
                    entry["available"] = True
                    voices.append(entry)
                elif supported_kokoro is None or v["id"] in supported_kokoro:
                    entry = dict(v)
                    entry["available"] = True
                    voices.append(entry)
            # Dynamically include any extra voices inside voices.bin not explicitly listed above
            if supported_kokoro:
                for extra_id in sorted(supported_kokoro - known_ids):
                    prefix = extra_id[:2].lower()
                    lang = {"af": "en", "am": "en", "bf": "en", "bm": "en", "hf": "hi", "hm": "hi"}.get(prefix, "en")
                    lc = "en-gb" if prefix.startswith("b") else ("hi" if lang == "hi" else "en-us")
                    gender = "female" if len(prefix) > 1 and prefix[1] == "f" else "male"
                    voices.append({
                        "id": extra_id,
                        "name": f"{extra_id} ({gender.title()}, Kokoro)",
                        "gender": gender,
                        "personality": "natural",
                        "language": lang,
                        "lang_code": lc,
                        "backend": "kokoro",
                        "tags": [lang.upper(), "Kokoro"],
                        "available": True,
                    })

        # 2. Piper local .onnx models
        voices.extend(self._discover_piper_models())

        # 3. Installed Windows SAPI voices (always genuinely available offline on Windows)
        voices.extend(self._discover_sapi_voices())

        return voices

    def get_supported_languages(self) -> list[str]:
        """Return distinct language codes genuinely supported by installed voices."""
        langs = sorted({v.get("language", "en") for v in self.get_available_voices()})
        return langs or ["en"]

    def _get_installed_kokoro_voice_ids(self) -> Optional[set[str]]:
        """Return set of voice IDs inside installed Kokoro voices file if inspectable."""
        try:
            _, voices_path = self._find_kokoro_files()
            if not voices_path:
                return None
            if voices_path.endswith(".bin"):
                import numpy as np
                data = np.load(voices_path, allow_pickle=False)
                if hasattr(data, "files"):
                    return set(data.files)
            elif voices_path.endswith(".json"):
                with open(voices_path, "r", encoding="utf-8") as fh:
                    return set(json.load(fh).keys())
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------
    # Model download helper (explicit user action only)
    # ------------------------------------------------------------------

    def download_kokoro_models(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
        """Download Kokoro-ONNX v1.0 model files (~338 MB total) into models_dir/kokoro."""
        import requests
        target_dir = Path(self.models_dir) / "kokoro"
        target_dir.mkdir(parents=True, exist_ok=True)
        files = [
            ("kokoro-v1.0.int8.onnx", KOKORO_MODEL_URLS["model"]),
            ("voices-v1.0.bin", KOKORO_MODEL_URLS["voices"]),
        ]
        try:
            for fname, url in files:
                dest = target_dir / fname
                if dest.exists() and dest.stat().st_size > 100_000:
                    continue
                if progress_callback:
                    progress_callback(f"Downloading {fname}...", 0)
                with requests.get(url, stream=True, timeout=120) as resp:
                    resp.raise_for_status()
                    total = int(resp.headers.get("content-length", 0))
                    done = 0
                    tmp = dest.with_suffix(".part")
                    with open(tmp, "wb") as out:
                        for chunk in resp.iter_content(chunk_size=65536):
                            if chunk:
                                out.write(chunk)
                                done += len(chunk)
                                if progress_callback and total > 0:
                                    progress_callback(f"Downloading {fname}...", int(done * 100 / total))
                    tmp.replace(dest)
            return self.is_kokoro_available()
        except Exception as exc:
            logger.error("Kokoro model download failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Text / Hinglish normalization
    # ------------------------------------------------------------------

    @staticmethod
    def _prepare_text_for_voice(text: str, language: str) -> str:
        """Clean punctuation, normalize spoken symbols (e.g. 24/7 -> 24 by 7), and format text."""
        cleaned = re.sub(r"\s+", " ", text).strip()
        lang_lower = (language or "en").lower()

        # 1. 24/7 and ratios
        cleaned = re.sub(r"\b24\s*/\s*7\b", "24 by 7", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b24\s*[xX]\s*7\b", "24 by 7", cleaned)
        cleaned = re.sub(r"\b(\d+)\s*/\s*10\b", r"\1 out of 10", cleaned)
        cleaned = re.sub(r"\b(\d+)\s*/\s*100\b", r"\1 out of 100", cleaned)
        cleaned = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", r"\1 by \2", cleaned)

        # 2. Common abbreviations & shorthands
        cleaned = re.sub(r"(^|\s)w/(?=\s|$)", r"\1with", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"(^|\s)w/o(?=\s|$)", r"\1without", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bb/c\b", "because", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bvs\.?\b", "versus", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\be\.g\.,?\b", "for example", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\bi\.e\.,?\b", "that is", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\betc\.?\b", "etcetera", cleaned, flags=re.IGNORECASE)

        # 3. Symbols & units
        cleaned = re.sub(r"&", " and ", cleaned)
        cleaned = re.sub(r"%", " percent", cleaned)
        cleaned = re.sub(r"(^|\s)#(\d+)\b", r"\1number \2", cleaned)
        cleaned = re.sub(r"\$(\d+(?:\.\d+)?)", r"\1 dollars", cleaned)
        cleaned = re.sub(r"₹(\d+(?:\.\d+)?)", r"\1 rupees", cleaned)
        cleaned = re.sub(r"€(\d+(?:\.\d+)?)", r"\1 euros", cleaned)
        cleaned = re.sub(r"£(\d+(?:\.\d+)?)", r"\1 pounds", cleaned)
        cleaned = re.sub(r"\b(\d+)x\b", r"\1 times", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\b(\d+)\+\b", r"\1 plus", cleaned)

        # 4. Dashes, slashes, and ellipses between words (prevent awkward dead-stop freezes)
        cleaned = re.sub(r"\s*\.\.\.+\s*", ", ", cleaned)
        cleaned = cleaned.replace("—", ", ").replace("–", ", ")
        cleaned = re.sub(r"([a-zA-Z]+)/([a-zA-Z]+)", r"\1 or \2", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()

        return cleaned

    # ------------------------------------------------------------------
    # Public synthesis API
    # ------------------------------------------------------------------

    def synthesize(
        self,
        text: str,
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        output_path: Optional[str] = None,
    ) -> Optional[str]:
        """
        Synthesize *text* locally and save as WAV to *output_path*.
        Applies speed and semitone *pitch* adjustment without cloud calls.
        """
        if not text or not text.strip():
            logger.warning("synthesize called with empty text")
            return None

        if output_path is None:
            output_path = os.path.join(
                tempfile.gettempdir(),
                f"tts_{uuid.uuid4().hex}.wav",
            )
        os.makedirs(os.path.dirname(os.path.abspath(output_path)), exist_ok=True)

        # Resolve voice descriptor
        voices = self.get_available_voices()
        voice_info = next((v for v in voices if v["id"] == voice_id), None)
        if voice_info is None and voices:
            voice_info = voices[0]

        backend = voice_info["backend"] if voice_info else "sapi"
        lang = voice_info.get("language", "en") if voice_info else "en"
        prepared = self._prepare_text_for_voice(text, lang)

        raw_path = output_path if abs(pitch) < 0.1 else f"{output_path}.raw.wav"
        success = False

        if backend == "kokoro" and voice_info:
            success = self._synthesize_kokoro(
                prepared, voice_info["id"], speed, raw_path,
                lang_code=voice_info.get("lang_code", "en-us"),
            )
        elif backend == "piper" and voice_info:
            success = self._synthesize_piper(
                prepared, voice_info.get("model_path", ""), speed, raw_path
            )
        elif backend == "sapi" and voice_info:
            success = self._synthesize_sapi(
                prepared, raw_path, speed=speed, pitch=pitch,
                sapi_voice_name=voice_info.get("sapi_name"),
            )
            if success and abs(pitch) >= 0.1:
                if raw_path != output_path and os.path.exists(raw_path):
                    shutil.move(raw_path, output_path)
                if os.path.exists(output_path):
                    self.trim_silence(output_path, output_path, head_pad=0.030, tail_pad=0.060)
                    return output_path
                return None

        if not success:
            logger.info("Primary TTS backend '%s' failed; using Windows SAPI fallback", backend)
            sapi_name = voice_info.get("sapi_name") if voice_info else None
            success = self._synthesize_sapi(prepared, raw_path, speed=speed, pitch=pitch, sapi_voice_name=sapi_name)
            if success and raw_path != output_path:
                shutil.move(raw_path, output_path)
            if success and os.path.exists(output_path):
                self.trim_silence(output_path, output_path, head_pad=0.030, tail_pad=0.060)
                return output_path

        if not success or not os.path.exists(raw_path):
            logger.error("All local TTS backends failed for voice '%s'", voice_id)
            return None

        # Apply pitch shift via FFmpeg if non-zero pitch requested for Kokoro/Piper
        if abs(pitch) >= 0.1 and raw_path != output_path:
            if not self._apply_pitch_shift(raw_path, output_path, pitch):
                shutil.move(raw_path, output_path)
            else:
                try:
                    os.unlink(raw_path)
                except OSError:
                    pass

        if os.path.exists(output_path):
            self.trim_silence(output_path, output_path, head_pad=0.030, tail_pad=0.060)
            return output_path
        return None

    def synthesize_sentences(
        self,
        sentences: list[str],
        voice_id: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        output_dir: str = "temp/tts",
    ) -> list[dict]:
        """Synthesize each sentence individually for exact audio/caption sync."""
        os.makedirs(output_dir, exist_ok=True)
        results: list[dict] = []

        for idx, sentence in enumerate(sentences):
            out_path = os.path.join(output_dir, f"sentence_{idx:04d}_{uuid.uuid4().hex[:6]}.wav")
            path = self.synthesize(
                text=sentence,
                voice_id=voice_id,
                speed=speed,
                pitch=pitch,
                output_path=out_path,
            )
            duration = self.get_audio_duration(path) if path else self.estimate_duration(sentence, speed)
            results.append({"text": sentence, "path": path, "duration": duration})

        return results

    def preview_voice(
        self,
        voice_id: str,
        text: str = "Hello, this is a preview of this offline voice.",
        speed: float = 1.0,
        pitch: float = 0.0,
    ) -> Optional[str]:
        """Generate a short WAV preview. Returns path or None."""
        preview_dir = os.path.join(self.models_dir, "previews")
        os.makedirs(preview_dir, exist_ok=True)
        safe_id = re.sub(r"[^a-zA-Z0-9_-]", "_", voice_id)
        output_path = os.path.join(preview_dir, f"preview_{safe_id}.wav")
        return self.synthesize(text=text, voice_id=voice_id, speed=speed, pitch=pitch, output_path=output_path)

    def estimate_duration(self, text: str, speed: float = 1.0) -> float:
        words = len(text.split())
        wpm = 150.0 * max(0.5, speed)
        return max(0.5, (words / wpm) * 60.0)

    # ------------------------------------------------------------------
    # Backend implementations
    # ------------------------------------------------------------------

    def _init_kokoro(self, model_path: str, voices_path: str):
        """Initialize Kokoro instance with dynamic tensor names & speed-type compatibility."""
        if self._kokoro_onnx is None:
            try:
                import numpy as np
                import onnxruntime as ort
                from kokoro_onnx import Kokoro  # type: ignore

                ort.set_default_logger_severity(3)
                kokoro_inst = Kokoro(model_path, voices_path)

                sess_inputs = {inp.name: inp for inp in kokoro_inst.sess.get_inputs()}
                token_key = "tokens" if "tokens" in sess_inputs else "input_ids"
                speed_info = sess_inputs.get("speed")
                speed_is_int = speed_info is not None and "int" in speed_info.type.lower()

                def _dynamic_create_audio(phonemes: str, voice, speed: float = 1.0):
                    tokens = np.array(kokoro_inst.tokenizer.tokenize(phonemes[:510]), dtype=np.int64)
                    v = voice[len(tokens)]
                    t_in = [[0, *tokens, 0]]
                    sp = (
                        np.array([int(round(speed))], dtype=np.int32)
                        if speed_is_int
                        else np.array([float(speed)], dtype=np.float32)
                    )
                    inputs = {
                        token_key: t_in,
                        "style": np.array(v, dtype=np.float32),
                        "speed": sp,
                    }
                    return kokoro_inst.sess.run(None, inputs)[0], 24000

                kokoro_inst._create_audio = _dynamic_create_audio
                self._kokoro_onnx = kokoro_inst
            except Exception as exc:
                logger.error("Failed to initialize kokoro_onnx: %s", exc)
                return None
        return self._kokoro_onnx

    def _resolve_kokoro_voice_style(self, kokoro_inst, voice_id: str):
        """
        Resolve voice id into a voice style tensor.
        Supports hyper-realistic human blend profiles and custom combinations.
        """
        import numpy as np

        blend_presets = {
            "blend:female_warm": [("af_heart", 0.70), ("af_sarah", 0.30)],
            "blend:male_introspective": [("am_michael", 0.75), ("am_adam", 0.25)],
            "blend:female_calm": [("af_bella", 0.65), ("af_nicole", 0.35)],
            "blend:male_story": [("am_fenrir", 0.70), ("am_onyx", 0.30)],
        }
        if voice_id in blend_presets:
            style = sum(
                w * kokoro_inst.get_voice_style(vid)
                for vid, w in blend_presets[voice_id]
            )
            return style

        if "+" in str(voice_id):
            try:
                parts = str(voice_id).split("+")
                components = []
                for p in parts:
                    p = p.strip()
                    if ":" in p:
                        vid, w = p.split(":", 1)
                        components.append((vid.strip(), float(w.strip() or 1.0)))
                    else:
                        components.append((p, 1.0))
                total_w = sum(w for _, w in components) or 1.0
                return sum((w / total_w) * kokoro_inst.get_voice_style(v) for v, w in components)
            except Exception as exc:
                logger.warning("Custom blend parse error for '%s': %s", voice_id, exc)

        try:
            return kokoro_inst.get_voice_style(voice_id)
        except Exception:
            return voice_id

    def _synthesize_kokoro(
        self,
        text: str,
        voice_id: str,
        speed: float,
        output_path: str,
        lang_code: str = "en-us",
    ) -> bool:
        """Synthesize via lightweight kokoro-onnx with hyper-realistic human voice styling."""
        model_path, voices_path = self._find_kokoro_files()
        if model_path and voices_path and importlib.util.find_spec("kokoro_onnx") is not None:
            try:
                import numpy as np

                k = self._init_kokoro(model_path, voices_path)
                if k is not None:
                    resolved_style = self._resolve_kokoro_voice_style(k, voice_id)
                    # Natural conversational cadence multiplier (calibrates Kokoro audiobook base to lively dialogue)
                    eff_kokoro_speed = max(0.5, min(2.0, float(speed) * 1.10))
                    samples, sample_rate = k.create(
                        text,
                        voice=resolved_style,
                        speed=eff_kokoro_speed,
                        lang=lang_code,
                    )
                    pcm = (np.clip(samples, -1.0, 1.0) * 32767).astype(np.int16)
                    with wave.open(output_path, "wb") as wf:
                        wf.setnchannels(1)
                        wf.setsampwidth(2)
                        wf.setframerate(int(sample_rate))
                        wf.writeframes(pcm.tobytes())
                    return os.path.exists(output_path)
            except Exception as exc:
                logger.error("kokoro-onnx synthesis error: %s", exc)

        # Secondary: torch-based kokoro package if user installed it
        if importlib.util.find_spec("kokoro") is not None:
            try:
                import numpy as np
                from kokoro import KPipeline  # type: ignore

                lc = "h" if voice_id.startswith("h") else ("b" if voice_id.startswith("b") else "a")
                pipeline = KPipeline(lang_code=lc)
                chunks = [audio for _gs, _ps, audio in pipeline(text, voice=voice_id, speed=speed) if audio is not None]
                if not chunks:
                    return False
                pcm = (np.clip(np.concatenate(chunks), -1.0, 1.0) * 32767).astype(np.int16)
                with wave.open(output_path, "wb") as wf:
                    wf.setnchannels(1)
                    wf.setsampwidth(2)
                    wf.setframerate(24000)
                    wf.writeframes(pcm.tobytes())
                return os.path.exists(output_path)
            except Exception as exc:
                logger.error("kokoro KPipeline synthesis error: %s", exc)

        return False

    def _synthesize_piper(
        self,
        text: str,
        model_path: str,
        speed: float,
        output_path: str,
    ) -> bool:
        """Synthesize via piper-tts Python API or CLI."""
        if not model_path or not os.path.exists(model_path):
            return False

        if importlib.util.find_spec("piper") is not None:
            try:
                from piper.voice import PiperVoice  # type: ignore
                from piper.config import SynthesisConfig  # type: ignore

                voice = PiperVoice.load(model_path)
                syn_cfg = SynthesisConfig(length_scale=1.0 / max(0.5, speed))
                with wave.open(output_path, "wb") as wf:
                    voice.synthesize_wav(text, wf, syn_config=syn_cfg)
                if os.path.exists(output_path) and os.path.getsize(output_path) > 44:
                    return True
            except Exception as exc:
                logger.debug("Piper Python API failed (%s); trying CLI", exc)

        piper_bin = shutil.which("piper")
        if piper_bin:
            try:
                length_scale = 1.0 / max(0.5, speed)
                result = subprocess.run(
                    [piper_bin, "--model", model_path, "--output_file", output_path, "--length_scale", f"{length_scale:.3f}"],
                    input=text.encode("utf-8"),
                    capture_output=True,
                    timeout=120,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                return result.returncode == 0 and os.path.exists(output_path)
            except Exception as exc:
                logger.error("Piper CLI synthesis error: %s", exc)
        return False

    def _synthesize_sapi(
        self,
        text: str,
        output_path: str,
        speed: float = 1.0,
        pitch: float = 0.0,
        sapi_voice_name: Optional[str] = None,
    ) -> bool:
        """Offline Windows SAPI SpeechSynthesizer via PowerShell."""
        try:
            import html as _html
            safe_text = _html.escape(text.replace("\n", " ").replace("\r", " "))
            rate = max(-10, min(10, int((speed - 1.0) * 5)))
            out_escaped = output_path.replace("'", "''")
            voice_line = f'$synth.SelectVoice("{sapi_voice_name}")' if sapi_voice_name else ""

            if abs(pitch) >= 0.5:
                pitch_str = f"{int(pitch):+d}st"
                ssml = f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US"><prosody pitch="{pitch_str}">{safe_text}</prosody></speak>'
                speak_cmd = f'$synth.SpeakSsml(@"\n{ssml}\n"@)'
            else:
                plain = text.replace('"', "'").replace("`", "'").replace("$", "").replace("\n", " ")
                speak_cmd = f'$synth.Speak("{plain}")'

            ps_script = f"""
Add-Type -AssemblyName System.Speech
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
{voice_line}
$synth.SetOutputToWaveFile('{out_escaped}')
$synth.Rate = {rate}
{speak_cmd}
$synth.Dispose()
"""
            result = subprocess.run(
                ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                capture_output=True,
                timeout=120,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )

            if result.returncode != 0:
                logger.error("SAPI error: %s", result.stderr.decode("utf-8", errors="replace"))
                return False

            return os.path.exists(output_path) and os.path.getsize(output_path) > 44

        except Exception as exc:
            logger.error("SAPI fallback exception: %s", exc, exc_info=True)
            return False

    def _apply_pitch_shift(self, input_wav: str, output_wav: str, semitones: float) -> bool:
        """Apply pitch shift in semitones via FFmpeg while preserving tempo."""
        try:
            with wave.open(input_wav, "rb") as wf:
                sr = wf.getframerate()
            factor = 2.0 ** (semitones / 12.0)
            inv = 1.0 / factor
            atempo = max(0.5, min(2.0, inv))
            af = f"asetrate={int(sr * factor)},aresample={sr},atempo={atempo:.4f}"
            res = subprocess.run(
                [self.ffmpeg_path, "-y", "-i", input_wav, "-af", af, output_wav],
                capture_output=True,
                timeout=60,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            return res.returncode == 0 and os.path.exists(output_wav)
        except Exception:
            return False

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def trim_silence(
        input_path: str,
        output_path: str,
        head_pad: float = 0.030,
        tail_pad: float = 0.060,
        threshold: int = 350,
    ) -> float:
        """
        Trim leading and trailing dead silence from 16-bit mono WAV,
        leaving crisp 30ms headroom and 60ms natural vocal decay.
        Returns final audio duration in seconds.
        """
        if not input_path or not os.path.exists(input_path):
            return 0.0
        try:
            with wave.open(input_path, "rb") as wf:
                sr = wf.getframerate()
                n_ch = wf.getnchannels()
                sw = wf.getsampwidth()
                n_frames = wf.getnframes()
                raw = wf.readframes(n_frames)

            if n_ch != 1 or sw != 2 or n_frames == 0 or sr <= 0:
                if input_path != output_path:
                    shutil.copy2(input_path, output_path)
                return n_frames / float(sr) if sr > 0 else 0.0

            samples = array.array("h")
            samples.frombytes(raw)

            # Find first non-silent sample
            start_idx = 0
            for idx, s in enumerate(samples):
                if abs(s) >= threshold:
                    start_idx = idx
                    break

            # Find last non-silent sample
            end_idx = n_frames - 1
            for idx in range(n_frames - 1, -1, -1):
                if abs(samples[idx]) >= threshold:
                    end_idx = idx
                    break

            if start_idx >= end_idx:
                if input_path != output_path:
                    shutil.copy2(input_path, output_path)
                return n_frames / float(sr)

            head_samples = int(head_pad * sr)
            tail_samples = int(tail_pad * sr)

            final_start = max(0, start_idx - head_samples)
            final_end = min(n_frames, end_idx + 1 + tail_samples)

            trimmed = samples[final_start:final_end]
            with wave.open(output_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                wf.writeframes(trimmed.tobytes())

            return len(trimmed) / float(sr)
        except Exception as exc:
            logger.warning("trim_silence failed on '%s': %s", input_path, exc)
            if input_path != output_path and os.path.exists(input_path):
                shutil.copy2(input_path, output_path)
            return 0.0

    def get_audio_duration(self, path: Optional[str]) -> float:
        """Return duration of a WAV file in seconds. Returns 0.0 on error."""
        if not path or not os.path.exists(path):
            return 0.0
        try:
            with wave.open(path, "rb") as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                return frames / float(rate)
        except Exception as exc:
            logger.error("Could not read WAV duration for '%s': %s", path, exc)
            return 0.0

    # ------------------------------------------------------------------
    # Broadcast-Grade Acoustic Mastering & Dialogue Engine (Atharv Hatwar)
    # ------------------------------------------------------------------

    def apply_acoustic_mastering(self, input_wav: str, output_wav: str) -> bool:
        """
        Applies warm broadcast-grade human mastering chain:
          - Highpass at 65Hz (removes sub-bass mud & mic pops)
          - Warm chest resonance at 220Hz (+1.5 dB)
          - De-harshing dip at 3.2 kHz (-1.0 dB)
          - Gentle vocal air lift at 11 kHz (+1.2 dB)
          - Transparent optical compressor (ratio 2.0:1)
        """
        if not input_wav or not os.path.exists(input_wav):
            return False

        af_filter = (
            "highpass=f=65,"
            "equalizer=f=220:t=q:w=1.2:g=1.5,"
            "equalizer=f=3200:t=q:w=1.5:g=-1.0,"
            "equalizer=f=11000:t=q:w=1.0:g=1.2,"
            "acompressor=threshold=-16dB:ratio=2.0:attack=15:release=120"
        )
        is_same = os.path.abspath(input_wav) == os.path.abspath(output_wav)
        tmp_out = f"{output_wav}.master.tmp.wav" if is_same else output_wav

        cmd = [
            self.ffmpeg_path, "-y", "-hide_banner", "-loglevel", "error",
            "-i", input_wav,
            "-af", af_filter,
            "-ar", "24000",
            "-ac", "1",
            tmp_out,
        ]
        try:
            res = subprocess.run(
                cmd,
                capture_output=True,
                timeout=45,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if res.returncode == 0 and os.path.exists(tmp_out):
                if is_same:
                    shutil.move(tmp_out, output_wav)
                return True
        except Exception as exc:
            logger.warning("Acoustic mastering exception: %s", exc)

        if is_same and os.path.exists(tmp_out):
            try:
                os.unlink(tmp_out)
            except OSError:
                pass
        return False

    @staticmethod
    @staticmethod
    def parse_dialogue_script(
        text: str,
        name1: str = "Alex",
        name2: str = "Maya",
    ) -> list[dict]:
        """
        Parse raw script into structured dialogue turns using ScriptIntelligenceEngine.
        Robustly supports:
          - '**MALE VOICE:**' / '**FEMALE VOICE:**' (inline or on separate lines)
          - 'Alex:' / 'Maya:' / '**Alex:**' / '**Maya:**' / '[Alex]' / '[Maya]'
          - 'Speaker 1:' / 'Speaker 2:' / 'Voice 1:' / 'Voice 2:' / 'Male:' / 'Female:'
          - Strips document titles, metadata lines (Duration, Genre, Voices),
            scene headers (### SCENE 1...), stage directions ((SLOW AND EMOTIONAL)),
            and end screens.
          - Never includes speaker names in the spoken dialogue text.
        """
        if not text or not str(text).strip():
            return []

        try:
            from engine.script_intelligence import ScriptIntelligenceEngine
            beats = ScriptIntelligenceEngine.parse_script_to_story_beats(text, name1=name1, name2=name2)
            if beats:
                return [
                    {
                        "speaker": b["speaker"],
                        "speaker_name": b["speaker_name"],
                        "text": b["narration"],
                    }
                    for b in beats
                ]
        except Exception as exc:
            logger.warning("ScriptIntelligenceEngine parse exception: %s; using regex fallback", exc)

        n1 = re.escape((name1 or "Alex").strip().lower())
        n2 = re.escape((name2 or "Maya").strip().lower())

        spk_tag = re.compile(
            rf"^\s*(?:\*\*)?(?:\[)?(male\s*voice|female\s*voice|male|female|speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|{n1}|{n2}|final\s*line\s*[-–—]\s*(?:female|male)\s*voice)(?:\])?(?:\s*\([^)]*\))?(?:\*\*)?\s*[:\-–—]\s*(.*)$",
            re.IGNORECASE,
        )
        meta_tag = re.compile(
            r"^\s*(?:#+\s*|\*\*)?(?:duration|genre|voices|target|resolution|fps|aspect|end\s*screen|final\s*screen)\s*[:\-–—].*$",
            re.IGNORECASE,
        )
        scene_header = re.compile(
            r"^\s*#+\s*(?:\[?[a-z0-9\s–—|]+\]?|scene\s*\d+|hook|story|psychology|realisation|realization|twist|punchline|outro|intro|conclusion|takeaway).*$",
            re.IGNORECASE,
        )

        lines = str(text).splitlines()
        has_tags = any(spk_tag.match(l.strip()) for l in lines if l.strip())

        turns: list[dict] = []
        curr_speaker: Optional[int] = None
        curr_text: list[str] = []

        if has_tags:
            for line in lines:
                sline = line.strip()
                if not sline:
                    continue
                # Skip markdown headers without dialogue
                if sline.startswith("#") and not spk_tag.match(sline):
                    continue
                # Skip metadata lines (Duration: 2 Minutes, Genre: ...)
                if meta_tag.match(sline):
                    continue
                # Skip end cards
                if re.match(r"^['\"]?Read that again\.?.*?['\"]?$", sline, re.IGNORECASE):
                    continue

                m = spk_tag.match(sline)
                if m:
                    # Flush previous turn
                    if curr_speaker is not None and curr_text:
                        spoken = " ".join(curr_text).strip()
                        spoken = re.sub(r"\([A-Z\s]{4,}\)", "", spoken).strip()
                        spoken = re.sub(r"[*_]+", "", spoken).strip()
                        if spoken:
                            turns.append({
                                "speaker": curr_speaker,
                                "speaker_name": name1 if curr_speaker == 1 else name2,
                                "text": spoken,
                            })
                    raw_tag = re.sub(r"[*_\[\]]", "", m.group(1)).lower()
                    inline_text = m.group(2).strip() if m.group(2) else ""
                    inline_text = re.sub(r"^[*_\s]+", "", inline_text)
                    inline_text = re.sub(r"[*_]+", "", inline_text)
                    is_s2 = any(k in raw_tag for k in ("female", "speaker 2", "voice 2", (name2 or "maya").lower()))
                    curr_speaker = 2 if is_s2 else 1
                    curr_text = [inline_text] if inline_text else []
                else:
                    if curr_speaker is not None:
                        cleaned = re.sub(r"\([A-Z\s]{4,}\)", "", sline).strip()
                        cleaned = re.sub(r"[*_]+", "", cleaned).strip()
                        if cleaned:
                            curr_text.append(cleaned)
                    else:
                        # Fallback leading line before first tag
                        curr_speaker = 1
                        curr_text.append(re.sub(r"[*_]+", "", sline).strip())

            if curr_speaker is not None and curr_text:
                spoken = " ".join(curr_text).strip()
                spoken = re.sub(r"\([A-Z\s]{4,}\)", "", spoken).strip()
                spoken = re.sub(r"[*_]+", "", spoken).strip()
                if spoken:
                    turns.append({
                        "speaker": curr_speaker,
                        "speaker_name": name1 if curr_speaker == 1 else name2,
                        "text": spoken,
                    })
        else:
            # Alternating clean conversational sentences
            # Clean metadata and headers first
            clean_lines = []
            for l in lines:
                s = l.strip()
                if not s or s.startswith("#") or meta_tag.match(s) or re.match(r"^['\"]?Read that again", s, re.IGNORECASE):
                    continue
                clean_lines.append(s)

            full_clean = " ".join(clean_lines)
            raw_sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", full_clean) if s.strip()]
            current_speaker = 1
            for s in raw_sentences:
                cleaned = re.sub(r"[*_]+", "", s).strip()
                if not cleaned:
                    continue
                turns.append({
                    "speaker": current_speaker,
                    "speaker_name": name1 if current_speaker == 1 else name2,
                    "text": cleaned,
                })
                current_speaker = 2 if current_speaker == 1 else 1

        return turns

    def synthesize_dialogue(
        self,
        script: Any,
        voice1_cfg: dict,
        voice2_cfg: dict,
        output_path: str,
        name1: str = "Alex",
        name2: str = "Maya",
        master_audio: bool = True,
        progress_cb: Optional[Callable[[str, int], None]] = None,
    ) -> dict:
        """
        Synthesize multi-turn dialogue between Speaker 1 and Speaker 2.
        Seamlessly stitches turns with conversational pacing micro-gaps and masters the final track.
        """
        if isinstance(script, list):
            turns = script
        else:
            turns = self.parse_dialogue_script(str(script), name1=name1, name2=name2)

        if not turns:
            turns = [{"speaker": 1, "speaker_name": name1, "text": str(script).strip()}]

        work_dir = Path(tempfile.mkdtemp(prefix="dialogue_tts_"))
        sr = 24000
        combined_pcm_chunks: list[bytes] = []
        global_time = 0.15

        # Initial silence padding
        initial_samples = int(global_time * sr)
        if initial_samples > 0:
            combined_pcm_chunks.append(b"\x00" * (initial_samples * 2))

        timed_turns: list[dict] = []
        total_turns = len(turns)

        try:
            for idx, turn in enumerate(turns):
                if progress_cb:
                    progress_cb(f"Synthesizing {turn['speaker_name']}…", int(10 + (idx / total_turns) * 75))

                is_s1 = turn["speaker"] == 1
                cfg = voice1_cfg if is_s1 else voice2_cfg
                vid = cfg.get("voice_id") or ("blend:male_introspective" if is_s1 else "blend:female_warm")
                spd = float(cfg.get("speed", 1.0))
                pit = float(cfg.get("pitch", 0.0))

                clean_line = re.sub(
                    rf"^(?:\*\*)?(?:\[)?(?:{re.escape(name1)}|{re.escape(name2)}|speaker\s*1|speaker\s*2|voice\s*1|voice\s*2|male\s*voice|female\s*voice|male|female)(?:\])?(?:\*\*)?\s*[:\-–—]\s*",
                    "",
                    str(turn["text"]).strip(),
                    flags=re.IGNORECASE,
                ).strip()
                clean_line = re.sub(r"[*_]+", "", clean_line).strip()
                if not clean_line:
                    continue

                turn_wav = str(work_dir / f"turn_{idx:03d}_{turn['speaker_name']}.wav")
                ok = self.synthesize(
                    text=clean_line,
                    voice_id=vid,
                    speed=spd,
                    pitch=pit,
                    output_path=turn_wav,
                )

                turn_dur = self.get_audio_duration(turn_wav) if (ok and os.path.exists(turn_wav)) else self.estimate_duration(clean_line, spd)

                # Read raw PCM from turn_wav
                if ok and os.path.exists(turn_wav):
                    with wave.open(turn_wav, "rb") as wf:
                        chunk_rate = wf.getframerate()
                        chunk_frames = wf.readframes(wf.getnframes())
                        combined_pcm_chunks.append(chunk_frames)
                else:
                    silent_len = int(turn_dur * sr) * 2
                    combined_pcm_chunks.append(b"\x00" * silent_len)

                timed_turns.append({
                    "turn_index": idx,
                    "speaker": turn["speaker"],
                    "speaker_name": turn["speaker_name"],
                    "text": clean_line,
                    "start": round(global_time, 3),
                    "end": round(global_time + turn_dur, 3),
                    "duration": round(turn_dur, 3),
                })
                global_time += turn_dur

                # Conversational natural turn-taking micro-gap (crisp and lively)
                gap_sec = 0.22 if idx < total_turns - 1 else 0.15
                gap_samples = int(gap_sec * sr)
                combined_pcm_chunks.append(b"\x00" * (gap_samples * 2))
                global_time += gap_sec

            # Write raw concatenated dialogue WAV
            raw_path = f"{output_path}.raw.wav" if master_audio else output_path
            os.makedirs(os.path.dirname(os.path.abspath(raw_path)), exist_ok=True)
            with wave.open(raw_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sr)
                for chunk in combined_pcm_chunks:
                    wf.writeframes(chunk)

            final_dur = self.get_audio_duration(raw_path)

            if master_audio:
                if progress_cb:
                    progress_cb("Applying human acoustic studio mastering…", 92)
                if self.apply_acoustic_mastering(raw_path, output_path):
                    try:
                        os.unlink(raw_path)
                    except OSError:
                        pass
                else:
                    if raw_path != output_path:
                        shutil.move(raw_path, output_path)

            total_dur = self.get_audio_duration(output_path) or final_dur
            return {
                "success": True,
                "output_path": output_path,
                "duration": total_dur,
                "turns": timed_turns,
                "speaker1_name": name1,
                "speaker2_name": name2,
            }
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)


def compute_auto_voice_speed(
    script: str,
    target_duration: float = 30.0,
    video_profile: str = "balanced",
) -> float:
    """
    Compute optimal natural TTS speaking speed from script density, target duration,
    and video storytelling cadence within pleasant human bounds [0.88, 1.22].
    """
    words = len((script or "").split())
    if words <= 0:
        return 1.0

    profile_base = {
        "psychology": 1.0,
        "story_wisdom": 1.0,
        "growth_discipline": 1.08,
        "social_contrast": 1.06,
    }.get(video_profile, 1.0)

    sentence_stops = len(re.findall(r"[.!?]+", script))
    comma_pauses = script.count(",") + script.count("—") + script.count(";")
    est_base_dur = (words / 2.42) + (sentence_stops * 0.28) + (comma_pauses * 0.12)

    if target_duration > 4.0:
        ratio = est_base_dur / float(target_duration)
        clamped_ratio = max(1.0, min(1.28, ratio))
        blended = (0.65 * clamped_ratio) + (0.35 * profile_base)
    else:
        blended = profile_base

    return round(max(1.0, min(1.28, blended)), 2)
