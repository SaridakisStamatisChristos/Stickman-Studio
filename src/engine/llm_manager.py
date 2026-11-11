"""
LLM Manager - Handles local Ollama integration for scene planning and script generation.
Optimized for AMD Ryzen 5 4600H / 8GB RAM / GTX 1650 4GB VRAM.
"""

from __future__ import annotations

import json
import logging
import socket
import subprocess
import threading
import time
from typing import Callable, Iterator, Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

RECOMMENDED_MODELS: dict[str, str] = {
    "fast":       "qwen3.5:0.8b",
    "ultra_fast": "qwen2.5:0.5b",
    "balanced":   "qwen2.5:1.5b",
    "quality":    "qwen3.5:2b",
}

MODEL_SIZE_ESTIMATES: dict[str, str] = {
    "qwen3.5:0.8b":  "550 MB",
    "qwen3.5:2b":    "1.4 GB",
    "qwen2.5:0.5b":  "395 MB",
    "qwen2.5:1.5b":  "934 MB",
    "qwen2.5:3b":    "1.9 GB",
    "llama3.2:1b":   "1.3 GB",
    "llama3.2:3b":   "2.0 GB",
}

# Models that are small enough for 8 GB RAM + 4 GB VRAM laptops
SAFE_LOCAL_MODELS: tuple[str, ...] = (
    "qwen3.5:0.8b",
    "qwen2.5:0.5b",
    "qwen2.5:1.5b",
    "qwen3.5:2b",
    "llama3.2:1b",
)

_DEFAULT_TIMEOUT_SECONDS = 120
_PULL_TIMEOUT_SECONDS    = 1800   # 30 min for large models
_STATUS_TIMEOUT_SECONDS  = 5


# ---------------------------------------------------------------------------
# LLMManager
# ---------------------------------------------------------------------------

