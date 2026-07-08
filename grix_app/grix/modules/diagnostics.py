"""
Grix System Sentinel - Diagnostics & Repair Backend
=====================================================

Design philosophy (per Grix's guiding principles):
  1. Detect problems
  2. Explain what was found, in plain language
  3. Offer safe fixes
  4. Require user confirmation before anything is changed
  5. Log every action and provide rollback hints where possible

Every check returns a CheckResult. Every fix is a Fix object that
knows its own severity, the exact command(s) it will run, a
human explanation, and whether it needs sudo.

Nothing in this file runs a command without it being explicitly
triggered by the UI, and destructive/advanced fixes always carry
severity SeverityLevel.ADVANCED so the UI can demand extra
confirmation.
"""

from __future__ import annotations

import getpass
import os
import re
import shlex
import shutil
import subprocess
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable, Optional


class Status(Enum):
    GREEN = "green"     # all good
    YELLOW = "yellow"   # minor issue, not urgent
    RED = "red"         # needs attention
    UNKNOWN = "unknown"


class SeverityLevel(Enum):
    SAFE = "safe"               # green - clean logs, clear cache, refresh lists
    APPROVAL = "approval"        # yellow - install drivers, restart services, remove packages
    ADVANCED = "advanced"        # red - filesystem repair, kernel changes, bootloader


