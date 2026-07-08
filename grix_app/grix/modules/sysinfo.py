"""
Grix - System Information Reader
===================================

Reads system hardware and configuration from two sources:

1. /etc/kernel-autotune/state.json  (written by Kernel Autotune, a
   separate Griffin Linux tool - optional, works fine without it)
2. Standard Linux system calls and /proc / /sys files (always
   available, no external tools needed)

The state.json gives Grix a richer picture than it could get on its
own: CPU model, GPU, driver, RAM, device type, and every tuning
parameter Kernel Autotune has applied. This is used for display only
- Grix reads it but never writes to it, and never makes diagnostic
decisions based on it (the diagnostic checks in diagnostics.py are
completely independent of this file and run correctly whether or not
Kernel Autotune is installed).

Purpose of this display: when something goes wrong that Grix can't
fix automatically, the user can share their full system snapshot with
the Griffin Linux community (Discord: https://discord.gg/fMCpeNCxhv)
so they can get help with context that actually matters (CPU, GPU,
driver, kernel, distro, tuning state) rather than guessing blind.
"""

from __future__ import annotations

import json
import os
import platform
import re
import subprocess
from dataclasses import dataclass, field
from typing import Any

KERNEL_AUTOTUNE_STATE = "/etc/kernel-autotune/state.json"
DISCORD_INVITE = "https://discord.gg/fMCpeNCxhv"


@dataclass
class SystemInfo:
    # ------------------------------------------------------------------
    # Hardware (from state.json if available, otherwise /proc fallbacks)
    # ------------------------------------------------------------------
    hostname: str = ""
    distro: str = ""
    kernel_version: str = ""
    cpu_model: str = ""
    cpu_cores: int = 0
    ram_mb: int = 0
    gpu_model: str = ""
    gpu_driver: str = ""
    device_type: str = ""         # "desktop" / "laptop" / etc.
    has_ssd: bool = False
    is_numa: bool = False
    has_thermal: bool = False

    # ------------------------------------------------------------------
    # Kernel Autotune state (only available if state.json is present)
    # ------------------------------------------------------------------
    autotune_available: bool = False
    autotune_version: str = ""
    autotune_last_updated: str = ""
    autotune_kernel_type: str = ""  # "generic" / "low-latency" etc.
    autotune_apply_complete: bool = False
    autotune_last_apply_duration: float = 0.0
    autotune_applied_steps: list[str] = field(default_factory=list)
    autotune_failed_steps: list[str] = field(default_factory=list)
    autotune_config: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Raw state.json for full display if needed
    # ------------------------------------------------------------------
    raw_state: dict[str, Any] = field(default_factory=dict)


def _read_state_json() -> dict | None:
    """Try to read /etc/kernel-autotune/state.json. Returns the parsed
    dict on success, None if not present or unreadable."""
    try:
        with open(KERNEL_AUTOTUNE_STATE) as f:
            return json.load(f)
    except (FileNotFoundError, PermissionError, json.JSONDecodeError,
            OSError):
        return None


def _proc_cpu_model() -> str:
    """Read CPU model from /proc/cpuinfo."""
    try:
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("model name"):
                    return line.split(":", 1)[1].strip()
    except OSError:
        pass
    return ""


def _proc_cpu_cores() -> int:
    """Count logical CPU cores from /proc/cpuinfo."""
    try:
        count = 0
        with open("/proc/cpuinfo") as f:
            for line in f:
                if line.startswith("processor"):
                    count += 1
        return count
    except OSError:
        return 0


def _proc_ram_mb() -> int:
    """Read total RAM from /proc/meminfo."""
    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if line.startswith("MemTotal"):
                    kb = int(line.split()[1])
                    return kb // 1024
    except (OSError, ValueError, IndexError):
        pass
    return 0


def _lsb_distro() -> str:
    """Best-effort distro name from /etc/os-release."""
    try:
        with open("/etc/os-release") as f:
            for line in f:
                if line.startswith("PRETTY_NAME="):
                    return line.split("=", 1)[1].strip().strip('"')
    except OSError:
        pass
    return platform.platform()


