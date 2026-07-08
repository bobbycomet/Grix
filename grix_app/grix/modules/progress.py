"""
Grix Linux Academy - Progress Tracking
=========================================

Tracks which lessons a user has completed, persisted to a small
JSON file in the user's home directory.
"""

from __future__ import annotations

import json
import os

PROGRESS_DIR = os.path.expanduser("~/.local/share/grix")
PROGRESS_FILE = os.path.join(PROGRESS_DIR, "academy_progress.json")


def _ensure_dir() -> None:
    os.makedirs(PROGRESS_DIR, exist_ok=True)


def load_progress() -> dict:
    _ensure_dir()
    if not os.path.exists(PROGRESS_FILE):
        return {"completed": []}
    try:
        with open(PROGRESS_FILE, "r") as f:
            data = json.load(f)
        if "completed" not in data:
            data["completed"] = []
        return data
    except (json.JSONDecodeError, OSError):
        return {"completed": []}


def save_progress(data: dict) -> None:
    _ensure_dir()
    with open(PROGRESS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def mark_complete(track_id: str, lesson_id: str) -> None:
    data = load_progress()
    key = f"{track_id}/{lesson_id}"
    if key not in data["completed"]:
        data["completed"].append(key)
        save_progress(data)


def is_complete(track_id: str, lesson_id: str) -> bool:
    data = load_progress()
    return f"{track_id}/{lesson_id}" in data["completed"]


def completed_count(track_id: str | None = None) -> int:
    data = load_progress()
    if track_id is None:
        return len(data["completed"])
    return sum(1 for k in data["completed"] if k.startswith(f"{track_id}/"))


def reset_progress() -> None:
    save_progress({"completed": []})