class RiskLevel(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


def _strip_sudo_prefix(command: str) -> str:
    """Return a command with a leading 'sudo ' removed, if present."""
    command = command.strip()
    if command.startswith("sudo "):
        return command[len("sudo "):]
    return command


def sudo_form(command: str) -> str:
    """Return the sudo-prefixed form of a command, for users who prefer
    to copy/paste it into their own terminal."""
    bare = _strip_sudo_prefix(command)
    return f"sudo {bare}"


def pkexec_form(command: str) -> str:
    """Return the pkexec-prefixed form of a command. pkexec (PolicyKit)
    is what Grix actually runs privileged commands through by default -
    it shows a native graphical authentication prompt instead of asking
    for a password in a terminal that may not be visible. Falls back to
    sudo automatically at execution time if pkexec isn't installed."""
    bare = _strip_sudo_prefix(command)
    return f"pkexec {bare}"


def privileged_command_variants(command: str) -> tuple[str, str]:
    """Return (pkexec_form, sudo_form) for a command that needs
    elevated privileges, for display in the Repair Preview so users can
    copy whichever they prefer."""
    return pkexec_form(command), sudo_form(command)


# ---------------------------------------------------------------------------
# grix-helper integration
# ---------------------------------------------------------------------------
# If Grix's PolicyKit policy + helper script are installed (see
# policykit/install.sh), privileged commands are run through
# `pkexec grix-helper <subcommand> [args]` instead of
# `pkexec <bare command>`. This is the more tightly-scoped path: the
# PolicyKit policy only grants access to grix-helper, and grix-helper
# itself only accepts this fixed, allowlisted set of subcommands - so
# authenticating never grants a generic root shell, only these specific
# well-understood maintenance actions.
#
# Each entry maps a bare (sudo-stripped) command PREFIX to the
# grix-helper subcommand that performs the same action. Commands with
# arguments (package names, unit names, etc.) are handled by stripping
# the matched prefix and passing the remainder through unchanged -
# grix-helper does its own validation of those arguments.
_HELPER_COMMAND_MAP: list[tuple[str, str]] = [
    ("dpkg --configure -a", "dpkg-configure"),
    ("apt --fix-broken install", "fix-broken"),
    ("apt-get --fix-broken install", "fix-broken"),
    ("apt update && sudo apt upgrade -y", "apt-upgrade"),
    ("apt update", "apt-update"),
    ("apt clean", "apt-clean"),
    ("apt autoremove", "apt-autoremove"),
    ("journalctl --vacuum-time=", "journal-vacuum-time "),
    ("journalctl --vacuum-size=", "journal-vacuum-size "),
    ("systemctl restart NetworkManager", "restart-networkmanager"),
    ("systemctl restart ", "restart-service "),
    ("resolvectl flush-caches", "flush-dns"),
    ("ufw enable", "enable-firewall"),
    ("ufw status", "firewall-status"),
    ("apt remove --purge ", "remove-packages "),
]

_CHOWN_RE = re.compile(r"^chown\s+([a-z_][a-z0-9_-]*):\1\s+(.+)$")


def _have_grix_helper() -> bool:
    return _have("grix-helper") or shutil.which("/usr/bin/grix-helper") is not None


def _to_helper_invocation(bare_command: str) -> Optional[str]:
    """If grix-helper is installed and recognizes this command, return
    the equivalent `grix-helper <subcommand> ...` invocation. Returns
    None if there's no mapping (caller should fall back to running the
    bare command directly under pkexec/sudo instead)."""
    chown_match = _CHOWN_RE.match(bare_command)
    if chown_match:
        username, paths = chown_match.groups()
        return f"grix-helper chown-home {username} {paths}"

    for prefix, helper_form in _HELPER_COMMAND_MAP:
        if bare_command == prefix.rstrip():
            return f"grix-helper {helper_form.rstrip()}"
        if prefix.endswith((" ", "=")) and bare_command.startswith(prefix):
            remainder = bare_command[len(prefix):]
            return f"grix-helper {helper_form}{remainder}"
    return None


def privileged_run_command(bare_command: str) -> str:
    """Return the actual command Grix will execute for a privileged
    action: through grix-helper if installed (preferred, narrower
    privilege scope), otherwise the bare command directly. Callers
    still need to prefix this with pkexec or sudo - see apply_fix."""
    helper_invocation = _to_helper_invocation(bare_command) if _have_grix_helper() else None
    return helper_invocation if helper_invocation else bare_command


def display_command_for_fix_preview(command: str) -> str:
    """Return the command exactly as Grix will execute it (including
    pkexec and, if installed, grix-helper), for display in the Repair
    Preview - so what's shown always matches what actually runs.
    Non-privileged commands are returned unchanged."""
    if not command.strip().startswith("sudo "):
        return command
    bare = _strip_sudo_prefix(command)
    target = privileged_run_command(bare)
    return f"pkexec {target}"


@dataclass
class FixOption:
    """One selectable item within a checkbox-style fix (e.g. one old kernel)."""
    id: str
    label: str
    detail: str = ""           # e.g. "Frees ~310MB"
    protected: bool = False     # if True, cannot be selected (e.g. current kernel)
    protected_reason: str = ""  # shown when protected


@dataclass
class Fix:
    """A single safe-repair action that Grix can offer the user."""
    id: str
    title: str
    explanation: str
    commands: list[str]
    severity: SeverityLevel
    needs_sudo: bool = True
    rollback_hint: Optional[str] = None

    # --- Repair Preview fields ---
    reason: str = ""                 # short "why Grix wants to do this"
    risk: RiskLevel = RiskLevel.LOW
    expected_changes: list[str] = field(default_factory=list)

    # --- Learn from this repair ---
    related_lesson: Optional[tuple[str, str]] = None  # (track_id, lesson_id)

    # --- Checkbox-style fixes (e.g. "remove these old kernels") ---
    # If options is non-empty, the UI shows a checklist instead of a
    # single apply button. `commands` becomes a template where
    # {selected} is replaced with the chosen option ids/labels.
    options: list[FixOption] = field(default_factory=list)
    command_template: Optional[str] = None  # e.g. "sudo apt remove {selected}"


@dataclass
class CheckResult:
    """The result of running one diagnostic check."""
    id: str
    title: str
    status: Status
    summary: str
    details: str = ""
    fixes: list[Fix] = field(default_factory=list)
    raw_output: str = ""
    why: str = ""  # "Why did this happen?" plain-language background

    # If True, this result represents a critical situation that should
    # always be shown even if the user has snoozed this check (e.g.
    # disk space reaching 95% full). Individual checks set this based
    # on their own thresholds; see check_disk_space() for an example.
    force_override: bool = False


def _run(cmd: list[str], timeout: int = 15) -> tuple[int, str, str]:
    """Run a read-only command and capture output. Never raises.

    Forces LC_ALL=C and LANG=C so every tool's output is in plain
    English regardless of the user's system locale. This is important
    for all string-matching diagnostics - ufw, dpkg, apt, journalctl,
    systemctl, etc. all translate their output when a non-English
    locale is configured, which would silently break any check that
    searches for specific English words or phrases in their output
    (e.g. "inactive", "broken packages", "failed", "active").
    """
    try:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        env["LANG"] = "C"
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"
    except Exception as exc:  # pragma: no cover - defensive
        return 1, "", str(exc)


def _have(binary: str) -> bool:
    return shutil.which(binary) is not None


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------

def check_package_manager() -> CheckResult:
    """Detect interrupted installs, broken deps, held packages.

    Also detects the common post-boot race condition where
    unattended-upgrades or apt-daily.service holds the dpkg lock,
    causing confusing errors if the user tries to run apt while
    background updates are still in progress.
    """
    if not _have("dpkg"):
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.UNKNOWN,
            summary="dpkg was not found, so this check only applies to "
                    "Debian/Ubuntu-based systems.",
        )

    # APT lock race condition check - must happen FIRST.
    # Many Ubuntu/Debian systems run unattended-upgrades shortly after
    # boot (via apt-daily.service). If a user opens Grix immediately
    # after booting, the dpkg lock-frontend will be held by the
    # background updater, and dpkg/apt commands will appear to fail
    # or report confusing partial results. A clear "please wait"
    # message is much more helpful than false "broken packages" reports.
    LOCK_FILES = [
        "/var/lib/dpkg/lock-frontend",
        "/var/lib/dpkg/lock",
        "/var/cache/apt/archives/lock",
    ]
    # fuser returns exit code 0 when a process has the file open.
    # It needs no root to check lock files that exist as readable.
    # If fuser isn't available, fall through to the normal checks.
    if _have("fuser"):
        for lock_path in LOCK_FILES:
            rc_fuser, _, _ = _run(["fuser", lock_path])
            if rc_fuser == 0:
                # A process holds the lock. Try to identify which one.
                holder = "another process"
                rc_ps, ps_out, _ = _run(["fuser", "-v", lock_path])
                # fuser -v output: look for process names like
                # unattended-upgrade, apt, dpkg in the output
                for daemon in ("unattended-upgrade", "apt", "dpkg", "update-manager", "software"):
                    if daemon in ps_out.lower():
                        holder = daemon
                        break

                return CheckResult(
                    id="package_manager",
                    title="Package Manager Health",
                    status=Status.YELLOW,
                    summary=(
                        f"The package manager is currently in use by "
                        f"{holder}. This is normal right after booting "
                        f"- Ubuntu/Debian automatically install security "
                        f"updates in the background. Wait a few minutes "
                        f"and then run a new scan."
                    ),
                    why=(
                        "Ubuntu and Debian-based systems use a service "
                        "called 'unattended-upgrades' to automatically "
                        "install important security updates in the "
                        "background, usually shortly after each boot. "
                        "While it's running, it holds an exclusive lock on "
                        "the package manager so nothing else can use it at "
                        "the same time. This is by design - it prevents "
                        "two things from modifying packages simultaneously "
                        "and causing corruption."
                    ),
                )

    issues = []
    fixes: list[Fix] = []

    # dpkg -l output lines look like:
    #   ii  package-name  1.2.3  amd64  Description...
    #   rc  old-package   1.0.0  amd64  Description...
    # The first column is Desired+Status+Err (3 chars), e.g. "ii ", "rc ".
    # "rc" (removed, config files remain) is a NORMAL, harmless state -
    # not an interrupted install - so it must NOT be flagged here.
    # Genuinely broken/interrupted states use uppercase letters in the
    # Status or Err position: "iU" (unpacked, not configured), "iF"
    # (half-configured), "pH" (half-installed), and any line whose 3rd
    # character (Err) is "R" (reinstall required) - the uppercase
    # convention dpkg itself documents as "bad".
    rc, out, _ = _run(["dpkg", "-l"])
    half_configured = []
    for line in out.splitlines():
        if len(line) < 3:
            continue
        status_field = line[:3]
        # Only consider lines that look like real package status rows
        # (first char is one of dpkg's desired-action codes)
        if status_field[0] not in "uirpUhH":
            continue
        # Bad states: uppercase Status char (position 2) signals
        # unpacked/half-configured/half-installed, or an Err flag (R) at
        # position 3 meaning reinstall required. Lowercase-only status
        # like "ii " or "rc " is healthy.
        status_char = status_field[1] if len(status_field) > 1 else ""
        err_char = status_field[2] if len(status_field) > 2 else ""
        if status_char.isupper() or err_char == "R":
            half_configured.append(line)
    if half_configured:
        issues.append(
            f"{len(half_configured)} package(s) are stuck mid-installation "
            f"or only partially removed."
        )
        fixes.append(Fix(
            id="dpkg_configure",
            title="Finish pending package configuration",
            explanation=(
                "Linux installs software through a system called APT, which "
                "uses dpkg underneath to unpack and configure programs. "
                "Sometimes an installation gets interrupted (for example, a "
                "shutdown during an update), leaving packages half-set-up. "
                "This command finishes configuring anything that was left "
                "incomplete."
            ),
            commands=["sudo dpkg --configure -a"],
            severity=SeverityLevel.SAFE,
            rollback_hint="This only finishes configuration steps that were "
                           "already queued; there is nothing to roll back.",
            reason="Completes package setups that were interrupted partway "
                   "through, usually by a shutdown or crash during an "
                   "update.",
            risk=RiskLevel.LOW,
            expected_changes=[
                f"Finish configuring {len(half_configured)} package(s) "
                f"left in an incomplete state",
                "No packages are installed, removed, or upgraded",
            ],
            related_lesson=("intermediate", "i12_putting_it_together"),
        ))

    # Broken dependencies.
    #
    # IMPORTANT: apt-get check's exit code alone is not a reliable
    # signal. Run without root (which is how Grix runs all read-only
    # checks), it can fail to access /var/lib/apt/lists or
    # /var/cache/apt/archives and return a non-zero exit purely because
    # of a permission/lock error - NOT because anything is actually
    # broken. Treating that as "broken dependencies" caused Grix to
    # suggest 'apt --fix-broken install' forever, even right after a
    # user confirmed (correctly, with sudo) that nothing needed fixing.
    #
    # dpkg --audit is a much more reliable signal here: it only reads
    # dpkg's own status database (no apt locks, no root needed) and
    # prints package names only when something is genuinely
    # half-installed, unpacked-but-unconfigured, or otherwise broken.
    # An empty result means dpkg itself considers everything fine,
    # regardless of what apt-get check's exit code says.
    audit_rc, audit_out, audit_err = _run(["dpkg", "--audit"])
    has_real_audit_findings = bool(audit_out.strip())

    rc, out, err = _run(["apt-get", "check"])
    combined_output = f"{out}\n{err}".lower()

    permission_or_lock_issue = any(phrase in combined_output for phrase in (
        "permission denied",
        "are you root",
        "could not open lock",
        "unable to lock",
        "unable to acquire",
    ))

    dependency_problem_markers = (
        "unmet dependencies",
        "broken packages",
        "depends on",
        "but it is not",
        "but it is not installed",
    )
    looks_like_real_dependency_problem = any(
        marker in combined_output for marker in dependency_problem_markers
    )

    # Only report a real problem when dpkg's own audit agrees something
    # is broken, OR apt-get check's output describes an actual
    # dependency problem in plain language (not just a lock/permission
    # failure that happened to return non-zero).
    if has_real_audit_findings or (rc != 0 and looks_like_real_dependency_problem and not permission_or_lock_issue):
        issues.append("Some installed packages have broken or missing dependencies.")
        fixes.append(Fix(
            id="fix_broken",
            title="Repair broken dependencies",
            explanation=(
                "Some packages depend on other packages to work correctly. "
                "If one of those dependencies is missing or the wrong "
                "version, APT marks things as 'broken'. This command finds "
                "and installs whatever is missing to resolve the problem."
            ),
            commands=["sudo apt --fix-broken install"],
            severity=SeverityLevel.APPROVAL,
            rollback_hint="Packages that get installed to fix dependencies "
                           "can be removed again with 'sudo apt remove "
                           "<package>' if needed.",
            reason="Your package manager reported that some installed "
                   "packages have unmet dependencies, which can prevent "
                   "future installs and upgrades from working.",
            risk=RiskLevel.LOW,
            expected_changes=[
                "Install any missing dependency packages",
                "Complete configuration of any affected packages",
                "May remove a small number of conflicting packages if "
                "that's the only way to resolve the conflict (APT will "
                "list these before they're applied)",
            ],
            related_lesson=("intermediate", "i12_putting_it_together"),
        ))

    # Stale package lists (best-effort heuristic: check apt cache age).
    # An empty list (never refreshed at all) is a real issue worth
    # flagging. Lists that are merely old (>14 days) are common and not
    # urgent, so they get a quiet "Safe" suggestion without forcing the
    # whole check to YELLOW - consistent with not nagging about
    # non-urgent maintenance items.
    rc, out, _ = _run(["find", "/var/lib/apt/lists", "-maxdepth", "1", "-type", "f"])
    list_count = len([l for l in out.splitlines() if l.strip()])

    list_is_stale = False
    if list_count == 0:
        issues.append("Your package lists look empty or have never been refreshed.")
        list_is_stale = True
    else:
        rc, out, _ = _run([
            "find", "/var/lib/apt/lists", "-maxdepth", "1", "-type", "f",
            "-mtime", "+14",
        ])
        old_list_count = len([l for l in out.splitlines() if l.strip()])
        if old_list_count > 0 and old_list_count >= list_count:
            list_is_stale = True

    if list_is_stale:
        fixes.append(Fix(
            id="apt_update",
            title="Refresh package lists",
            explanation=(
                "APT keeps a local list of what software is available from "
                "your configured repositories. Refreshing it makes sure you "
                "see the latest available versions before installing or "
                "updating anything."
            ),
            commands=["sudo apt update"],
            severity=SeverityLevel.SAFE,
            rollback_hint="This only downloads new index data; nothing on "
                           "your system changes.",
            reason="Keeps APT's view of available software current so "
                   "other checks and fixes (like available updates) are "
                   "accurate.",
            risk=RiskLevel.LOW,
            expected_changes=[
                "Download the latest package index from your configured "
                "repositories",
                "No software is installed, removed, or upgraded",
            ],
            related_lesson=("beginner", "b12_installing_software"),
        ))

    # Cache size - only suggest clearing it once it's grown large enough
    # to matter (>150MB), not as a perpetual "you could do this" nag.
    cache_size = "unknown"
    cache_size_bytes = 0
    rc, out, _ = _run(["du", "-sb", "/var/cache/apt/archives"])
    if rc == 0 and out:
        try:
            cache_size_bytes = int(out.split()[0])
        except (ValueError, IndexError):
            cache_size_bytes = 0

    CACHE_THRESHOLD_BYTES = 150 * 1024 * 1024  # 150MB

    if cache_size_bytes > 0:
        cache_size_mb = cache_size_bytes / (1024 * 1024)
        cache_size = f"{cache_size_mb:.0f}MB"

    if cache_size_bytes >= CACHE_THRESHOLD_BYTES:
        fixes.append(Fix(
            id="apt_clean",
            title="Clear downloaded package cache",
            explanation=(
                "Whenever APT installs software, it keeps a copy of the "
                ".deb installer files in /var/cache/apt/archives. Unlike "
                "Windows, Linux does not clean these up automatically. "
                f"Right now that folder is using {cache_size}. Clearing it "
                "frees disk space and does not affect installed software."
            ),
            commands=["sudo apt clean"],
            severity=SeverityLevel.SAFE,
            rollback_hint="The cache will simply be re-downloaded next time "
                           "you install something, so there is nothing to "
                           "roll back.",
            reason=f"Downloaded installer files are taking up {cache_size} "
                   f"and are no longer needed once a package is installed.",
            risk=RiskLevel.LOW,
            expected_changes=[
                f"Delete all .deb files in /var/cache/apt/archives "
                f"(currently {cache_size})",
                "No installed software is changed",
            ],
            related_lesson=("intermediate", "i7_disk_usage"),
        ))

    # Unused packages
    rc, out, _ = _run(["apt-get", "--dry-run", "autoremove"])
    auto_lines = [l for l in out.splitlines() if l.startswith("Remv")]
    if auto_lines:
        issues.append(
            f"{len(auto_lines)} package(s) were installed as dependencies "
            f"and are no longer needed by anything."
        )
        removed_names = []
        for line in auto_lines[:15]:
            parts = line.split()
            if len(parts) >= 2:
                removed_names.append(parts[1])
        fixes.append(Fix(
            id="apt_autoremove",
            title="Remove unused dependency packages",
            explanation=(
                "When you install software, APT often pulls in extra "
                "'dependency' packages it needs. If you later remove the "
                "original software, those dependencies can be left behind "
                "even though nothing uses them anymore. This command removes "
                f"{len(auto_lines)} such package(s)."
            ),
            commands=["sudo apt autoremove"],
            severity=SeverityLevel.APPROVAL,
            rollback_hint="If you need one of these packages again later, "
                           "reinstall it with 'sudo apt install <package>'.",
            reason=f"{len(auto_lines)} package(s) were pulled in as "
                   f"dependencies for something that has since been "
                   f"removed, and nothing currently needs them.",
            risk=RiskLevel.LOW,
            expected_changes=(
                [f"Remove: {', '.join(removed_names)}"]
                + (["...and others"] if len(auto_lines) > len(removed_names) else [])
                + ["Frees disk space currently used by these packages"]
            ),
            related_lesson=("beginner", "b12_installing_software"),
        ))

    if not issues:
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.GREEN,
            summary="Your package manager looks healthy. No interrupted "
                    "installs or broken dependencies were found.",
            fixes=[f for f in fixes if f.severity == SeverityLevel.SAFE],
            why="APT (the package manager) tracks the installation state "
                "of every package. When everything is in the 'ii' "
                "(installed, configured) state and dependencies all "
                "resolve, there's nothing for Grix to fix here.",
        )

    status = Status.RED if any(f.severity == SeverityLevel.APPROVAL and f.id == "fix_broken" for f in fixes) else Status.YELLOW
    if half_configured:
        status = Status.RED if status != Status.RED else status

    return CheckResult(
        id="package_manager",
        title="Package Manager Health",
        status=status,
        summary=" ".join(issues),
        fixes=fixes,
        why=(
            "This usually happens after an update or installation was "
            "interrupted (power loss, closing a terminal mid-install, or "
            "manually cancelling apt), or after mixing software from "
            "different sources whose version requirements conflict. APT "
            "and dpkg track the exact state of every package, so they can "
            "detect this precisely - they just can't always fix it without "
            "your approval, since the fix sometimes involves installing or "
            "removing other packages."
        ),
    )


