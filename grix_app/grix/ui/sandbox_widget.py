"""
Grix Linux Academy - Sandbox Terminal Widget
================================================

A small terminal-look widget backed by SandboxTerminal (a simulated
filesystem). Used inside lessons for "try it yourself" practice.

Emits command_run(str) every time the user runs a command, so
PracticeBlock instances can check whether it matches the expected
command for that step.
"""

from __future__ import annotations

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QTextCursor, QFont
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QFrame,
)

from ..modules.sandbox import SandboxTerminal
from .theme import COLORS


WELCOME_TEXT = (
    "Grix Sandbox Terminal - a safe, simulated Linux filesystem.\n"
    "Nothing you type here affects your real computer.\n"
    "Type 'help' to see available commands.\n"
)


class SandboxTextEdit(QTextEdit):
    """A QTextEdit that behaves like a simple terminal input line."""

    line_entered = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._input_start = 0

    def keyPressEvent(self, event):  # noqa: N802 (Qt naming)
        cursor = self.textCursor()

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)
            doc = self.toPlainText()
            line = doc[self._input_start:]
            self.line_entered.emit(line)
            return

        if event.key() == Qt.Key.Key_Backspace:
            if cursor.position() <= self._input_start:
                return  # don't delete the prompt
            super().keyPressEvent(event)
            return

        # Prevent editing before the input start (e.g. arrow-key navigation
        # back into old output then typing)
        if cursor.position() < self._input_start:
            cursor.movePosition(QTextCursor.MoveOperation.End)
            self.setTextCursor(cursor)

        super().keyPressEvent(event)

    def write_output(self, text: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        if text:
            self.insertPlainText(text + "\n")

    def write_prompt(self, prompt: str) -> None:
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.setTextCursor(cursor)
        self.insertPlainText(prompt + " ")
        self._input_start = self.textCursor().position()
        self.ensureCursorVisible()


class SandboxWidget(QFrame):
    """Embeddable sandbox terminal with header bar."""

    command_run = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sandboxWidget")
        self.terminal = SandboxTerminal()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(12, 8, 12, 8)
        label = QLabel("\U0001F5A5\ufe0f Sandbox Terminal")
        label.setStyleSheet(f"color: {COLORS['text_primary']}; font-weight: 600; font-size: 12px;")
        header.addWidget(label)
        header.addStretch()

        reset_btn = QPushButton("Reset")
        reset_btn.setStyleSheet(
            f"background: {COLORS['bg_panel_alt']}; color: {COLORS['text_secondary']}; border: none; "
            f"border-radius: 4px; padding: 3px 10px; font-size: 11px;"
        )
        reset_btn.clicked.connect(self.reset)
        header.addWidget(reset_btn)

        header_widget = QWidget()
        header_widget.setLayout(header)
        header_widget.setStyleSheet(f"background: {COLORS['bg_sidebar']};")
        layout.addWidget(header_widget)

        self.output = SandboxTextEdit()
        self.output.setFont(QFont("JetBrains Mono", 11))
        self.output.setStyleSheet(
            f"background: {COLORS['bg_input']}; color: {COLORS['code_text_alt']}; border: none; "
            f"padding: 10px;"
        )
        self.output.setMinimumHeight(160)
        self.output.setMaximumHeight(220)
        self.output.line_entered.connect(self._on_line_entered)
        layout.addWidget(self.output)

        self.setStyleSheet(f"""
            #sandboxWidget {{
                border-radius: 10px;
                border: 1px solid {COLORS['border']};
            }}
        """)

        self._write_welcome()

    def _write_welcome(self) -> None:
        self.output.setPlainText(WELCOME_TEXT)
        self.output.write_prompt(self.terminal.prompt)
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output.setTextCursor(cursor)
        self.output.setFocus()

    def _on_line_entered(self, line: str) -> None:
        self.output.insertPlainText("\n")
        result = self.terminal.run(line)

        if result == "\x1bCLEAR\x1b":
            self.output.clear()
        elif result:
            self.output.write_output(result)

        self.output.write_prompt(self.terminal.prompt)

        stripped = line.strip()
        if stripped:
            self.command_run.emit(stripped)

    def reset(self) -> None:
        self.terminal = SandboxTerminal()
        self._write_welcome()

    def scroll_into_view(self) -> None:
        self.output.ensureCursorVisible()