class LLMManager:
    """
    Thin wrapper around the Ollama HTTP API (http://localhost:11434).

    All public methods are safe to call even when Ollama is not running –
    they return sensible defaults or empty values instead of raising.
    """

    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url.rstrip("/")
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})
        self._active_model: Optional[str] = None
        self.default_model: Optional[str] = None
        self.context_window: int = 2048
        self._last_used_model: Optional[str] = None
        self._last_benchmark: dict = {}
        self._lock = threading.Lock()
        self._ollama_cached_ok: Optional[bool] = None
        self._ollama_checked_at: float = 0.0

    # ------------------------------------------------------------------
    # Connectivity
    # ------------------------------------------------------------------

    def check_ollama_running(self, force_refresh: bool = False) -> bool:
        """
        Fast, non-blocking check whether an optional local Ollama server is active.
        Uses a short 0.25s socket probe + 20s cache so built-in offline AI never stalls.
        """
        now = time.monotonic()
        if not force_refresh and self._ollama_cached_ok is not None and (now - self._ollama_checked_at) < 20.0:
            return self._ollama_cached_ok

        ok = False
        try:
            parsed = urlparse(self.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 11434
            # Probe IPv4 loopback directly when host is localhost to avoid Windows ::1 2s stall
            probe_host = "127.0.0.1" if host.lower() == "localhost" else host
            with socket.create_connection((probe_host, port), timeout=0.25):
                pass
            resp = self._session.get(
                f"{self.base_url.replace('localhost', '127.0.0.1')}/",
                timeout=1.2,
            )
            ok = resp.status_code < 500
        except OSError:
            ok = False
        except requests.exceptions.RequestException:
            ok = False

        self._ollama_cached_ok = ok
        self._ollama_checked_at = now
        return ok

    # ------------------------------------------------------------------
    # Model discovery
    # ------------------------------------------------------------------

    def get_installed_models(self) -> list[dict]:
        """
        Call GET /api/tags and return the list of installed model descriptors.
        Each dict contains at least: name, size, modified_at, digest.
        Returns an empty list quickly when Ollama is not running.
        """
        if not self.check_ollama_running():
            return []
        try:
            resp = self._session.get(
                f"{self.base_url}/api/tags",
                timeout=2.0,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("models", [])
        except requests.exceptions.RequestException as exc:
            logger.debug("get_installed_models failed: %s", exc)
            return []
        except (json.JSONDecodeError, KeyError) as exc:
            logger.debug("get_installed_models parse error: %s", exc)
            return []

    def get_model_info(self, model_name: str) -> dict:
        """
        Call POST /api/show for a specific model and return raw info dict.
        Returns empty dict on any error.
        """
        try:
            resp = self._session.post(
                f"{self.base_url}/api/show",
                json={"name": model_name},
                timeout=_STATUS_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.RequestException as exc:
            logger.debug("get_model_info(%s) failed: %s", model_name, exc)
            return {}
        except json.JSONDecodeError as exc:
            logger.debug("get_model_info parse error: %s", exc)
            return {}

    def is_model_downloaded(self, model_name: str) -> bool:
        """Return True when *model_name* appears in the installed models list."""
        installed = self.get_installed_models()
        names = {m.get("name", "") for m in installed}
        # Exact match or prefix match (e.g. "qwen2.5:0.5b" vs "qwen2.5:0.5b-instruct-…")
        if model_name in names:
            return True
        base = model_name.split(":")[0]
        return any(n.startswith(base) for n in names)

    def get_model_size_estimate(self, model_name: str) -> str:
        """Return a human-readable file-size estimate for *model_name*."""
        # Exact match first
        if model_name in MODEL_SIZE_ESTIMATES:
            return MODEL_SIZE_ESTIMATES[model_name]
        # Prefix match
        for key, size in MODEL_SIZE_ESTIMATES.items():
            if model_name.startswith(key.split(":")[0]):
                return size
        return "Unknown"

    # ------------------------------------------------------------------
    # Hardware probing
    # ------------------------------------------------------------------

    def check_vram_available(self) -> int:
        """
        Return free NVIDIA VRAM in megabytes by parsing nvidia-smi output.
        Returns 0 when no NVIDIA GPU is present or nvidia-smi is unavailable.
        """
        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.free",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    line = line.strip()
                    if line.isdigit():
                        return int(line)
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            pass
        return 0

    def check_ram_available(self) -> int:
        """
        Return available system RAM in megabytes.
        Uses ctypes (Windows) with a psutil fallback, then a conservative
        hard-coded fallback so this never raises.
        """
        # --- ctypes / Windows ---
        try:
            import ctypes

            class _MEMSTATEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength",                ctypes.c_ulong),
                    ("dwMemoryLoad",            ctypes.c_ulong),
                    ("ullTotalPhys",            ctypes.c_ulonglong),
                    ("ullAvailPhys",            ctypes.c_ulonglong),
                    ("ullTotalPageFile",        ctypes.c_ulonglong),
                    ("ullAvailPageFile",        ctypes.c_ulonglong),
                    ("ullTotalVirtual",         ctypes.c_ulonglong),
                    ("ullAvailVirtual",         ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            stat = _MEMSTATEX()
            stat.dwLength = ctypes.sizeof(stat)
            ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            if ok:
                return int(stat.ullAvailPhys // (1024 * 1024))
        except Exception:
            pass

        # --- psutil fallback ---
        try:
            import psutil
            return int(psutil.virtual_memory().available // (1024 * 1024))
        except ImportError:
            pass

        # --- conservative default ---
        return 4096  # assume 4 GB

    def get_recommended_model(self) -> str:
        """
        Return the fastest reliable Ollama model tag for this machine.

        Rules (conservative, leaves room for the OS and the UI process):
        - If an approved lightweight model is already installed, prefer the fastest one.
        - Otherwise choose between qwen3.5:0.8b (fast) and qwen3.5:2b (better quality)
          based on available RAM and VRAM.
        """
        installed = {m.get("name", "") for m in self.get_installed_models()}
        # Prefer already-installed lightweight models in fast-first order
        for candidate in (
            "qwen3.5:0.8b",
            "qwen2.5:0.5b",
            "qwen2.5:1.5b",
            "qwen3.5:2b",
            "llama3.2:1b",
        ):
            if candidate in installed:
                return candidate

        available_mb = self.check_ram_available()
        vram_mb = self.check_vram_available()
        # On 8 GB RAM / 4 GB VRAM laptops, default to fast mode unless plenty of free RAM
        if available_mb < 4500 or vram_mb < 2500:
            return RECOMMENDED_MODELS["fast"]
        return RECOMMENDED_MODELS["quality"]

    def get_model_run_location(self) -> str:
        """
        Return "GPU", "CPU", or "Mixed (GPU + CPU)" by querying Ollama's
        GET /api/ps endpoint (which reports exact size vs size_vram), falling
        back to nvidia-smi when no model is currently resident.
        """
        if self.check_ollama_running():
            try:
                resp = self._session.get(
                    f"{self.base_url.replace('localhost', '127.0.0.1')}/api/ps",
                    timeout=1.5,
                )
                if resp.ok:
                    models = resp.json().get("models", [])
                    if models:
                        m = models[0]
                        total_size = int(m.get("size", 0))
                        vram_size = int(m.get("size_vram", 0))
                        if vram_size <= 0:
                            return "CPU"
                        if total_size > 0 and vram_size < total_size * 0.9:
                            return "Mixed (GPU + CPU)"
                        return "GPU"
            except Exception:
                pass

        try:
            result = subprocess.run(
                [
                    "nvidia-smi",
                    "--query-gpu=memory.used",
                    "--format=csv,noheader,nounits",
                ],
                capture_output=True,
                text=True,
                timeout=10,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    used = int(line.strip())
                    if used > 500:
                        return "GPU"
                return "CPU"
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError, ValueError):
            pass
        return "CPU"

    def benchmark_model(self, model_name: Optional[str] = None) -> dict:
        """
        Benchmark startup + generation speed of *model_name* via Ollama.
        Returns dict with {model, ok, startup_ms, total_ms, tokens_per_sec, run_location}.
        """
        import time as _time
        target = model_name or self.default_model or self.get_recommended_model()
        result = {
            "model": target,
            "ok": False,
            "startup_ms": 0,
            "total_ms": 0,
            "tokens_per_sec": 0.0,
            "run_location": "Unknown",
        }
        if not self.check_ollama_running(force_refresh=True):
            return result

        t0 = _time.perf_counter()
        try:
            resp = self._session.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": target,
                    "prompt": "Reply with one short sentence about stickman animation.",
                    "stream": False,
                    "options": {
                        "num_ctx": self.context_window,
                        "num_predict": 32,
                        "temperature": 0.2,
                    },
                },
                timeout=60,
            )
            elapsed_ms = int((_time.perf_counter() - t0) * 1000)
            if not resp.ok:
                return result
            data = resp.json()
            load_ns = int(data.get("load_duration", 0))
            eval_count = int(data.get("eval_count", 0))
            eval_ns = int(data.get("eval_duration", 0))
            tps = round(eval_count / (eval_ns / 1e9), 1) if eval_ns > 0 else 0.0
            result.update({
                "ok": True,
                "startup_ms": int(load_ns / 1e6) if load_ns else elapsed_ms,
                "total_ms": elapsed_ms,
                "tokens_per_sec": tps,
                "run_location": self.get_model_run_location(),
            })
            self._last_benchmark = result
        except Exception as exc:
            logger.debug("benchmark_model(%s) failed: %s", target, exc)
        return result

    # ------------------------------------------------------------------
    # Model management
    # ------------------------------------------------------------------

    def pull_model(
        self,
        model_name: str,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> bool:
        """
        Download *model_name* from the Ollama registry via POST /api/pull.

        *progress_callback* is called with (status_str, percent_int) on each
        progress update (percent is -1 when indeterminate).

        Returns True on success, False on any error.
        """
        try:
            with self._session.post(
                f"{self.base_url}/api/pull",
                json={"name": model_name, "stream": True},
                stream=True,
                timeout=_PULL_TIMEOUT_SECONDS,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    status   = chunk.get("status", "")
                    total    = chunk.get("total",    0)
                    completed= chunk.get("completed", 0)

                    if progress_callback is not None:
                        if total and total > 0:
                            pct = int(completed * 100 / total)
                        else:
                            pct = -1
                        try:
                            progress_callback(status, pct)
                        except Exception:
                            pass  # never let callback kill the pull

                    if status == "success":
                        return True

            return True  # stream ended without explicit success → assume ok
        except requests.exceptions.RequestException as exc:
            logger.error("pull_model(%s) failed: %s", model_name, exc)
            return False

    def unload_model(self, model_name: str) -> None:
        """
        Signal Ollama to evict *model_name* from VRAM/RAM by sending a
        generate request with keep_alive=0.
        """
        try:
            self._session.post(
                f"{self.base_url}/api/generate",
                json={"model": model_name, "keep_alive": 0},
                timeout=_STATUS_TIMEOUT_SECONDS,
            )
        except requests.exceptions.RequestException as exc:
            logger.debug("unload_model(%s) failed: %s", model_name, exc)

    def unload(self) -> None:
        """Unload whichever Ollama model was used in this run (no-op when unused)."""
        target = self._last_used_model
        if target:
            self.unload_model(target)
            self._last_used_model = None

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: int = 2048,
        temperature: float = 0.7,
        num_ctx: Optional[int] = None,
    ) -> str:
        """
        Send a non-streaming generate request and return the full response text.
        Returns an empty string on any error.
        """
        if not model:
            model = self.default_model or self.get_recommended_model()

        ctx = max(512, min(4096, int(num_ctx or self.context_window or 2048)))
        payload = {
            "model":   model,
            "prompt":  prompt,
            "stream":  False,
            "options": {
                "num_ctx":     ctx,
                "num_predict": max_tokens,
                "temperature": temperature,
            },
        }

        try:
            with self._lock:
                self._active_model = model
                self._last_used_model = model

            resp = self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("response", "")

        except requests.exceptions.Timeout:
            logger.error("generate() timed out after %ds", _DEFAULT_TIMEOUT_SECONDS)
            return ""
        except requests.exceptions.RequestException as exc:
            logger.error("generate() request failed: %s", exc)
            return ""
        except json.JSONDecodeError as exc:
            logger.error("generate() JSON decode error: %s", exc)
            return ""
        finally:
            with self._lock:
                self._active_model = None

    def generate_stream(
        self,
        prompt: str,
        model: Optional[str] = None,
        callback: Optional[Callable[[str], None]] = None,
    ) -> Iterator[str]:
        """
        Send a streaming generate request.  Yields each token string as it
        arrives.  When *callback* is provided it is also called with each token.
        On any error the generator silently stops.
        """
        if not model:
            model = self.get_recommended_model()

        payload = {
            "model":  model,
            "prompt": prompt,
            "stream": True,
        }

        try:
            with self._session.post(
                f"{self.base_url}/api/generate",
                json=payload,
                stream=True,
                timeout=_DEFAULT_TIMEOUT_SECONDS,
            ) as resp:
                resp.raise_for_status()
                for raw_line in resp.iter_lines():
                    if not raw_line:
                        continue
                    try:
                        chunk = json.loads(raw_line)
                    except json.JSONDecodeError:
                        continue

                    token = chunk.get("response", "")
                    if token:
                        if callback is not None:
                            try:
                                callback(token)
                            except Exception:
                                pass
                        yield token

                    if chunk.get("done", False):
                        break

        except requests.exceptions.RequestException as exc:
            logger.error("generate_stream() failed: %s", exc)
            return