def check_journal() -> CheckResult:
    """Check systemd journal disk usage."""
    if not _have("journalctl"):
        return CheckResult(
            id="journal",
            title="System Journal",
            status=Status.UNKNOWN,
            summary="journalctl was not found. This system may not use "
                    "systemd's journal for logging.",
        )

    rc, out, err = _run(["journalctl", "--disk-usage"])
    if rc != 0:
        return CheckResult(
            id="journal",
            title="System Journal",
            status=Status.UNKNOWN,
            summary="Could not read journal disk usage.",
            details=err,
        )

    summary_text = out
    # Try to pull a size like "1.2G" out of the output
    size_str = ""
    for token in out.split():
        if any(token.endswith(u) for u in ("B", "K", "M", "G", "T")):
            size_str = token
            break

    fixes = [
        Fix(
            id="journal_vacuum_14d",
            title="Keep only the last 14 days of logs",
            explanation=(
                "The system journal records everything from boot messages "
                "to application errors. It is safe to trim, and Grix "
                "recommends keeping at least a couple of weeks of history "
                "so you can still investigate recent problems."
            ),
            commands=["sudo journalctl --vacuum-time=14d"],
            severity=SeverityLevel.SAFE,
            rollback_hint="Old log entries cannot be restored once removed, "
                           "but new entries continue to be recorded "
                           "immediately.",
            reason=f"Your journal is currently using "
                   f"{size_str or 'a significant amount of space'}, and "
                   f"logs older than 14 days are rarely needed for "
                   f"day-to-day troubleshooting.",
            risk=RiskLevel.LOW,
            expected_changes=[
                "Delete journal entries older than 14 days",
                "Keep the most recent 14 days of logs",
                "New log entries continue to be written normally",
            ],
            related_lesson=("intermediate", "i6_logs"),
        ),
        Fix(
            id="journal_vacuum_500m",
            title="Limit logs to 500MB total",
            explanation=(
                "Instead of trimming by age, this caps the total size of "
                "stored logs at 500MB, removing the oldest entries first "
                "until the journal fits."
            ),
            commands=["sudo journalctl --vacuum-size=500M"],
            severity=SeverityLevel.SAFE,
            rollback_hint="Old log entries cannot be restored once removed.",
            reason=f"Your journal is currently using "
                   f"{size_str or 'more than 500MB'}; capping the total "
                   f"size keeps disk usage predictable regardless of how "
                   f"busy the system has been.",
            risk=RiskLevel.LOW,
            expected_changes=[
                "Remove the oldest journal entries until total size is "
                "at or below 500MB",
                "New log entries continue to be written normally",
            ],
            related_lesson=("intermediate", "i6_logs"),
        ),
    ]

    status = Status.GREEN
    if size_str:
        # crude size check: flag if it looks like it's in the gigabytes
        if size_str.upper().endswith("G"):
            try:
                gb = float(size_str[:-1])
                if gb >= 2:
                    status = Status.YELLOW
            except ValueError:
                pass

    return CheckResult(
        id="journal",
        title="System Journal",
        status=status,
        summary=f"Your system logs are currently using {size_str or 'an unknown amount of space'}."
                + (" That's a healthy size." if status == Status.GREEN else
                   " That's getting large - trimming old logs is safe and "
                   "frees up disk space."),
        details=summary_text,
        # IMPORTANT: a healthy (GREEN) journal must have ZERO fixes.
        # Previously this always attached the 14-day-vacuum fix even
        # when the journal was small and fine, which made the card
        # look like it perpetually "needed attention" even right after
        # being cleaned - exactly the kind of unconditional fix that
        # should never happen (see "Avoid unconditional Safe fixes" in
        # CONTRIBUTING.md). Only offer fixes when there's an actual
        # reason to (status != GREEN).
        fixes=fixes if status != Status.GREEN else [],
        why=(
            "systemd's journal records messages from the kernel, system "
            "services, and many applications, and keeps them indefinitely "
            "by default. On a system that's been running for a while - or "
            "one with a service that logs a lot (sometimes due to an "
            "underlying problem repeating itself) - this can add up to "
            "several gigabytes over time."
        ),
    )


def check_failed_services() -> CheckResult:
    """List any systemd units that failed to start."""
    if not _have("systemctl"):
        return CheckResult(
            id="services",
            title="System Services",
            status=Status.UNKNOWN,
            summary="systemctl was not found. This system may not use "
                    "systemd.",
        )

    rc, out, err = _run(
        ["systemctl", "--failed", "--no-legend", "--no-pager", "--plain"]
    )
    if rc != 0 and not out:
        return CheckResult(
            id="services",
            title="System Services",
            status=Status.UNKNOWN,
            summary="Could not check service status.",
            details=err,
        )

    failed_units = []
    for line in out.splitlines():
        parts = line.split()
        if parts:
            failed_units.append(parts[0])

    if not failed_units:
        return CheckResult(
            id="services",
            title="System Services",
            status=Status.GREEN,
            summary="All system services are running normally. Nothing has "
                    "failed to start.",
        )

    fixes = []
    for unit in failed_units:
        fixes.append(Fix(
            id=f"restart_{unit}",
            title=f"Restart {unit}",
            explanation=(
                f"The service '{unit}' did not start successfully. "
                f"Services are background programs (sometimes called "
                f"'daemons') that handle things like printing, networking, "
                f"or hardware. Restarting it will try again and often "
                f"clears a temporary failure."
            ),
            commands=[f"sudo systemctl restart {unit}"],
            severity=SeverityLevel.APPROVAL,
            rollback_hint=f"If the service starts failing again, view its "
                          f"logs with 'journalctl -u {unit}' to find the "
                          f"underlying cause.",
            reason=f"'{unit}' is currently in a failed state and is not "
                   f"running.",
            risk=RiskLevel.LOW,
            expected_changes=[
                f"Stop and restart the '{unit}' service",
                "Any feature provided by this service is briefly "
                "unavailable during the restart",
            ],
            related_lesson=("intermediate", "i5_systemd"),
        ))

    details_lines = []
    for unit in failed_units:
        rc2, out2, _ = _run(["systemctl", "status", unit, "--no-pager", "--lines=0"])
        details_lines.append(f"{unit}:\n{out2}\n")

    return CheckResult(
        id="services",
        title="System Services",
        status=Status.YELLOW,
        summary=f"{len(failed_units)} service(s) failed to start: "
                f"{', '.join(failed_units)}.",
        details="\n".join(details_lines),
        fixes=fixes,
        why=(
            "A service can fail to start for many reasons: a missing "
            "configuration file, a port already in use by something else, "
            "a hardware device that wasn't ready yet during boot, or a bug "
            "triggered by a recent update. Restarting resolves the failure "
            "when the underlying cause was temporary (like a device not "
            "being ready yet); if the same service keeps failing after a "
            "restart, its logs (via journalctl) usually point at the real "
            "cause."
        ),
    )


