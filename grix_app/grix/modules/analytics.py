"""
Grix - Local Insights (opt-in, local-only)
==============================================

Tracks how often each diagnostic check fires with a non-green status,
purely to help Grix (and, if the user chooses to read it, the user)
understand which areas of their system need attention most often -
and to help prioritize which Academy lessons might be most useful to
them.

Privacy model:
  - OFF by default. Nothing is recorded unless the user opts in via
    Settings.
  - Counts are stored in a local JSON file
    (~/.local/share/grix/local_insights.json) and are NEVER
    transmitted anywhere - there is no network code in this module at
    all.
  - Only check ids and fix ids are recorded (e.g. "disk", "apt_clean")
    - no file paths, package names, error messages, or other
    potentially identifying details.
  - The user can view exactly what's recorded, and clear it at any
    time, from Settings.
"""

from __future__ import annotations

import json
import os
from datetime import datetime

INSIGHTS_DIR = os.path.expanduser("~/.local/share/grix")
INSIGHTS_FILE = os.path.join(INSIGHTS_DIR, "local_insights.json")


def _ensure_dir() -> None:
    os.makedirs(INSIGHTS_DIR, exist_ok=True)


def _default_data() -> dict:
    return {
        "enabled": False,
        "check_status_counts": {},   # check_id -> {"green": n, "yellow": n, "red": n, "unknown": n}
        "fix_applied_counts": {},    # fix_id -> count
        "scans_run": 0,
        "since": None,
    }


def load() -> dict:
    _ensure_dir()
    if not os.path.exists(INSIGHTS_FILE):
        return _default_data()
    try:
        with open(INSIGHTS_FILE, "r") as f:
            data = json.load(f)
        defaults = _default_data()
        defaults.update(data)
        return defaults
    except (OSError, json.JSONDecodeError):
        return _default_data()


def save(data: dict) -> None:
    _ensure_dir()
    with open(INSIGHTS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def is_enabled() -> bool:
    return bool(load().get("enabled", False))


def set_enabled(enabled: bool) -> None:
    data = load()
    data["enabled"] = enabled
    if enabled and not data.get("since"):
        data["since"] = datetime.now().strftime("%Y-%m-%d")
    save(data)


def record_scan(results) -> None:
    """Record the outcome of a scan, if enabled. `results` is a list of
    CheckResult-like objects with `.id` and `.status.value`."""
    data = load()
    if not data.get("enabled"):
        return

    data["scans_run"] = data.get("scans_run", 0) + 1
    counts = data.setdefault("check_status_counts", {})
    for result in results:
        entry = counts.setdefault(result.id, {"green": 0, "yellow": 0, "red": 0, "unknown": 0})
        status_key = result.status.value
        entry[status_key] = entry.get(status_key, 0) + 1

    save(data)


def record_fix_applied(fix_id: str) -> None:
    """Record that a fix was applied, if enabled."""
    data = load()
    if not data.get("enabled"):
        return

    counts = data.setdefault("fix_applied_counts", {})
    counts[fix_id] = counts.get(fix_id, 0) + 1
    save(data)


def clear() -> None:
    save(_default_data())


def summary() -> dict:
    """Return a human-readable-ish summary for display in Settings."""
    data = load()
    counts = data.get("check_status_counts", {})

    most_flagged = sorted(
        counts.items(),
        key=lambda kv: kv[1].get("yellow", 0) + kv[1].get("red", 0),
        reverse=True,
    )
    most_flagged = [(k, v) for k, v in most_flagged if v.get("yellow", 0) + v.get("red", 0) > 0]

    return {
        "enabled": data.get("enabled", False),
        "since": data.get("since"),
        "scans_run": data.get("scans_run", 0),
        "most_flagged_checks": most_flagged[:5],
        "fix_applied_counts": data.get("fix_applied_counts", {}),
    }
