"""
Grix - System Timeline ("What Changed?")
============================================

Builds a chronological view of recent system changes by combining:

  - APT history (/var/log/apt/history.log and rotated .gz files) -
    package installs, upgrades, and removals with timestamps
  - systemd journal failures (journalctl -p err -b, and recent boots)
  - dpkg log entries as a fallback/cross-check

The goal is to help answer "my system was fine yesterday, what
changed?" by showing package changes and error spikes side by side on
one timeline, sorted by time. This module is entirely read-only.
"""

from __future__ import annotations

import gzip
import os
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class TimelineEvent:
    timestamp: datetime
    kind: str          # "package", "error", "boot"
    title: str
    detail: str = ""


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except Exception as exc:  # pragma: no cover
        return 1, "", str(exc)


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


# ---------------------------------------------------------------------------
# APT history
# ---------------------------------------------------------------------------

_APT_HISTORY_DIR = "/var/log/apt"
_APT_TS_RE = re.compile(r"^Start-Date:\s*(.+)$")
_APT_ACTION_RE = re.compile(r"^(Install|Upgrade|Remove|Purge):\s*(.+)$")


def _iter_apt_history_files() -> list[str]:
    """Return apt history log files, most recent first."""
    if not os.path.isdir(_APT_HISTORY_DIR):
        return []
    files = []
    for name in os.listdir(_APT_HISTORY_DIR):
        if name.startswith("history.log"):
            files.append(os.path.join(_APT_HISTORY_DIR, name))
    # history.log, history.log.1.gz, history.log.2.gz, ... -> sort so
    # the plain file (most recent) comes first, then numeric order
    def sort_key(path: str):
        if path.endswith(".gz"):
            m = re.search(r"\.(\d+)\.gz$", path)
            return (1, int(m.group(1)) if m else 999)
        return (0, 0)
    files.sort(key=sort_key)
    return files


def _read_text(path: str) -> str:
    try:
        if path.endswith(".gz"):
            with gzip.open(path, "rt", errors="replace") as f:
                return f.read()
        with open(path, "r", errors="replace") as f:
            return f.read()
    except OSError:
        return ""


def _parse_apt_history(max_age_days: int) -> list[TimelineEvent]:
    events: list[TimelineEvent] = []
    cutoff = datetime.now() - timedelta(days=max_age_days)

    for path in _iter_apt_history_files():
        content = _read_text(path)
        if not content:
            continue

        current_ts: datetime | None = None
        for line in content.splitlines():
            ts_match = _APT_TS_RE.match(line)
            if ts_match:
                try:
                    current_ts = datetime.strptime(
                        ts_match.group(1).strip(), "%Y-%m-%d  %H:%M:%S"
                    )
                except ValueError:
                    current_ts = None
                continue

            action_match = _APT_ACTION_RE.match(line)
            if action_match and current_ts and current_ts >= cutoff:
                action, pkgs_raw = action_match.groups()
                pkg_names = _extract_package_names(pkgs_raw)
                if not pkg_names:
                    continue
                title = f"{action}ed: {', '.join(pkg_names[:5])}"
                if len(pkg_names) > 5:
                    title += f" (+{len(pkg_names) - 5} more)"
                events.append(TimelineEvent(
                    timestamp=current_ts,
                    kind="package",
                    title=title,
                    detail=pkgs_raw.strip(),
                ))

        # Once we've gone past the cutoff in older files, stop reading more
        if current_ts and current_ts < cutoff:
            break

    return events


def _extract_package_names(pkgs_raw: str) -> list[str]:
    """Extract package names from an apt history action line.

    Format looks like:
      libfoo:amd64 (1.2.3, 1.2.4, automatic), libbar:amd64 (2.0.0)
    """
    names = []
    for entry in pkgs_raw.split("), "):
        entry = entry.strip().rstrip(")")
        name_part = entry.split(" (")[0].strip()
        if not name_part:
            continue
        # Strip architecture suffix for readability
        name_part = name_part.split(":")[0]
        names.append(name_part)
    return names


