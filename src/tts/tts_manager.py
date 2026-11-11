"""
TTS Manager - Local text-to-speech with Kokoro-ONNX, Piper, and Windows SAPI backends.
Fully offline. No cloud TTS. No paid APIs.

Strictly exposes only voices and languages genuinely supported by locally
installed models/engines.
"""

from __future__ import annotations

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
        self.ffmpeg_path: str = ffmpeg_path
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
        search_dirs = [
            Path(self.models_dir) / "kokoro",
            Path(self.models_dir),
            Path("assets/voices/kokoro"),
            Path("models/kokoro"),
        ]
        model_names = ("kokoro-v1.0.int8.onnx", "kokoro-v1.0.onnx", "kokoro-v1.0.fp16.onnx", "kokoro-v0_19.onnx")
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
                if supported_kokoro is None or v["id"] in supported_kokoro:
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

        # 4. Dashes and slashes between words
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
                return output_path if os.path.exists(output_path) else None

        if not success:
            logger.info("Primary TTS backend '%s' failed; using Windows SAPI fallback", backend)
            sapi_name = voice_info.get("sapi_name") if voice_info else None
            success = self._synthesize_sapi(prepared, raw_path, speed=speed, pitch=pitch, sapi_voice_name=sapi_name)
            if success and raw_path != output_path:
                shutil.move(raw_path, output_path)
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

        return output_path if os.path.exists(output_path) else None

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

    def _synthesize_kokoro(
        self,
        text: str,
        voice_id: str,
        speed: float,
        output_path: str,
        lang_code: str = "en-us",
    ) -> bool:
        """Synthesize via lightweight kokoro-onnx (preferred) or kokoro."""
        model_path, voices_path = self._find_kokoro_files()
        if model_path and voices_path and importlib.util.find_spec("kokoro_onnx") is not None:
            try:
                import numpy as np
                from kokoro_onnx import Kokoro  # type: ignore

                if self._kokoro_onnx is None:
                    self._kokoro_onnx = Kokoro(model_path, voices_path)

                samples, sample_rate = self._kokoro_onnx.create(
                    text, voice=voice_id, speed=max(0.5, min(2.0, speed)), lang=lang_code
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
