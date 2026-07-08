"""
Grix - System Info Panel
============================

Shows hardware and system configuration in a human-readable table.
If Kernel Autotune is installed, also shows every tuning parameter it
has applied to the system.

If something goes wrong that Grix can't fix automatically, the user
can share this panel's contents with the Griffin Linux community on
Discord: https://discord.gg/fMCpeNCxhv

This panel reads /etc/kernel-autotune/state.json (via sysinfo.py) but
gracefully degrades to /proc-based readings when that file isn't
present. Nothing in here is a diagnostic check - it's purely
informational display.
"""

from __future__ import annotations

import subprocess
import webbrowser

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QVBoxLayout, QWidget,
)

from ..modules import sysinfo as sysinfo_module
from ..modules.sysinfo import SystemInfo, DISCORD_INVITE
from .theme import COLORS


class _LoadWorker(QThread):
    """Load system info on a background thread - gpu detection
    (nvidia-smi / glxinfo) can take a second or two."""
    done = pyqtSignal(object)

    def run(self):
        self.done.emit(sysinfo_module.load())


class SysInfoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Header row
        header_row = QHBoxLayout()
        title = QLabel("System Information")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        header_row.addWidget(title)
        header_row.addStretch()

        refresh_btn = QPushButton("\u21BB  Refresh")
        refresh_btn.setToolTip("Re-read system info and state.json")
        refresh_btn.clicked.connect(self._load)
        header_row.addWidget(refresh_btn)
        outer.addLayout(header_row)

        subtitle = QLabel(
            "Hardware and configuration as Grix sees your system. If "
            "something goes wrong that Grix can\u2019t fix automatically, "
            "sharing this with the Griffin Linux community helps them help "
            "you with the context that actually matters."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        outer.addWidget(subtitle)

        # Discord callout banner
        discord_card = QFrame()
        discord_card.setObjectName("settingsCard")
        discord_layout = QHBoxLayout(discord_card)
        discord_layout.setContentsMargins(16, 12, 16, 12)

        discord_icon = QLabel("\U0001F4AC")
        discord_icon.setStyleSheet("font-size: 22px;")
        discord_layout.addWidget(discord_icon)

        discord_text = QLabel(
            "<b>Need help?</b> Share this page in the "
            "<a href='https://discord.gg/fMCpeNCxhv' "
            "style='color:#7289DA;'>Griffin Linux Discord server</a> "
            "and someone can help you figure out what\u2019s going on."
        )
        discord_text.setWordWrap(True)
        discord_text.setTextFormat(Qt.TextFormat.RichText)
        discord_text.setOpenExternalLinks(True)
        discord_text.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        discord_layout.addWidget(discord_text, stretch=1)

        discord_btn = QPushButton("Open Discord")
        discord_btn.setStyleSheet(
            "background-color: #5865F2; color: white; font-weight: 700; "
            "border-radius: 6px; padding: 6px 14px;"
        )
        discord_btn.clicked.connect(lambda: webbrowser.open(DISCORD_INVITE))
        discord_layout.addWidget(discord_btn)
        outer.addWidget(discord_card)

        # Scrollable content area
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setSpacing(12)
        self._content_layout.setContentsMargins(0, 0, 4, 0)
        self._scroll.setWidget(self._content_widget)
        outer.addWidget(self._scroll, stretch=1)

        self._loading_label = QLabel("Loading system information\u2026")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px;")
        self._content_layout.addWidget(self._loading_label)
        self._content_layout.addStretch()

        self._worker: _LoadWorker | None = None
        self._loaded = False

    def showEvent(self, event):
        super().showEvent(event)
        if not self._loaded:
            self._load()

    def _load(self) -> None:
        # Clear all existing content
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        self._loading_label = QLabel("Loading system information\u2026")
        self._loading_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._loading_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px;")
        self._content_layout.addWidget(self._loading_label)
        self._content_layout.addStretch()

        self._worker = _LoadWorker()
        self._worker.done.connect(self._on_loaded)
        self._worker.start()

    def _on_loaded(self, info: SystemInfo) -> None:
        self._loaded = True
        # Clear loading label
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        # -- Hardware Overview card --
        self._content_layout.addWidget(
            self._build_hardware_card(info)
        )

        # -- Kernel Autotune state card (if available) --
        if info.autotune_available:
            self._content_layout.addWidget(
                self._build_autotune_status_card(info)
            )
            self._content_layout.addWidget(
                self._build_autotune_config_card(info)
            )
        else:
            self._content_layout.addWidget(
                self._build_no_autotune_card()
            )

        self._content_layout.addStretch()

    # ------------------------------------------------------------------ #
    # Card builders                                                        #
    # ------------------------------------------------------------------ #

    def _card(self, title_emoji: str, title_text: str) -> tuple[QFrame, QVBoxLayout]:
        card = QFrame()
        card.setObjectName("settingsCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(10)
        title_label = QLabel(f"{title_emoji} {title_text}")
        title_label.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title_label)
        return card, layout

    def _row(self, label: str, value: str, muted: bool = False) -> QWidget:
        """A single label: value display row."""
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 2, 0, 2)
        row_layout.setSpacing(12)

        lbl = QLabel(label)
        lbl.setFixedWidth(200)
        lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        row_layout.addWidget(lbl)

        val = QLabel(value or "\u2014")
        val.setWordWrap(True)
        val.setTextFormat(Qt.TextFormat.PlainText)
        val.setStyleSheet(
            f"color: {COLORS['text_muted'] if muted else COLORS['text_primary']}; "
            f"font-size: 13px;"
        )
        row_layout.addWidget(val, stretch=1)
        return row

    def _divider(self) -> QFrame:
        d = QFrame()
        d.setFrameShape(QFrame.Shape.HLine)
        d.setStyleSheet(f"color: {COLORS['border']}; margin: 4px 0;")
        return d

    def _section_label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 11px; "
            f"font-weight: 700; letter-spacing: 0.5px; margin-top: 4px;"
        )
        return lbl

    def _build_hardware_card(self, info: SystemInfo) -> QFrame:
        card, layout = self._card("\U0001F5A5", "Hardware")

        layout.addWidget(self._section_label("SYSTEM"))
        layout.addWidget(self._row("Hostname", info.hostname))
        layout.addWidget(self._row("Distribution", info.distro))
        layout.addWidget(self._row("Kernel", info.kernel_version))
        if info.device_type:
            layout.addWidget(self._row("Device Type", info.device_type.title()))

        layout.addWidget(self._divider())
        layout.addWidget(self._section_label("PROCESSOR"))
        layout.addWidget(self._row("CPU", info.cpu_model or "Unknown"))
        layout.addWidget(self._row("Cores", str(info.cpu_cores) if info.cpu_cores else "Unknown"))
        if info.is_numa:
            layout.addWidget(self._row("NUMA", "Yes (multiple memory nodes)"))

        layout.addWidget(self._divider())
        layout.addWidget(self._section_label("MEMORY & STORAGE"))
        layout.addWidget(self._row("RAM", sysinfo_module.format_ram(info.ram_mb)))
        if info.autotune_available:
            layout.addWidget(self._row(
                "Storage",
                "SSD" if info.has_ssd else "HDD",
            ))

        if info.gpu_model:
            layout.addWidget(self._divider())
            layout.addWidget(self._section_label("GRAPHICS"))
            layout.addWidget(self._row("GPU", info.gpu_model))
            if info.gpu_driver:
                layout.addWidget(self._row("Driver", info.gpu_driver))

        if info.has_thermal:
            layout.addWidget(self._divider())
            layout.addWidget(self._row(
                "Thermal sensors", "Present",
                muted=False,
            ))

        return card

    def _build_autotune_status_card(self, info: SystemInfo) -> QFrame:
        card, layout = self._card("\u26A1", "Kernel Autotune Status")

        status_text = (
            "\u2705 All steps applied successfully"
            if info.autotune_apply_complete and not info.autotune_failed_steps
            else "\u26A0\ufe0f Some steps did not complete"
        )
        status_label = QLabel(status_text)
        status_label.setStyleSheet(
            f"color: {COLORS['green'] if info.autotune_apply_complete and not info.autotune_failed_steps else COLORS['yellow']}; "
            f"font-size: 13px; font-weight: 700;"
        )
        layout.addWidget(status_label)

        layout.addWidget(self._row("Version", info.autotune_version))
        layout.addWidget(self._row("Last Applied", _fmt_timestamp(info.autotune_last_updated)))
        layout.addWidget(self._row(
            "Apply Duration",
            f"{info.autotune_last_apply_duration:.1f}s" if info.autotune_last_apply_duration else "—",
        ))
        layout.addWidget(self._row("Kernel Type", info.autotune_kernel_type or "—"))

        if info.autotune_applied_steps:
            layout.addWidget(self._divider())
            layout.addWidget(self._section_label("APPLIED STEPS"))
            steps_text = "  \u2022  ".join(info.autotune_applied_steps)
            layout.addWidget(self._row("", steps_text))

        if info.autotune_failed_steps:
            layout.addWidget(self._section_label("FAILED STEPS"))
            failed_label = QLabel("  \u2022  ".join(info.autotune_failed_steps))
            failed_label.setWordWrap(True)
            failed_label.setStyleSheet(
                f"color: {COLORS['yellow']}; font-size: 13px; padding-left: 8px;"
            )
            layout.addWidget(failed_label)

        return card

    def _build_autotune_config_card(self, info: SystemInfo) -> QFrame:
        card, layout = self._card("\u2699\ufe0f", "Kernel Autotune Configuration")

        desc = QLabel(
            "These are the tuning parameters Kernel Autotune has applied to "
            "this system. You can adjust them using WinBridge, Griffin Linux\u2019s "
            "configuration bridge tool."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        layout.addWidget(desc)
        layout.addWidget(self._divider())

        if not info.autotune_config:
            layout.addWidget(QLabel("No configuration data available."))
            return card

        for key, value in info.autotune_config.items():
            label = sysinfo_module.describe_config_key(key)

            if isinstance(value, bool) or key in ("zram_enabled", "zswap_enabled"):
                display = "Enabled" if value else "Disabled"
            elif key == "zram_ratio":
                display = f"{value}%"
            elif key in ("swappiness", "dirty_ratio", "dirty_bg_ratio",
                         "vfs_cache_pressure"):
                display = str(value)
            else:
                display = str(value)

            layout.addWidget(self._row(label, display))

        return card

    def _build_no_autotune_card(self) -> QFrame:
        card, layout = self._card("\u2139\ufe0f", "Kernel Autotune")

        msg = QLabel(
            f"Kernel Autotune is not installed or has not run yet \u2014 "
            f"<b><code>{sysinfo_module.KERNEL_AUTOTUNE_STATE}</code></b> "
            f"was not found. That\u2019s completely fine \u2014 Grix works "
            f"fully without it. If you\u2019d like to install Kernel Autotune "
            f"or need help with your system, the Griffin Linux Discord is the "
            f"best place to start."
        )
        msg.setWordWrap(True)
        msg.setTextFormat(Qt.TextFormat.RichText)
        msg.setStyleSheet(
            f"color: {COLORS['text_secondary']}; font-size: 13px;"
        )
        layout.addWidget(msg)
        return card


def _fmt_timestamp(ts: str) -> str:
    """Make an ISO-8601 timestamp readable: '2026-06-30T01:12:52-05:00'
    → '2026-06-30 at 01:12 (UTC-5)'."""
    if not ts:
        return "—"
    try:
        # Split on T to get date and time, strip tz offset for display
        date_part, rest = ts.split("T", 1)
        # Remove fractional seconds and tz offset
        time_part = rest[:5]  # HH:MM
        # Try to parse timezone offset for display
        tz_part = ""
        for sep in ("+", "-"):
            if sep in rest[5:]:
                tz_raw = sep + rest[5:].split(sep, 1)[1]
                tz_hours = tz_raw.split(":")[0]
                tz_part = f" (UTC{tz_hours})"
                break
        return f"{date_part} at {time_part}{tz_part}"
    except (ValueError, IndexError):
        return ts