def _glxinfo_gpu() -> tuple[str, str]:
    """Try to get GPU model and driver version from glxinfo or
    nvidia-smi. Returns (model, driver) or ("", "")."""
    # Try nvidia-smi first (fast, precise)
    try:
        out = subprocess.check_output(
            ["nvidia-smi", "--query-gpu=name,driver_version",
             "--format=csv,noheader,nounits"],
            timeout=5, stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if out:
            parts = out.split(",", 1)
            model = parts[0].strip()
            driver = parts[1].strip() if len(parts) > 1 else ""
            return model, driver
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        pass

    # Try glxinfo (works for AMD/Intel)
    try:
        out = subprocess.check_output(
            ["glxinfo", "-B"], timeout=5,
            stderr=subprocess.DEVNULL, text=True,
        )
        model = ""
        for line in out.splitlines():
            if "OpenGL renderer string:" in line:
                model = line.split(":", 1)[1].strip()
                break
        return model, ""
    except (FileNotFoundError, subprocess.SubprocessError, OSError):
        pass

    return "", ""


def load() -> SystemInfo:
    """Load system info from all available sources. Never raises —
    missing data is represented as empty strings / False / 0."""
    info = SystemInfo()

    # Base system info from /proc and platform (always available)
    info.hostname = platform.node()
    info.distro = _lsb_distro()
    info.kernel_version = platform.release()
    info.cpu_model = _proc_cpu_model()
    info.cpu_cores = _proc_cpu_cores()
    info.ram_mb = _proc_ram_mb()

    # Try to enrich from Kernel Autotune state.json
    state = _read_state_json()
    if state:
        info.autotune_available = True
        info.raw_state = state

        # Override base fields with richer data from state.json where
        # available - these are usually more accurate (state.json uses
        # the kernel autotune script's own hardware detection which is
        # more thorough than /proc reads alone)
        info.hostname = state.get("hostname", info.hostname)
        info.distro = state.get("distro", info.distro)
        info.kernel_version = state.get("kernel_version", info.kernel_version)
        info.cpu_model = state.get("cpu_model", info.cpu_model)
        info.cpu_cores = int(state.get("cpu_cores", info.cpu_cores))
        info.ram_mb = int(state.get("ram_mb", info.ram_mb))
        info.gpu_model = state.get("gpu_model", "")
        info.gpu_driver = state.get("gpu_driver", "")
        info.device_type = state.get("device_type", "")
        info.has_ssd = bool(state.get("has_ssd", False))
        info.is_numa = bool(state.get("is_numa", False))
        info.has_thermal = bool(state.get("has_thermal", False))

        info.autotune_version = state.get("script_version", "")
        info.autotune_last_updated = state.get("last_updated", "")
        info.autotune_kernel_type = state.get("kernel", "")
        info.autotune_apply_complete = bool(state.get("apply_complete", False))
        info.autotune_last_apply_duration = float(
            state.get("last_apply_duration", 0.0)
        )
        info.autotune_applied_steps = list(state.get("applied_steps", []))
        info.autotune_failed_steps = list(state.get("failed_steps", []))
        info.autotune_config = dict(state.get("config", {}))
    else:
        # No state.json - try to get GPU from system tools
        info.gpu_model, info.gpu_driver = _glxinfo_gpu()

    return info


def format_ram(mb: int) -> str:
    """Format RAM in MB as a human-friendly string: 'X GB' or 'X MB'."""
    if mb <= 0:
        return "Unknown"
    if mb >= 1024:
        gb = round(mb / 1024, 1)
        return f"{gb} GB"
    return f"{mb} MB"


def describe_config_key(key: str) -> str:
    """Plain-English label for a Kernel Autotune config key."""
    labels = {
        "swappiness":         "Swappiness",
        "dirty_ratio":        "Dirty Ratio",
        "dirty_bg_ratio":     "Dirty Background Ratio",
        "vfs_cache_pressure": "VFS Cache Pressure",
        "cpu_governor":       "CPU Governor",
        "thp":                "Transparent Huge Pages",
        "zram_enabled":       "ZRAM Enabled",
        "zram_ratio":         "ZRAM Ratio",
        "zram_algo":          "ZRAM Algorithm",
        "zswap_enabled":      "ZSWAP Enabled",
        "tcp_congestion":     "TCP Congestion Control",
        "net_qdisc":          "Network Queue Discipline",
    }
    return labels.get(key, key.replace("_", " ").title())
