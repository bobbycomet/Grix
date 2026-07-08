"""
Grix Linux Academy - Lesson Browser & Viewer
================================================

Two-pane layout: a tree of tracks/lessons on the left (with
completion checkmarks), and the lesson content on the right.

Lesson content is rendered block-by-block:
  text     -> Markdown-ish QLabel (basic bold/code handling via simple HTML)
  command  -> a styled "try this command" box with explanation
  quiz     -> multiple choice with immediate feedback
  practice -> embeds the sandbox terminal pre-focused, checks the
              user's input against the expected command(s)
"""

from __future__ import annotations

import re

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QScrollArea,
    QFrame, QTreeWidget, QTreeWidgetItem, QButtonGroup, QRadioButton,
    QSplitter, QSizePolicy,
)

from ..modules import lessons as lessons_module
from ..modules import progress
from ..modules.lessons import Lesson, Track
from .mascot import GrixMascot
from .sandbox_widget import SandboxWidget
from .theme import COLORS


def _markdownish_to_html(text: str) -> str:
    """Very small subset of markdown -> HTML for lesson text blocks."""
    # Escape existing HTML special chars first
    text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # Code blocks ```...```
    def code_block(match):
        content = match.group(1)
        return (
            f'<pre style="background:{COLORS["code_bg"]};color:{COLORS["code_text_alt"]};padding:10px;'
            f'border-radius:6px;font-family:\'JetBrains Mono\',monospace;'
            f'font-size:12px;">' + content + '</pre>'
        )
    text = re.sub(r"```\n?(.*?)```", code_block, text, flags=re.DOTALL)

    # Inline code `...`
    text = re.sub(
        r"`([^`]+)`",
        rf'<code style="background:{COLORS["bg_panel_alt"]};color:{COLORS["accent"]};padding:2px 5px;'
        rf'border-radius:4px;font-family:\'JetBrains Mono\',monospace;'
        rf'font-size:12px;">\1</code>',
        text,
    )

    # Bold **...**
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)

    # Bullet lists: lines starting with "- "
    lines = text.split("\n")
    html_lines = []
    in_list = False
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("- "):
            if not in_list:
                html_lines.append("<ul style='margin:4px 0 4px 18px;'>")
                in_list = True
            html_lines.append(f"<li>{stripped[2:]}</li>")
        else:
            if in_list:
                html_lines.append("</ul>")
                in_list = False
            if stripped:
                html_lines.append(f"<p style='margin:6px 0;'>{line}</p>")
            else:
                html_lines.append("<div style='height:4px;'></div>")
    if in_list:
        html_lines.append("</ul>")

    return "\n".join(html_lines)


class TextBlock(QLabel):
    def __init__(self, text: str, parent=None):
        super().__init__(parent)
        self.setText(_markdownish_to_html(text))
        self.setWordWrap(True)
        self.setTextFormat(Qt.TextFormat.RichText)
        self.setStyleSheet(f"font-size: 14px; color: {COLORS['text_primary']}; line-height: 150%;")


class CommandBlock(QFrame):
    def __init__(self, command: str, explanation: str, parent=None):
        super().__init__(parent)
        self.setObjectName("commandBlock")
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(14, 10, 14, 10)

        cmd_label = QLabel(command)
        cmd_label.setStyleSheet(
            f"font-family: 'JetBrains Mono', monospace; font-size: 13px; "
            f"font-weight: 700; color: {COLORS['code_text']}; background: {COLORS['code_bg']}; "
            f"padding: 8px 10px; border-radius: 6px;"
        )
        layout.addWidget(cmd_label)

        explain = QLabel(explanation)
        explain.setWordWrap(True)
        explain.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        layout.addWidget(explain)

        self.setStyleSheet(f"""
            #commandBlock {{
                background: {COLORS['bg_panel_alt']};
                border-radius: 8px;
                border-left: 4px solid {COLORS['accent']};
            }}
        """)


