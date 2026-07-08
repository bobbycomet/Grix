"""
Grix - Check Snoozing ("Ignore for a week" / "Ignore forever")
====================================================================

Lets users dismiss non-urgent findings without losing visibility
entirely. Two snooze durations are supported:

  - "week"     - hidden for 7 days, then reappears automatically
  - "forever"  - hidden indefinitely

Snoozes are keyed by CheckResult.id (e.g. "disk", "services") so they
persist across scans and app restarts, stored in a local JSON file.

Safety override: some checks define a "force-reshow" threshold (for
example, disk space reaching 95% full). When a check's status would be
RED on the latest scan, Grix always shows it regardless of any active
snooze - urgent problems are never permanently hidden. This is
enforced by the caller (diagnostics/sentinel UI), not this module,
since only the check itself knows its current severity.

Users can also re-enable (un-snooze) any check at any time from the UI.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Optional

SNOOZE_DIR = os.path.expanduser("~/.local/share/grix")
SNOOZE_FILE = os.path.join(SNOOZE_DIR, "snoozed_checks.json")

WEEK_SECONDS = 7 * 24 * 60 * 60


@dataclass
class SnoozeEntry:
    check_id: str
    kind: str                  # "week" or "forever"
    snoozed_at: str            # ISO timestamp
    expires_at: Optional[str]  # ISO timestamp, or None for "forever"


def _ensure_dir() -> None:
    os.makedirs(SNOOZE_DIR, exist_ok=True)


def _load_raw() -> dict:
    _ensure_dir()
    if not os.path.exists(SNOOZE_FILE):
        return {}
    try:
        with open(SNOOZE_FILE, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _save_raw(data: dict) -> None:
    _ensure_dir()
    with open(SNOOZE_FILE, "w") as f:
        json.dump(data, f, indent=2)


def load_all() -> dict[str, SnoozeEntry]:
    raw = _load_raw()
    result = {}
    for check_id, entry in raw.items():
        try:
            result[check_id] = SnoozeEntry(**entry)
        except TypeError:
            continue
    return result


def snooze_for_a_week(check_id: str) -> None:
    now = datetime.now()
    entry = SnoozeEntry(
        check_id=check_id,
        kind="week",
        snoozed_at=now.isoformat(),
        expires_at=(now + timedelta(days=7)).isoformat(),
    )
    raw = _load_raw()
    raw[check_id] = asdict(entry)
    _save_raw(raw)


def snooze_forever(check_id: str) -> None:
    now = datetime.now()
    entry = SnoozeEntry(
        check_id=check_id,
        kind="forever",
        snoozed_at=now.isoformat(),
        expires_at=None,
    )
    raw = _load_raw()
    raw[check_id] = asdict(entry)
    _save_raw(raw)


def unsnooze(check_id: str) -> None:
    raw = _load_raw()
    if check_id in raw:
        del raw[check_id]
        _save_raw(raw)


def unsnooze_all() -> None:
    _save_raw({})


def is_snoozed(check_id: str) -> bool:
    """Return True if this check is currently snoozed (and the snooze
    hasn't expired). Expired week-long snoozes are treated as not
    snoozed and are lazily cleaned up."""
    raw = _load_raw()
    entry = raw.get(check_id)
    if entry is None:
        return False

    if entry.get("kind") == "forever":
        return True

    expires_at = entry.get("expires_at")
    if not expires_at:
        return False

    try:
        expiry = datetime.fromisoformat(expires_at)
    except ValueError:
        return False

    if datetime.now() >= expiry:
        # Expired - clean up and report as not snoozed
        del raw[check_id]
        _save_raw(raw)
        return False

    return True


def get_snooze_info(check_id: str) -> Optional[SnoozeEntry]:
    """Return the SnoozeEntry for a check if it's currently (and validly)
    snoozed, else None. Also performs lazy expiry cleanup."""
    if not is_snoozed(check_id):
        return None
    raw = _load_raw()
    entry = raw.get(check_id)
    if entry is None:
        return None
    return SnoozeEntry(**entry)


def days_remaining(entry: SnoozeEntry) -> Optional[int]:
    """Days left on a week-long snooze, or None for forever/invalid."""
    if entry.kind != "week" or not entry.expires_at:
        return None
    try:
        expiry = datetime.fromisoformat(entry.expires_at)
    except ValueError:
        return None
    remaining = expiry - datetime.now()
    return max(0, remaining.days)
