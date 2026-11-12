"""
Config Manager - Persistent settings storage for Stickman Studio.
Stores settings in JSON, loads on startup, saves on change/exit.
"""
import json
import os
from pathlib import Path
from typing import Any


class ConfigManager:
    """Manages application settings and project history."""

    DEFAULT_SETTINGS = {
        "version": "1.0.0",
        # LLM settings
        "llm_model": "auto",
        "llm_context_window": 2048,
        "llm_temperature": 0.7,
        "unload_llm_after_planning": True,
        "ollama_base_url": "http://localhost:11434",
        # TTS settings
        "default_voice": "af_heart",
        "default_speed": 1.0,
        "default_pitch": 0.0,
        "default_tts_volume": 100,
        # Video settings
        "default_duration": 30,
        "default_format": "9:16",
        "default_resolution": "1080p",
        "default_fps": 24,
        "default_style": "auto",
        "default_style_variant": "",
        "use_hardware_encoding": True,
        # Audio settings
        "default_music_style": "calm",
        "default_music_volume": 30,
        "default_sfx_volume": 70,
        "default_voice_volume": 100,
        "audio_fade_in_ds": 5,
        "audio_fade_out_ds": 5,
        "script_mode": "use_as_is",
        # Caption settings
        "default_caption_style": "bold_social",
        "caption_font_name": "Arial Bold",
        "caption_font_size": 38,
        "caption_position": "auto",
        "caption_color": "#FFFFFF",
        "caption_highlight_color": "",
        # Output settings
        "output_dir": str(Path(__file__).resolve().parent.parent.parent / "output"),
        # Performance settings
        "max_render_ram_gb": 3,
        "frame_batch_size": 48,
        # UI settings
        "window_width": 1200,
        "window_height": 850,
        "window_x": -1,
        "window_y": -1,
        # Recent data
        "recent_topics": [],
        "recent_scripts": [],
        "last_topic": "",
        "last_script": "",
    }

    def __init__(self, app_data_dir: str = None):
        if app_data_dir is None:
            app_data_dir = str(Path.home() / "AppData" / "Local" / "OfflineStickmanStudio")
        self.app_data_dir = Path(app_data_dir)
        self.config_path = self.app_data_dir / "settings.json"
        self._settings: dict = {}
        self._load()

    def _load(self):
        """Load settings from disk, merging with defaults."""
        self.app_data_dir.mkdir(parents=True, exist_ok=True)
        if self.config_path.exists():
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    saved = json.load(f)
                self._settings = {**self.DEFAULT_SETTINGS, **saved}
                return
            except Exception as e:
                print(f"[Config] Failed to load settings: {e}. Using defaults.")
        self._settings = dict(self.DEFAULT_SETTINGS)
        self._save()

    def _save(self):
        """Persist settings to disk."""
        try:
            self.app_data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(self._settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"[Config] Failed to save settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        return self._settings.get(key, default if default is not None else self.DEFAULT_SETTINGS.get(key))

    def set(self, key: str, value: Any, save: bool = True):
        self._settings[key] = value
        if save:
            self._save()

    def get_all(self) -> dict:
        return dict(self._settings)

    def update(self, updates: dict, save: bool = True):
        self._settings.update(updates)
        if save:
            self._save()

    def save(self):
        self._save()

    def add_recent_topic(self, topic: str):
        recents = self._settings.get("recent_topics", [])
        if topic in recents:
            recents.remove(topic)
        recents.insert(0, topic)
        self._settings["recent_topics"] = recents[:10]
        self._settings["last_topic"] = topic
        self._save()

    def add_recent_script(self, script: str):
        # Only store first 200 chars as preview
        preview = script[:200]
        recents = self._settings.get("recent_scripts", [])
        if preview not in recents:
            recents.insert(0, preview)
        self._settings["recent_scripts"] = recents[:5]
        self._settings["last_script"] = script
        self._save()

    def get_models_dir(self) -> str:
        d = self.app_data_dir / "models"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)

    def get_voices_dir(self) -> str:
        d = self.app_data_dir / "voices"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)

    def get_temp_dir(self) -> str:
        d = self.app_data_dir / "temp"
        d.mkdir(parents=True, exist_ok=True)
        return str(d)

    def get_output_dir(self) -> str:
        fallback = Path(__file__).resolve().parent.parent.parent / "output"
        configured = self._settings.get("output_dir") or str(fallback)
        d = Path(configured)
        try:
            d.mkdir(parents=True, exist_ok=True)
            # Quick write check in case folder is protected by Windows Controlled Folder Access
            probe = d / ".write_test"
            probe.touch(exist_ok=True)
            probe.unlink(missing_ok=True)
            return str(d)
        except OSError as e:
            print(f"[Config] Output directory '{d}' not writable ({e}); falling back to '{fallback}'.")
            fallback.mkdir(parents=True, exist_ok=True)
            self._settings["output_dir"] = str(fallback)
            self._save()
            return str(fallback)

