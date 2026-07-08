"""
Grix - "Explain This Error" Mode
====================================

A small pattern-matching knowledge base of common Linux/Ubuntu error
messages. Users can paste an error message (from a terminal, a log
file, or a crash dialog) and Grix will explain what it likely means,
in plain language, plus suggest diagnosis steps and link to any
related System Sentinel fixes or Academy lessons.

This is intentionally a knowledge base, not a live analysis tool - it
never runs commands on its own. Matching is done with simple
case-insensitive substring/regex patterns, ordered roughly from most
to least specific so the first match is usually the best one.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ErrorExplanation:
    id: str
    title: str
    explanation: str
    diagnosis_steps: list[str] = field(default_factory=list)
    related_check_id: str | None = None   # links to a CheckResult.id
    related_lesson: tuple[str, str] | None = None  # (track_id, lesson_id)
    category: str = "general"


# Broad categories of error this knowledge base covers, used to explain
# Grix's scope to users (both in the UI and in documentation) rather
# than leaving "doesn't recognize this" unexplained. Keep this in sync
# with the actual _register() calls below - it's deliberately a
# hand-maintained summary, not auto-derived, so it stays written in
# plain language rather than just listing internal pattern ids.
SCOPE_CATEGORIES: list[tuple[str, str]] = [
    (
        "Package management (APT/dpkg)",
        "Broken or held packages, interrupted installs, missing "
        "packages, and the package manager lock being held by another "
        "process.",
    ),
    (
        "Permissions and ownership",
        "\"Permission denied\" and related access-control errors for "
        "files, folders, and commands.",
    ),
    (
        "Disk and storage",
        "Running out of disk space, and errors that result from it "
        "(failed writes, failed installs).",
    ),
    (
        "Networking",
        "DNS/hostname resolution failures, and a port already being in "
        "use by another program.",
    ),
    (
        "Services and processes",
        "A systemd service failing to start, and crashes that produce "
        "a segmentation fault.",
    ),
    (
        "Shell basics",
        "\"Command not found\" and similar everyday terminal errors.",
    ),
]

SCOPE_EXCLUSIONS: list[str] = [
    "Application-specific errors from individual programs (a game "
    "crashing, a specific website not loading, a particular app's "
    "internal bug) - these number in the millions and are simply too "
    "specific for a general system knowledge base.",
    "Programming language errors and stack traces (Python tracebacks, "
    "compiler errors, etc.) - Grix is a system troubleshooter, not a "
    "development environment.",
    "Hardware failures (failing drives, GPU driver crashes, faulty "
    "RAM) - Grix can point you toward relevant logs, but diagnosing "
    "physical hardware problems is outside what a knowledge-base "
    "pattern match can responsibly do.",
    "Distro-specific errors from non-Debian/Ubuntu-based systems (Arch, "
    "Fedora, openSUSE, etc.) - package manager and service messages "
    "differ enough that Grix's explanations would often be wrong.",
    "Errors in a language other than English - matching is currently "
    "English-only.",
]


# Ordered list of (pattern, ErrorExplanation). Patterns are matched
# case-insensitively against the pasted text. First match wins.
_PATTERNS: list[tuple[re.Pattern, ErrorExplanation]] = []


def _register(pattern: str, explanation: ErrorExplanation) -> None:
    _PATTERNS.append((re.compile(pattern, re.IGNORECASE), explanation))


_register(
    r"unable to correct problems.*held broken packages",
    ErrorExplanation(
        id="held_broken_packages",
        category="Package management (APT/dpkg)",
        title="APT: held broken packages",
        explanation=(
            "APT found packages that can't be installed or upgraded "
            "together - their version requirements conflict. This often "
            "happens after an interrupted upgrade, after mixing software "
            "from different repositories (like a PPA) with the main "
            "Ubuntu repositories, or partway through a release upgrade."
        ),
        diagnosis_steps=[
            "Run System Sentinel's Package Manager Health check - it "
            "looks for exactly this kind of conflict and can offer a "
            "guided fix.",
            "Check what's currently broken with: apt-get check",
            "If you recently added a PPA or third-party repository, that "
            "is a common cause - removing it and re-running the fix can "
            "help.",
        ],
        related_check_id="package_manager",
        related_lesson=("beginner", "b12_installing_software"),
    ),
)

_register(
    r"sub-?process .*returned an error code",
    ErrorExplanation(
        id="dpkg_subprocess_error",
        category="Package management (APT/dpkg)",
        title="dpkg: sub-process returned an error code",
        explanation=(
            "A package's installation script (run automatically by dpkg "
            "while installing or removing it) exited with an error. The "
            "package itself may now be in a 'half-configured' state. This "
            "is usually fixable without losing data."
        ),
        diagnosis_steps=[
            "Run System Sentinel's Package Manager Health check - "
            "'Finish pending package configuration' addresses exactly "
            "this.",
            "If that doesn't resolve it, the full error usually names the "
            "specific package - searching for that package name plus "
            "'dpkg error' often finds others who hit the same issue.",
        ],
        related_check_id="package_manager",
        related_lesson=("intermediate", "i12_putting_it_together"),
    ),
)

_register(
    r"e: unable to locate package",
    ErrorExplanation(
        id="unable_to_locate_package",
        category="Package management (APT/dpkg)",
        title="APT: Unable to locate package",
        explanation=(
            "APT doesn't know about a package with this name. Either "
            "there's a typo, the package is in a repository you haven't "
            "added yet, or your package list is out of date."
        ),
        diagnosis_steps=[
            "Double-check the spelling of the package name - Linux "
            "package names are case-sensitive and often use hyphens.",
            "Run 'sudo apt update' to refresh your package list (System "
            "Sentinel's 'Refresh package lists' fix does this safely).",
            "Search for the package name at packages.ubuntu.com to "
            "confirm it exists and find out which repository provides "
            "it.",
        ],
        related_check_id="package_manager",
        related_lesson=("beginner", "b12_installing_software"),
    ),
)

_register(
    r"permission denied",
    ErrorExplanation(
        id="permission_denied",
        category="Permissions and ownership",
        title="Permission denied",
        explanation=(
            "Your user account doesn't have permission to read, write, or "
            "execute the file or directory involved. This is one of the "
            "most common Linux messages and is usually expected behavior "
            "- it's the system protecting files that belong to another "
            "user or to the system itself."
        ),
        diagnosis_steps=[
            "If you expect to be able to access this file, check who owns "
            "it with: ls -l <path>",
            "If the file should belong to you but is owned by 'root', "
            "System Sentinel's File Permissions check can help fix "
            "ownership for files in your home directory.",
            "If the action genuinely requires administrator rights (like "
            "editing a system configuration file), prefix the command "
            "with 'sudo' - but make sure you understand what the command "
            "does first.",
            "Avoid 'fix everything' permission commands like 'chmod -R "
            "777' - they remove important protections.",
        ],
        related_check_id="permissions",
        related_lesson=("intermediate", "i3_permissions"),
    ),
)

_register(
    r"no space left on device",
    ErrorExplanation(
        id="no_space_left",
        category="Disk and storage",
        title="No space left on device",
        explanation=(
            "A partition is completely full, so the operation that "
            "triggered this couldn't write the data it needed. This can "
            "also cause unrelated-looking failures (a browser failing to "
            "save a download, a package install failing partway through, "
            "etc.), since almost everything needs to write something to "
            "disk."
        ),
        diagnosis_steps=[
            "Run System Sentinel's Disk Space check to see how full your "
            "drive is and get safe cleanup suggestions.",
            "Check usage per-folder with: du -h --max-depth=1 /home/"
            "yourname | sort -rh",
            "If the disk was nearly full and something failed partway "
            "through, re-run that operation after freeing up space - it "
            "often completes successfully the second time.",
        ],
        related_check_id="disk",
        related_lesson=("intermediate", "i7_disk_usage"),
    ),
)

_register(
    r"could not resolve host|temporary failure in name resolution",
    ErrorExplanation(
        id="dns_resolution_failure",
        category="Networking",
        title="Could not resolve host / DNS failure",
        explanation=(
            "Your system couldn't translate a domain name (like "
            "example.com) into a numeric address. This usually means "
            "either your internet connection is down, or specifically "
            "DNS (name lookup) isn't working even though the connection "
            "itself is fine."
        ),
        diagnosis_steps=[
            "Run System Sentinel's Network Connectivity check - it tests "
            "the connection and DNS separately.",
            "Try 'ping 1.1.1.1' (tests the connection by number) versus "
            "'ping google.com' (tests DNS by name) to narrow it down.",
            "If only DNS fails, clearing the DNS cache (System Sentinel's "
            "'Clear the DNS cache' fix) often resolves it.",
        ],
        related_check_id="network",
        related_lesson=("intermediate", "i11_networking"),
    ),
)

_register(
    r"failed to start|job for .* failed",
    ErrorExplanation(
        id="service_failed_to_start",
        category="Services and processes",
        title="A service failed to start",
        explanation=(
            "A systemd service (a background program that handles things "
            "like networking, printing, or hardware) didn't start "
            "successfully. The service is now in a 'failed' state until "
            "it's restarted or the underlying problem is fixed."
        ),
        diagnosis_steps=[
            "Run System Sentinel's System Services check - it lists any "
            "failed services and can offer to restart them.",
            "View the service's own logs for details: journalctl -u "
            "<service-name>",
            "If it keeps failing after a restart, the logs usually point "
            "to a specific cause - a missing config file, a port "
            "conflict, or a hardware device not being ready.",
        ],
        related_check_id="services",
        related_lesson=("intermediate", "i5_systemd"),
    ),
)

_register(
    r"command not found",
    ErrorExplanation(
        id="command_not_found",
        category="Shell basics",
        title="Command not found",
        explanation=(
            "The shell looked for a program with this name in every "
            "folder listed in your PATH and didn't find it. Either the "
            "program isn't installed, there's a typo, or it's installed "
            "somewhere not in your PATH."
        ),
        diagnosis_steps=[
            "Check for typos - Linux commands are case-sensitive.",
            "If the program should be installed, try installing it: sudo "
            "apt install <name> (the package name is sometimes different "
            "from the command name).",
            "If you just installed something and it's still not found, "
            "try opening a new terminal - PATH changes sometimes only "
            "apply to new sessions.",
            "If you meant to run a script in the current folder, remember "
            "it needs './' in front, like './script.sh'.",
        ],
        related_lesson=("intermediate", "i8_environment"),
    ),
)

_register(
    r"e: could not get lock|unable to acquire the dpkg frontend lock",
    ErrorExplanation(
        id="apt_lock",
        category="Package management (APT/dpkg)",
        title="APT/dpkg lock held by another process",
        explanation=(
            "Only one package-management operation can run at a time. "
            "This error means something else - often a background update "
            "checker, or another terminal - already has the package "
            "database locked."
        ),
        diagnosis_steps=[
            "Wait a minute and try again - background update checks "
            "usually finish quickly.",
            "Check if anything is actively using apt/dpkg: ps aux | grep "
            "-i -E 'apt|dpkg'",
            "Avoid commands that force-remove the lock file unless you're "
            "sure nothing is actually running - removing it while a "
            "process is genuinely using it can corrupt the package "
            "database.",
        ],
        related_check_id="package_manager",
        related_lesson=("beginner", "b12_installing_software"),
    ),
)

_register(
    r"segmentation fault|core dumped",
    ErrorExplanation(
        id="segfault",
        category="Services and processes",
        title="Segmentation fault (core dumped)",
        explanation=(
            "A program tried to access memory it wasn't allowed to and "
            "crashed. This is almost always a bug in that program (or one "
            "of its libraries) rather than something wrong with your "
            "overall system, though a corrupted installation or a "
            "hardware issue (rarely) can also cause it."
        ),
        diagnosis_steps=[
            "Try updating the program and its dependencies - segfaults "
            "are often fixed in newer versions: sudo apt update && sudo "
            "apt upgrade",
            "Check the system journal around the time of the crash for "
            "more context: journalctl -b | grep -i <program name>",
            "If it happens consistently with one specific file or action, "
            "that's useful information to include if you report the bug "
            "to the program's developers.",
        ],
        related_lesson=("intermediate", "i6_logs"),
    ),
)

_register(
    r"e: dpkg was interrupted",
    ErrorExplanation(
        id="dpkg_interrupted",
        category="Package management (APT/dpkg)",
        title="dpkg was interrupted",
        explanation=(
            "A previous package operation didn't finish - usually because "
            "the system was shut down, restarted, or the terminal was "
            "closed midway through an install or update."
        ),
        diagnosis_steps=[
            "Run System Sentinel's Package Manager Health check and apply "
            "'Finish pending package configuration' - this is exactly "
            "what that fix is for.",
        ],
        related_check_id="package_manager",
        related_lesson=("intermediate", "i12_putting_it_together"),
    ),
)

_register(
    r"address already in use",
    ErrorExplanation(
        id="address_in_use",
        category="Networking",
        title="Address already in use",
        explanation=(
            "A program tried to start a network service on a port that's "
            "already being used by another program. Only one program can "
            "listen on a given port at a time."
        ),
        diagnosis_steps=[
            "Find out what's using the port (replace 8080 with the port "
            "in the error): sudo ss -tulpn | grep 8080",
            "If it's an old instance of the same program that didn't shut "
            "down cleanly, stopping that process (or the related systemd "
            "service) frees the port.",
        ],
        related_lesson=("intermediate", "i4_processes"),
    ),
)


def explain(text: str) -> ErrorExplanation | None:
    """Return the best-matching explanation for pasted error text, or None."""
    text = text.strip()
    if not text:
        return None
    for pattern, explanation in _PATTERNS:
        if pattern.search(text):
            return explanation
    return None


def all_known_patterns() -> list[ErrorExplanation]:
    """Return all known explanations, e.g. for a 'browse common errors' list."""
    return [exp for _, exp in _PATTERNS]