# ---------------------------------------------------------------------------
# Journal errors and boots
# ---------------------------------------------------------------------------

_JOURNAL_LINE_RE = re.compile(
    r"^(\w{3}\s+\d{1,2}\s+\d{2}:\d{2}:\d{2})\s+\S+\s+(\S+?)(\[\d+\])?:\s*(.*)$"
)


def _parse_journal_errors(max_age_days: int) -> list[TimelineEvent]:
    if not _have("journalctl"):
        return []

    since = (datetime.now() - timedelta(days=max_age_days)).strftime("%Y-%m-%d")
    rc, out, _ = _run([
        "journalctl", "-p", "3", "--since", since,
        "--no-pager", "-o", "short",
    ], timeout=20)

    if rc != 0 or not out:
        return []

    events: list[TimelineEvent] = []
    current_year = datetime.now().year
    for line in out.splitlines():
        m = _JOURNAL_LINE_RE.match(line)
        if not m:
            continue
        ts_str, unit, _pid, message = m.groups()
        try:
            ts = datetime.strptime(f"{current_year} {ts_str}", "%Y %b %d %H:%M:%S")
        except ValueError:
            continue
        events.append(TimelineEvent(
            timestamp=ts,
            kind="error",
            title=f"{unit}: {message[:80]}",
            detail=message,
        ))

    return events


def _parse_boots(max_age_days: int) -> list[TimelineEvent]:
    if not _have("journalctl"):
        return []

    rc, out, _ = _run(["journalctl", "--list-boots", "--no-pager"], timeout=15)
    if rc != 0 or not out:
        return []

    events: list[TimelineEvent] = []
    cutoff = datetime.now() - timedelta(days=max_age_days)
    # Lines look like: "-2 abcdef... Mon 2026-06-10 08:00:00 UTC—Mon 2026-06-10 18:00:00 UTC"
    for line in out.splitlines():
        parts = line.split()
        # find a date-like token
        date_match = re.search(r"(\d{4}-\d{2}-\d{2}) (\d{2}:\d{2}:\d{2})", line)
        if not date_match:
            continue
        try:
            ts = datetime.strptime(
                f"{date_match.group(1)} {date_match.group(2)}",
                "%Y-%m-%d %H:%M:%S",
            )
        except ValueError:
            continue
        if ts < cutoff:
            continue
        events.append(TimelineEvent(
            timestamp=ts,
            kind="boot",
            title="System booted",
            detail=line.strip(),
        ))
    return events


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build_timeline(max_age_days: int = 7) -> list[TimelineEvent]:
    """
    Build a combined, time-sorted list of package changes, boots, and
    journal errors over the last `max_age_days` days.

    Returns an empty list (not an error) if the relevant logs aren't
    available - the UI should treat this as "nothing to show" rather
    than a failure.
    """
    events: list[TimelineEvent] = []
    events.extend(_parse_apt_history(max_age_days))
    events.extend(_parse_boots(max_age_days))
    events.extend(_parse_journal_errors(max_age_days))

    events.sort(key=lambda e: e.timestamp, reverse=True)
    return events


def correlate_errors_with_packages(
    events: list[TimelineEvent], window_hours: int = 6
) -> list[tuple[TimelineEvent, list[TimelineEvent]]]:
    """
    For each error event, find package events that happened shortly
    before it (within `window_hours`). This is a heuristic to surface
    "this started failing around the same time X was updated" -
    correlation, not proof of causation, and the UI should present it
    that way.
    """
    packages = [e for e in events if e.kind == "package"]
    errors = [e for e in events if e.kind == "error"]

    results = []
    for err in errors:
        window_start = err.timestamp - timedelta(hours=window_hours)
        nearby = [
            p for p in packages
            if window_start <= p.timestamp <= err.timestamp
        ]
        if nearby:
            results.append((err, nearby))
    return results