class ClickableLabel(QLabel):
    """A QLabel that toggles a target radio button (or checkbox) when
    clicked - used so long quiz option text can word-wrap normally
    (which QRadioButton's own text cannot) while still being clickable
    like the rest of the option, not just the small indicator circle."""
    def __init__(self, text: str, target, parent=None):
        super().__init__(text, parent)
        self._target = target
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):  # noqa: N802 (Qt naming)
        self._target.setChecked(True)
        super().mousePressEvent(event)


class QuizBlock(QFrame):
    def __init__(self, question: str, options: list[str], correct_index: int,
                 explanation: str, parent=None):
        super().__init__(parent)
        self.setObjectName("quizBlock")
        self.correct_index = correct_index

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 12, 14, 12)

        q_label = QLabel(f"\U0001F914 Quick check: {question}")
        q_label.setWordWrap(True)
        q_label.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(q_label)

        self.button_group = QButtonGroup(self)
        self.radio_buttons: list[QRadioButton] = []
        for i, opt in enumerate(options):
            # QRadioButton has no word-wrap support of its own, so a
            # long option (anything beyond a short phrase) would force
            # this whole block - and the surrounding lesson panel -
            # wider than the viewport instead of wrapping. Pairing an
            # empty-text radio button with a separate, word-wrapping
            # QLabel (and forwarding clicks on the label to the button)
            # gives long options the same clean wrapping as everything
            # else in the lesson.
            option_row = QHBoxLayout()
            option_row.setSpacing(6)

            rb = QRadioButton()
            rb.setStyleSheet("font-size: 13px;")
            self.button_group.addButton(rb, i)
            self.radio_buttons.append(rb)
            option_row.addWidget(rb, alignment=Qt.AlignmentFlag.AlignTop)

            opt_label = ClickableLabel(opt, target=rb)
            opt_label.setWordWrap(True)
            opt_label.setStyleSheet("font-size: 13px;")
            option_row.addWidget(opt_label, stretch=1)

            layout.addLayout(option_row)

        self.check_btn = QPushButton("Check answer")
        self.check_btn.clicked.connect(self._check)
        layout.addWidget(self.check_btn)

        self.feedback_label = QLabel()
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setStyleSheet("font-size: 13px; margin-top: 4px;")
        self.feedback_label.setVisible(False)
        layout.addWidget(self.feedback_label)

        self._explanation = explanation

        self.setStyleSheet(f"""
            #quizBlock {{
                background: {COLORS['yellow_bg']};
                border-radius: 8px;
                border-left: 4px solid {COLORS['yellow']};
            }}
        """)

    def _check(self) -> None:
        checked_id = self.button_group.checkedId()
        if checked_id == -1:
            self.feedback_label.setText("Pick an answer first!")
            self.feedback_label.setStyleSheet(f"font-size: 13px; color: {COLORS['yellow']}; margin-top: 4px;")
            self.feedback_label.setVisible(True)
            return

        if checked_id == self.correct_index:
            self.feedback_label.setText(f"\u2705 Correct! {self._explanation}")
            self.feedback_label.setStyleSheet(f"font-size: 13px; color: {COLORS['green']}; margin-top: 4px;")
        else:
            self.feedback_label.setText(f"\u274C Not quite. {self._explanation}")
            self.feedback_label.setStyleSheet(f"font-size: 13px; color: {COLORS['red']}; margin-top: 4px;")
        self.feedback_label.setWordWrap(True)
        self.feedback_label.setVisible(True)


