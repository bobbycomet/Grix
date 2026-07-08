"""
Griffin Linux Suite integration, as an ordinary Grix plugin.

This is a working example of Grix's plugin API, and also the real
integration shipped with Grix for the rest of the Griffin Suite
(Kernel Autotune, Fan Hub, Process Sentry, and anything else built on
the same status-file convention).

HOW IT WORKS
------------
Any tool - Griffin Suite or otherwise - can drop a status file at:

    ~/.local/share/griffin/<tool-name>/status.json

containing one finding (a JSON object) or several (a JSON array of
objects), in this format:

{
  "id": "kernel_autotune_governor",
  "title": "CPU governor not optimized",
  "status": "yellow",                 // green | yellow | red
  "summary": "...",
  "why": "...",                        // optional
  "fixes": [
    {
      "id": "...",
      "title": "...",
      "explanation": "...",
      "commands": ["..."],
      "severity": "safe|approval|advanced",
      "needs_sudo": true,
      "rollback_hint": "...",
      "reason": "...",
      "risk": "low|medium|high",
      "expected_changes": ["..."],
      "related_lesson": ["beginner", "b1_what_is_linux"]   // optional
    }
  ]
}

There is NO fixed list of recognized tool names - <tool-name> can be
anything. Earlier versions of this integration only recognized a
hardcoded set of official Griffin Suite tool names; that's gone. Any
directory under ~/.local/share/griffin/ with a status.json that parses
correctly is picked up, whether it's an official Griffin Suite
component or a developer's own tool using the same convention.

If nothing has written a status file, this plugin contributes nothing
to a scan - there's no hard dependency on any other software being
installed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

from grix.modules.diagnostics import CheckResult, Fix, Status, SeverityLevel, RiskLevel

GRIFFIN_DATA_DIR = os.path.expanduser("~/.local/share/griffin")

_STATUS_MAP = {
    "green": Status.GREEN,
    "yellow": Status.YELLOW,
    "red": Status.RED,
    "unknown": Status.UNKNOWN,
}

_SEVERITY_MAP = {
    "safe": SeverityLevel.SAFE,
    "approval": SeverityLevel.APPROVAL,
    "advanced": SeverityLevel.ADVANCED,
}

_RISK_MAP = {
    "low": RiskLevel.LOW,
    "medium": RiskLevel.MEDIUM,
    "high": RiskLevel.HIGH,
}


@dataclass
class GriffinComponentStatus:
    key: str
    display_name: str
    status_file_found: bool
    check_results: list[CheckResult]


def _humanize(key: str) -> str:
    """Turn a directory name like 'kernel-autotune' into a friendly
    display name like 'Kernel Autotune', without needing it to be in
    any predefined list."""
    return key.replace("-", " ").replace("_", " ").title()


def _parse_fix(data: dict) -> Fix | None:
    try:
        related_lesson = None
        rl = data.get("related_lesson")
        if isinstance(rl, (list, tuple)) and len(rl) == 2:
            related_lesson = (str(rl[0]), str(rl[1]))

        return Fix(
            id=str(data["id"]),
            title=str(data["title"]),
            explanation=str(data.get("explanation", "")),
            commands=[str(c) for c in data.get("commands", [])],
            severity=_SEVERITY_MAP.get(str(data.get("severity", "approval")).lower(), SeverityLevel.APPROVAL),
            needs_sudo=bool(data.get("needs_sudo", True)),
            rollback_hint=data.get("rollback_hint"),
            reason=str(data.get("reason", "")),
            risk=_RISK_MAP.get(str(data.get("risk", "low")).lower(), RiskLevel.LOW),
            expected_changes=[str(c) for c in data.get("expected_changes", [])],
            related_lesson=related_lesson,
        )
    except (KeyError, TypeError, ValueError):
        return None


def _parse_status_file(component_key: str, path: str) -> list[CheckResult]:
    try:
        with open(path, "r") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return []

    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        return []

    results = []
    for item in data:
        if not isinstance(item, dict):
            continue
        try:
            fixes = [
                f for f in (_parse_fix(fd) for fd in item.get("fixes", []))
                if f is not None
            ]
            results.append(CheckResult(
                id=f"griffin_{component_key}_{item.get('id', 'unknown')}",
                title=str(item.get("title", _humanize(component_key))),
                status=_STATUS_MAP.get(str(item.get("status", "unknown")).lower(), Status.UNKNOWN),
                summary=str(item.get("summary", "")),
                details=str(item.get("details", "")),
                why=str(item.get("why", "")),
                fixes=fixes,
            ))
        except (KeyError, TypeError, ValueError):
            continue

    return results


def discover_component_statuses() -> list[GriffinComponentStatus]:
    """Scan ~/.local/share/griffin/ for ANY subdirectory containing a
    status.json - no fixed list of tool names. Used by Settings to
    show what's currently reporting in."""
    statuses: list[GriffinComponentStatus] = []
    if not os.path.isdir(GRIFFIN_DATA_DIR):
        return statuses

    try:
        entries = sorted(os.listdir(GRIFFIN_DATA_DIR))
    except OSError:
        return statuses

    for key in entries:
        component_dir = os.path.join(GRIFFIN_DATA_DIR, key)
        if not os.path.isdir(component_dir):
            continue
        status_file = os.path.join(component_dir, "status.json")
        found = os.path.isfile(status_file)
        results = _parse_status_file(key, status_file) if found else []
        statuses.append(GriffinComponentStatus(
            key=key,
            display_name=_humanize(key),
            status_file_found=found,
            check_results=results,
        ))
    return statuses


def griffin_suite_check() -> CheckResult:
    """A single rolled-up CheckResult summarizing every Griffin Suite
    (or Griffin-format) finding, for System Sentinel. Individual
    per-tool findings with their own fixes are reported as separate
    CheckResults via griffin_suite_findings() below; this one is a
    lightweight "is anything connected" summary."""
    statuses = discover_component_statuses()
    reporting = [s for s in statuses if s.status_file_found]

    if not statuses:
        return CheckResult(
            id="griffin_suite_summary",
            title="Griffin Suite Tools",
            status=Status.UNKNOWN,
            summary="No Griffin Suite (or Griffin-format) tools detected "
                    "on this system.",
        )

    if not reporting:
        names = ", ".join(s.display_name for s in statuses)
        return CheckResult(
            id="griffin_suite_summary",
            title="Griffin Suite Tools",
            status=Status.GREEN,
            summary=f"Detected but not currently reporting: {names}.",
        )

    names = ", ".join(s.display_name for s in reporting)
    return CheckResult(
        id="griffin_suite_summary",
        title="Griffin Suite Tools",
        status=Status.GREEN,
        summary=f"Connected and reporting: {names}. See individual "
                f"findings below if any need attention.",
    )


def griffin_suite_findings() -> list[CheckResult]:
    """Return one CheckResult per individual finding from any
    connected Griffin-format tool - these are the ones that can
    actually carry fixes, unlike the rolled-up summary above."""
    results = []
    for status in discover_component_statuses():
        results.extend(status.check_results)
    return results


def register(api) -> None:
    api.register_check(griffin_suite_check)
    # griffin_suite_findings() can return any number of results
    # depending on what other tools currently have to report - using
    # register_dynamic_checks (rather than register_check) means it's
    # re-evaluated fresh on every scan instead of being frozen at
    # plugin-load time.
    api.register_dynamic_checks(griffin_suite_findings)
