"""
Grix Settings Panel
======================

Houses:
  - Local Insights opt-in (analytics module): off by default,
    local-only, never transmitted. Shows exactly what's recorded and
    lets the user clear it.
  - Plugin status: lists every discovered plugin (loaded or failed)
    from grix/modules/plugins.py - including the bundled Griffin Linux
    Suite integration, which is itself an ordinary plugin.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QTime
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QCheckBox, QScrollArea, QMessageBox, QComboBox, QSpinBox,
    QButtonGroup, QRadioButton, QTimeEdit, QTabWidget,
)

from ..modules import analytics, snooze, policykit, diagnostics, plugins
from ..modules import schedule as schedule_module
from ..ui import workers
from .sysinfo_panel import SysInfoPanel
from .theme import COLORS

# Friendly display names for check ids, used in the "Snoozed Checks"
# management list. Falls back to the raw id if not found here.
CHECK_TITLES = {
    "package_manager": "Package Manager Health",
    "updates": "Available Updates",
    "services": "System Services",
    "disk": "Disk Space",
    "flatpak_snap": "Flatpak & Snap Runtimes",
    "audio": "Audio Stack",
    "timeshift": "Backup Snapshot Usage",
    "journal": "System Journal",
    "network": "Network Connectivity",
    "permissions": "File Permissions",
    "boot": "Boot Time",
    "security": "Firewall",
    "old_kernels": "Old Kernel Versions",
}


class SettingsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        title = QLabel("Settings")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        outer.addWidget(title)

        # Tab widget: Settings | System Info
        self._tabs = QTabWidget()
        self._tabs.setStyleSheet(
            f"QTabBar::tab {{ padding: 8px 18px; font-size: 13px; }}"
            f"QTabBar::tab:selected {{ font-weight: 700; color: {COLORS['accent']}; }}"
        )
        outer.addWidget(self._tabs, stretch=1)

        # ── Tab 1: Settings ───────────────────────────────────────────
        settings_widget = QWidget()
        settings_outer = QVBoxLayout(settings_widget)
        settings_outer.setContentsMargins(0, 12, 0, 0)
        settings_outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(16)
        content_layout.setContentsMargins(0, 0, 4, 0)
        scroll.setWidget(content)
        settings_outer.addWidget(scroll, stretch=1)

        self._tabs.addTab(settings_widget, "\u2699\ufe0f  Settings")

        # ── Tab 2: System Info ────────────────────────────────────────
        self._sysinfo_panel = SysInfoPanel()
        self._tabs.addTab(self._sysinfo_panel, "\U0001F5A5  System Info")

        # -- Auto-Scan Schedule --
        sched_card = QFrame()
        sched_card.setObjectName("settingsCard")
        sched_card_layout = QVBoxLayout(sched_card)
        sched_card_layout.setContentsMargins(20, 16, 20, 16)
        sched_card_layout.setSpacing(10)

        sched_title = QLabel("\U000023F0 Auto-Scan Schedule")
        sched_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        sched_card_layout.addWidget(sched_title)

        sched_desc = QLabel(
            "Grix can check your system health automatically in the "
            "background without opening the window - the mascot and "
            "tray icon update as normal when results come in. The Scan "
            "button still works exactly as before."
        )
        sched_desc.setWordWrap(True)
        sched_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        sched_card_layout.addWidget(sched_desc)

        # Mode radio buttons
        self._sched_group = QButtonGroup(self)

        # Row: Every N hours
        interval_row = QHBoxLayout()
        self._rb_interval = QRadioButton()
        self._sched_group.addButton(self._rb_interval, 0)
        interval_row.addWidget(self._rb_interval)
        interval_label = QLabel("Every")
        interval_label.setStyleSheet("font-size: 13px;")
        interval_row.addWidget(interval_label)
        self._interval_spin = QSpinBox()
        self._interval_spin.setRange(1, 24)
        self._interval_spin.setValue(1)
        self._interval_spin.setSuffix(" hour(s)")
        self._interval_spin.setFixedWidth(120)
        self._interval_spin.setStyleSheet(f"color: {COLORS['text_primary']}; background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 4px;")
        interval_row.addWidget(self._interval_spin)
        interval_row.addStretch()
        sched_card_layout.addLayout(interval_row)

        # Row: Daily at HH:MM AM/PM
        daily_row = QHBoxLayout()
        self._rb_daily = QRadioButton()
        self._sched_group.addButton(self._rb_daily, 1)
        daily_row.addWidget(self._rb_daily)
        daily_label = QLabel("Daily at")
        daily_label.setStyleSheet("font-size: 13px;")
        daily_row.addWidget(daily_label)
        self._daily_time = QTimeEdit()
        self._daily_time.setDisplayFormat("hh:mm AP")
        self._daily_time.setFixedWidth(110)
        self._daily_time.setStyleSheet(f"color: {COLORS['text_primary']}; background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 4px;")
        daily_row.addWidget(self._daily_time)
        daily_row.addStretch()
        sched_card_layout.addLayout(daily_row)

        # Row: Weekly on <Day> at HH:MM
        weekly_row = QHBoxLayout()
        self._rb_weekly = QRadioButton()
        self._sched_group.addButton(self._rb_weekly, 2)
        weekly_row.addWidget(self._rb_weekly)
        weekly_label = QLabel("Weekly on")
        weekly_label.setStyleSheet("font-size: 13px;")
        weekly_row.addWidget(weekly_label)
        self._weekly_day = QComboBox()
        for day in schedule_module.WEEKDAY_NAMES:
            self._weekly_day.addItem(day)
        self._weekly_day.setFixedWidth(120)
        self._weekly_day.setStyleSheet(f"color: {COLORS['text_primary']}; background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 4px;")
        weekly_row.addWidget(self._weekly_day)
        weekly_at_label = QLabel("at")
        weekly_at_label.setStyleSheet("font-size: 13px;")
        weekly_row.addWidget(weekly_at_label)
        self._weekly_time = QTimeEdit()
        self._weekly_time.setDisplayFormat("hh:mm AP")
        self._weekly_time.setFixedWidth(110)
        self._weekly_time.setStyleSheet(f"color: {COLORS['text_primary']}; background: {COLORS['bg_input']}; border: 1px solid {COLORS['border']}; border-radius: 4px; padding: 2px 4px;")
        weekly_row.addWidget(self._weekly_time)
        weekly_row.addStretch()
        sched_card_layout.addLayout(weekly_row)

        # Row: Never (manual only)
        never_row = QHBoxLayout()
        self._rb_never = QRadioButton()
        self._sched_group.addButton(self._rb_never, 3)
        never_row.addWidget(self._rb_never)
        never_label = QLabel("Never (manual scans only)")
        never_label.setStyleSheet("font-size: 13px;")
        never_row.addWidget(never_label)
        never_row.addStretch()
        sched_card_layout.addLayout(never_row)

        # Preview + save
        self._sched_preview = QLabel()
        self._sched_preview.setWordWrap(True)
        self._sched_preview.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 4px;")
        sched_card_layout.addWidget(self._sched_preview)

        sched_save_btn = QPushButton("Save Schedule")
        sched_save_btn.clicked.connect(self._on_save_schedule)
        sched_card_layout.addWidget(sched_save_btn, alignment=Qt.AlignmentFlag.AlignLeft)

        # Wire controls to update the preview live as the user changes things
        self._sched_group.idToggled.connect(lambda _id, _checked: self._update_sched_preview())
        self._interval_spin.valueChanged.connect(lambda _v: self._update_sched_preview())
        self._daily_time.timeChanged.connect(lambda _t: self._update_sched_preview())
        self._weekly_day.currentIndexChanged.connect(lambda _i: self._update_sched_preview())
        self._weekly_time.timeChanged.connect(lambda _t: self._update_sched_preview())

        content_layout.addWidget(sched_card)

        # -- Local Insights --
        insights_card = QFrame()
        insights_card.setObjectName("settingsCard")
        insights_layout = QVBoxLayout(insights_card)
        insights_layout.setContentsMargins(20, 16, 20, 16)
        insights_layout.setSpacing(8)

        insights_title = QLabel("\U0001F4CA Local Insights")
        insights_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        insights_layout.addWidget(insights_title)

        insights_desc = QLabel(
            "When enabled, Grix keeps a small local record of which "
            "checks come back with issues most often, and which fixes "
            "you apply. This is used only to help Grix (and, if you "
            "look, you) understand which parts of your system need "
            "attention most - for example, to prioritize which Linux "
            "Academy lessons might be useful to suggest.\n\n"
            "This data never leaves your computer. There is no "
            "telemetry, no ads, and nothing is sent anywhere else - not "
            "to Griffin, not to any third party, not anywhere. Only "
            "check and fix identifiers are recorded (like \u201cdisk\u201d "
            "or \u201capt_clean\u201d) - never file paths, package names, "
            "or error message contents."
        )
        insights_desc.setWordWrap(True)
        insights_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        insights_layout.addWidget(insights_desc)

        self.insights_checkbox = QCheckBox("Enable Local Insights")
        self.insights_checkbox.setStyleSheet("font-size: 13px; font-weight: 600; margin-top: 4px;")
        self.insights_checkbox.toggled.connect(self._on_insights_toggled)
        insights_layout.addWidget(self.insights_checkbox)

        self.insights_summary_label = QLabel()
        self.insights_summary_label.setWordWrap(True)
        self.insights_summary_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 4px;")
        insights_layout.addWidget(self.insights_summary_label)

        insights_btn_row = QHBoxLayout()
        clear_btn = QPushButton("Clear recorded data")
        clear_btn.clicked.connect(self._on_clear_insights)
        insights_btn_row.addWidget(clear_btn)
        insights_btn_row.addStretch()
        insights_layout.addLayout(insights_btn_row)

        content_layout.addWidget(insights_card)

        # -- Snoozed Checks --
        snoozed_card = QFrame()
        snoozed_card.setObjectName("settingsCard")
        snoozed_layout = QVBoxLayout(snoozed_card)
        snoozed_layout.setContentsMargins(20, 16, 20, 16)
        snoozed_layout.setSpacing(8)

        snoozed_title = QLabel("\U0001F515 Ignored Checks")
        snoozed_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        snoozed_layout.addWidget(snoozed_title)

        snoozed_desc = QLabel(
            "Checks you've chosen to ignore from System Sentinel show up "
            "here. \u201cIgnore for a week\u201d brings a check back "
            "automatically after 7 days; \u201cIgnore forever\u201d keeps "
            "it hidden until you bring it back yourself. Either way, a "
            "check still reappears immediately if it becomes urgent - for "
            "example, Disk Space always comes back once usage reaches 95%, "
            "no matter how it was ignored."
        )
        snoozed_desc.setWordWrap(True)
        snoozed_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        snoozed_layout.addWidget(snoozed_desc)

        self.snoozed_list_layout = QVBoxLayout()
        self.snoozed_list_layout.setSpacing(6)
        snoozed_layout.addLayout(self.snoozed_list_layout)

        snoozed_btn_row = QHBoxLayout()
        unsnooze_all_btn = QPushButton("Show all ignored checks again")
        unsnooze_all_btn.clicked.connect(self._on_unsnooze_all)
        snoozed_btn_row.addWidget(unsnooze_all_btn)
        snoozed_btn_row.addStretch()
        snoozed_layout.addLayout(snoozed_btn_row)

        content_layout.addWidget(snoozed_card)

        # -- PolicyKit Integration --
        polkit_card = QFrame()
        polkit_card.setObjectName("settingsCard")
        polkit_layout = QVBoxLayout(polkit_card)
        polkit_layout.setContentsMargins(20, 16, 20, 16)
        polkit_layout.setSpacing(8)

        polkit_title = QLabel("\U0001F510 PolicyKit Integration")
        polkit_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        polkit_layout.addWidget(polkit_title)

        polkit_desc = QLabel(
            "Grix runs administrator actions through pkexec, which always "
            "shows a graphical authentication prompt either way. "
            "Installing this gives that prompt a Grix-branded message and "
            "narrows what it can authorize to a fixed, validated set of "
            "maintenance actions (see grix-helper) rather than an "
            "arbitrary command. Optional - Grix works the same without it."
        )
        polkit_desc.setWordWrap(True)
        polkit_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        polkit_layout.addWidget(polkit_desc)

        self.polkit_status_label = QLabel()
        self.polkit_status_label.setWordWrap(True)
        self.polkit_status_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px; margin-top: 4px;")
        polkit_layout.addWidget(self.polkit_status_label)

        polkit_btn_row = QHBoxLayout()
        self.polkit_action_btn = QPushButton()
        self.polkit_action_btn.clicked.connect(self._on_polkit_action)
        polkit_btn_row.addWidget(self.polkit_action_btn)
        polkit_btn_row.addStretch()
        polkit_layout.addLayout(polkit_btn_row)

        content_layout.addWidget(polkit_card)

        # -- Diagnostic Scope --
        scope_card = QFrame()
        scope_card.setObjectName("settingsCard")
        scope_layout = QVBoxLayout(scope_card)
        scope_layout.setContentsMargins(20, 16, 20, 16)
        scope_layout.setSpacing(8)

        scope_title = QLabel("\U0001F50E What System Sentinel Checks For")
        scope_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        scope_layout.addWidget(scope_title)

        scope_desc = QLabel(
            "System Sentinel runs a fixed set of system-health checks, "
            "listed below - it doesn't perform open-ended analysis. If "
            "something feels off that isn't listed here, \u201cExplain "
            "This Error\u201d (under System Sentinel) can help with "
            "specific error messages, and Settings \u2192 Plugins lets "
            "you (or a developer) add new checks Grix doesn't cover "
            "out of the box."
        )
        scope_desc.setWordWrap(True)
        scope_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        scope_layout.addWidget(scope_desc)

        self.scope_toggle_btn = QPushButton("Show full coverage list \u25BE")
        self.scope_toggle_btn.setCheckable(True)
        self.scope_toggle_btn.toggled.connect(self._toggle_scope_detail)
        scope_layout.addWidget(self.scope_toggle_btn)

        self.scope_detail = QWidget()
        scope_detail_layout = QVBoxLayout(self.scope_detail)
        scope_detail_layout.setContentsMargins(0, 6, 0, 0)
        scope_detail_layout.setSpacing(8)

        covered_title = QLabel("Checks for:")
        covered_title.setStyleSheet("font-weight: 700; font-size: 12px;")
        scope_detail_layout.addWidget(covered_title)
        for name, desc in diagnostics.SCOPE_COVERED:
            row = QLabel(f"\u2022 <b>{name}</b> - {desc}")
            row.setWordWrap(True)
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            scope_detail_layout.addWidget(row)

        scope_detail_layout.addSpacing(4)
        not_covered_title = QLabel("Does NOT check for:")
        not_covered_title.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {COLORS['yellow']};")
        scope_detail_layout.addWidget(not_covered_title)
        for desc in diagnostics.SCOPE_NOT_COVERED:
            row = QLabel(f"\u2022 {desc}")
            row.setWordWrap(True)
            row.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            scope_detail_layout.addWidget(row)

        self.scope_detail.setVisible(False)
        scope_layout.addWidget(self.scope_detail)

        content_layout.addWidget(scope_card)

        # -- Griffin Integration --
        griffin_card = QFrame()
        griffin_card.setObjectName("settingsCard")
        griffin_layout = QVBoxLayout(griffin_card)
        griffin_layout.setContentsMargins(20, 16, 20, 16)
        griffin_layout.setSpacing(8)

        griffin_title = QLabel("\U0001F50C Plugins")
        griffin_title.setStyleSheet("font-size: 16px; font-weight: 700;")
        griffin_layout.addWidget(griffin_title)

        griffin_desc = QLabel(
            "Grix can be extended by anyone - new System Sentinel "
            "checks, new Linux Academy lessons, or new UI panels - "
            "without modifying Grix itself. Drop a plugin folder into "
            f"<code>{plugins.USER_PLUGIN_DIR}</code> and it's picked up "
            "automatically on the next launch (or click \u201cReload "
            "Plugins\u201d below). The Griffin Linux Suite integration "
            "is itself an ordinary plugin - not special-cased - useful "
            "as a working example if you want to write your own. See "
            "CONTRIBUTING.md for the full plugin API."
        )
        griffin_desc.setWordWrap(True)
        griffin_desc.setTextFormat(Qt.TextFormat.RichText)
        griffin_desc.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        griffin_layout.addWidget(griffin_desc)

        self.griffin_status_layout = QVBoxLayout()
        self.griffin_status_layout.setSpacing(6)
        griffin_layout.addLayout(self.griffin_status_layout)

        reload_row = QHBoxLayout()
        reload_btn = QPushButton("Reload Plugins")
        reload_btn.clicked.connect(self._on_reload_plugins)
        reload_row.addWidget(reload_btn)

        open_folder_btn = QPushButton("Open Plugins Folder")
        open_folder_btn.clicked.connect(self._on_open_plugin_folder)
        reload_row.addWidget(open_folder_btn)
        reload_row.addStretch()
        griffin_layout.addLayout(reload_row)

        content_layout.addWidget(griffin_card)

        content_layout.addStretch()

        self.refresh()

    def refresh(self) -> None:
        data = analytics.load()
        self.insights_checkbox.blockSignals(True)
        self.insights_checkbox.setChecked(data.get("enabled", False))
        self.insights_checkbox.blockSignals(False)
        self._update_insights_summary()
        self._update_snoozed_list()
        self._update_polkit_status()
        self._refresh_schedule()
        self._update_griffin_status()

    def _refresh_schedule(self) -> None:
        """Load the saved schedule and populate the UI controls."""
        sched = schedule_module.load()
        # Temporarily block signals so updating controls doesn't
        # re-fire the preview updater while we're mid-population
        for widget in (self._interval_spin, self._daily_time,
                       self._weekly_day, self._weekly_time):
            widget.blockSignals(True)

        self._interval_spin.setValue(max(1, min(24, sched.interval_hours)))
        self._daily_time.setTime(QTime(sched.hour, sched.minute))
        self._weekly_day.setCurrentIndex(sched.weekday % 7)
        self._weekly_time.setTime(QTime(sched.hour, sched.minute))

        mode_to_btn = {
            "interval": self._rb_interval,
            "daily":    self._rb_daily,
            "weekly":   self._rb_weekly,
            "never":    self._rb_never,
        }
        btn = mode_to_btn.get(sched.mode, self._rb_interval)
        btn.blockSignals(True)
        btn.setChecked(True)
        btn.blockSignals(False)

        for widget in (self._interval_spin, self._daily_time,
                       self._weekly_day, self._weekly_time):
            widget.blockSignals(False)

        self._update_sched_preview()

    def _update_sched_preview(self) -> None:
        """Build a Schedule from the current UI state and show its
        plain-English description under the controls."""
        sched = self._sched_from_ui()
        self._sched_preview.setText(schedule_module.describe(sched))

    def _sched_from_ui(self) -> schedule_module.Schedule:
        """Read current control values and return a Schedule object."""
        mode_id = self._sched_group.checkedId()
        mode = {0: "interval", 1: "daily", 2: "weekly", 3: "never"}.get(mode_id, "interval")
        daily_t = self._daily_time.time()
        weekly_t = self._weekly_time.time()
        # For daily/weekly, use whichever time widget is relevant;
        # store the time in the shared hour/minute fields on Schedule.
        if mode == "daily":
            hour, minute = daily_t.hour(), daily_t.minute()
        elif mode == "weekly":
            hour, minute = weekly_t.hour(), weekly_t.minute()
        else:
            hour, minute = 9, 0  # default, not used by interval/never
        return schedule_module.Schedule(
            mode=mode,
            interval_hours=self._interval_spin.value(),
            hour=hour,
            minute=minute,
            weekday=self._weekly_day.currentIndex(),
        )

    def _on_save_schedule(self) -> None:
        sched = self._sched_from_ui()
        # Preserve the last_scan_at so saving schedule doesn't reset
        # the clock and cause an immediate re-scan
        existing = schedule_module.load()
        sched.last_scan_at = existing.last_scan_at
        schedule_module.save(sched)
        self._update_sched_preview()
        # Brief confirmation inline rather than a blocking dialog
        self._sched_preview.setText(
            "\u2705 Saved. " + schedule_module.describe(sched)
        )

    def _update_snoozed_list(self) -> None:
        while self.snoozed_list_layout.count() > 0:
            item = self.snoozed_list_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        entries = snooze.load_all()
        # Filter out anything lazily-expired by re-checking is_snoozed
        active = {
            check_id: entry for check_id, entry in entries.items()
            if snooze.is_snoozed(check_id)
        }

        if not active:
            label = QLabel("Nothing is currently being ignored.")
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
            self.snoozed_list_layout.addWidget(label)
            return

        for check_id, entry in active.items():
            row = QHBoxLayout()
            title = CHECK_TITLES.get(check_id, check_id)
            name_label = QLabel(title)
            name_label.setStyleSheet(f"color: {COLORS['text_primary']}; font-size: 13px;")
            row.addWidget(name_label, stretch=1)

            detail_text = (
                "Ignored forever" if entry.kind == "forever"
                else f"{snooze.days_remaining(entry)} day(s) left"
            )
            detail_label = QLabel(detail_text)
            detail_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px;")
            row.addWidget(detail_label)

            show_btn = QPushButton("Show me again")
            show_btn.clicked.connect(lambda _checked=False, cid=check_id: self._on_unsnooze_one(cid))
            row.addWidget(show_btn)

            row_widget = QWidget()
            row_widget.setLayout(row)
            self.snoozed_list_layout.addWidget(row_widget)

    def _on_unsnooze_one(self, check_id: str) -> None:
        snooze.unsnooze(check_id)
        self._update_snoozed_list()

    def _on_unsnooze_all(self) -> None:
        if not snooze.load_all():
            return
        reply = QMessageBox.question(
            self, "Show All Ignored Checks",
            "This brings back every check you've ignored, so they'll "
            "show up in System Sentinel again on the next scan. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            snooze.unsnooze_all()
            self._update_snoozed_list()

    def _update_polkit_status(self) -> None:
        if not policykit.has_pkexec():
            self.polkit_status_label.setText(
                "pkexec was not found on this system, so this integration "
                "isn't available here. Grix will fall back to sudo for "
                "administrator actions."
            )
            self.polkit_action_btn.setText("Unavailable")
            self.polkit_action_btn.setEnabled(False)
            return

        if policykit.is_installed():
            self.polkit_status_label.setText(
                "Installed - administrator prompts are Grix-branded and "
                "narrowly scoped."
            )
            self.polkit_action_btn.setText("Remove PolicyKit Integration")
            self.polkit_action_btn.setEnabled(True)
        elif policykit.is_available_to_install():
            self.polkit_status_label.setText(
                "Not installed - administrator prompts will use a generic "
                "pkexec dialog instead of a Grix-branded one."
            )
            self.polkit_action_btn.setText("Install PolicyKit Integration")
            self.polkit_action_btn.setEnabled(True)
        else:
            self.polkit_status_label.setText(
                "Grix couldn't find its own bundled PolicyKit files to "
                "install from here."
            )
            self.polkit_action_btn.setText("Unavailable")
            self.polkit_action_btn.setEnabled(False)

    def _on_polkit_action(self) -> None:
        if policykit.is_installed():
            reply = QMessageBox.question(
                self, "Remove PolicyKit Integration",
                "This removes the Grix-branded administrator prompt. Grix "
                "will continue to work normally, falling back to a "
                "generic pkexec/sudo prompt for administrator actions. "
                "Continue?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            success, message = policykit.uninstall()
        else:
            success, message = policykit.install()

        if success:
            QMessageBox.information(self, "Grix", message)
        else:
            QMessageBox.warning(self, "Grix", message)
        self._update_polkit_status()

    def _toggle_scope_detail(self, checked: bool) -> None:
        self.scope_detail.setVisible(checked)
        self.scope_toggle_btn.setText(
            "Hide full coverage list \u25B4" if checked
            else "Show full coverage list \u25BE"
        )

    def _update_insights_summary(self) -> None:
        summary = analytics.summary()
        if not summary["enabled"]:
            self.insights_summary_label.setText(
                "Local Insights is currently off. Nothing is being "
                "recorded."
            )
            return

        lines = [
            f"Enabled since {summary['since']}. "
            f"{summary['scans_run']} scan(s) recorded."
        ]
        if summary["most_flagged_checks"]:
            lines.append("Most frequently flagged checks:")
            for check_id, counts in summary["most_flagged_checks"]:
                flagged = counts.get("yellow", 0) + counts.get("red", 0)
                lines.append(f"  \u2022 {check_id}: flagged {flagged} time(s)")
        if summary["fix_applied_counts"]:
            lines.append("Fixes applied:")
            for fix_id, count in summary["fix_applied_counts"].items():
                lines.append(f"  \u2022 {fix_id}: {count} time(s)")

        self.insights_summary_label.setText("\n".join(lines))

    def _update_griffin_status(self) -> None:
        while self.griffin_status_layout.count() > 0:
            item = self.griffin_status_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

        infos = workers.get_plugin_infos()

        if not infos:
            label = QLabel(
                "No plugins installed. That's completely fine - Grix "
                "works fully on its own."
            )
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; margin-top: 4px;")
            self.griffin_status_layout.addWidget(label)
            return

        for info in sorted(infos, key=lambda i: i.name.lower()):
            row = QVBoxLayout()
            row.setSpacing(2)

            source_tag = "bundled" if info.source == "bundled" else "user-installed"
            if info.loaded:
                header_text = f"\u2705 <b>{info.name}</b> v{info.version} ({source_tag})"
            else:
                header_text = f"\u26A0\ufe0f <b>{info.name}</b> v{info.version} ({source_tag}) - failed to load"
            header = QLabel(header_text)
            header.setTextFormat(Qt.TextFormat.RichText)
            header.setWordWrap(True)
            header.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            row.addWidget(header)

            if info.description and info.loaded:
                desc = QLabel(info.description)
                desc.setWordWrap(True)
                desc.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
                row.addWidget(desc)

            if info.error:
                err = QLabel(info.error)
                err.setWordWrap(True)
                err.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 11px;")
                row.addWidget(err)

            self.griffin_status_layout.addLayout(row)

    def _on_reload_plugins(self) -> None:
        workers.reload_plugins()
        self._update_griffin_status()
        QMessageBox.information(
            self, "Grix",
            "Plugins reloaded. New or changed checks will appear on "
            "your next System Sentinel scan; new lesson tracks or "
            "panels need an app restart to fully take effect."
        )

    def _on_open_plugin_folder(self) -> None:
        import subprocess
        os.makedirs(plugins.USER_PLUGIN_DIR, exist_ok=True)
        try:
            subprocess.Popen(["xdg-open", plugins.USER_PLUGIN_DIR])
        except (OSError, FileNotFoundError):
            QMessageBox.information(
                self, "Plugins Folder",
                f"Plugins live in:\n{plugins.USER_PLUGIN_DIR}",
            )

    def _on_insights_toggled(self, checked: bool) -> None:
        analytics.set_enabled(checked)
        self._update_insights_summary()

    def _on_clear_insights(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Local Insights",
            "This will permanently delete Grix's locally recorded "
            "insights data. This does not affect your system - only "
            "Grix's own record. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            was_enabled = analytics.is_enabled()
            analytics.clear()
            if was_enabled:
                analytics.set_enabled(True)
            self.refresh()