class PracticeBlock(QFrame):
    """A practice exercise that uses a shared sandbox terminal."""

    def __init__(self, prompt: str, expected, hint: str,
                 sandbox_widget: SandboxWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("practiceBlock")
        self.sandbox_widget = sandbox_widget

        if isinstance(expected, str):
            self.expected_commands = [expected]
        else:
            self.expected_commands = list(expected)

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(14, 12, 14, 12)

        title = QLabel("\U0001F4BB Try it yourself")
        title.setStyleSheet("font-weight: 700; font-size: 13px;")
        layout.addWidget(title)

        prompt_label = QLabel(prompt)
        prompt_label.setWordWrap(True)
        prompt_label.setStyleSheet(f"font-size: 13px; color: {COLORS['text_secondary']};")
        layout.addWidget(prompt_label)

        row = QHBoxLayout()
        hint_btn = QPushButton("Show hint")
        hint_btn.clicked.connect(self._toggle_hint)
        row.addWidget(hint_btn)

        focus_btn = QPushButton("Go to sandbox terminal \u2193")
        focus_btn.clicked.connect(self._scroll_to_sandbox)
        row.addWidget(focus_btn)
        row.addStretch()
        layout.addLayout(row)

        self.hint_label = QLabel(f"\U0001F4A1 {hint}")
        self.hint_label.setWordWrap(True)
        self.hint_label.setStyleSheet(f"font-size: 12px; color: {COLORS['accent']};")
        self.hint_label.setVisible(False)
        layout.addWidget(self.hint_label)

        self.status_label = QLabel("Not completed yet.")
        self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['text_muted']};")
        layout.addWidget(self.status_label)

        self._completed_steps = 0
        self.sandbox_widget.command_run.connect(self._on_command_run)

        self.setStyleSheet(f"""
            #practiceBlock {{
                background: {COLORS['bg_panel_alt']};
                border-radius: 8px;
                border-left: 4px solid {COLORS['accent_strong']};
            }}
        """)

    def _toggle_hint(self) -> None:
        self.hint_label.setVisible(not self.hint_label.isVisible())

    def _scroll_to_sandbox(self) -> None:
        self.sandbox_widget.setFocus()
        self.sandbox_widget.scroll_into_view()

    def _normalize(self, cmd: str) -> str:
        return " ".join(cmd.strip().split())

    def _on_command_run(self, command: str) -> None:
        if self._completed_steps >= len(self.expected_commands):
            return
        expected = self._normalize(self.expected_commands[self._completed_steps])
        actual = self._normalize(command)
        if actual == expected:
            self._completed_steps += 1
            if self._completed_steps >= len(self.expected_commands):
                self.status_label.setText("\u2705 Completed!")
                self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['green']}; font-weight: 600;")
            else:
                self.status_label.setText(
                    f"\u2705 Step {self._completed_steps} of "
                    f"{len(self.expected_commands)} done - keep going."
                )
                self.status_label.setStyleSheet(f"font-size: 12px; color: {COLORS['green']};")


