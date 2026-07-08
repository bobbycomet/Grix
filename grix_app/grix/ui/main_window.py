"""
Grix - Main Window
====================

Sidebar navigation between Dashboard, System Sentinel, Linux Academy,
and Settings, all sharing one Grix mascot instance whose mood reflects
whatever the active panel is doing.

Also wires up the "Learn about this" / "Learn from this repair"
pipeline: System Sentinel can ask the main window to jump to a
specific Linux Academy lesson, which switches both the page and the
selected lesson.
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QPushButton,
    QStackedWidget, QLabel, QFrame,
)

from .mascot import GrixMascot, ASSET_DIR
from .dashboard import DashboardPanel
from .sentinel import SentinelPanel
from .academy import AcademyPanel
from .settings_panel import SettingsPanel
from .theme import COLORS, GLOBAL_STYLESHEET
from ..modules import plugins


NAV_ITEMS = [
    ("dashboard", "\U0001F3E0  Dashboard"),
    ("sentinel", "\U0001F6E1\ufe0f  System Sentinel"),
    ("academy", "\U0001F393  Linux Academy"),
    ("settings", "\u2699\ufe0f  Settings"),
]


class MainWindow(QMainWindow):
    def __init__(self, on_mood_change=None):
        super().__init__()
        self.setWindowTitle("Grix")
        self.setMinimumSize(1000, 680)
        self.on_mood_change = on_mood_change

        icon_path = os.path.join(ASSET_DIR, "grix_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Shared mascot instance shown in the sidebar
        self.sidebar_mascot = GrixMascot(size=96, show_caption=True)

        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # -- Sidebar --
        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(16, 24, 16, 24)
        sidebar_layout.setSpacing(8)

        sidebar_layout.addWidget(self.sidebar_mascot, alignment=Qt.AlignmentFlag.AlignHCenter)

        app_name = QLabel("Grix")
        app_name.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        app_name.setStyleSheet("font-size: 20px; font-weight: 800; margin: 8px 0 16px 0;")
        sidebar_layout.addWidget(app_name)

        self.nav_buttons: dict[str, QPushButton] = {}
        self._nav_button_box = sidebar_layout  # so plugin panels can append below

        for key, label in NAV_ITEMS:
            self._add_nav_button(sidebar_layout, key, label)

        self._nav_stretch_index = sidebar_layout.count()
        sidebar_layout.addStretch()

        footer = QLabel("Griffin Linux Suite")
        footer.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        footer.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        sidebar_layout.addWidget(footer)

        root_layout.addWidget(sidebar)

        # -- Main content stack --
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack, stretch=1)

        self.dashboard_panel = DashboardPanel(self.sidebar_mascot, on_navigate=self.navigate)
        self.academy_panel = AcademyPanel(self.sidebar_mascot)
        self.sentinel_panel = SentinelPanel(
            self.sidebar_mascot,
            on_open_lesson=self.open_lesson,
            on_mood_change=self.on_mood_change,
        )
        self.settings_panel = SettingsPanel()

        self._panel_index: dict[str, int] = {}
        for key, panel in [
            ("dashboard", self.dashboard_panel),
            ("sentinel", self.sentinel_panel),
            ("academy", self.academy_panel),
            ("settings", self.settings_panel),
        ]:
            self._panel_index[key] = self.stack.addWidget(panel)

        self._load_plugin_panels()

        self.navigate("dashboard")
        self._apply_styles()

    def _add_nav_button(self, sidebar_layout: QVBoxLayout, key: str, label: str) -> None:
        btn = QPushButton(label)
        btn.setObjectName("navButton")
        btn.setCheckable(True)
        btn.setMinimumHeight(42)
        btn.clicked.connect(lambda _checked=False, k=key: self.navigate(k))
        sidebar_layout.insertWidget(getattr(self, "_nav_stretch_index", sidebar_layout.count()), btn)
        self.nav_buttons[key] = btn

    def _load_plugin_panels(self) -> None:
        """Add a nav button + stack entry for every panel a plugin
        registered via PluginAPI.register_panel(). A panel whose
        factory raises is skipped (logged to stderr) rather than
        taking down the rest of the window - the same defensive
        posture as plugin checks and lesson tracks."""
        try:
            registry = plugins.get_plugin_registry()
        except Exception:
            return

        for spec in registry.panels:
            if spec.key in self._panel_index:
                continue  # a built-in (or earlier plugin) already owns this key
            try:
                widget = spec.factory()
            except Exception as exc:  # pragma: no cover - defensive
                print(f"Grix: plugin panel '{spec.key}' failed to load: {exc}")
                continue
            self._add_nav_button(self._nav_button_box, spec.key, spec.label)
            self._panel_index[spec.key] = self.stack.addWidget(widget)

    def navigate(self, key: str) -> None:
        index = self._panel_index.get(key, 0)
        self.stack.setCurrentIndex(index)
        for k, btn in self.nav_buttons.items():
            btn.setChecked(k == key)
        if key == "dashboard":
            self.dashboard_panel.refresh()
        elif key == "settings":
            self.settings_panel.refresh()

    def open_lesson(self, track_id: str, lesson_id: str) -> None:
        """Navigate to Linux Academy and open a specific lesson - used by
        System Sentinel's 'Learn about this' / 'Learn from this repair'
        links."""
        self.navigate("academy")
        self.academy_panel.open_lesson(track_id, lesson_id)

    def _apply_styles(self) -> None:
        self.setStyleSheet(GLOBAL_STYLESHEET)