def check_disk_space() -> CheckResult:
    """Check disk usage on key mount points and home cache directories."""
    import os

    rc, out, err = _run(["df", "-h", "--output=target,pcent,avail", "/"])
    if rc != 0:
        return CheckResult(
            id="disk",
            title="Disk Space",
            status=Status.UNKNOWN,
            summary="Could not check disk usage.",
            details=err,
        )

    lines = out.splitlines()
    pct = 0
    avail = "unknown"
    if len(lines) >= 2:
        parts = lines[1].split()
        if len(parts) >= 3:
            pct_str = parts[1].rstrip("%")
            avail = parts[2]
            try:
                pct = int(pct_str)
            except ValueError:
                pct = 0

    fixes = []
    home = os.path.expanduser("~")
    cache_dir = os.path.join(home, ".cache")
    thumb_dir = os.path.join(home, ".cache", "thumbnails")

    cache_size = None
    if os.path.isdir(cache_dir):
        rc2, out2, _ = _run(["du", "-sh", cache_dir])
        if rc2 == 0 and out2:
            cache_size = out2.split()[0]
            fixes.append(Fix(
                id="clear_user_cache",
                title=f"Clear your personal cache ({cache_size})",
                explanation=(
                    f"Many applications store temporary files in "
                    f"~/.cache. This folder is currently using "
                    f"{cache_size}. Removing its contents is safe - "
                    f"applications will simply recreate what they need."
                ),
                commands=[f"rm -rf {cache_dir}/*"],
                severity=SeverityLevel.SAFE,
                needs_sudo=False,
                rollback_hint="Apps rebuild their cache automatically; "
                               "nothing important is lost, though some apps "
                               "may feel briefly slower the next time they "
                               "start.",
                reason=f"~/.cache is currently using {cache_size} of "
                       f"temporary files that applications can regenerate "
                       f"on demand.",
                risk=RiskLevel.LOW,
                expected_changes=[
                    f"Delete the contents of ~/.cache (currently "
                    f"{cache_size})",
                    "Your documents, settings, and installed software are "
                    "not affected",
                    "Some apps may take slightly longer to start next "
                    "time while they rebuild their cache",
                ],
                related_lesson=("intermediate", "i7_disk_usage"),
            ))

    if os.path.isdir(thumb_dir):
        fixes.append(Fix(
            id="clear_thumbnails",
            title="Clear thumbnail cache",
            explanation=(
                "File managers generate small preview images for photos "
                "and videos and store them in ~/.cache/thumbnails. This is "
                "safe to clear and thumbnails will simply regenerate."
            ),
            commands=[f"rm -rf {thumb_dir}/*"],
            severity=SeverityLevel.SAFE,
            needs_sudo=False,
            rollback_hint="Thumbnails regenerate automatically when you "
                           "browse files again.",
            reason="Thumbnail previews accumulate over time as you browse "
                   "photos and videos, and aren't needed once you stop "
                   "viewing those files.",
            risk=RiskLevel.LOW,
            expected_changes=[
                "Delete cached thumbnail images in ~/.cache/thumbnails",
                "Your original photos and videos are not touched",
                "Thumbnails regenerate the next time you browse those "
                "files, which may take a moment",
            ],
            related_lesson=("intermediate", "i7_disk_usage"),
        ))

    rc3, out3, _ = _run(["du", "-sb", "/var/cache/apt/archives"])
    apt_cache_bytes = 0
    if rc3 == 0 and out3:
        try:
            apt_cache_bytes = int(out3.split()[0])
        except (ValueError, IndexError):
            apt_cache_bytes = 0

    if apt_cache_bytes >= 150 * 1024 * 1024:  # only nag once it's >150MB
        apt_cache_size = f"{apt_cache_bytes / (1024 * 1024):.0f}MB"
        fixes.append(Fix(
            id="apt_clean_disk",
            title="Clear the APT package cache",
            explanation=(
                "Downloaded package files build up in "
                "/var/cache/apt/archives over time. Clearing this is safe "
                f"and currently frees {apt_cache_size}."
            ),
            commands=["sudo apt clean"],
            severity=SeverityLevel.SAFE,
            rollback_hint="The cache is rebuilt automatically the next "
                           "time you install something.",
            reason=f"Downloaded .deb installer files are using "
                   f"{apt_cache_size} in /var/cache/apt/archives and are "
                   f"kept after installation even though they're rarely "
                   f"needed again.",
            risk=RiskLevel.LOW,
            expected_changes=[
                f"Delete all .deb files in /var/cache/apt/archives "
                f"(currently {apt_cache_size})",
                "No installed software is changed",
            ],
            related_lesson=("intermediate", "i7_disk_usage"),
        ))

    if pct >= 95:
        status = Status.RED
        summary = (
            f"Your root partition (/) is critically full at {pct}% with "
            f"only {avail} free. Act soon - running completely out of "
            f"space can cause crashes or prevent the system from booting "
            f"properly."
        )
    elif pct >= 90:
        status = Status.RED
        summary = (
            f"Your root partition (/) is {pct}% full with only {avail} "
            f"free. This is a serious issue - your system can become "
            f"unstable if it runs completely out of space."
        )
    elif pct >= 75:
        status = Status.YELLOW
        summary = (
            f"Your root partition (/) is {pct}% full ({avail} free). "
            f"It's worth clearing some space soon."
        )
    else:
        status = Status.GREEN
        summary = f"Your root partition (/) is {pct}% full ({avail} free). Plenty of room."

    # Disk space is one of the checks users most often snooze since it's
    # rarely urgent - but a 95%+ full disk is a genuine emergency, so it
    # always reappears even if previously snoozed, no matter the snooze
    # duration chosen.
    force_override = pct >= 95

    return CheckResult(
        id="disk",
        title="Disk Space",
        status=status,
        summary=summary,
        fixes=fixes if status != Status.GREEN else [f for f in fixes if f.severity == SeverityLevel.SAFE][:1],
        force_override=force_override,
        why=(
            "Disk space gets used up gradually by a combination of "
            "installed software, downloaded package files that are kept "
            "after installation, application caches, log files, and your "
            "own documents and downloads. Unlike Windows, Linux doesn't "
            "automatically clean most of these up - which is exactly what "
            "the fixes below do, safely."
        ),
    )


def check_updates() -> CheckResult:
    """Check for available package updates and unattended-upgrade health."""
    if not _have("apt"):
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.UNKNOWN,
            summary="apt was not found. This check only applies to "
                    "Debian/Ubuntu-based systems.",
        )

    rc, out, _ = _run(["apt", "list", "--upgradable"])
    upgradable = [
        line for line in out.splitlines()
        if line and not line.startswith("Listing...")
    ]

    if not upgradable:
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.GREEN,
            summary="Your system is fully up to date.",
        )

    security_count = sum(1 for l in upgradable if "security" in l.lower())

    pkg_names = []
    for line in upgradable[:15]:
        parts = line.split("/")
        if parts:
            pkg_names.append(parts[0])

    fix = Fix(
        id="apt_upgrade",
        title=f"Install {len(upgradable)} available update(s)",
        explanation=(
            f"There are {len(upgradable)} package update(s) available"
            + (f", including {security_count} security update(s)" if security_count else "")
            + ". Keeping software up to date fixes bugs and security "
              "issues. Grix will refresh the package list first, then "
              "upgrade."
        ),
        commands=["sudo apt update", "sudo apt upgrade -y"],
        severity=SeverityLevel.APPROVAL,
        rollback_hint="Most packages can be downgraded with "
                       "'sudo apt install <package>=<old-version>' if an "
                       "update causes a problem, though this is rarely "
                       "needed.",
        reason=(
            f"{len(upgradable)} package(s) have newer versions available "
            f"from your configured repositories"
            + (f", including {security_count} that address security "
               f"issues" if security_count else "")
            + "."
        ),
        risk=RiskLevel.MEDIUM if security_count == 0 else RiskLevel.LOW,
        expected_changes=(
            [f"Upgrade: {', '.join(pkg_names)}"]
            + (["...and others"] if len(upgradable) > len(pkg_names) else [])
            + ["Some services may restart automatically as part of the "
               "upgrade"]
        ),
        related_lesson=("beginner", "b12_installing_software"),
    )

    status = Status.RED if security_count > 0 else Status.YELLOW
    summary = f"{len(upgradable)} update(s) are available"
    if security_count:
        summary += f", including {security_count} security update(s)"
    summary += "."

    return CheckResult(
        id="updates",
        title="Available Updates",
        status=status,
        summary=summary,
        details="\n".join(upgradable[:25]),
        fixes=[fix],
        why=(
            "Software projects regularly release new versions that fix "
            "bugs, patch security vulnerabilities, or add features. Your "
            "system checks its configured repositories for newer versions "
            "of installed packages; when one is available, it's listed "
            "here until you choose to install it."
        ),
    )