class AcademyPanel(QWidget):
    """Main Linux Academy screen: lesson tree + lesson viewer."""

    def __init__(self, mascot: GrixMascot, parent=None):
        super().__init__(parent)
        self.mascot = mascot
        self.current_track: Track | None = None
        self.current_lesson: Lesson | None = None
        self.current_block_index = 0

        outer = QVBoxLayout(self)
        outer.setContentsMargins(24, 24, 24, 24)
        outer.setSpacing(16)

        header = QVBoxLayout()
        title = QLabel("Linux Academy")
        title.setStyleSheet("font-size: 22px; font-weight: 800;")
        header.addWidget(title)

        self.subtitle = QLabel(
            "Beginner-to-intermediate lessons that explain Linux the way "
            "Grix explains repairs - in plain language, with hands-on "
            "practice in a safe sandbox."
        )
        self.subtitle.setWordWrap(True)
        self.subtitle.setStyleSheet(f"color: {COLORS['text_secondary']};")
        header.addWidget(self.subtitle)
        outer.addLayout(header)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        outer.addWidget(splitter, stretch=1)

        # -- Left: lesson tree --
        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setMinimumWidth(260)
        self.tree.setMaximumWidth(340)
        self.tree.itemClicked.connect(self._on_tree_item_clicked)
        splitter.addWidget(self.tree)

        # -- Right: lesson content --
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(12)

        self.lesson_scroll = QScrollArea()
        self.lesson_scroll.setWidgetResizable(True)
        self.lesson_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.lesson_content = QWidget()
        self.lesson_layout = QVBoxLayout(self.lesson_content)
        self.lesson_layout.setSpacing(14)
        self.lesson_layout.setContentsMargins(4, 4, 16, 4)
        self.lesson_layout.addStretch()
        self.lesson_scroll.setWidget(self.lesson_content)
        right_layout.addWidget(self.lesson_scroll, stretch=1)

        # Shared sandbox terminal, embedded at the bottom of each lesson
        self.sandbox_widget = SandboxWidget()
        right_layout.addWidget(self.sandbox_widget)

        # Navigation footer
        nav_row = QHBoxLayout()
        self.prev_btn = QPushButton("\u2190 Previous")
        self.prev_btn.clicked.connect(self._go_previous)
        nav_row.addWidget(self.prev_btn)
        nav_row.addStretch()

        self.complete_btn = QPushButton("Mark lesson complete")
        self.complete_btn.setObjectName("primaryButton")
        self.complete_btn.clicked.connect(self._mark_complete)
        nav_row.addWidget(self.complete_btn)

        self.next_btn = QPushButton("Next \u2192")
        self.next_btn.clicked.connect(self._go_next)
        nav_row.addWidget(self.next_btn)
        right_layout.addLayout(nav_row)

        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        self._build_tree()
        self._show_welcome()

    # -- Tree building -----------------------------------------------------

    def _build_tree(self) -> None:
        self.tree.clear()
        for track in lessons_module.all_tracks():
            done = progress.completed_count(track.id)
            total = len(track.lessons)
            track_item = QTreeWidgetItem([f"{track.title}  ({done}/{total})"])
            track_item.setData(0, Qt.ItemDataRole.UserRole, ("track", track.id, None))
            font = track_item.font(0)
            font.setBold(True)
            track_item.setFont(0, font)

            for lesson in track.lessons:
                check = "\u2713 " if progress.is_complete(track.id, lesson.id) else "\u25CB "
                lesson_item = QTreeWidgetItem([check + lesson.title])
                lesson_item.setData(0, Qt.ItemDataRole.UserRole, ("lesson", track.id, lesson.id))
                track_item.addChild(lesson_item)

            self.tree.addTopLevelItem(track_item)
            track_item.setExpanded(True)

    def _on_tree_item_clicked(self, item: QTreeWidgetItem, column: int) -> None:
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if data is None:
            return
        kind, track_id, lesson_id = data
        if kind == "track":
            track = lessons_module.get_track(track_id)
            if track and track.lessons:
                self._load_lesson(track_id, track.lessons[0].id)
        else:
            self._load_lesson(track_id, lesson_id)

    # -- Welcome / empty state -----------------------------------------------

    def _show_welcome(self) -> None:
        self._clear_lesson_content()
        welcome = QLabel(
            "Welcome to the Linux Academy! \U0001F393\n\n"
            "Pick a lesson from the list on the left to get started. "
            "The Beginner track covers the absolute basics - opening a "
            "terminal, moving around the filesystem, and managing files. "
            "The Intermediate track builds on that with pipes, "
            "permissions, processes, and the same tools System Sentinel "
            "uses to diagnose problems.\n\n"
            "Every lesson includes things to try in a safe sandbox "
            "terminal - nothing you type there touches your real "
            "computer."
        )
        welcome.setWordWrap(True)
        welcome.setStyleSheet(f"font-size: 14px; color: {COLORS['text_secondary']}; padding: 20px;")
        self.lesson_layout.insertWidget(0, welcome)
        self.sandbox_widget.setVisible(False)
        self.prev_btn.setEnabled(False)
        self.next_btn.setEnabled(False)
        self.complete_btn.setEnabled(False)

    # -- Lesson loading -------------------------------------------------------

    def _clear_lesson_content(self) -> None:
        while self.lesson_layout.count() > 0:
            item = self.lesson_layout.takeAt(0)
            w = item.widget()
            if w is not None:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def open_lesson(self, track_id: str, lesson_id: str) -> None:
        """Public entry point for navigating to a specific lesson from
        outside the Academy panel (e.g. a 'Learn about this' link from
        System Sentinel)."""
        self._load_lesson(track_id, lesson_id)

    def _load_lesson(self, track_id: str, lesson_id: str) -> None:
        track = lessons_module.get_track(track_id)
        lesson = lessons_module.get_lesson(track_id, lesson_id)
        if track is None or lesson is None:
            return

        self.current_track = track
        self.current_lesson = lesson
        self.mascot.set_state("study", caption="Studying with you...")

        self._clear_lesson_content()

        # Lesson header
        title_label = QLabel(lesson.title)
        title_label.setStyleSheet("font-size: 20px; font-weight: 800;")
        self.lesson_layout.addWidget(title_label)

        summary_label = QLabel(lesson.summary)
        summary_label.setWordWrap(True)
        summary_label.setStyleSheet(f"color: {COLORS['text_secondary']}; font-size: 13px;")
        self.lesson_layout.addWidget(summary_label)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {COLORS['border']};")
        self.lesson_layout.addWidget(sep)

        has_practice = False
        for block in lesson.blocks:
            kind = block[0]
            if kind == "text":
                self.lesson_layout.addWidget(TextBlock(block[1]))
            elif kind == "command":
                self.lesson_layout.addWidget(CommandBlock(block[1], block[2]))
            elif kind == "quiz":
                self.lesson_layout.addWidget(QuizBlock(block[1], block[2], block[3], block[4]))
            elif kind == "practice":
                has_practice = True
                self.lesson_layout.addWidget(
                    PracticeBlock(block[1], block[2], block[3], self.sandbox_widget)
                )

        self.lesson_layout.addStretch()

        self.sandbox_widget.setVisible(has_practice)

        # Update completion button
        is_done = progress.is_complete(track_id, lesson_id)
        self.complete_btn.setEnabled(not is_done)
        self.complete_btn.setText(
            "\u2713 Lesson complete" if is_done else "Mark lesson complete"
        )

        # Update nav buttons
        idx = track.lessons.index(lesson)
        self.prev_btn.setEnabled(idx > 0)
        self.next_btn.setEnabled(idx < len(track.lessons) - 1)

        # Select in tree
        self._select_in_tree(track_id, lesson_id)

        self.lesson_scroll.verticalScrollBar().setValue(0)

    def _select_in_tree(self, track_id: str, lesson_id: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            track_item = self.tree.topLevelItem(i)
            for j in range(track_item.childCount()):
                lesson_item = track_item.child(j)
                data = lesson_item.data(0, Qt.ItemDataRole.UserRole)
                if data and data[1] == track_id and data[2] == lesson_id:
                    self.tree.setCurrentItem(lesson_item)
                    return

    # -- Navigation -----------------------------------------------------------

    def _go_previous(self) -> None:
        if not self.current_track or not self.current_lesson:
            return
        idx = self.current_track.lessons.index(self.current_lesson)
        if idx > 0:
            prev_lesson = self.current_track.lessons[idx - 1]
            self._load_lesson(self.current_track.id, prev_lesson.id)

    def _go_next(self) -> None:
        if not self.current_track or not self.current_lesson:
            return
        idx = self.current_track.lessons.index(self.current_lesson)
        if idx < len(self.current_track.lessons) - 1:
            next_lesson = self.current_track.lessons[idx + 1]
            self._load_lesson(self.current_track.id, next_lesson.id)

    def _mark_complete(self) -> None:
        if not self.current_track or not self.current_lesson:
            return
        progress.mark_complete(self.current_track.id, self.current_lesson.id)
        self.complete_btn.setEnabled(False)
        self.complete_btn.setText("\u2713 Lesson complete")
        self.mascot.set_state("fixed", caption="Nice work!")
        self._build_tree()
        self._select_in_tree(self.current_track.id, self.current_lesson.id)
