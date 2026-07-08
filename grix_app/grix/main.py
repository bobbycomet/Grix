#!/usr/bin/env python3
"""
Grix - Linux System Sentinel & Academy
==========================================

Entry point. Launches the PyQt6 application with:
  - A Steam-inspired dark palette applied globally before any windows open
  - A system tray icon that shows Grix's current health state at a glance
  - A right-click tray menu for quick scan, show/hide, and quit
"""

from __future__ import annotations

import os
import sys

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QIcon, QPixmap
from PyQt6.QtWidgets import (
    QApplication, QSystemTrayIcon, QMenu,
)

from .ui.main_window import MainWindow
from .ui.mascot import ASSET_DIR, STATE_FILES
from .ui.theme import apply_theme, GLOBAL_STYLESHEET
from .modules import schedule as schedule_module


def _load_tray_icon(state: str = "icon") -> QIcon:
    """Load a mascot image as a tray icon, falling back to a plain icon."""
    filename = STATE_FILES.get(state, STATE_FILES["icon"])
    path = os.path.join(ASSET_DIR, filename)
    pix = QPixmap(path)
    if not pix.isNull():
        # Scale to a typical tray icon size
        pix = pix.scaled(
            48, 48,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        return QIcon(pix)
    return QIcon()


class GrixApplication:
    """Ties together the QApplication, main window, and system tray icon."""

    def __init__(self, argv: list[str]):
        self.app = QApplication(argv)
        self.app.setApplicationName("Grix")
        self.app.setApplicationDisplayName("Grix")
        self.app.setStyle("Fusion")

        # Apply dark palette and stylesheet at the application level so
        # every top-level window (main window, dialogs, popups) inherits
        # consistent theming automatically - not just the main window.
        apply_theme(self.app)
        self.app.setStyleSheet(GLOBAL_STYLESHEET)

        # Don't quit when the last window is closed - stay in tray instead
        self.app.setQuitOnLastWindowClosed(False)

        # Build the tray icon first so it exists before the window does
        # anything that might want to update it
        self.tray = self._build_tray()
        self.tray.show()

        # Build the main window, wiring mood changes through to the tray
        self.window = MainWindow(on_mood_change=self._update_tray_state)

        win_icon_path = os.path.join(ASSET_DIR, "grix_icon.png")
        if os.path.exists(win_icon_path):
            self.window.setWindowIcon(QIcon(win_icon_path))

        # Keep the app running in the tray when the window is closed
        # (rather than quit), by intercepting the close event.
        self.window.closeEvent = self._on_window_close_event

        # Auto-scan timer: fires every 60 seconds, checks whether a
        # scheduled scan is due (per the user's schedule in Settings →
        # Auto-Scan Schedule), and runs a silent background scan if so.
        # The scan button and manual tray Quick Scan are completely
        # unaffected - this only *adds* background scanning on top of
        # them. Using 60-second resolution means the actual scan fires
        # within one minute of the scheduled time, which is more than
        # precise enough for any of the supported schedule modes.
        self._schedule_timer = QTimer(self.app)
        self._schedule_timer.setInterval(60_000)  # 1 minute in ms
        self._schedule_timer.timeout.connect(self._check_auto_scan)
        self._schedule_timer.start()

    # -- Tray icon -----------------------------------------------------------

    def _build_tray(self) -> QSystemTrayIcon:
        tray = QSystemTrayIcon(self.app)
        tray.setIcon(_load_tray_icon("sleep"))
        tray.setToolTip("Grix - System Sentinel")

        menu = QMenu()

        show_action = menu.addAction("Show Grix")
        show_action.triggered.connect(self._show_window)

        menu.addSeparator()

        scan_action = menu.addAction("Quick Scan")
        scan_action.triggered.connect(self._quick_scan)

        menu.addSeparator()

        quit_action = menu.addAction("Quit Grix")
        quit_action.triggered.connect(self.app.quit)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)

        return tray

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single-click: toggle window visibility
            if self.window.isVisible():
                self.window.hide()
            else:
                self._show_window()

    def _on_window_close_event(self, event) -> None:
        """Closing the main window hides it to the tray rather than
        quitting the application, so the tray icon (and its at-a-glance
        health state) remains available. Use 'Quit Grix' from the tray
        menu to actually exit."""
        event.ignore()
        self.window.hide()
        if not getattr(self, "_shown_tray_hint", False):
            self.tray.showMessage(
                "Grix",
                "Grix is still running in the system tray. Right-click "
                "the tray icon to quit.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )
            self._shown_tray_hint = True

    def _show_window(self) -> None:
        self.window.show()
        self.window.raise_()
        self.window.activateWindow()

    def _quick_scan(self) -> None:
        """Show the app on the Sentinel tab and start a scan."""
        self._show_window()
        self.window.navigate("sentinel")
        # Delay slightly so the window is drawn before the scan starts
        QTimer.singleShot(200, self.window.sentinel_panel.start_scan)

    def _check_auto_scan(self) -> None:
        """Called once per minute by the schedule timer. Runs a silent
        background scan if the user's auto-scan schedule says one is due.

        'Silent' means: the window is NOT shown or raised, the scan
        runs in the background, and the mascot / tray icon update as
        normal when results come in. The user only gets interrupted
        if the results change the mood (the tray icon updates as usual).

        If a manual scan is already in progress when this fires, we
        skip - there's no point running two scans simultaneously, and
        the manual one will update the result just as well.
        """
        sched = schedule_module.load()
        if not schedule_module.is_scan_due(sched):
            return
        if self.window.sentinel_panel.is_scanning():
            # Manual scan already in progress - count it as our scheduled
            # scan so the timer doesn't re-fire next minute.
            schedule_module.record_scan_ran()
            return
        # Hook into the scan-finished signal to record completion AFTER
        # the scan actually finishes, not before - so a partial or failed
        # scan doesn't erroneously reset the clock.
        sentinel = self.window.sentinel_panel
        sentinel.scan_finished_once(schedule_module.record_scan_ran)
        # Run a background scan: don't show or raise the window.
        sentinel.start_scan()

    def _update_tray_state(self, state: str) -> None:
        """Change the tray icon to reflect the latest scan result mood."""
        self.tray.setIcon(_load_tray_icon(state))
        tooltips = {
            "green": "Grix - System is healthy",
            "yellow": "Grix - Some things need attention",
            "red": "Grix - Urgent issues detected",
            "sleep": "Grix - No scan run yet",
            "study": "Grix - Scanning...",
            "fixed": "Grix - Fix applied",
        }
        self.tray.setToolTip(tooltips.get(state, "Grix"))
        if state == "red":
            self.tray.showMessage(
                "Grix - Urgent",
                "System Sentinel found issues that need your attention.",
                QSystemTrayIcon.MessageIcon.Warning,
                4000,
            )
        elif state == "yellow":
            self.tray.showMessage(
                "Grix",
                "Scan complete. A few things could use attention.",
                QSystemTrayIcon.MessageIcon.Information,
                3000,
            )

    def run(self) -> int:
        self.window.show()
        return self.app.exec()


def main() -> int:
    grix = GrixApplication(sys.argv)
    return grix.run()


if __name__ == "__main__":
    sys.exit(main())
