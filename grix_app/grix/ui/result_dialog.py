"""
Grix System Sentinel - Fix Result Dialog
============================================

Shown after a fix has been applied. Reports success or failure,
shows the raw command output for transparency, and - if successful
and a related lesson exists - offers a "Learn from this repair" link
into Linux Academy.
"""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
)

from ..modules.diagnostics import Fix
from ..ui.mascot import GrixMascot
from .theme import COLORS, code_box_style


class FixResultDialog(QDialog):
    """If `on_open_lesson` is provided and `fix.related_lesson` is set,
    shows a "Learn from this repair" button. Sets
    `self.open_lesson_requested` to True if the user clicked it, so the
    caller can navigate after this dialog closes."""

    def __init__(self, fix: Fix, success: bool, output: str,
                 on_open_lesson=None, parent=None):
        super().__init__(parent)
        self.fix = fix
        self.on_open_lesson = on_open_lesson
        self.open_lesson_requested = False

        self.setWindowTitle("Fix Result")
        self.setMinimumWidth(480)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        top_row = QHBoxLayout()
        mascot = GrixMascot(size=80, show_caption=False)
        mascot.set_state("fixed" if success else "red")
        top_row.addWidget(mascot)

        text_col = QVBoxLayout()
        header = QLabel("Fixed!" if success else "Something went wrong")
        header.setStyleSheet("font-size: 18px; font-weight: 700;")
        text_col.addWidget(header)

        sub = QLabel(
            f"\u201c{fix.title}\u201d completed successfully."
            if success else
            f"Grix tried to apply \u201c{fix.title}\u201d but it didn't "
            f"complete successfully. Nothing further was changed."
        )
        sub.setWordWrap(True)
        text_col.addWidget(sub)
        top_row.addLayout(text_col)
        layout.addLayout(top_row)

        if output.strip():
            out_label = QLabel("Details:")
            out_label.setStyleSheet("font-weight: 600;")
            layout.addWidget(out_label)

            out_box = QTextEdit()
            out_box.setReadOnly(True)
            out_box.setPlainText(output.strip())
            out_box.setStyleSheet(code_box_style())
            out_box.setMinimumHeight(140)
            layout.addWidget(out_box)

        # -- Learn from this repair --
        if success and fix.related_lesson and self.on_open_lesson:
            learn_frame_layout = QHBoxLayout()
            prompt = QLabel("Want to understand what just happened?")
            prompt.setWordWrap(True)
            prompt.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
            learn_frame_layout.addWidget(prompt, stretch=1)

            learn_btn = QPushButton("\U0001F393 Learn about this")
            learn_btn.setObjectName("learnButton")
            learn_btn.clicked.connect(self._on_learn_clicked)
            learn_frame_layout.addWidget(learn_btn)
            layout.addLayout(learn_frame_layout)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.setObjectName("primaryButton")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)

    def _on_learn_clicked(self) -> None:
        self.open_lesson_requested = True
        self.accept()
