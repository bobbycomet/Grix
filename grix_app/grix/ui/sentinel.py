"""
Grix System Sentinel - Diagnostics Panel
============================================

The main troubleshooting screen. Tabs:

  - Diagnostics: Grix's overall mood, a "Scan my system" button, and a
    list of check results, each with a status badge, an optional
    "Why did this happen?" expandable section, and any available
    fixes (opened via the Repair Preview dialog).
  - Explain This Error: paste an error message for a plain-language
    explanation and next steps.
  - System Timeline: "what changed?" view combining package history
    and recent errors.
  - Repair History: log of every fix Grix has applied.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QSizePolicy, QTabWidget, QListWidget, QListWidgetItem,
    QTextEdit, QMessageBox, QMenu,
)

from ..modules import diagnostics, history, analytics, snooze
from ..modules.diagnostics import CheckResult, Status, Fix, SeverityLevel
from .mascot import GrixMascot
from .workers import ScanWorker, FixWorker
from .fix_dialog import FixConfirmDialog
from .result_dialog import FixResultDialog
from .explain_error import ExplainErrorPanel
from .timeline_panel import TimelinePanel
from .theme import COLORS, code_box_style_alt, status_badge_style


STATUS_BADGE = {
    Status.GREEN: ("All good", COLORS["green"], COLORS["green_bg"]),
    Status.YELLOW: ("Needs attention", COLORS["yellow"], COLORS["yellow_bg"]),
    Status.RED: ("Urgent", COLORS["red"], COLORS["red_bg"]),
    Status.UNKNOWN: ("Not checked", COLORS["grey"], COLORS["grey_bg"]),
}

FRIENDLY_NAMES = {
    "check_package_manager": "Package Manager Health",
    "check_updates": "Available Updates",
    "check_failed_services": "System Services",
    "check_disk_space": "Disk Space",
    "check_journal": "System Journal",
    "check_network": "Network Connectivity",
    "check_user_owned_root_files": "File Permissions",
    "check_boot_time": "Boot Time",
    "check_security_basics": "Firewall",
    "check_old_kernels": "Old Kernel Versions",
}


class CheckCard(QFrame):
    """A single diagnostic result, with status badge, an optional
    'Why did this happen?' expandable section, fix buttons, and an
    'Ignore' control for snoozing non-urgent checks."""

    def __init__(self, result: CheckResult, on_apply_fix, on_snooze_changed=None, parent=None):
        super().__init__(parent)
        self.result = result
        self.on_apply_fix = on_apply_fix
        self.on_snooze_changed = on_snooze_changed
        self.setObjectName("checkCard")
        self.setFrameShape(QFrame.Shape.NoFrame)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(16, 12, 16, 12)

        header_row = QHBoxLayout()
        title = QLabel(result.title)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        header_row.addWidget(title)
        header_row.addStretch()

        text, fg, bg = STATUS_BADGE[result.status]
        badge = QLabel(text)
        badge.setStyleSheet(status_badge_style(fg, bg))
        header_row.addWidget(badge)

        # -- Ignore / snooze control --
        # Urgent (RED) findings, and anything marked force_override by
        # the check itself (e.g. disk space at 95%+), aren't offered an
        # ignore option - they matter too much to hide.
        if result.status != Status.RED and not result.force_override:
            self.ignore_btn = QPushButton()
            self.ignore_btn.setObjectName("ignoreButton")
            self._update_ignore_button_label()
            self.ignore_btn.clicked.connect(self._show_ignore_menu)
            header_row.addWidget(self.ignore_btn)
        else:
            self.ignore_btn = None

        layout.addLayout(header_row)

        snooze_info = snooze.get_snooze_info(result.id)
        if snooze_info is not None:
            note_text = (
                "\U0001F515 Ignored forever - will only reappear if the "
                "situation becomes urgent."
                if snooze_info.kind == "forever" else
                f"\U0001F515 Ignored for now - will reappear in "
                f"{snooze.days_remaining(snooze_info)} day(s), or sooner "
                f"if the situation becomes urgent."
            )
            snooze_note = QLabel(note_text)
            snooze_note.setWordWrap(True)
            snooze_note.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px; font-style: italic;")
            layout.addWidget(snooze_note)

        summary = QLabel(result.summary)
        summary.setWordWrap(True)
        summary.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(summary)

        if result.details:
            details_box = QTextEdit()
            details_box.setReadOnly(True)
            details_box.setPlainText(result.details)
            details_box.setMaximumHeight(110)
            details_box.setStyleSheet(code_box_style_alt())
            layout.addWidget(details_box)

        # -- Why did this happen? (expandable) --
        if result.why:
            self.why_toggle = QPushButton("\U0001F50D Why did this happen?")
            self.why_toggle.setObjectName("whyToggle")
            self.why_toggle.setCheckable(True)
            self.why_toggle.clicked.connect(self._toggle_why)
            layout.addWidget(self.why_toggle)

            self.why_label = QLabel(result.why)
            self.why_label.setWordWrap(True)
            self.why_label.setStyleSheet(
                f"color: {COLORS['text_secondary']}; font-size: 12px; "
                f"background: {COLORS['bg_panel_alt']}; "
                f"border-radius: 6px; padding: 8px;"
            )
            self.why_label.setVisible(False)
            layout.addWidget(self.why_label)
        else:
            self.why_toggle = None
            self.why_label = None

        if result.fixes:
            fixes_label = QLabel("Suggested fixes:")
            fixes_label.setStyleSheet("font-weight: 600; margin-top: 4px; font-size: 12px;")
            layout.addWidget(fixes_label)

            for fix in result.fixes:
                row = QHBoxLayout()
                sev_text, sev_color = {
                    SeverityLevel.SAFE: ("Safe", COLORS["green"]),
                    SeverityLevel.APPROVAL: ("Approval", COLORS["yellow"]),
                    SeverityLevel.ADVANCED: ("Advanced", COLORS["red"]),
                }[fix.severity]

                dot = QLabel("\u25CF")
                dot.setStyleSheet(f"color: {sev_color}; font-size: 12px;")
                row.addWidget(dot)

                fix_label = QLabel(fix.title)
                fix_label.setWordWrap(True)
                row.addWidget(fix_label, stretch=1)

                btn = QPushButton("Review and Apply")
                btn.setObjectName("fixButton")
                btn.clicked.connect(lambda _checked=False, f=fix: self.on_apply_fix(f))
                row.addWidget(btn)

                layout.addLayout(row)

    def _toggle_why(self) -> None:
        if self.why_label is not None:
            self.why_label.setVisible(self.why_toggle.isChecked())

    def _update_ignore_button_label(self) -> None:
        if snooze.is_snoozed(self.result.id):
            self.ignore_btn.setText("Ignored \u25BE")
        else:
            self.ignore_btn.setText("Ignore \u25BE")

    def _show_ignore_menu(self) -> None:
        menu = QMenu(self)
        is_snoozed = snooze.is_snoozed(self.result.id)

        if is_snoozed:
            show_again = menu.addAction("Show me again")
            show_again.triggered.connect(self._unsnooze)
        else:
            week_action = menu.addAction("Ignore for a week")
            week_action.triggered.connect(self._snooze_week)
            forever_action = menu.addAction("Ignore forever")
            forever_action.triggered.connect(self._snooze_forever)

        menu.exec(self.ignore_btn.mapToGlobal(self.ignore_btn.rect().bottomLeft()))

    def _snooze_week(self) -> None:
        snooze.snooze_for_a_week(self.result.id)
        self._update_ignore_button_label()
        if self.on_snooze_changed is not None:
            self.on_snooze_changed()

    def _snooze_forever(self) -> None:
        snooze.snooze_forever(self.result.id)
        self._update_ignore_button_label()
        if self.on_snooze_changed is not None:
            self.on_snooze_changed()

    def _unsnooze(self) -> None:
        snooze.unsnooze(self.result.id)
        self._update_ignore_button_label()
        if self.on_snooze_changed is not None:
            self.on_snooze_changed()


class SentinelPanel(QWidget):
    """Main System Sentinel screen."""

    def __init__(self, mascot: GrixMascot, on_open_lesson=None, on_mood_change=None, parent=None):
        super().__init__(parent)
        self.mascot = mascot
        self.on_open_lesson = on_open_lesson
        self.on_mood_change = on_mood_change
        self.scan_worker: ScanWorker | None = None
        self.fix_worker: FixWorker | None = None
        self.last_results: list[CheckResult] = []
        self.snoozed_results: list[CheckResult] = []

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        # Header
        header = QHBoxLayout()
        title_col = QVBoxLayout()
        title = QLabel("System Sentinel")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        title_col.addWidget(title)

        self.status_label = QLabel(
            "Run a scan and Grix will check your system for common "
            "issues, explain anything it finds, and suggest safe fixes "
            "you can review before anything changes."
        )
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        title_col.addWidget(self.status_label)
        header.addLayout(title_col, stretch=1)

        self.scan_btn = QPushButton("Scan my system")
        self.scan_btn.setObjectName("primaryButton")
        self.scan_btn.setMinimumHeight(40)
        self.scan_btn.clicked.connect(self.start_scan)
        header.addWidget(self.scan_btn, alignment=Qt.AlignmentFlag.AlignTop)

        outer.addLayout(header)

        # Tabs
        self.tabs = QTabWidget()
        outer.addWidget(self.tabs, stretch=1)

        # -- Diagnostics tab --
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 12, 0, 0)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setSpacing(10)
        self.results_layout.setContentsMargins(0, 0, 4, 0)
        self.results_layout.addStretch()
        self.results_scroll.setWidget(self.results_container)
        results_layout.addWidget(self.results_scroll)

        self.empty_label = QLabel(
            "No scan has been run yet. Click \u201cScan my system\u201d to "
            "get started - Grix will only look at your system; nothing "
            "will be changed without your approval."
        )
        self.empty_label.setWordWrap(True)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 40px;")
        self.results_layout.insertWidget(0, self.empty_label)

        self.tabs.addTab(results_widget, "Diagnostics")

        # -- Explain This Error tab --
        self.explain_panel = ExplainErrorPanel(
            on_run_check=self._scroll_to_check,
            on_open_lesson=self.on_open_lesson,
        )
        self.tabs.addTab(self.explain_panel, "Explain This Error")

        # -- System Timeline tab --
        self.timeline_panel = TimelinePanel()
        self.tabs.addTab(self.timeline_panel, "System Timeline")

        # -- History tab --
        history_widget = QWidget()
        history_layout = QVBoxLayout(history_widget)
        history_layout.setContentsMargins(0, 12, 0, 0)

        self.history_list = QListWidget()
        self.history_list.setAlternatingRowColors(True)
        history_layout.addWidget(self.history_list)

        history_btn_row = QHBoxLayout()
        history_btn_row.addStretch()
        clear_history_btn = QPushButton("Clear history")
        clear_history_btn.clicked.connect(self.clear_history)
        history_btn_row.addWidget(clear_history_btn)
        history_layout.addLayout(history_btn_row)

        self.tabs.addTab(history_widget, "Repair History")
        self.tabs.currentChanged.connect(self._on_tab_changed)

        self.refresh_history()

    def _set_mood(self, mood: str, caption: str | None = None) -> None:
        """Update Grix's mascot state and notify any external listener
        (e.g. the system tray icon) of the new mood."""
        self.mascot.set_state(mood, caption)
        if self.on_mood_change is not None:
            self.on_mood_change(mood)

    # -- Scanning -----------------------------------------------------------

    def is_scanning(self) -> bool:
        """Return True if a scan is currently in progress."""
        return not self.scan_btn.isEnabled()

    def scan_finished_once(self, callback) -> None:
        """Connect a one-shot callback to fire when the next scan
        finishes, then auto-disconnect. Used by the auto-scan timer to
        record completion AFTER the scan actually finishes rather than
        before it starts, so a partial or errored scan doesn't
        erroneously reset the schedule clock."""
        def _on_done(results):
            try:
                if self.scan_worker is not None:
                    self.scan_worker.all_finished.disconnect(_on_done)
            except (RuntimeError, TypeError):
                pass  # already disconnected or worker gone
            callback()

        if self.scan_worker is not None and self.scan_worker.isRunning():
            # Scan already in progress - connect to the live worker
            self.scan_worker.all_finished.connect(_on_done)
        else:
            # Scan hasn't started yet (scan_finished_once called just
            # before start_scan) - store the callback and wire it in
            # start_scan() when the worker is created
            if not hasattr(self, '_pending_once_callbacks'):
                self._pending_once_callbacks: list = []
            self._pending_once_callbacks.append(_on_done)

    def start_scan(self) -> None:
        if self.scan_worker is not None and self.scan_worker.isRunning():
            return

        self.scan_btn.setEnabled(False)
        self.scan_btn.setText("Scanning...")
        self._set_mood("study")
        self.status_label.setText("Grix is checking your system for common issues...")

        self.scan_worker = ScanWorker()
        self.scan_worker.all_finished.connect(self._on_scan_finished)

        # Wire in any pending once-callbacks that were registered before
        # the worker existed (i.e. via scan_finished_once() called just
        # before this start_scan() call from the auto-scan timer)
        pending = getattr(self, '_pending_once_callbacks', [])
        for cb in pending:
            self.scan_worker.all_finished.connect(cb)
        self._pending_once_callbacks = []

        self.scan_worker.start()

    def _on_scan_finished(self, results: list[CheckResult]) -> None:
        self.last_results = results
        self.scan_btn.setEnabled(True)
        self.scan_btn.setText("Scan again")

        analytics.record_scan(results)

        # A check stays hidden if the user snoozed it - UNLESS it's
        # currently RED (urgent) or the check itself demands to be shown
        # regardless of snooze status (force_override, e.g. disk space
        # reaching 95% full). This is what stops Grix from nagging about
        # things like disk space or a non-critical failed service once
        # dismissed, while still surfacing anything that's become a
        # genuine emergency.
        #
        # IMPORTANT: this split must happen BEFORE computing the overall
        # mood/status. Grix's mascot, the tray icon, and the headline
        # text should only ever reflect checks the user can currently
        # see - an ignored (snoozed) yellow disk-space check must not
        # keep flagging "attention needed" once it's been dismissed.
        visible_results = []
        snoozed_results = []
        for r in results:
            currently_snoozed = snooze.is_snoozed(r.id)
            if currently_snoozed and r.status != Status.RED and not r.force_override:
                snoozed_results.append(r)
            else:
                visible_results.append(r)
        self.snoozed_results = snoozed_results

        overall = diagnostics.overall_status(visible_results)
        mood = {
            Status.GREEN: "green",
            Status.YELLOW: "yellow",
            Status.RED: "red",
            Status.UNKNOWN: "sleep",
        }[overall]
        self._set_mood(mood)

        issue_count = sum(1 for r in visible_results if r.status in (Status.YELLOW, Status.RED))
        if overall == Status.GREEN:
            if snoozed_results:
                noun = "check" if len(snoozed_results) == 1 else "checks"
                self.status_label.setText(
                    "Everything looks healthy! Grix checked "
                    f"{len(results)} areas and found nothing that needs "
                    f"fixing right now. ({len(snoozed_results)} {noun} "
                    f"currently ignored - see below.)"
                )
            else:
                self.status_label.setText(
                    "Everything looks healthy! Grix checked "
                    f"{len(results)} areas and found nothing that needs "
                    "fixing right now."
                )
        elif overall == Status.UNKNOWN:
            self.status_label.setText(
                "Grix wasn't able to check everything on this system "
                "(some tools may not be installed), but nothing it could "
                "check looks broken."
            )
        elif issue_count == 0:
            # Reachable when every visible result is UNKNOWN/GREEN mixed
            # in a way that overall_status() didn't resolve to GREEN
            # above (e.g. all UNKNOWN) - kept as a clear, honest fallback.
            self.status_label.setText(
                "Nothing needs your attention right now. Some checks may "
                "be ignored below - they'll reappear automatically if "
                "they become urgent."
            )
        else:
            noun = "thing" if issue_count == 1 else "things"
            self.status_label.setText(
                f"Grix found {issue_count} {noun} that could use "
                f"attention. Review each one below - nothing will change "
                f"until you approve a fix."
            )

        # Rebuild result cards
        self.empty_label.setVisible(False)
        # Remove old cards (everything except the stretch and empty label)
        while self.results_layout.count() > 0:
            item = self.results_layout.takeAt(0)
            w = item.widget()
            if w is not None and w is not self.empty_label:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif w is None:
                continue

        # Sort: red first, then yellow, then unknown, then green
        order = {Status.RED: 0, Status.YELLOW: 1, Status.UNKNOWN: 2, Status.GREEN: 3}
        sorted_results = sorted(visible_results, key=lambda r: order[r.status])

        self._check_cards: dict[str, CheckCard] = {}
        for result in sorted_results:
            card = CheckCard(
                result,
                on_apply_fix=self.confirm_and_apply_fix,
                on_snooze_changed=self._on_snooze_changed,
            )
            self.results_layout.addWidget(card)
            self._check_cards[result.id] = card

        if snoozed_results:
            self.results_layout.addWidget(self._build_snoozed_summary(snoozed_results))

        self.results_layout.addStretch()

    def _build_snoozed_summary(self, snoozed_results: list[CheckResult]) -> QFrame:
        """A small expandable summary listing checks currently being
        ignored, each with a 'Show me again' button - so ignoring
        something never means losing track of it entirely."""
        frame = QFrame()
        frame.setObjectName("snoozedSummary")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(6)

        toggle = QPushButton(
            f"\U0001F515 {len(snoozed_results)} check(s) currently ignored \u25BE"
        )
        toggle.setObjectName("whyToggle")
        toggle.setCheckable(True)
        layout.addWidget(toggle)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        body_layout.setContentsMargins(0, 4, 0, 0)
        body_layout.setSpacing(6)

        for result in snoozed_results:
            row = QHBoxLayout()
            label = QLabel(result.title)
            label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            row.addWidget(label, stretch=1)

            info = snooze.get_snooze_info(result.id)
            if info is not None:
                detail_text = (
                    "ignored forever" if info.kind == "forever"
                    else f"{snooze.days_remaining(info)}d left"
                )
                detail = QLabel(detail_text)
                detail.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
                row.addWidget(detail)

            show_btn = QPushButton("Show me again")
            show_btn.setObjectName("fixButton")
            show_btn.clicked.connect(lambda _checked=False, cid=result.id: self._unsnooze_and_refresh(cid))
            row.addWidget(show_btn)

            body_layout.addLayout(row)

        body.setVisible(False)
        layout.addWidget(body)
        toggle.toggled.connect(body.setVisible)

        frame.setStyleSheet(f"""
            #snoozedSummary {{
                background: {COLORS['bg_panel_alt']};
                border-radius: 10px;
                border: 1px dashed {COLORS['border_light']};
            }}
        """)
        return frame

    def _unsnooze_and_refresh(self, check_id: str) -> None:
        snooze.unsnooze(check_id)
        self._on_snooze_changed()

    def _on_snooze_changed(self) -> None:
        """Re-render the results list after a snooze/unsnooze action,
        without re-running the scan itself."""
        if self.last_results:
            self._on_scan_finished(self.last_results)

    def _scroll_to_check(self, check_id: str) -> None:
        """Switch to the Diagnostics tab and scroll to a specific check,
        running a scan first if needed."""
        self.tabs.setCurrentIndex(0)
        if not self.last_results:
            self.start_scan()
            return
        card = getattr(self, "_check_cards", {}).get(check_id)
        if card is not None:
            self.results_scroll.ensureWidgetVisible(card)

    # -- Applying fixes -------------------------------------------------------

    def confirm_and_apply_fix(self, fix: Fix) -> None:
        dialog = FixConfirmDialog(fix, on_open_lesson=self.on_open_lesson, parent=self)
        if dialog.exec() != dialog.DialogCode.Accepted:
            return

        self._set_mood("fix")
        self.status_label.setText(f"Applying: {fix.title}...")
        self.scan_btn.setEnabled(False)

        self.fix_worker = FixWorker(fix, dialog.selected_option_ids)
        self.fix_worker.finished_fix.connect(self._on_fix_finished)
        self.fix_worker.start()

    def _on_fix_finished(self, fix: Fix, success: bool, output: str) -> None:
        self.scan_btn.setEnabled(True)
        history.record_fix(
            fix_id=fix.id,
            title=fix.title,
            commands=fix.commands,
            success=success,
            output=output,
            rollback_hint=fix.rollback_hint,
        )
        if success:
            analytics.record_fix_applied(fix.id)
        self.refresh_history()

        result_dialog = FixResultDialog(
            fix, success, output, on_open_lesson=self.on_open_lesson, parent=self
        )
        result_dialog.exec()

        if result_dialog.open_lesson_requested and fix.related_lesson and self.on_open_lesson:
            self.on_open_lesson(*fix.related_lesson)

        if success:
            self._set_mood("fixed")
            self.status_label.setText(
                f"\u201c{fix.title}\u201d completed. Run a new scan to see "
                f"the updated status."
            )
        else:
            self._set_mood("red")
            self.status_label.setText(
                f"\u201c{fix.title}\u201d did not complete successfully. "
                f"Nothing else was changed."
            )

    # -- History --------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        if index == 3:
            self.refresh_history()

    def refresh_history(self) -> None:
        self.history_list.clear()
        entries = history.load_history()
        if not entries:
            item = QListWidgetItem(
                "No repairs have been applied yet. When Grix fixes "
                "something, it'll be logged here."
            )
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.history_list.addItem(item)
            return

        for entry in reversed(entries):
            status_icon = "\u2705" if entry.success else "\u26A0\ufe0f"
            text = f"{status_icon} {entry.timestamp} \u2014 {entry.title}"
            if entry.rollback_hint:
                text += f"\n     Rollback: {entry.rollback_hint}"
            item = QListWidgetItem(text)
            self.history_list.addItem(item)

    def clear_history(self) -> None:
        reply = QMessageBox.question(
            self, "Clear Repair History",
            "This will permanently delete Grix's repair log. This does "
            "not undo any repairs - it only clears the record. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            history.clear_history()
            self.refresh_history()
