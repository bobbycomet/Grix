"""
Grix - Theme (Steam-inspired dark palette)
==============================================

A centralized color palette and stylesheet so every widget in Grix
uses consistent, readable colors instead of ad-hoc per-widget choices
that can end up as white-on-white or black-on-black depending on the
platform's default palette.

Palette inspired by Steam's client: deep blue-grey backgrounds, lighter
panel surfaces, soft blue accents, and off-white text - never pure
white-on-white or black-on-black.

Usage:
    from .theme import COLORS, apply_theme
    apply_theme(app)              # call once on QApplication
    main_window.setStyleSheet(GLOBAL_STYLESHEET)   # or use COLORS directly
"""

from __future__ import annotations

from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# Palette
# ---------------------------------------------------------------------------

COLORS = {
    # Backgrounds
    "bg_app": "#1b2838",          # Steam's signature dark blue-grey
    "bg_sidebar": "#171a21",       # near-black blue, sidebar/header
    "bg_panel": "#2a3f5a",         # card/panel surface
    "bg_panel_alt": "#34495e",     # slightly lighter alt surface
    "bg_input": "#0e1822",         # text inputs / code blocks
    "bg_hover": "#3d5a7a",         # hover state on panels/buttons

    # Text
    "text_primary": "#e8f0f7",     # near-white, primary text
    "text_secondary": "#b8c4d0",   # muted body text
    "text_muted": "#8696a7",       # captions, placeholders
    "text_on_accent": "#ffffff",   # text on top of accent-colored buttons

    # Accent (Steam blue)
    "accent": "#66c0f4",           # Steam's light blue accent
    "accent_strong": "#1a9fff",    # brighter blue for emphasis/links
    "accent_hover": "#4cb0ec",

    # Status colors (kept distinguishable on dark backgrounds)
    "green": "#90ee90",
    "green_bg": "#1f3a2e",
    "yellow": "#ffd479",
    "yellow_bg": "#3a3320",
    "red": "#ff8a80",
    "red_bg": "#3a2426",
    "grey": "#a0aab5",
    "grey_bg": "#2a3441",

    # Borders
    "border": "#3c5878",
    "border_light": "#4a6a8a",

    # Code / terminal
    "code_bg": "#0e1822",
    "code_text": "#a6e3a1",
    "code_text_alt": "#cdd6f4",
}


# ---------------------------------------------------------------------------
# QPalette - sets sensible defaults for native widgets (dialogs, menus,
# scrollbars, etc.) so anything not explicitly styled still looks right.
# ---------------------------------------------------------------------------

def build_qpalette() -> QPalette:
    p = QPalette()

    p.setColor(QPalette.ColorRole.Window, QColor(COLORS["bg_app"]))
    p.setColor(QPalette.ColorRole.WindowText, QColor(COLORS["text_primary"]))

    p.setColor(QPalette.ColorRole.Base, QColor(COLORS["bg_panel"]))
    p.setColor(QPalette.ColorRole.AlternateBase, QColor(COLORS["bg_panel_alt"]))

    p.setColor(QPalette.ColorRole.Text, QColor(COLORS["text_primary"]))
    p.setColor(QPalette.ColorRole.PlaceholderText, QColor(COLORS["text_muted"]))

    p.setColor(QPalette.ColorRole.Button, QColor(COLORS["bg_panel_alt"]))
    p.setColor(QPalette.ColorRole.ButtonText, QColor(COLORS["text_primary"]))

    p.setColor(QPalette.ColorRole.ToolTipBase, QColor(COLORS["bg_sidebar"]))
    p.setColor(QPalette.ColorRole.ToolTipText, QColor(COLORS["text_primary"]))

    p.setColor(QPalette.ColorRole.Highlight, QColor(COLORS["accent"]))
    p.setColor(QPalette.ColorRole.HighlightedText, QColor(COLORS["bg_sidebar"]))

    p.setColor(QPalette.ColorRole.Link, QColor(COLORS["accent_strong"]))

    # Disabled state
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, QColor(COLORS["text_muted"]))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, QColor(COLORS["text_muted"]))
    p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, QColor(COLORS["text_muted"]))

    return p


def apply_theme(app: QApplication) -> None:
    """Apply the dark palette to the whole application. Call once after
    creating the QApplication and before showing any windows."""
    app.setPalette(build_qpalette())


# ---------------------------------------------------------------------------
# Global stylesheet
# ---------------------------------------------------------------------------
# Centralizes object-name-based styling used across panels (cards, badges,
# buttons, code blocks) so individual widget files don't need to repeat
# hardcoded colors that might clash with the palette.

