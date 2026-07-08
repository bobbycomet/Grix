"""
Grix System Sentinel - System Timeline Panel
================================================

"Your system was healthy yesterday. What changed?"

Shows a combined, time-sorted view of recent package changes, boots,
and journal errors (modules/timeline.py), and highlights cases where
an error appeared shortly after a package change - presented as a
possible correlation, not a confirmed cause.

Entirely read-only.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
    QScrollArea, QComboBox,
)

from ..modules import timeline as timeline_module
from .workers_timeline import TimelineWorker
from .theme import COLORS


KIND_STYLE = {
    "package": ("\U0001F4E6", COLORS["accent"], COLORS["bg_panel_alt"]),
    "error": ("\u26A0\ufe0f", COLORS["red"], COLORS["red_bg"]),
    "boot": ("\U0001F50C", COLORS["green"], COLORS["green_bg"]),
}


class TimelinePanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.worker: TimelineWorker | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        intro = QLabel(
            "\u201cMy system was fine yesterday - what changed?\u201d Grix "
            "builds a timeline from your package history and recent "
            "system errors so you can see what happened, and when. "
            "This is read-only - nothing here changes your system."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(intro)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("Show the last:"))
        self.range_combo = QComboBox()
        self.range_combo.addItems(["24 hours", "3 days", "7 days", "14 days", "30 days"])
        self.range_combo.setCurrentIndex(2)
        controls.addWidget(self.range_combo)

        refresh_btn = QPushButton("Build timeline")
        refresh_btn.setObjectName("primaryButton")
        refresh_btn.clicked.connect(self.build_timeline)
        controls.addWidget(refresh_btn)
        controls.addStretch()
        layout.addLayout(controls)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setSpacing(8)
        self.container_layout.setContentsMargins(0, 0, 4, 0)
        self.container_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll, stretch=1)

        self._show_placeholder(
            "Click \u201cBuild timeline\u201d to see recent package "
            "changes, reboots, and system errors."
        )

    def _days_for_range(self) -> int:
        return {0: 1, 1: 3, 2: 7, 3: 14, 4: 30}[self.range_combo.currentIndex()]

    def _clear(self) -> None:
        while self.container_layout.count() > 0:
            item = self.container_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _show_placeholder(self, text: str) -> None:
        self._clear()
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 30px;")
        self.container_layout.insertWidget(0, label)

    def build_timeline(self) -> None:
        if self.worker is not None and self.worker.isRunning():
            return
        self._show_placeholder("Building timeline...")
        self.worker = TimelineWorker(self._days_for_range())
        self.worker.finished_timeline.connect(self._on_timeline_ready)
        self.worker.start()

    def _on_timeline_ready(self, events: list, correlations: list) -> None:
        self._clear()

        if not events:
            self._show_placeholder(
                "Grix couldn't find any package history or error logs to "
                "build a timeline from. This can happen on systems where "
                "/var/log/apt isn't available, or where there simply "
                "haven't been any changes or errors in this time range."
            )
            return

        self.container_layout.addStretch()

        # Add event rows first
        for event in events:
            row = self._make_event_row(event)
            self.container_layout.insertWidget(self.container_layout.count() - 1, row)

        # Then insert the correlation summary above everything
        if correlations:
            corr_frame = QFrame()
            corr_frame.setObjectName("correlationFrame")
            corr_layout = QVBoxLayout(corr_frame)
            corr_layout.setContentsMargins(14, 12, 14, 12)
            corr_layout.setSpacing(6)

            corr_title = QLabel("\U0001F50D Possible connections")
            corr_title.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {COLORS['accent']};")
            corr_layout.addWidget(corr_title)

            corr_note = QLabel(
                "These errors appeared shortly after a package change. "
                "This doesn't prove the update caused the problem - but "
                "it's often a good place to start looking."
            )
            corr_note.setWordWrap(True)
            corr_note.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            corr_layout.addWidget(corr_note)

            for err, nearby in correlations[:5]:
                pkg_titles = ", ".join(p.title for p in nearby[:3])
                line = QLabel(
                    f"\u2022 <b>{err.timestamp.strftime('%b %d %H:%M')}</b> "
                    f"\u2014 {err.title}<br>"
                    f"&nbsp;&nbsp;&nbsp;possibly related to: {pkg_titles}"
                )
                line.setWordWrap(True)
                line.setTextFormat(Qt.TextFormat.RichText)
                line.setStyleSheet(f"font-size: 12px; color: {COLORS['text_secondary']};")
                corr_layout.addWidget(line)

            self.container_layout.insertWidget(0, corr_frame)

    def _make_event_row(self, event) -> QFrame:
        icon, fg, bg = KIND_STYLE.get(event.kind, ("\u2022", COLORS["text_muted"], COLORS["bg_panel_alt"]))

        frame = QFrame()
        frame.setObjectName("timelineRow")
        layout = QHBoxLayout(frame)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet(
            f"background: {bg}; color: {fg}; border-radius: 6px; "
            f"padding: 4px 8px; font-size: 13px;"
        )
        layout.addWidget(icon_label)

        text_col = QVBoxLayout()
        text_col.setSpacing(2)

        time_label = QLabel(event.timestamp.strftime("%a %b %d, %H:%M"))
        time_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
        text_col.addWidget(time_label)

        title_label = QLabel(event.title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-size: 13px; color: {COLORS['text_primary']};")
        text_col.addWidget(title_label)

        layout.addLayout(text_col, stretch=1)

        return frame
