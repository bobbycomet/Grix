"""
Grix Repair History
====================

Keeps a simple JSON log of every fix Grix has applied, so users can
see what changed and when. This is intentionally a log, not an undo
system - true rollback on Linux depends on the action taken, so each
entry stores the rollback hint that was shown to the user at the time.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Optional

HISTORY_DIR = os.path.expanduser("~/.local/share/grix")
HISTORY_FILE = os.path.join(HISTORY_DIR, "repair_history.json")


@dataclass
class HistoryEntry:
    timestamp: str
    fix_id: str
    title: str
    commands: list[str]
    success: bool
    output: str
    rollback_hint: Optional[str] = None


def _ensure_dir() -> None:
    os.makedirs(HISTORY_DIR, exist_ok=True)


def load_history() -> list[HistoryEntry]:
    _ensure_dir()
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, "r") as f:
            raw = json.load(f)
        return [HistoryEntry(**item) for item in raw]
    except (json.JSONDecodeError, TypeError, OSError):
        return []


def add_entry(entry: HistoryEntry) -> None:
    _ensure_dir()
    history = load_history()
    history.append(entry)
    # Keep the most recent 200 entries
    history = history[-200:]
    with open(HISTORY_FILE, "w") as f:
        json.dump([asdict(e) for e in history], f, indent=2)


def record_fix(fix_id: str, title: str, commands: list[str],
                success: bool, output: str,
                rollback_hint: Optional[str] = None) -> None:
    entry = HistoryEntry(
        timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        fix_id=fix_id,
        title=title,
        commands=commands,
        success=success,
        output=output,
        rollback_hint=rollback_hint,
    )
    add_entry(entry)


def clear_history() -> None:
    _ensure_dir()
    if os.path.exists(HISTORY_FILE):
        os.remove(HISTORY_FILE)
