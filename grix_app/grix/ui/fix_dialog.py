"""
Grix System Sentinel - Fix Confirmation / Repair Preview Dialog
===================================================================

Per Grix's safety philosophy, no fix runs without explicit
confirmation. This dialog is the "Repair Preview":

  - what will happen, in plain language (reason)
  - the exact command(s) that will run (always visible - dry-run
    transparency, even for "Safe" fixes)
  - the severity level and risk level
  - a bullet list of expected changes
  - rollback information
  - for ADVANCED fixes, requires the user to type CONFIRM
  - for checkbox-style fixes (e.g. "remove these old kernels"), a
    per-item checklist where protected items (like the running
    kernel) cannot be selected
  - an optional "Learn about this" link into the relevant Academy
    lesson
"""

from __future__ import annotations

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QWidget, QCheckBox, QScrollArea,
)

from ..modules import diagnostics
from ..modules.diagnostics import Fix, SeverityLevel, RiskLevel
from .theme import COLORS, code_box_style, small_badge_style

SEVERITY_INFO = {
    SeverityLevel.SAFE: ("\U0001F7E2 Safe", COLORS["green"]),
    SeverityLevel.APPROVAL: ("\U0001F7E1 Requires approval", COLORS["yellow"]),
    SeverityLevel.ADVANCED: ("\U0001F534 Advanced", COLORS["red"]),
}

RISK_INFO = {
    RiskLevel.LOW: ("Low risk", COLORS["green"], COLORS["green_bg"]),
    RiskLevel.MEDIUM: ("Medium risk", COLORS["yellow"], COLORS["yellow_bg"]),
    RiskLevel.HIGH: ("High risk", COLORS["red"], COLORS["red_bg"]),
}


def _bullet_list(items: list[str]) -> QLabel:
    html = "<ul style='margin:4px 0 0 -18px;'>" + "".join(
        f"<li style='margin-bottom:2px;'>{item}</li>" for item in items
    ) + "</ul>"
    label = QLabel(html)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.RichText)
    label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
    return label