def check_network() -> CheckResult:
    """Check basic internet connectivity and DNS resolution."""
    fixes = []
    issues = []

    rc, out, err = _run(["ping", "-c", "1", "-W", "2", "1.1.1.1"])
    internet_ok = rc == 0
    if not internet_ok:
        issues.append("Could not reach the internet (ping to 1.1.1.1 failed).")
        if _have("systemctl"):
            fixes.append(Fix(
                id="restart_networkmanager",
                title="Restart NetworkManager",
                explanation=(
                    "NetworkManager is the service that controls your "
                    "Wi-Fi and wired connections. Restarting it often "
                    "resolves connections that have dropped or gotten "
                    "stuck."
                ),
                commands=["sudo systemctl restart NetworkManager"],
                severity=SeverityLevel.APPROVAL,
                rollback_hint="This briefly interrupts your network "
                               "connection while it restarts, then "
                               "reconnects automatically.",
                reason="A direct ping to 1.1.1.1 (a public DNS server "
                       "often used as a connectivity test) did not get a "
                       "response, which usually means the network "
                       "connection itself is down or stuck.",
                risk=RiskLevel.LOW,
                expected_changes=[
                    "Briefly disconnect and reconnect Wi-Fi/Ethernet",
                    "Re-establish your network connection automatically",
                ],
                related_lesson=("intermediate", "i11_networking"),
            ))

    dns_ok = True
    if _have("resolvectl"):
        rc, out, err = _run(["resolvectl", "status"])
        dns_ok = rc == 0
    elif _have("getent"):
        rc, out, err = _run(["getent", "hosts", "example.com"])
        dns_ok = rc == 0

    if not dns_ok:
        issues.append("DNS name resolution does not appear to be working.")
        if _have("resolvectl"):
            fixes.append(Fix(
                id="flush_dns",
                title="Clear the DNS cache",
                explanation=(
                    "DNS translates names like 'example.com' into the "
                    "numeric addresses computers actually use. If your "
                    "system has cached a bad result, clearing the cache "
                    "forces it to look things up fresh."
                ),
                commands=["sudo resolvectl flush-caches"],
                severity=SeverityLevel.SAFE,
                rollback_hint="The cache rebuilds automatically as you "
                               "browse and connect to services.",
                reason="DNS lookups are not resolving correctly, which can "
                       "happen when a stale or incorrect result has been "
                       "cached.",
                risk=RiskLevel.LOW,
                expected_changes=[
                    "Clear cached DNS lookup results",
                    "The next lookup for any domain is performed fresh",
                ],
                related_lesson=("intermediate", "i11_networking"),
            ))

    if not issues:
        return CheckResult(
            id="network",
            title="Network Connectivity",
            status=Status.GREEN,
            summary="Your internet connection and DNS resolution both look "
                    "healthy.",
        )

    return CheckResult(
        id="network",
        title="Network Connectivity",
        status=Status.RED if not internet_ok else Status.YELLOW,
        summary=" ".join(issues),
        fixes=fixes,
        why=(
            "Network problems usually fall into one of two categories: the "
            "connection itself is down (no Wi-Fi/Ethernet signal, or the "
            "network service has gotten stuck), or the connection works "
            "but DNS - the system that translates names like "
            "'example.com' into numeric addresses - isn't responding "
            "correctly. Grix checks both separately so the fix matches "
            "the actual problem."
        ),
    )


def check_user_owned_root_files() -> CheckResult:
    """Look for files in the home directory owned by root (common after migrations)."""
    import os
    home = os.path.expanduser("~")

    if os.geteuid() == 0:
        return CheckResult(
            id="permissions",
            title="File Permissions",
            status=Status.UNKNOWN,
            summary="Grix is running as root, so this check is skipped to "
                    "avoid a false positive.",
        )

    # -xdev keeps find from crossing into other mounted filesystems
    # (NFS/SSHFS/Samba shares mounted inside the home directory, or
    # other partitions) - without it, a slow network mount can make
    # this thrash for the full timeout on every single scan.
    # -not -path '*/.*' skips hidden directory trees (where container
    # runtimes, language version managers, and similar large caches
    # commonly live, e.g. ~/.cache, ~/.local, ~/.docker) since files
    # there are essentially never the "accidentally root-owned after a
    # migration" scenario this check is looking for.
    rc, out, err = _run(
        ["find", home, "-maxdepth", "3", "-xdev", "-not", "-path", "*/.*", "-user", "root"],
        timeout=20,
    )
    bad_files = [l for l in out.splitlines() if l.strip()]

    if not bad_files:
        return CheckResult(
            id="permissions",
            title="File Permissions",
            status=Status.GREEN,
            summary="No files in your home folder are owned by the root "
                    "user. Permissions look normal.",
        )

    current_user = os.environ.get("SUDO_USER") or os.environ.get("USER") or getpass.getuser()
    # shlex.quote() correctly escapes every shell metacharacter,
    # including a literal double-quote embedded in a filename (e.g.
    # 'Malformed " File.txt') - the previous manual f'"{p}"' wrapping
    # broke on exactly that case, splitting the filename into two
    # invalid arguments instead of one valid one.
    quoted_paths = " ".join(shlex.quote(p) for p in bad_files[:50])
    fix = Fix(
        id="fix_ownership",
        title=f"Give yourself ownership of {len(bad_files)} file(s)",
        explanation=(
            f"Grix found {len(bad_files)} file(s) or folder(s) in your home "
            f"directory that are owned by 'root' instead of your own "
            f"account. This often happens after running a graphical "
            f"program with sudo by mistake, or after restoring files from "
            f"a backup. Grix will change the owner back to you for the "
            f"affected items only - never your whole home folder with "
            f"unsafe options."
        ),
        commands=[f"sudo chown {current_user}:{current_user} {quoted_paths}"],
        severity=SeverityLevel.APPROVAL,
        rollback_hint="If something needs to be owned by root again, run "
                       "'sudo chown root:root <path>' on that specific "
                       "item.",
        reason=f"{len(bad_files)} file(s) in your home directory are owned "
               f"by 'root', which can prevent your normal account from "
               f"opening, editing, or deleting them.",
        risk=RiskLevel.LOW,
        expected_changes=[
            f"Change the owner of {min(len(bad_files), 50)} specific "
            f"file(s)/folder(s) to your user account",
            "Only the exact items listed are affected - not your whole "
            "home folder",
        ],
        related_lesson=("intermediate", "i3_permissions"),
    )

    return CheckResult(
        id="permissions",
        title="File Permissions",
        status=Status.YELLOW,
        summary=f"{len(bad_files)} item(s) in your home folder are owned by "
                f"root instead of you.",
        details="\n".join(bad_files[:50]),
        fixes=[fix],
        why=(
            "This typically happens after running a graphical application "
            "with 'sudo' by mistake (which makes any files it creates or "
            "touches owned by root), after restoring files from a backup "
            "made under a different account, or after copying files while "
            "logged in as another user. The files themselves are usually "
            "fine - only their ownership needs correcting."
        ),
    )


def check_boot_time() -> CheckResult:
    """Report systemd boot timing and identify slow services."""
    if not _have("systemd-analyze"):
        return CheckResult(
            id="boot",
            title="Boot Time",
            status=Status.UNKNOWN,
            summary="systemd-analyze was not found. This system may not "
                    "use systemd.",
        )

    rc, out, err = _run(["systemd-analyze"])
    if rc != 0:
        return CheckResult(
            id="boot",
            title="Boot Time",
            status=Status.UNKNOWN,
            summary="Could not analyze boot time. Your system may still be "
                    "starting up.",
            details=err,
        )

    rc2, blame, _ = _run(["systemd-analyze", "blame"])
    top_offenders = blame.splitlines()[:5]

    status = Status.GREEN
    summary = out
    if top_offenders:
        first = top_offenders[0]
        try:
            time_part = first.split()[0]
            if "min" in time_part or (time_part.endswith("s") and float(time_part[:-1]) > 10):
                status = Status.YELLOW
        except (ValueError, IndexError):
            pass

    return CheckResult(
        id="boot",
        title="Boot Time",
        status=status,
        summary=summary,
        details="Slowest services to start:\n" + "\n".join(top_offenders),
    )


def check_security_basics() -> CheckResult:
    """Check firewall status as a basic security check.

    Checking ufw's status requires root, same as enabling it - there's
    no unprivileged way to read it. Using 'sudo -n' (non-interactive)
    here would silently fail on most desktops unless the user very
    recently authenticated, making this check effectively useless
    (always reporting "needs administrator access" instead of the
    real status). Instead, this uses the same pkexec/grix-helper path
    as every other privileged action in Grix, which shows one
    graphical authentication prompt and can stay cached for the rest
    of the scan session depending on the system's PolicyKit policy.
    """
    if not _have("ufw"):
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.UNKNOWN,
            summary="ufw (Uncomplicated Firewall) was not found. You may be "
                    "using a different firewall tool.",
        )

    status_command = privileged_run_command("ufw status")
    if _have("pkexec"):
        rc, out, err = _run(["pkexec"] + status_command.split(), timeout=15)
    elif _have("sudo"):
        rc, out, err = _run(["sudo", "-n"] + status_command.split(), timeout=5)
    else:
        rc, out, err = 1, "", "no privilege escalation tool available"

    if rc != 0:
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.UNKNOWN,
            summary="Grix needs administrator access to check your firewall "
                    "status. Run a full scan and approve the authentication "
                    "prompt to check this.",
        )

    if "inactive" in out.lower():
        fix = Fix(
            id="enable_ufw",
            title="Enable the firewall",
            explanation=(
                "A firewall blocks unwanted incoming connections to your "
                "computer. Yours is currently turned off. Enabling it with "
                "default settings allows all outgoing traffic while "
                "blocking unsolicited incoming traffic - a sensible default "
                "for most desktop users."
            ),
            commands=["sudo ufw enable"],
            severity=SeverityLevel.APPROVAL,
            rollback_hint="Disable again at any time with 'sudo ufw "
                           "disable' if it interferes with something you "
                           "need (like file sharing).",
            reason="Your firewall (ufw) is currently inactive, meaning "
                   "nothing is filtering incoming network connections to "
                   "this computer.",
            risk=RiskLevel.MEDIUM,
            expected_changes=[
                "Turn on the firewall with its default rules",
                "Allow all outgoing connections (web browsing, updates, "
                "etc. continue to work normally)",
                "Block unsolicited incoming connections from other "
                "devices/networks",
                "May interfere with services that need incoming "
                "connections, like file sharing or hosting a local "
                "server - these can be allowed individually afterward "
                "with 'sudo ufw allow <port>'",
            ],
            related_lesson=("intermediate", "i11_networking"),
        )
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.YELLOW,
            summary="Your firewall is currently turned off.",
            fixes=[fix],
            why=(
                "ufw (Uncomplicated Firewall) ships with Ubuntu but is not "
                "enabled by default on most desktop installs. Without it, "
                "your system accepts incoming connection attempts on any "
                "port that has a listening service - usually not "
                "dangerous on a home network, but enabling the firewall "
                "is a simple extra layer of protection, especially on "
                "public Wi-Fi."
            ),
        )

    return CheckResult(
        id="security",
        title="Firewall",
        status=Status.GREEN,
        summary="Your firewall is active.",
        details=out,
    )


