"""
system_info.py - Windows system information utilities.
Retrieves RAM, VRAM, CPU name, GPU name without psutil dependency.
Uses ctypes (GlobalMemoryStatusEx), subprocess (nvidia-smi), and winreg.
Optimised for the AMD Ryzen 5 4600H / 8 GB RAM / NVIDIA GTX 1650 target.
"""

import ctypes
import ctypes.wintypes as wintypes
import re
import subprocess
import winreg
from typing import Optional


# ---------------------------------------------------------------------------
# Windows MEMORYSTATUSEX structure
# ---------------------------------------------------------------------------

class _MEMORYSTATUSEX(ctypes.Structure):  # noqa: N801
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


def _global_memory_status() -> Optional[_MEMORYSTATUSEX]:
    """Call GlobalMemoryStatusEx; return None on failure."""
    stat = _MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    try:
        ok = ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat if ok else None
    except Exception:
        return None


# ---------------------------------------------------------------------------
# RAM
# ---------------------------------------------------------------------------

def get_system_ram_mb() -> int:
    """Return total physical RAM in megabytes (0 on failure)."""
    stat = _global_memory_status()
    if stat is None:
        return 0
    return int(stat.ullTotalPhys // (1024 * 1024))


def get_available_ram_mb() -> int:
    """Return currently available (free) physical RAM in megabytes."""
    stat = _global_memory_status()
    if stat is None:
        return 0
    return int(stat.ullAvailPhys // (1024 * 1024))


# ---------------------------------------------------------------------------
# NVIDIA VRAM via nvidia-smi
# ---------------------------------------------------------------------------

def _run_nvidia_smi(*extra_args: str) -> Optional[str]:
    """
    Run nvidia-smi with the supplied arguments and return stdout as a string.
    Returns None if nvidia-smi is not found or the process fails.
    """
    try:
        result = subprocess.run(
            ["nvidia-smi", *extra_args],
            capture_output=True,
            text=True,
            timeout=10,
            creationflags=subprocess.CREATE_NO_WINDOW,  # type: ignore[attr-defined]
        )
        if result.returncode == 0:
            return result.stdout
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass
    return None


def get_nvidia_vram_mb() -> int:
    """
    Return total VRAM of the first NVIDIA GPU in megabytes.
    Returns 0 when no NVIDIA GPU / driver is present.
    """
    out = _run_nvidia_smi(
        "--query-gpu=memory.total",
        "--format=csv,noheader,nounits",
    )
    if out is None:
        return 0
    for line in out.strip().splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
        m = re.search(r"(\d+)", line)
        if m:
            return int(m.group(1))
    return 0


def get_nvidia_free_vram_mb() -> int:
    """
    Return free VRAM of the first NVIDIA GPU in megabytes.
    Returns 0 when not available.
    """
    out = _run_nvidia_smi(
        "--query-gpu=memory.free",
        "--format=csv,noheader,nounits",
    )
    if out is None:
        return 0
    for line in out.strip().splitlines():
        line = line.strip()
        if line.isdigit():
            return int(line)
        m = re.search(r"(\d+)", line)
        if m:
            return int(m.group(1))
    return 0


# ---------------------------------------------------------------------------
# CPU name via winreg
# ---------------------------------------------------------------------------

def get_cpu_name() -> str:
    """Return the CPU brand string from the Windows registry."""
    key_path = r"HARDWARE\DESCRIPTION\System\CentralProcessor\0"
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return str(name).strip()
    except (FileNotFoundError, OSError, WindowsError):
        return "Unknown CPU"


# ---------------------------------------------------------------------------
# GPU name
# ---------------------------------------------------------------------------

def get_gpu_name() -> str:
    """
    Return the GPU name, preferring nvidia-smi for accuracy.
    Falls back to the Windows registry Display adapter entry.
    """
    # Try nvidia-smi first
    out = _run_nvidia_smi("--query-gpu=name", "--format=csv,noheader")
    if out:
        name = out.strip().splitlines()[0].strip()
        if name:
            return name

    # Fallback: Windows registry
    key_path = (
        r"SYSTEM\CurrentControlSet\Control\Class"
        r"\{4d36e968-e325-11ce-bfc1-08002be10318}\0000"
    )
    for value_name in ("DriverDesc", "Device Description"):
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, key_path) as key:
                name, _ = winreg.QueryValueEx(key, value_name)
                return str(name).strip()
        except (FileNotFoundError, OSError):
            continue

    return "Unknown GPU"


# ---------------------------------------------------------------------------
# Combined summary
# ---------------------------------------------------------------------------

def get_system_summary() -> dict:
    """
    Return a dict with all relevant system information.

    Keys
    ----
    cpu_name, gpu_name,
    total_ram_mb, available_ram_mb,
    total_vram_mb, free_vram_mb,
    recommended_model
    """
    total_ram = get_system_ram_mb()
    avail_ram = get_available_ram_mb()
    total_vram = get_nvidia_vram_mb()
    free_vram = get_nvidia_free_vram_mb()

    return {
        "cpu_name":          get_cpu_name(),
        "gpu_name":          get_gpu_name(),
        "total_ram_mb":      total_ram,
        "available_ram_mb":  avail_ram,
        "total_vram_mb":     total_vram,
        "free_vram_mb":      free_vram,
        "has_gpu":           total_vram > 0,
        "nvenc_ready":       total_vram > 0,
        "recommended_model": recommend_model_for_system(
            available_ram_mb=avail_ram,
            free_vram_mb=free_vram,
        ),
    }


# ---------------------------------------------------------------------------
# Model recommendation
# ---------------------------------------------------------------------------

def recommend_model_for_system(
    available_ram_mb: Optional[int] = None,
    free_vram_mb: Optional[int] = None,
) -> str:
    """
    Return the name of the recommended Ollama model based on available
    system resources.

    Thresholds (conservative to leave headroom for the OS and UI):
    - <  3 GB available RAM  → qwen2.5:0.5b   (~395 MB)
    - <  5 GB available RAM  → qwen2.5:1.5b   (~934 MB)
    - <  8 GB available RAM  → qwen2.5:3b     (~1.9 GB)
    - >= 8 GB available RAM  → qwen2.5:7b     (~4.7 GB)

    When enough VRAM is free (>= 2 GB), bumps up one tier.
    """
    if available_ram_mb is None:
        available_ram_mb = get_available_ram_mb()
    if free_vram_mb is None:
        free_vram_mb = get_nvidia_free_vram_mb()

    has_good_vram = free_vram_mb >= 2500  # >= 2.5 GB free VRAM
    avail_gb = available_ram_mb / 1024

    if avail_gb >= 4.5 and has_good_vram:
        return "qwen3.5:2b"
    return "qwen3.5:0.8b"
