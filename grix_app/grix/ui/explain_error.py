"""
Grix System Sentinel - "Explain This Error" Panel
======================================================

Lets users paste an error message (from a terminal, log file, or
crash dialog) and get a plain-language explanation, diagnosis steps,
and links to related System Sentinel checks or Academy lessons.

This panel never runs commands - it only matches the pasted text
against a local knowledge base (modules/error_explainer.py).
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit,
    QFrame, QScrollArea,
)

from ..modules import error_explainer
from ..modules.error_explainer import SCOPE_CATEGORIES, SCOPE_EXCLUSIONS
from .theme import COLORS


class ExplainErrorPanel(QWidget):
    """Paste-an-error panel. `on_run_check` is called with a check id
    when the user wants to jump to that diagnostic; `on_open_lesson`
    with (track_id, lesson_id) for the related lesson."""

    def __init__(self, on_run_check=None, on_open_lesson=None, parent=None):
        super().__init__(parent)
        self.on_run_check = on_run_check
        self.on_open_lesson = on_open_lesson

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 12, 0, 0)
        layout.setSpacing(12)

        intro = QLabel(
            "Paste an error message below - from a terminal, a log file, "
            "or a crash dialog - and Grix will explain what it likely "
            "means and suggest next steps. Grix only reads the text you "
            "paste here; nothing is run automatically.\n\n"
            "This works from a knowledge base of common Linux system "
            "errors (package management, permissions, disk space, "
            "networking, services, and shell basics) - not a general AI "
            "assistant, so it won't recognize app-specific bugs, "
            "programming errors, or hardware failures. See \u201cWhat "
            "does this recognize?\u201d below for the full picture."
        )
        intro.setWordWrap(True)
        intro.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(intro)

        self.scope_toggle = QPushButton("\u2139\ufe0f What does this recognize? \u25BE")
        self.scope_toggle.setObjectName("whyToggle")
        self.scope_toggle.setCheckable(True)
        self.scope_toggle.toggled.connect(self._toggle_scope)
        layout.addWidget(self.scope_toggle)

        self.scope_panel = self._build_scope_panel()
        self.scope_panel.setVisible(False)
        layout.addWidget(self.scope_panel)

        self.input_box = QTextEdit()
        self.input_box.setPlaceholderText(
            "e.g. E: Unable to correct problems, you have held broken packages."
        )
        self.input_box.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; font-size: 12px; "
            f"background: {COLORS['bg_input']}; color: {COLORS['code_text_alt']}; "
            f"border-radius: 8px; padding: 10px;"
        )
        self.input_box.setFixedHeight(110)
        layout.addWidget(self.input_box)

        btn_row = QHBoxLayout()
        explain_btn = QPushButton("Explain this error")
        explain_btn.setObjectName("primaryButton")
        explain_btn.clicked.connect(self._on_explain)
        btn_row.addWidget(explain_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(clear_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        self.result_scroll = QScrollArea()
        self.result_scroll.setWidgetResizable(True)
        self.result_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.result_container = QWidget()
        self.result_layout = QVBoxLayout(self.result_container)
        self.result_layout.setSpacing(10)
        self.result_layout.setContentsMargins(0, 0, 4, 0)
        self.result_layout.addStretch()
        self.result_scroll.setWidget(self.result_container)
        layout.addWidget(self.result_scroll, stretch=1)

        self._show_placeholder()

    def _build_scope_panel(self) -> QFrame:
        """A collapsible reference listing what categories of errors
        this knowledge base recognizes, and what it explicitly doesn't -
        so a no-match result is understandable rather than mysterious."""
        panel = QFrame()
        panel.setObjectName("explainCard")
        panel_layout = QVBoxLayout(panel)
        panel_layout.setContentsMargins(16, 12, 16, 12)
        panel_layout.setSpacing(10)

        covers_title = QLabel("Recognizes errors about:")
        covers_title.setStyleSheet("font-weight: 700; font-size: 13px;")
        panel_layout.addWidget(covers_title)

        for name, desc in SCOPE_CATEGORIES:
            row = QLabel(f"\u2022 <b>{name}</b> - {desc}")
            row.setWordWrap(True)
            row.setTextFormat(Qt.TextFormat.RichText)
            row.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            panel_layout.addWidget(row)

        panel_layout.addSpacing(8)

        excludes_title = QLabel("Out of scope (Grix will say so rather than guess):")
        excludes_title.setWordWrap(True)
        excludes_title.setStyleSheet(f"font-weight: 700; font-size: 13px; color: {COLORS['yellow']};")
        panel_layout.addWidget(excludes_title)

        for desc in SCOPE_EXCLUSIONS:
            row = QLabel(f"\u2022 {desc}")
            row.setWordWrap(True)
            row.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            panel_layout.addWidget(row)

        return panel

    def _toggle_scope(self, checked: bool) -> None:
        self.scope_panel.setVisible(checked)
        self.scope_toggle.setText(
            ("\u2139\ufe0f What does this recognize? \u25B4") if checked
            else ("\u2139\ufe0f What does this recognize? \u25BE")
        )

    def _clear_results(self) -> None:
        while self.result_layout.count() > 0:
            item = self.result_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _show_placeholder(self) -> None:
        self._clear_results()
        placeholder = QLabel(
            "Paste an error message above and click \u201cExplain this "
            "error\u201d to get started."
        )
        placeholder.setWordWrap(True)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setStyleSheet(f"color: {COLORS['text_muted']}; padding: 30px;")
        self.result_layout.insertWidget(0, placeholder)

    def _on_clear(self) -> None:
        self.input_box.clear()
        self._show_placeholder()

    def _on_explain(self) -> None:
        text = self.input_box.toPlainText().strip()
        self._clear_results()

        if not text:
            self._show_placeholder()
            return

        explanation = error_explainer.explain(text)

        if explanation is None:
            no_match = QLabel(
                "Grix doesn't recognize this specific message. This "
                "could mean it's a known category Grix just hasn't "
                "learned the exact wording for yet, or it could be "
                "outside Grix's scope entirely - things like an "
                "individual app's internal bug, a programming error, or "
                "a hardware failure aren't something a system "
                "troubleshooting knowledge base can responsibly "
                "diagnose. Check \u201cWhat does this recognize?\u201d "
                "above for the full picture.\n\n"
                "A few general next steps that often help regardless:\n\n"
                "\u2022 Search for the exact error text (in quotes) - "
                "someone else has often hit the same issue.\n"
                "\u2022 Check System Sentinel's Diagnostics tab - many "
                "common problems show up there with explanations and "
                "fixes.\n"
                "\u2022 Check recent logs around when this happened with "
                "journalctl -b, or use the System Timeline tab to see "
                "what changed recently."
            )
            no_match.setWordWrap(True)
            no_match.setStyleSheet(f"color: {COLORS['text_secondary']}; padding: 16px; font-size: 13px;")
            self.result_layout.insertWidget(0, no_match)
            return

        card = QFrame()
        card.setObjectName("explainCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        title = QLabel(explanation.title)
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        title.setWordWrap(True)
        card_layout.addWidget(title)

        body = QLabel(explanation.explanation)
        body.setWordWrap(True)
        body.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        card_layout.addWidget(body)

        if explanation.diagnosis_steps:
            steps_title = QLabel("Suggested next steps:")
            steps_title.setStyleSheet("font-weight: 600; margin-top: 4px; font-size: 13px;")
            card_layout.addWidget(steps_title)

            steps_html = "<ol style='margin:4px 0 0 -18px;'>" + "".join(
                f"<li style='margin-bottom:4px;'>{step}</li>"
                for step in explanation.diagnosis_steps
            ) + "</ol>"
            steps_label = QLabel(steps_html)
            steps_label.setWordWrap(True)
            steps_label.setTextFormat(Qt.TextFormat.RichText)
            steps_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
            card_layout.addWidget(steps_label)

        action_row = QHBoxLayout()
        if explanation.related_check_id and self.on_run_check:
            run_btn = QPushButton("\U0001F6E1\ufe0f Run this check in System Sentinel")
            run_btn.setObjectName("learnButton")
            run_btn.clicked.connect(
                lambda: self.on_run_check(explanation.related_check_id)
            )
            action_row.addWidget(run_btn)

        if explanation.related_lesson and self.on_open_lesson:
            learn_btn = QPushButton("\U0001F393 Learn more in Linux Academy")
            learn_btn.setObjectName("learnButton")
            learn_btn.clicked.connect(
                lambda: self.on_open_lesson(*explanation.related_lesson)
            )
            action_row.addWidget(learn_btn)

        action_row.addStretch()
        card_layout.addLayout(action_row)

        self.result_layout.insertWidget(0, card)