def check_old_kernels() -> CheckResult:
    """
    Detect old kernel packages that could be removed to free space.

    This is the canonical example of a "checkbox" fix: Grix never
    auto-selects the currently running kernel, and explains exactly
    what would be removed and why, per item.
    """
    if not _have("dpkg") or not _have("uname"):
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.UNKNOWN,
            summary="This check only applies to Debian/Ubuntu-based "
                    "systems.",
        )

    rc, out, _ = _run(["dpkg", "--list"])
    kernel_lines = [
        l for l in out.splitlines()
        if l.startswith("ii") and (
            "linux-image-" in l.split()[1] if len(l.split()) > 1 else False
        )
    ]

    rc2, current, _ = _run(["uname", "-r"])
    current = current.strip()

    kernel_packages = []
    for line in kernel_lines:
        parts = line.split()
        if len(parts) >= 2:
            pkg = parts[1]
            kernel_packages.append(pkg)

    # Only consider "linux-image-X.Y.Z-generic" style packages, not
    # meta-packages like linux-image-generic
    versioned = [p for p in kernel_packages if p != "linux-image-generic"
                  and any(c.isdigit() for c in p)]

    if len(versioned) <= 1:
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.GREEN,
            summary="Only one kernel version is installed, so there's "
                    "nothing to clean up here.",
        )

    # Sort and keep the 2 most recent (by package name, which sorts
    # correctly for typical Ubuntu version strings)
    versioned_sorted = sorted(versioned, reverse=True)
    keep = set(versioned_sorted[:2])

    removable = []
    for pkg in versioned:
        if pkg in keep:
            continue
        # Never offer to remove the currently running kernel
        if current and current in pkg:
            continue
        removable.append(pkg)

    if not removable:
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.GREEN,
            summary=f"{len(versioned)} kernel version(s) are installed, "
                    f"which is normal - Ubuntu keeps a couple of recent "
                    f"ones as a fallback. Nothing needs cleaning up yet.",
        )

    options = []
    total_size_estimate = 0
    for pkg in removable:
        rc3, size_out, _ = _run(["dpkg-query", "-Wf", "${Installed-Size}", pkg])
        size_kb = 0
        try:
            size_kb = int(size_out.strip())
        except ValueError:
            pass
        total_size_estimate += size_kb
        size_mb = size_kb / 1024
        detail = f"Frees approximately {size_mb:.0f}MB" if size_kb else ""
        is_running = current and current in pkg
        options.append(FixOption(
            id=pkg,
            label=pkg,
            detail=detail,
            protected=is_running,
            protected_reason="This is your currently running kernel and "
                              "cannot be removed." if is_running else "",
        ))

    fix = Fix(
        id="remove_old_kernels",
        title=f"Remove {len(removable)} old kernel version(s)",
        explanation=(
            "Ubuntu keeps old kernel versions installed as a fallback in "
            "case a new kernel causes problems - you can normally see "
            "these as extra options in your boot menu. Once you've been "
            "running the newer kernel without issues for a while, older "
            "ones can be safely removed to free up space. Grix always "
            "keeps at least the most recent two kernels, and never "
            "removes the one you're currently running."
        ),
        commands=[],  # populated via command_template + selected options
        severity=SeverityLevel.APPROVAL,
        rollback_hint="If you need an old kernel again, it can be "
                       "reinstalled with 'sudo apt install <package "
                       "name>=<version>' if it's still in your package "
                       "cache or repositories, though this is rarely "
                       "needed.",
        reason=f"{len(removable)} older kernel version(s) are installed "
               f"in addition to the ones Ubuntu recommends keeping as a "
               f"fallback.",
        risk=RiskLevel.MEDIUM,
        expected_changes=[
            f"Frees approximately {total_size_estimate / 1024:.0f}MB total "
            f"if all selected kernels are removed",
            "Your currently running kernel is never removed",
            "The two most recent kernel versions are kept regardless of "
            "your selection",
            "Boot menu entries for removed kernels will disappear",
        ],
        related_lesson=("intermediate", "i10_kernel_drivers"),
        options=options,
        command_template="sudo apt remove --purge {selected}",
    )

    return CheckResult(
        id="old_kernels",
        title="Old Kernel Versions",
        status=Status.YELLOW,
        summary=f"{len(removable)} old kernel version(s) could be removed "
                f"to free up space. Review the list before removing "
                f"anything - Grix never selects your current kernel "
                f"automatically.",
        details="Currently running: " + (current or "unknown") + "\n"
                "Installed kernel packages:\n" + "\n".join(versioned_sorted),
        fixes=[fix],
        why=(
            "Every time the kernel is updated, Ubuntu installs the new "
            "version alongside the old ones rather than replacing them, "
            "specifically so you can boot into a previous kernel if the "
            "new one has a problem with your hardware. This is a useful "
            "safety net, but each kernel version takes up a few hundred "
            "megabytes, so old ones are worth clearing out periodically."
        ),
    )


# ---------------------------------------------------------------------------
# Desktop Baseline Checks
# ---------------------------------------------------------------------------

