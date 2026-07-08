"""
Grix Mascot Widget
====================

Displays the Grix character with the appropriate expression/state:

  icon    - default, idle (sitting on dashboard, nothing happening)
  study   - actively scanning/checking the system
  fix     - user has approved a fix, Grix is working on it
  fixed   - a fix just completed successfully
  green   - overall system health is good
  yellow  - overall system health needs non-urgent attention
  red     - overall system health needs immediate attention
  sleep   - idle / no scan run yet, or app just opened
"""

from __future__ import annotations

import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import QLabel, QVBoxLayout, QWidget

ASSET_DIR = os.path.join(os.path.dirname(__file__), "..", "assets")

STATE_FILES = {
    "icon": "grix_icon.png",
    "study": "grix_study.png",
    "fix": "grix_fix.png",
    "fixed": "grix_fixed.png",
    "green": "grix_green.png",
    "yellow": "grix_yellow.png",
    "red": "grix_red.png",
    "sleep": "grix_sleep.png",
}

STATE_CAPTIONS = {
    "icon": "Hi! I'm Grix.",
    "study": "Checking your system...",
    "fix": "Working on it!",
    "fixed": "All done!",
    "green": "Everything looks healthy.",
    "yellow": "A few things could use attention.",
    "red": "Something needs your attention.",
    "sleep": "Ready when you are.",
}


class GrixMascot(QWidget):
    """A widget showing Grix's current mood plus an optional caption."""

    def __init__(self, size: int = 160, show_caption: bool = True, parent=None):
        super().__init__(parent)
        self._size = size
        self._pixmaps: dict[str, QPixmap] = {}
        self._load_pixmaps()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.image_label)

        self.caption_label = None
        if show_caption:
            self.caption_label = QLabel()
            self.caption_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.caption_label.setObjectName("grixCaption")
            self.caption_label.setWordWrap(True)
            self.caption_label.setMaximumWidth(self._size + 40)
            layout.addWidget(self.caption_label)

        self.set_state("sleep")

    def _load_pixmaps(self) -> None:
        for state, filename in STATE_FILES.items():
            path = os.path.join(ASSET_DIR, filename)
            pix = QPixmap(path)
            if not pix.isNull():
                pix = pix.scaled(
                    self._size, self._size,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            self._pixmaps[state] = pix

    def set_state(self, state: str, caption: str | None = None) -> None:
        if state not in self._pixmaps:
            state = "sleep"
        pix = self._pixmaps.get(state)
        if pix is not None and not pix.isNull():
            self.image_label.setPixmap(pix)
        if self.caption_label is not None:
            self.caption_label.setText(caption or STATE_CAPTIONS.get(state, ""))

    def sizeHint(self) -> QSize:  # noqa: N802 (Qt naming)
        extra = 30 if self.caption_label else 0
        return QSize(self._size, self._size + extra)
