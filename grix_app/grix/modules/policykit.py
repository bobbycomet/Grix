"""
Grix - PolicyKit Integration Management
===========================================

Lets the Settings panel install or remove Grix's PolicyKit integration
(grix-helper + its .policy file) without needing a terminal - this
mirrors what policykit/install.sh does for source/pip installs, but is
also what the AppImage's first-run prompt and Settings panel call into
directly via pkexec, since there's no terminal to run a shell script in
from a GUI context.

This module never silently elevates anything: every install/uninstall
action goes through pkexec, which always shows its own authentication
prompt - there is no hidden privilege escalation here.

IMPORTANT - AppImage + FUSE + root:
When running from an AppImage, the bundled files live inside the
AppImage's FUSE mount (e.g. /tmp/.mount_Grix-XXXXXX/usr/share/grix/...).
FUSE mounts default to blocking access from any user other than the
one who created the mount - this restriction applies even to root,
which is exactly what FUSE is designed to do (see "allow_root"/
"allow_other" mount options). Since the AppImage is normally launched
by a regular user, pkexec (running as root) gets a flat "Permission
denied" trying to read anything inside that mount directly, no matter
what the file's own permission bits say.

The fix is to copy the bundled files out of the FUSE mount into a
regular temporary directory FIRST, as the normal user (who can read
the mount), and only then have pkexec operate on that plain-filesystem
copy. A plain tmpfs/disk path has no such restriction.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile

HELPER_DEST = "/usr/bin/grix-helper"
POLICY_DEST = "/usr/share/polkit-1/actions/com.griffinlinux.grix.policy"

# Where bundled copies live relative to the running app, checked in
# order: AppImage bundle layout first, then the source tree's
# policykit/ directory (covers `pip install -e .` / running from
# source / a regular install).
_BUNDLE_CANDIDATES = [
    # AppImage: $APPDIR/usr/share/grix/policykit/
    os.path.join(
        os.environ.get("APPDIR", ""), "usr", "share", "grix", "policykit"
    ) if os.environ.get("APPDIR") else None,
    # Source tree: grix_app/policykit/ (two levels up from this file:
    # grix/modules/policykit.py -> grix/ -> grix_app/)
    os.path.normpath(os.path.join(os.path.dirname(__file__), "..", "..", "policykit")),
]


def _find_bundled_dir() -> str | None:
    for candidate in _BUNDLE_CANDIDATES:
        if candidate and os.path.isfile(os.path.join(candidate, "grix-helper")) and \
           os.path.isfile(os.path.join(candidate, "com.griffinlinux.grix.policy")):
            return candidate
    return None


def is_available_to_install() -> bool:
    """Whether Grix can find its own bundled helper/policy files to
    offer installing (regardless of whether they're already installed)."""
    return _find_bundled_dir() is not None


def is_installed() -> bool:
    return os.path.isfile(HELPER_DEST) and os.path.isfile(POLICY_DEST)


def has_pkexec() -> bool:
    return shutil.which("pkexec") is not None


def _stage_outside_fuse_mount(bundled_dir: str) -> tuple[str, str] | None:
    """Copy the bundled helper + policy files into a regular temp
    directory (NOT inside any FUSE mount), as the current user, so
    that a subsequent pkexec call (running as root) can actually read
    them. Returns (staged_helper_path, staged_policy_path), or None if
    the copy failed.

    This staging step is what actually fixes the AppImage
    "Permission denied" issue - root genuinely cannot read out of a
    FUSE mount it didn't create, no matter the file permissions, so
    pkexec must never be pointed directly at a path under
    /tmp/.mount_*. A plain temp directory has no such restriction."""
    try:
        staging_dir = tempfile.mkdtemp(prefix="grix-policykit-")
        staged_helper = os.path.join(staging_dir, "grix-helper")
        staged_policy = os.path.join(staging_dir, "com.griffinlinux.grix.policy")
        shutil.copy2(os.path.join(bundled_dir, "grix-helper"), staged_helper)
        shutil.copy2(os.path.join(bundled_dir, "com.griffinlinux.grix.policy"), staged_policy)
        os.chmod(staged_helper, 0o755)
        # Staged copies need to be readable by root regardless of the
        # original umask - world-readable is fine here, these are
        # public files (a shell script and an XML policy) about to be
        # installed to world-readable system locations anyway.
        os.chmod(staging_dir, 0o755)
        os.chmod(staged_policy, 0o644)
        return staged_helper, staged_policy
    except OSError:
        return None


def install() -> tuple[bool, str]:
    """Install grix-helper + policy via a single pkexec authentication.
    Returns (success, message)."""
    bundled_dir = _find_bundled_dir()
    if bundled_dir is None:
        return False, "Could not find Grix's bundled PolicyKit files to install."
    if not has_pkexec():
        return False, "pkexec was not found on this system. Install policykit-1 (or your distro's PolicyKit package) first."

    # Stage outside any FUSE mount first - see module docstring. This
    # is a no-op in terms of file content whether running from an
    # AppImage or from source, but is required for the AppImage case
    # specifically, since pkexec (as root) cannot read directly out of
    # the AppImage's FUSE mount.
    staged = _stage_outside_fuse_mount(bundled_dir)
    if staged is None:
        return False, "Could not prepare the PolicyKit files for installation (failed to copy to a temporary location)."
    staged_helper, staged_policy = staged
    staging_dir = os.path.dirname(staged_helper)

    script = (
        f'install -m 0755 -o root -g root "{staged_helper}" "{HELPER_DEST}" && '
        f'install -m 0644 -o root -g root "{staged_policy}" "{POLICY_DEST}"'
    )

    try:
        proc = subprocess.run(
            ["pkexec", "sh", "-c", script],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "Installation timed out."
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return False, f"Installation failed{f': {detail}' if detail else '.'}"

    return True, "Installed successfully."


def uninstall() -> tuple[bool, str]:
    """Remove grix-helper + policy via a single pkexec authentication."""
    if not has_pkexec():
        return False, "pkexec was not found on this system."

    script = f'rm -f "{HELPER_DEST}" "{POLICY_DEST}"'

    try:
        proc = subprocess.run(
            ["pkexec", "sh", "-c", script],
            capture_output=True, text=True, timeout=60,
        )
    except subprocess.TimeoutExpired:
        return False, "Removal timed out."
    except Exception as exc:  # pragma: no cover - defensive
        return False, str(exc)

    if proc.returncode != 0:
        detail = (proc.stderr or proc.stdout or "").strip()
        return False, f"Removal failed{f': {detail}' if detail else '.'}"

    return True, "Removed successfully."