def check_flatpak_snap_bloat() -> CheckResult:
    """Check for unused Flatpak runtimes and old Snap revisions.

    Old Flatpak runtimes and superseded Snap revisions are one of the
    most common causes of unexpected disk bloat on modern Ubuntu/Mint/
    Pop!_OS desktops - easily 5-10GB or more, silently accumulating
    with each app update without any cleanup prompt. Neither system
    removes old versions automatically by default.
    """
    has_flatpak = _have("flatpak")
    has_snap = _have("snap")

    if not has_flatpak and not has_snap:
        return CheckResult(
            id="flatpak_snap",
            title="Flatpak & Snap Runtimes",
            status=Status.UNKNOWN,
            summary="Neither Flatpak nor Snap are installed on this system.",
        )

    fixes: list[Fix] = []
    findings: list[str] = []
    total_recoverable_mb = 0

    # --- Flatpak ---
    if has_flatpak:
        rc, out, _ = _run(["flatpak", "list", "--runtime", "--columns=size"])
        # Parse total runtime disk use
        total_runtime_mb = 0
        if rc == 0:
            for line in out.splitlines():
                line = line.strip()
                if not line or line == "Size":
                    continue
                try:
                    num, unit = line.split()
                    factor = {"B": 1/1048576, "kB": 1/1024, "MB": 1, "GB": 1024}.get(unit, 0)
                    total_runtime_mb += float(num) * factor
                except (ValueError, AttributeError):
                    continue

        # Check for unused runtimes specifically.
        #
        # IMPORTANT: real-world `flatpak uninstall --unused --dry-run`
        # output commonly looks like this even when there is genuinely
        # NOTHING to remove:
        #
        #   These runtimes in installation 'system' are pinned and
        #   won't be removed; see flatpak-pin(1):
        #   runtime/com.valvesoftware.Steam.CompatibilityTool.Proton-GE/x86_64/stable
        #   runtime/org.freedesktop.Platform.VulkanLayer.MangoHud/x86_64/21.08
        #   Nothing unused to uninstall
        #
        # Pinned runtimes (Steam's Proton-GE, MangoHud, etc. are
        # commonly pinned) are listed but will NEVER actually be
        # removed by this command - they're explicitly exempted. The
        # previous version of this check counted those pinned-runtime
        # lines as "removable", so on any system with pinned runtimes
        # this fix would show up forever, even immediately after
        # running it successfully (since the pinned lines never go
        # away - that's the whole point of pinning). It also gated on
        # `rc_unused == 0`, but flatpak's exit code for this command
        # is not a reliable "is there anything to clean" signal across
        # versions.
        #
        # The fix: only ever count lines that appear in an ACTUAL
        # removal listing (flatpak's removal table uses numbered rows
        # like "1.\t[-]\torg.foo.Bar"), and treat the literal string
        # "Nothing unused to uninstall" as the authoritative "nothing
        # to do" signal regardless of exit code or any pinned-runtime
        # listing above it.
        rc_unused, unused_out, _ = _run(
            ["flatpak", "uninstall", "--unused", "--dry-run"],
        )

        if "nothing unused to uninstall" in unused_out.lower():
            removable_lines = []
        else:
            # Flatpak's removal table always starts each row with a
            # number and a period (e.g. " 1. " or "1.\t"), optionally
            # followed by a "[-]" marker depending on flatpak version.
            # The pinned-runtime listing above it never uses numbered
            # rows - just bare "runtime/..." lines - so anchoring on
            # "^\s*\d+\." reliably distinguishes an actual removal row
            # from anything else in the output, regardless of marker
            # format.
            removable_lines = [
                l for l in unused_out.splitlines()
                if re.match(r"^\s*\d+\.\s", l)
            ]

        if removable_lines:
            findings.append(
                f"{len(removable_lines)} unused Flatpak runtime(s) found that "
                f"can be safely removed."
            )
            # Estimate savings based on average runtime size
            estimated_mb = len(removable_lines) * (total_runtime_mb / max(1, len(removable_lines) + 5))
            total_recoverable_mb += estimated_mb

            fixes.append(Fix(
                id="flatpak_clean_unused",
                title=f"Remove {len(removable_lines)} unused Flatpak runtime(s)",
                explanation=(
                    "Flatpak keeps old runtime versions around even after "
                    "apps that needed them have been updated or removed. "
                    "These 'unused' runtimes can silently consume several "
                    "gigabytes. Removing them is safe - no installed apps "
                    "depend on them (Flatpak verifies this before removing "
                    "anything)."
                ),
                commands=["flatpak uninstall --unused -y"],
                needs_sudo=False,
                severity=SeverityLevel.SAFE,
                rollback_hint="Flatpak re-downloads a runtime automatically "
                               "if a future app needs it.",
                reason=f"{len(removable_lines)} unused Flatpak runtime(s) "
                       f"are taking up space that no installed app needs.",
                risk=RiskLevel.LOW,
                expected_changes=[
                    f"Remove {len(removable_lines)} unused runtime(s)",
                    "No installed Flatpak apps are affected",
                ],
                related_lesson=("intermediate", "i7_disk_usage"),
            ))

    # --- Snap ---
    if has_snap:
        rc, out, _ = _run(["snap", "list", "--all"])
        disabled_snaps: list[tuple[str, str]] = []
        if rc == 0:
            for line in out.splitlines()[1:]:
                parts = line.split()
                if len(parts) >= 6 and "disabled" in line.lower():
                    # columns: Name, Version, Rev, Tracking, Publisher, Notes
                    disabled_snaps.append((parts[0], parts[2]))

        if disabled_snaps:
            snap_names = [f"{name} (rev {rev})" for name, rev in disabled_snaps[:5]]
            estimated_snap_mb = len(disabled_snaps) * 150  # conservative 150MB/snap revision
            total_recoverable_mb += estimated_snap_mb
            findings.append(
                f"{len(disabled_snaps)} old Snap revision(s) found: "
                + ", ".join(snap_names[:3])
                + ("..." if len(disabled_snaps) > 3 else "")
                + f". These are kept as a rollback safety net but take up "
                f"~{estimated_snap_mb}MB."
            )
            # Build remove commands for every old revision found - NOT
            # just the first 10. Capping this at 10 (as a previous
            # version did) meant that on a system with, say, 15 old
            # revisions, the fix would claim to "Remove 15 old Snap
            # revision(s)" but the actual command list only removed
            # 10 - leaving 5 behind that would immediately re-trigger
            # this exact same finding on the very next scan, making
            # the fix look like it never worked. There is no
            # practical reason to cap this list: snap remove is cheap
            # and safe to run for each one.
            remove_cmds = [
                f"sudo snap remove {name} --revision={rev}"
                for name, rev in disabled_snaps
            ]
            fixes.append(Fix(
                id="snap_remove_old_revisions",
                title=f"Remove {len(disabled_snaps)} old Snap revision(s)",
                explanation=(
                    "Snap keeps the previous revision of each installed app "
                    "as a fallback in case the new version has a problem. "
                    "While useful right after an update, these old revisions "
                    "accumulate over time and can waste several gigabytes. "
                    "The current version of each app is unaffected."
                ),
                commands=remove_cmds,
                severity=SeverityLevel.SAFE,
                rollback_hint="You can reinstall a specific revision with "
                               "'snap install <name> --revision=<rev>' if "
                               "you need to roll back after removing it.",
                reason=f"{len(disabled_snaps)} old Snap revision(s) are "
                       f"taking up ~{estimated_snap_mb}MB as disabled "
                       f"backups that are rarely needed after a few days.",
                risk=RiskLevel.LOW,
                expected_changes=[
                    f"Remove {len(disabled_snaps)} old Snap revision(s)",
                    "Current versions of all Snap apps are unaffected",
                ],
                related_lesson=("intermediate", "i7_disk_usage"),
            ))

    if not findings and not fixes:
        summary = "Your Flatpak runtimes and Snap packages look clean - no significant unused bloat found."
        status = Status.GREEN
    elif total_recoverable_mb > 1024:
        summary = f"Found ~{total_recoverable_mb/1024:.1f}GB of recoverable space: {' | '.join(findings)}"
        status = Status.YELLOW
    else:
        summary = f"Found ~{total_recoverable_mb:.0f}MB of recoverable space: {' | '.join(findings)}"
        status = Status.YELLOW if total_recoverable_mb > 200 else Status.GREEN

    return CheckResult(
        id="flatpak_snap",
        title="Flatpak & Snap Runtimes",
        status=status,
        summary=summary,
        fixes=fixes,
        why=(
            "Flatpak and Snap both keep old versions of runtimes and apps "
            "as a safety net - Flatpak keeps unused runtimes that were once "
            "needed but no longer are, and Snap keeps the previous revision "
            "of each app in case you need to roll back. Both are useful "
            "features right after an update, but they accumulate silently "
            "over time and can waste several gigabytes of disk space that "
            "most users don't know is there."
        ),
    )


def check_audio_stack() -> CheckResult:
    """Check if the user's audio stack (PipeWire/PulseAudio) is running.

    Audio issues are among the most common desktop Linux complaints.
    This check runs against the USER's own systemd session (--user),
    not the system-wide services, so it requires no elevated
    privileges at all - another reason not to use the existing
    privileged-command path.
    """
    # Detect which audio stack is in use (prefer PipeWire, fall back to PulseAudio)
    has_pipewire = _have("pipewire")
    has_pulseaudio = _have("pulseaudio")
    has_systemctl = _have("systemctl")

    if not (has_pipewire or has_pulseaudio):
        return CheckResult(
            id="audio",
            title="Audio Stack",
            status=Status.UNKNOWN,
            summary="No audio server (PipeWire or PulseAudio) was detected.",
        )

    if not has_systemctl:
        return CheckResult(
            id="audio",
            title="Audio Stack",
            status=Status.UNKNOWN,
            summary="Could not check audio service status (systemctl not found).",
        )

    if has_pipewire:
        services_to_check = ["pipewire", "wireplumber"]
        stack_name = "PipeWire"
        restart_cmd = "systemctl --user restart pipewire wireplumber"
    else:
        services_to_check = ["pulseaudio"]
        stack_name = "PulseAudio"
        restart_cmd = "systemctl --user restart pulseaudio"

    failed_services: list[str] = []
    for svc in services_to_check:
        rc, out, _ = _run(["systemctl", "--user", "is-active", svc])
        if out.strip() not in ("active", "activating"):
            failed_services.append(svc)

    if not failed_services:
        return CheckResult(
            id="audio",
            title="Audio Stack",
            status=Status.GREEN,
            summary=f"{stack_name} is running normally.",
            why=(
                f"{stack_name} is your system's audio server - it manages "
                f"sound routing between applications and your hardware. "
                f"Everything is running as expected."
            ),
        )

    return CheckResult(
        id="audio",
        title="Audio Stack",
        status=Status.YELLOW,
        summary=(
            f"{', '.join(failed_services)} "
            f"{'is' if len(failed_services) == 1 else 'are'} not running. "
            f"This may cause missing sound or audio device issues."
        ),
        fixes=[
            Fix(
                id="restart_audio",
                title=f"Restart {stack_name}",
                explanation=(
                    f"Your {stack_name} audio session service doesn't appear to "
                    f"be running. Restarting it often fixes 'no sound' or "
                    f"'audio device disappeared' issues without needing a full "
                    f"reboot. This only affects your own user session - nothing "
                    f"system-wide is changed."
                ),
                commands=[restart_cmd],
                needs_sudo=False,
                severity=SeverityLevel.SAFE,
                rollback_hint="If restarting makes audio worse, log out and "
                               "back in to let the session restart audio "
                               "automatically.",
                reason=(
                    f"{', '.join(failed_services)} "
                    f"{'is' if len(failed_services) == 1 else 'are'} "
                    f"not active in your user session, which typically "
                    f"causes missing or broken audio output."
                ),
                risk=RiskLevel.LOW,
                expected_changes=[
                    f"Restart {', '.join(services_to_check)} in your user session",
                    "No system-wide services are affected",
                    "Running apps may briefly lose audio and reconnect",
                ],
            ),
        ],
        why=(
            f"{stack_name} is your system's audio server. When it stops "
            f"or crashes, apps lose access to the sound system - this "
            f"shows up as no sound, a missing audio device in settings, "
            f"or Bluetooth headphones connecting but producing no audio. "
            f"Restarting {stack_name} re-establishes the audio session "
            f"and usually fixes these issues immediately without needing "
            f"to log out or reboot."
        ),
    )


