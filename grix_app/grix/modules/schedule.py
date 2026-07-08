"""
Grix - Auto-Scan Schedule
============================

Persists and evaluates the user's preferred auto-scan schedule.
The schedule is stored in ~/.local/share/grix/schedule.json and
read once at startup, then on every Settings refresh.

Schedule modes
--------------
  "interval"   - scan every N hours (default: 1). The simplest and
                 most useful: keeps the mascot/tray current without
                 anything more complex to configure.

  "daily"      - scan once per day at a specific clock time.
                 Stored as {"mode": "daily", "hour": 9, "minute": 0}
                 for 9:00 AM.

  "weekly"     - scan once per week on a specific day + time.
                 Stored as {"mode": "weekly", "weekday": 0, "hour": 9,
                 "minute": 0}. weekday: 0=Mon, 1=Tue … 6=Sun.

  "never"      - manual only. Auto-scan is completely disabled.

The scheduler is evaluated by main.py's once-per-minute QTimer - it
calls is_scan_due() and starts a silent background scan when True.
Recording the last-scan timestamp happens in record_scan_ran() after
a scan actually completes, not when it starts (so a scan that errors
mid-way doesn't erroneously reset the clock).
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timedelta

GRIX_DIR = os.path.expanduser("~/.local/share/grix")
SCHEDULE_FILE = os.path.join(GRIX_DIR, "schedule.json")

# Friendly day names, 0=Monday to match Python's datetime.weekday()
WEEKDAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday",
                 "Friday", "Saturday", "Sunday"]


@dataclass
class Schedule:
    mode: str = "interval"       # interval | daily | weekly | never
    interval_hours: int = 1      # used when mode == "interval"
    hour: int = 9                # clock hour (0-23), used for daily/weekly
    minute: int = 0              # clock minute (0-59), used for daily/weekly
    weekday: int = 0             # 0=Mon…6=Sun, used for weekly
    last_scan_at: str | None = None   # ISO-format datetime of last auto-scan


def _ensure_dir() -> None:
    os.makedirs(GRIX_DIR, exist_ok=True)


def load() -> Schedule:
    _ensure_dir()
    if not os.path.exists(SCHEDULE_FILE):
        return Schedule()
    try:
        with open(SCHEDULE_FILE) as f:
            data = json.load(f)
        return Schedule(
            mode=str(data.get("mode", "interval")),
            interval_hours=int(data.get("interval_hours", 1)),
            hour=int(data.get("hour", 9)),
            minute=int(data.get("minute", 0)),
            weekday=int(data.get("weekday", 0)),
            last_scan_at=data.get("last_scan_at"),
        )
    except (OSError, json.JSONDecodeError, ValueError, TypeError):
        return Schedule()


def save(schedule: Schedule) -> None:
    _ensure_dir()
    try:
        with open(SCHEDULE_FILE, "w") as f:
            json.dump({
                "mode": schedule.mode,
                "interval_hours": schedule.interval_hours,
                "hour": schedule.hour,
                "minute": schedule.minute,
                "weekday": schedule.weekday,
                "last_scan_at": schedule.last_scan_at,
            }, f, indent=2)
    except OSError:
        pass


def record_scan_ran() -> None:
    """Call this after a scheduled scan completes to reset the clock."""
    schedule = load()
    schedule.last_scan_at = datetime.now().isoformat()
    save(schedule)


def is_scan_due(schedule: Schedule | None = None) -> bool:
    """Return True if an auto-scan should start right now, False otherwise.

    Called every minute by main.py's idle timer. Deliberately cheap:
    reads from the already-loaded schedule object, does a quick
    datetime comparison, returns immediately.

    Considers a scan "due" if:
      - mode is "interval" and it's been >= interval_hours since the
        last auto-scan (or there has never been one)
      - mode is "daily" and today's scheduled time has passed but we
        haven't scanned since it passed
      - mode is "weekly" and this week's scheduled day/time has passed
        but we haven't scanned since it passed
      - mode is "never": always False
    """
    if schedule is None:
        schedule = load()
    if schedule.mode == "never":
        return False

    now = datetime.now()

    if schedule.last_scan_at is None:
        # Never scanned via auto-schedule - scan now to establish baseline
        return True

    try:
        last = datetime.fromisoformat(schedule.last_scan_at)
    except (ValueError, TypeError):
        return True  # corrupted timestamp - just scan

    if schedule.mode == "interval":
        return now >= last + timedelta(hours=schedule.interval_hours)

    if schedule.mode == "daily":
        # Due if: there is a clock time today that has already passed
        # AND the last scan was before that time today.
        target_today = now.replace(hour=schedule.hour, minute=schedule.minute,
                                   second=0, microsecond=0)
        return now >= target_today and last < target_today

    if schedule.mode == "weekly":
        # Due if: the most recent past occurrence of the target weekday
        # and time has passed AND the last scan was before it.
        days_back = (now.weekday() - schedule.weekday) % 7
        candidate = now.replace(hour=schedule.hour, minute=schedule.minute,
                                second=0, microsecond=0) - timedelta(days=days_back)
        # If that candidate is in the future (e.g. it's Monday 8 AM and
        # the target is Monday 9 AM), step back one full week
        if candidate > now:
            candidate -= timedelta(weeks=1)
        return last < candidate

    return False


def describe(schedule: Schedule) -> str:
    """Return a one-line human description of the schedule, shown under
    the schedule card in Settings so the user can confirm their choice
    at a glance."""
    if schedule.mode == "never":
        return "Auto-scan is off. Use the Scan button in System Sentinel to check manually."
    if schedule.mode == "interval":
        h = schedule.interval_hours
        if h == 1:
            return "Scanning automatically every hour."
        return f"Scanning automatically every {h} hours."
    if schedule.mode == "daily":
        return (f"Scanning once a day at "
                f"{_fmt_time(schedule.hour, schedule.minute)}.")
    if schedule.mode == "weekly":
        day = WEEKDAY_NAMES[schedule.weekday % 7]
        return (f"Scanning once a week, every {day} at "
                f"{_fmt_time(schedule.hour, schedule.minute)}.")
    return "Unknown schedule."


def _fmt_time(hour: int, minute: int) -> str:
    """Format a 24-hour hour+minute as 12-hour clock: '9:00 AM'."""
    am_pm = "AM" if hour < 12 else "PM"
    h12 = hour % 12 or 12
    return f"{h12}:{minute:02d} {am_pm}"
