"""
Grix Dashboard
================

The landing screen: Grix mascot, a quick summary of the last scan
(if any), and quick links into System Sentinel and Linux Academy.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
)

from ..modules import diagnostics, history, progress
from ..modules import lessons as lessons_module
from .mascot import GrixMascot
from .theme import COLORS


class DashboardPanel(QWidget):
    def __init__(self, mascot: GrixMascot, on_navigate, parent=None):
        super().__init__(parent)
        self.mascot = mascot
        self.on_navigate = on_navigate

        outer = QVBoxLayout(self)
        outer.setContentsMargins(32, 32, 32, 32)
        outer.setSpacing(24)
        outer.setAlignment(Qt.AlignmentFlag.AlignTop)

        # Big mascot + greeting
        top_row = QHBoxLayout()
        top_row.setSpacing(24)

        self.big_mascot = GrixMascot(size=180, show_caption=True)
        top_row.addWidget(self.big_mascot)

        greeting_col = QVBoxLayout()
        greeting_col.setSpacing(8)
        title = QLabel("Hi, I'm Grix!")
        title.setStyleSheet("font-size: 26px; font-weight: 800;")
        greeting_col.addWidget(title)

        self.greeting_text = QLabel()
        self.greeting_text.setWordWrap(True)
        self.greeting_text.setStyleSheet(f"font-size: 14px; color: {COLORS['text_secondary']};")
        greeting_col.addWidget(self.greeting_text)

        greeting_col.addStretch()
        top_row.addLayout(greeting_col, stretch=1)
        outer.addLayout(top_row)

        # Two cards: System Sentinel / Linux Academy
        cards_row = QHBoxLayout()
        cards_row.setSpacing(16)

        self.sentinel_card = self._make_card(
            icon="\U0001F6E1\ufe0f",
            title="System Sentinel",
            body=(
                "Run a health check on your system. Grix will explain "
                "anything it finds and suggest safe fixes you can review "
                "before anything changes."
            ),
            button_text="Open System Sentinel",
            on_click=lambda: self.on_navigate("sentinel"),
        )
        cards_row.addWidget(self.sentinel_card)

        self.academy_card = self._make_card(
            icon="\U0001F393",
            title="Linux Academy",
            body=(
                "Learn Linux from the ground up - the terminal, the "
                "filesystem, permissions, and more - with a safe sandbox "
                "to practice in."
            ),
            button_text="Open Linux Academy",
            on_click=lambda: self.on_navigate("academy"),
        )
        cards_row.addWidget(self.academy_card)

        outer.addLayout(cards_row)
        outer.addStretch()

        self.refresh()

    def _make_card(self, icon: str, title: str, body: str, button_text: str, on_click) -> QFrame:
        card = QFrame()
        card.setObjectName("dashCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(10)

        icon_label = QLabel(icon)
        icon_label.setStyleSheet("font-size: 32px;")
        layout.addWidget(icon_label)

        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 17px; font-weight: 700;")
        layout.addWidget(title_label)

        body_label = QLabel(body)
        body_label.setWordWrap(True)
        body_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(body_label)

        layout.addStretch()

        status_label = QLabel()
        status_label.setObjectName("cardStatus")
        status_label.setWordWrap(True)
        status_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 12px; font-style: italic;")
        layout.addWidget(status_label)
        card.status_label = status_label  # type: ignore[attr-defined]

        btn = QPushButton(button_text)
        btn.setObjectName("primaryButton")
        btn.clicked.connect(on_click)
        layout.addWidget(btn)

        card.setStyleSheet(f"""
            #dashCard {{
                background: {COLORS['bg_panel']};
                border-radius: 12px;
                border: 1px solid {COLORS['border']};
            }}
        """)
        return card

    def refresh(self) -> None:
        """Refresh greeting text and card statuses based on saved state."""
        entries = history.load_history()
        if entries:
            last = entries[-1]
            self.greeting_text.setText(
                f"Last repair: \u201c{last.title}\u201d on {last.timestamp}. "
                f"Run a new scan any time to check for new issues, or "
                f"continue your Linux lessons below."
            )
            self.mascot.set_state("fixed" if last.success else "yellow")
        else:
            self.greeting_text.setText(
                "I help keep your Linux system healthy and help you learn "
                "how it all works. Run a scan with System Sentinel, or "
                "start learning with Linux Academy - whichever you'd "
                "like first!"
            )
            self.mascot.set_state("sleep")

        # Sentinel card status
        if entries:
            success_count = sum(1 for e in entries if e.success)
            self.sentinel_card.status_label.setText(
                f"{success_count} fix(es) applied so far."
            )
        else:
            self.sentinel_card.status_label.setText("No scan run yet.")

        # Academy card status
        total = lessons_module.total_lesson_count()
        done = progress.completed_count()
        self.academy_card.status_label.setText(
            f"{done} of {total} lessons completed."
        )