def check_timeshift_disk_usage() -> CheckResult:
    """Check if Timeshift or backup snapshots are consuming excessive space.

    Timeshift is the default snapshot tool on Linux Mint and some other
    distros. Misconfigured retention policies cause snapshot directories
    to grow silently until they fill the root partition - the exact
    scenario the 95% disk-full force_override check guards against,
    but much better to catch it early before it becomes critical.
    """
    TIMESHIFT_PATHS = [
        "/timeshift",
        "/run/timeshift",
    ]
    BACKUP_PATHS = [
        "/backup",
        "/backups",
    ]

    snapshot_size_mb = 0
    found_path: str | None = None

    for path in TIMESHIFT_PATHS + BACKUP_PATHS:
        if not os.path.isdir(path):
            continue
        rc, out, _ = _run(["du", "-sm", path])
        if rc == 0 and out:
            try:
                size_mb = int(out.split()[0])
                if size_mb > snapshot_size_mb:
                    snapshot_size_mb = size_mb
                    found_path = path
            except (ValueError, IndexError):
                continue

    if found_path is None:
        return CheckResult(
            id="timeshift",
            title="Backup Snapshot Usage",
            status=Status.UNKNOWN,
            summary="No Timeshift or common backup directories were found.",
        )

    snapshot_size_gb = snapshot_size_mb / 1024

    # Check how much of the root filesystem the snapshots consume
    rc, out, _ = _run(["df", "-h", "/"])
    root_total_gb = 0
    if rc == 0:
        for line in out.splitlines()[1:]:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    size_str = parts[1].rstrip("G")
                    root_total_gb = float(size_str)
                except (ValueError, IndexError):
                    pass

    pct_of_root = (snapshot_size_mb / max(1, root_total_gb * 1024)) * 100 if root_total_gb else 0

    if snapshot_size_gb < 5:
        return CheckResult(
            id="timeshift",
            title="Backup Snapshot Usage",
            status=Status.GREEN,
            summary=(
                f"Backup snapshots at {found_path} are using "
                f"{snapshot_size_gb:.1f}GB - no concern right now."
            ),
        )

    if pct_of_root > 30 or snapshot_size_gb > 50:
        status = Status.YELLOW
        concern = "This is getting large"
    else:
        status = Status.GREEN
        concern = "This is manageable"

    if snapshot_size_gb >= 30 or pct_of_root > 40:
        status = Status.YELLOW

    fixes: list[Fix] = []
    if _have("timeshift"):
        fixes.append(Fix(
            id="open_timeshift",
            title="Open Timeshift to review snapshots",
            explanation=(
                "Timeshift's graphical interface lets you see all your "
                "snapshots, delete old ones, and adjust how many are kept "
                "automatically. This is the safest way to reclaim space "
                "from the backup directory without accidentally deleting "
                "something you might need."
            ),
            commands=["timeshift-gtk"],
            needs_sudo=False,
            severity=SeverityLevel.SAFE,
            rollback_hint="Snapshots you delete in Timeshift are permanently "
                           "removed - don't delete recent ones unless you're "
                           "confident your system is healthy.",
            reason=(
                f"Your backup snapshot directory ({found_path}) is using "
                f"{snapshot_size_gb:.1f}GB "
                f"({pct_of_root:.0f}% of your root partition). "
                f"{concern} and worth reviewing."
            ),
            risk=RiskLevel.LOW,
            expected_changes=[
                "Opens the Timeshift GUI - no changes happen automatically",
                "You choose which snapshots to delete",
            ],
        ))

    return CheckResult(
        id="timeshift",
        title="Backup Snapshot Usage",
        status=status,
        summary=(
            f"Backup snapshots at {found_path} are using "
            f"{snapshot_size_gb:.1f}GB "
            f"({pct_of_root:.0f}% of root). {concern}."
        ),
        fixes=fixes,
        why=(
            "Timeshift (and similar backup tools) take regular snapshots "
            "of your system so you can roll back if something goes wrong. "
            "By default, they keep a fixed number of snapshots - but if "
            "the retention policy isn't adjusted, snapshots can quietly "
            "fill your root partition over weeks or months. This is one "
            "of the most common reasons desktops gradually run low on disk "
            "space even when the user hasn't installed much new software."
        ),
    )


# ---------------------------------------------------------------------------
# Registry of all checks
# ---------------------------------------------------------------------------

# What System Sentinel actually checks for, in plain language - shown in
# Settings so the scope is never a mystery, and used to generate the
# equivalent section in the project README. Keep this in sync with
# ALL_CHECKS below; it's deliberately hand-written rather than derived
# from docstrings so it reads naturally rather than like an API dump.
SCOPE_COVERED: list[tuple[str, str]] = [
    ("Package management", "Broken dependencies, interrupted installs, "
     "available updates, stale package lists, and APT lock conflicts "
     "with background updaters."),
    ("Disk space", "Root partition usage, APT cache bloat, old kernel "
     "versions, unused Flatpak runtimes and Snap revisions, and "
     "oversized Timeshift/backup snapshot directories."),
    ("Services", "Failed systemd services, and the user-session audio "
     "stack (PipeWire/PulseAudio)."),
    ("Networking", "Basic internet connectivity and the firewall "
     "(ufw) status."),
    ("System logs", "Recent errors in the systemd journal, with "
     "package-change correlation via System Timeline."),
    ("File permissions", "Files in your home directory unexpectedly "
     "owned by root."),
    ("Boot time", "How long the most recent boot took."),
]

SCOPE_NOT_COVERED: list[str] = [
    "Individual application bugs or crashes (a specific game, browser "
    "extension, or app misbehaving) - System Sentinel checks "
    "system-level health, not the internal behavior of every installed "
    "program.",
    "Hardware diagnostics (failing drives, GPU issues, RAM problems) - "
    "beyond surfacing relevant log entries, dedicated hardware "
    "diagnostic tools (smartctl, memtest86+, etc.) do this properly.",
    "Security auditing or intrusion detection - the firewall check "
    "confirms ufw is active, but Grix is not a security scanner and "
    "doesn't check for malware, rootkits, or unauthorized access.",
    "Non-Debian/Ubuntu-based distros - checks rely on apt/dpkg and "
    "Debian-family conventions; on other distros most checks report "
    "\"not checked\" rather than guessing.",
    "Anything Grix wasn't explicitly told to check for - System "
    "Sentinel only runs the checks in ALL_CHECKS (or installed "
    "plugins, see grix/modules/plugins.py); it does not perform open-"
    "ended system analysis.",
]

ALL_CHECKS: list[Callable[[], CheckResult]] = [
    check_package_manager,
    check_updates,
    check_failed_services,
    check_disk_space,
    check_flatpak_snap_bloat,
    check_audio_stack,
    check_timeshift_disk_usage,
    check_journal,
    check_network,
    check_user_owned_root_files,
    check_boot_time,
    check_security_basics,
    check_old_kernels,
]


def overall_status(results: list[CheckResult]) -> Status:
    """Roll up individual check results into one headline status.

    An empty list means "nothing to report" - either no checks ran
    (true UNKNOWN), or every result that came back is currently hidden
    because the user snoozed it (which should read as healthy, not
    "not yet scanned"). Callers that filter out snoozed results before
    calling this (sentinel.py does) rely on the empty-list case here
    resolving to GREEN, not UNKNOWN - Python's `all()` on an empty
    sequence is vacuously True, which would otherwise silently send
    this down the UNKNOWN branch below.
    """
    if not results:
        return Status.GREEN
    statuses = [r.status for r in results]
    if Status.RED in statuses:
        return Status.RED
    if Status.YELLOW in statuses:
        return Status.YELLOW
    if all(s == Status.UNKNOWN for s in statuses):
        return Status.UNKNOWN
    return Status.GREEN


def apply_fix(fix: Fix, selected_option_ids: Optional[list[str]] = None) -> tuple[bool, str]:
    """
    Execute a fix's commands. Returns (success, combined_output).

    This is the ONLY function that performs write actions, and it
    is only ever called after explicit user confirmation in the UI.

    Privileged commands (anything written with a 'sudo ' prefix in its
    definition) are run through pkexec by default, which shows a native
    graphical PolicyKit authentication prompt - this works correctly
    from a GUI app even when there's no visible terminal for sudo to
    prompt in. If pkexec isn't installed, Grix automatically falls back
    to running the command with sudo instead (which will prompt via
    whatever askpash mechanism is configured, or fail gracefully if
    none is available).

    For checkbox-style fixes (fix.options non-empty), pass the list of
    selected option ids; fix.command_template's "{selected}" placeholder
    is replaced with those ids, space-separated. If nothing is selected,
    no command runs.
    """
    commands = list(fix.commands)

    if fix.options:
        selected = [
            opt.id for opt in fix.options
            if selected_option_ids and opt.id in selected_option_ids
            and not opt.protected
        ]
        if not selected:
            return True, "Nothing was selected, so no changes were made."
        if fix.command_template:
            # Always shell-quote substituted values, even though
            # today's only user (old-kernel package names from
            # dpkg-query) can't contain shell metacharacters - this is
            # defense-in-depth so any future command_template-based fix
            # is automatically safe against option ids with spaces,
            # quotes, or other special characters.
            quoted_selected = " ".join(shlex.quote(s) for s in selected)
            commands = [fix.command_template.format(selected=quoted_selected)]

    use_pkexec = _have("pkexec")

    outputs = []
    for cmd in commands:
        is_privileged = cmd.strip().startswith("sudo ")
        if is_privileged:
            bare = _strip_sudo_prefix(cmd)
            # Prefer the narrowly-scoped grix-helper if it's installed
            # (see policykit/install.sh) - this keeps pkexec's
            # authorization limited to a fixed set of known-safe
            # maintenance actions rather than an arbitrary command.
            target = privileged_run_command(bare)
            run_cmd = f"pkexec {target}" if use_pkexec else f"sudo {target}"
        else:
            run_cmd = cmd

        rc, out, err = _run_shell(run_cmd)
        outputs.append(f"$ {run_cmd}\n{out}\n{err}".strip())
        if rc != 0:
            return False, "\n\n".join(outputs)
    return True, "\n\n".join(outputs)


def _run_shell(cmd: str, timeout: int = 120) -> tuple[int, str, str]:
    """Run a privileged shell command (apply_fix only). Never raises.
    Forces LC_ALL=C so any output captured for the repair log is in
    English, which is easier to parse for the user and for any future
    automated analysis of repair results."""
    try:
        env = os.environ.copy()
        env["LC_ALL"] = "C"
        env["LANG"] = "C"
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except subprocess.TimeoutExpired:
        return 124, "", "command timed out"
    except Exception as exc:  # pragma: no cover
        return 1, "", str(exc)