GLOBAL_STYLESHEET = f"""
    QMainWindow, QDialog, QWidget {{
        background: {COLORS["bg_app"]};
        color: {COLORS["text_primary"]};
    }}

    QLabel {{
        color: {COLORS["text_primary"]};
        background: transparent;
    }}

    /* -- Sidebar -- */
    #sidebar {{
        background: {COLORS["bg_sidebar"]};
        border-right: 1px solid {COLORS["border"]};
    }}
    #navButton {{
        text-align: left;
        padding: 10px 14px;
        border: none;
        border-radius: 8px;
        background: transparent;
        font-size: 13px;
        color: {COLORS["text_secondary"]};
    }}
    #navButton:hover {{
        background: {COLORS["bg_panel"]};
        color: {COLORS["text_primary"]};
    }}
    #navButton:checked {{
        background: {COLORS["bg_panel_alt"]};
        color: {COLORS["accent"]};
        font-weight: 700;
    }}

    /* -- Buttons -- */
    QPushButton {{
        font-family: inherit;
        background: {COLORS["bg_panel_alt"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 6px;
        padding: 6px 14px;
    }}
    QPushButton:hover {{
        background: {COLORS["bg_hover"]};
        border-color: {COLORS["border_light"]};
    }}
    QPushButton:disabled {{
        color: {COLORS["text_muted"]};
        background: {COLORS["bg_panel"]};
        border-color: {COLORS["border"]};
    }}
    QPushButton:checked {{
        background: {COLORS["bg_hover"]};
        border-color: {COLORS["accent"]};
    }}

    #primaryButton {{
        background: {COLORS["accent_strong"]};
        color: {COLORS["text_on_accent"]};
        border: none;
        border-radius: 8px;
        padding: 8px 16px;
        font-size: 13px;
        font-weight: 600;
    }}
    #primaryButton:hover {{
        background: {COLORS["accent_hover"]};
    }}
    #primaryButton:disabled {{
        background: {COLORS["bg_panel_alt"]};
        color: {COLORS["text_muted"]};
    }}

    #fixButton {{
        background: {COLORS["bg_panel_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 6px;
        padding: 4px 12px;
        font-size: 12px;
        color: {COLORS["text_primary"]};
    }}
    #fixButton:hover {{
        background: {COLORS["bg_hover"]};
        border-color: {COLORS["accent"]};
    }}

    #ignoreButton {{
        background: transparent;
        border: 1px solid {COLORS["border_light"]};
        border-radius: 10px;
        padding: 2px 10px;
        font-size: 11px;
        color: {COLORS["text_muted"]};
    }}
    #ignoreButton:hover {{
        color: {COLORS["text_primary"]};
        border-color: {COLORS["accent"]};
        background: {COLORS["bg_hover"]};
    }}

    #learnButton {{
        background: {COLORS["yellow_bg"]};
        border: 1px solid #6b5a2e;
        border-radius: 6px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
        color: {COLORS["yellow"]};
    }}
    #learnButton:hover {{
        background: #4a3f28;
        border-color: {COLORS["yellow"]};
    }}

    #whyToggle {{
        text-align: left;
        background: transparent;
        border: none;
        color: {COLORS["accent"]};
        font-size: 12px;
        font-weight: 600;
        padding: 2px 0;
    }}
    #whyToggle:hover {{
        color: {COLORS["accent_hover"]};
    }}

    /* -- Cards / panels -- */
    #checkCard, #dashCard, #settingsCard, #explainCard, #timelineRow {{
        background: {COLORS["bg_panel"]};
        border-radius: 10px;
        border: 1px solid {COLORS["border"]};
    }}

    #reasonFrame, #correlationFrame {{
        background: {COLORS["bg_panel_alt"]};
        border-radius: 8px;
        border-left: 4px solid {COLORS["accent"]};
    }}

    /* -- Text inputs / code blocks -- */
    QTextEdit, QLineEdit, QPlainTextEdit {{
        background: {COLORS["bg_input"]};
        color: {COLORS["code_text_alt"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 6px;
        padding: 4px;
        selection-background-color: {COLORS["accent"]};
        selection-color: {COLORS["bg_sidebar"]};
    }}
    QLineEdit:focus, QTextEdit:focus {{
        border-color: {COLORS["accent"]};
    }}

    /* -- Tabs -- */
    QTabWidget::pane {{
        border: 1px solid {COLORS["border"]};
        border-radius: 8px;
        background: {COLORS["bg_panel"]};
    }}
    QTabBar::tab {{
        background: {COLORS["bg_sidebar"]};
        color: {COLORS["text_secondary"]};
        padding: 8px 16px;
        font-size: 12px;
        border: 1px solid {COLORS["border"]};
        border-bottom: none;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background: {COLORS["bg_panel"]};
        font-weight: 700;
        color: {COLORS["accent"]};
    }}
    QTabBar::tab:hover {{
        color: {COLORS["text_primary"]};
    }}

    /* -- Trees / lists -- */
    QTreeWidget, QListWidget {{
        border: 1px solid {COLORS["border"]};
        background: {COLORS["bg_panel"]};
        border-radius: 10px;
        padding: 6px;
        color: {COLORS["text_primary"]};
    }}
    QTreeWidget::item, QListWidget::item {{
        padding: 6px 4px;
        border-radius: 4px;
    }}
    QTreeWidget::item:selected, QListWidget::item:selected {{
        background: {COLORS["bg_hover"]};
        color: {COLORS["accent"]};
    }}
    QListWidget::item:alternate {{
        background: {COLORS["bg_panel_alt"]};
    }}

    /* -- Scrollbars -- */
    QScrollBar:vertical {{
        background: transparent;
        width: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS["border_light"]};
        border-radius: 5px;
        min-height: 24px;
    }}
    QScrollBar::handle:vertical:hover {{
        background: {COLORS["accent"]};
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
    QScrollBar:horizontal {{
        background: transparent;
        height: 12px;
        margin: 2px;
    }}
    QScrollBar::handle:horizontal {{
        background: {COLORS["border_light"]};
        border-radius: 5px;
        min-width: 24px;
    }}
    QScrollBar::handle:horizontal:hover {{
        background: {COLORS["accent"]};
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
        width: 0px;
    }}

    /* -- Checkboxes / radio buttons -- */
    QCheckBox, QRadioButton {{
        color: {COLORS["text_primary"]};
        spacing: 8px;
        background: transparent;
    }}
    QCheckBox::indicator, QRadioButton::indicator {{
        width: 16px;
        height: 16px;
        border: 1px solid {COLORS["accent"]};
        border-radius: 3px;
        background: {COLORS["bg_input"]};
    }}
    QRadioButton::indicator {{
        border-radius: 8px;
    }}
    QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
        background: {COLORS["accent_strong"]};
        border-color: {COLORS["accent_strong"]};
    }}
    QCheckBox::indicator:disabled, QRadioButton::indicator:disabled {{
        background: {COLORS["bg_panel"]};
        border-color: {COLORS["border"]};
    }}

    /* -- Combo boxes -- */
    QComboBox {{
        background: {COLORS["bg_panel_alt"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
        border-radius: 6px;
        padding: 4px 8px;
    }}
    QComboBox:hover {{
        border-color: {COLORS["border_light"]};
    }}
    QComboBox QAbstractItemView {{
        background: {COLORS["bg_panel"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
        selection-background-color: {COLORS["bg_hover"]};
        selection-color: {COLORS["accent"]};
    }}

    /* -- Splitter -- */
    QSplitter::handle {{
        background: transparent;
        width: 16px;
    }}

    /* -- Frame separators -- */
    QFrame[frameShape="4"], QFrame[frameShape="5"] {{
        color: {COLORS["border"]};
    }}

    #grixCaption {{
        color: {COLORS["text_muted"]};
        font-size: 11px;
    }}

    QMenu {{
        background: {COLORS["bg_panel"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["border"]};
    }}
    QMenu::item:selected {{
        background: {COLORS["bg_hover"]};
        color: {COLORS["accent"]};
    }}
"""


# ---------------------------------------------------------------------------
# Helper inline styles for widgets that build their own setStyleSheet()
# strings (status badges, code boxes, etc.) - imported by panels instead
# of hardcoding hex values.
# ---------------------------------------------------------------------------

def code_box_style() -> str:
    return (
        f"font-family: 'JetBrains Mono', monospace; "
        f"background: {COLORS['code_bg']}; color: {COLORS['code_text']}; "
        f"border-radius: 6px; padding: 8px;"
    )


def code_box_style_alt() -> str:
    return (
        f"font-family: 'JetBrains Mono', monospace; font-size: 11px; "
        f"background: {COLORS['bg_input']}; border-radius: 6px; padding: 6px; "
        f"color: {COLORS['text_secondary']};"
    )


def status_badge_style(fg: str, bg: str) -> str:
    return (
        f"background: {bg}; color: {fg}; border-radius: 10px; "
        f"padding: 3px 10px; font-size: 11px; font-weight: 600;"
    )


def small_badge_style(fg: str, bg: str) -> str:
    return (
        f"background: {bg}; color: {fg}; border-radius: 10px; "
        f"padding: 2px 10px; font-size: 11px; font-weight: 600;"
    )