class FixConfirmDialog(QDialog):
    """Returns Accepted with `selected_option_ids` populated for
    checkbox-style fixes (empty list otherwise)."""

    def __init__(self, fix: Fix, on_open_lesson=None, parent=None):
        super().__init__(parent)
        self.fix = fix
        self.on_open_lesson = on_open_lesson
        self.selected_option_ids: list[str] = []
        self.setWindowTitle("Repair Preview")
        self.setMinimumWidth(540)
        self.setMaximumHeight(720)

        outer = QVBoxLayout(self)
        outer.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(4, 4, 16, 4)
        scroll.setWidget(content)
        outer.addWidget(scroll, stretch=1)

        # -- Header: severity + risk badges --
        badge_row = QHBoxLayout()
        label_text, color = SEVERITY_INFO[fix.severity]
        severity_label = QLabel(label_text)
        severity_label.setStyleSheet(
            f"font-weight: 600; font-size: 13px; color: {color};"
        )
        badge_row.addWidget(severity_label)

        risk_text, risk_fg, risk_bg = RISK_INFO[fix.risk]
        risk_label = QLabel(risk_text)
        risk_label.setStyleSheet(small_badge_style(risk_fg, risk_bg))
        badge_row.addWidget(risk_label)
        badge_row.addStretch()
        layout.addLayout(badge_row)

        title = QLabel(fix.title)
        title.setStyleSheet("font-size: 17px; font-weight: 700;")
        title.setWordWrap(True)
        layout.addWidget(title)

        explanation = QLabel(fix.explanation)
        explanation.setWordWrap(True)
        explanation.setStyleSheet(f"color: {COLORS['text_secondary']};")
        layout.addWidget(explanation)

        # -- Why Grix wants to do this --
        if fix.reason:
            reason_frame = QFrame()
            reason_frame.setObjectName("reasonFrame")
            reason_layout = QVBoxLayout(reason_frame)
            reason_layout.setContentsMargins(12, 10, 12, 10)
            reason_layout.setSpacing(4)

            reason_title = QLabel("Why Grix wants to do this")
            reason_title.setStyleSheet(f"font-weight: 700; font-size: 12px; color: {COLORS['accent']};")
            reason_layout.addWidget(reason_title)

            reason_body = QLabel(fix.reason)
            reason_body.setWordWrap(True)
            reason_body.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
            reason_layout.addWidget(reason_body)

            layout.addWidget(reason_frame)

        # -- Checkbox options (e.g. old kernels) --
        self.option_checkboxes: dict[str, QCheckBox] = {}
        if fix.options:
            options_title = QLabel("Select what to include:")
            options_title.setStyleSheet("font-weight: 600; margin-top: 4px; font-size: 13px;")
            layout.addWidget(options_title)

            for opt in fix.options:
                row = QHBoxLayout()
                cb = QCheckBox(opt.label)
                cb.setStyleSheet("font-family: 'JetBrains Mono', monospace; font-size: 12px;")
                if opt.protected:
                    cb.setChecked(False)
                    cb.setEnabled(False)
                else:
                    cb.setChecked(True)
                self.option_checkboxes[opt.id] = cb
                row.addWidget(cb)

                if opt.detail:
                    detail_label = QLabel(opt.detail)
                    detail_label.setStyleSheet(f"color: {COLORS['text_muted']}; font-size: 11px;")
                    row.addWidget(detail_label)

                row.addStretch()
                layout.addLayout(row)

                if opt.protected and opt.protected_reason:
                    note = QLabel(f"  \u21B3 {opt.protected_reason}")
                    note.setWordWrap(True)
                    note.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 11px; margin-left: 6px;")
                    layout.addWidget(note)

        # -- Expected changes --
        if fix.expected_changes:
            changes_title = QLabel("Expected changes:")
            changes_title.setStyleSheet("font-weight: 600; margin-top: 4px; font-size: 13px;")
            layout.addWidget(changes_title)
            layout.addWidget(_bullet_list(fix.expected_changes))

        # -- Commands box (always visible, even for Safe fixes) --
        cmd_label = QLabel(
            "Exact command(s) that will run:"
            if not fix.options else
            "Command template (applied to your selection above):"
        )
        cmd_label.setStyleSheet("font-weight: 600; margin-top: 4px; font-size: 13px;")
        layout.addWidget(cmd_label)

        raw_commands = (
            [fix.command_template] if fix.options and fix.command_template
            else list(fix.commands)
        )

        # Grix runs privileged commands (anything written with a 'sudo'
        # prefix) through pkexec by default, which shows a native
        # PolicyKit authentication dialog - using Grix's own helper
        # (grix-helper) if it's installed, for a narrower privilege
        # scope, or the bare command otherwise. The box below shows
        # exactly what will actually run. A second, separate box offers
        # the plain 'sudo' version of the underlying command for anyone
        # who would rather copy it into their own terminal instead of
        # using the graphical prompt.
        display_commands = [
            diagnostics.display_command_for_fix_preview(c)
            for c in raw_commands
        ]
        cmd_text = "\n".join(display_commands)

        cmd_box = QTextEdit()
        cmd_box.setReadOnly(True)
        cmd_box.setPlainText(cmd_text)
        cmd_box.setStyleSheet(code_box_style())
        line_count = max(1, cmd_text.count("\n") + 1)
        cmd_box.setFixedHeight(40 + 18 * line_count)
        layout.addWidget(cmd_box)

        has_privileged_commands = any(c.strip().startswith("sudo ") for c in raw_commands)

        if fix.needs_sudo and has_privileged_commands:
            sudo_note = QLabel(
                "\U0001F510 This needs administrator privileges. Grix runs "
                "it through pkexec (PolicyKit), which will show a "
                "graphical authentication prompt - or falls back to sudo "
                "automatically if pkexec isn't available on this system."
            )
            sudo_note.setWordWrap(True)
            sudo_note.setStyleSheet(f"color: {COLORS['yellow']}; font-size: 12px;")
            layout.addWidget(sudo_note)

            sudo_commands = [
                diagnostics.sudo_form(c) if c.strip().startswith("sudo ") else c
                for c in raw_commands
            ]
            sudo_text = "\n".join(sudo_commands)

            copy_label = QLabel("Prefer your own terminal? Copy this instead:")
            copy_label.setStyleSheet(f"font-weight: 600; font-size: 12px; margin-top: 4px; color: {COLORS['text_secondary']};")
            layout.addWidget(copy_label)

            sudo_box = QTextEdit()
            sudo_box.setReadOnly(True)
            sudo_box.setPlainText(sudo_text)
            sudo_box.setStyleSheet(code_box_style())
            sudo_line_count = max(1, sudo_text.count("\n") + 1)
            sudo_box.setFixedHeight(36 + 18 * sudo_line_count)
            layout.addWidget(sudo_box)

        if fix.rollback_hint:
            rollback = QLabel(f"\U0001F501 If you need to undo this: {fix.rollback_hint}")
            rollback.setWordWrap(True)
            rollback.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 12px;")
            layout.addWidget(rollback)

        # -- Learn about this --
        if fix.related_lesson and self.on_open_lesson:
            learn_row = QHBoxLayout()
            learn_btn = QPushButton("\U0001F393 Learn about this in Linux Academy")
            learn_btn.setObjectName("learnButton")
            learn_btn.clicked.connect(self._on_learn_clicked)
            learn_row.addWidget(learn_btn)
            learn_row.addStretch()
            layout.addLayout(learn_row)

        # Advanced fixes require typed confirmation
        self.confirm_input: QLineEdit | None = None
        if fix.severity == SeverityLevel.ADVANCED:
            warn = QLabel(
                "This is an advanced action. Type CONFIRM below to "
                "proceed."
            )
            warn.setStyleSheet(f"color: {COLORS['red']}; font-weight: 600;")
            warn.setWordWrap(True)
            layout.addWidget(warn)

            self.confirm_input = QLineEdit()
            self.confirm_input.setPlaceholderText("Type CONFIRM")
            layout.addWidget(self.confirm_input)

        layout.addStretch()

        # -- Buttons (outside the scroll area) --
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet(f"color: {COLORS['border']};")
        outer.addWidget(line)

        btn_container = QWidget()
        btn_row = QHBoxLayout(btn_container)
        btn_row.setContentsMargins(0, 10, 0, 0)
        btn_row.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)

        apply_text = "Apply Fix"
        if fix.options:
            apply_text = "Apply to Selected"
        self.apply_btn = QPushButton(apply_text)
        self.apply_btn.setObjectName("primaryButton")
        self.apply_btn.clicked.connect(self._on_apply)
        btn_row.addWidget(self.apply_btn)

        outer.addWidget(btn_container)

        if self.confirm_input is not None:
            self.confirm_input.textChanged.connect(self._update_apply_enabled)
            self._update_apply_enabled()

        if self.option_checkboxes:
            for cb in self.option_checkboxes.values():
                cb.toggled.connect(self._update_apply_enabled)
            self._update_apply_enabled()

    def _update_apply_enabled(self) -> None:
        enabled = True
        if self.confirm_input is not None:
            enabled = enabled and (self.confirm_input.text().strip().upper() == "CONFIRM")
        if self.option_checkboxes:
            enabled = enabled and any(cb.isChecked() for cb in self.option_checkboxes.values())
        self.apply_btn.setEnabled(enabled)

    def _on_learn_clicked(self) -> None:
        if self.fix.related_lesson and self.on_open_lesson:
            self.on_open_lesson(*self.fix.related_lesson)

    def _on_apply(self) -> None:
        if self.confirm_input is not None:
            if self.confirm_input.text().strip().upper() != "CONFIRM":
                return
        if self.option_checkboxes:
            self.selected_option_ids = [
                opt_id for opt_id, cb in self.option_checkboxes.items()
                if cb.isChecked()
            ]
            if not self.selected_option_ids:
                return
        self.accept()
