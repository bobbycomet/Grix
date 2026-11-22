"""Shared DNF-based diagnostics used by Fedora and RPM-family plugins."""

import os
import re
import shutil
import subprocess
from collections.abc import Iterable

from grix.modules.diagnostics import (
    CheckResult,
    Fix,
    FixOption,
    RiskLevel,
    SeverityLevel,
    Status,
)


def _run(args: list[str], timeout: int = 45) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["LC_ALL"] = "C"
    try:
        result = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            check=False,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 127, "", str(exc)


def _distribution_ids() -> set[str]:
    try:
        values = {}
        with open("/etc/os-release", encoding="utf-8") as release:
            for line in release:
                key, separator, value = line.partition("=")
                if separator and key in {"ID", "ID_LIKE"}:
                    values[key] = value.strip().strip("\"'").lower()
        return {values.get("ID", ""), *values.get("ID_LIKE", "").split()}
    except OSError:
        return set()


def _check_package_manager(prefix: str) -> CheckResult:
    rc, output, error = _run(["dnf", "check"])
    combined = f"{output}\n{error}".lower()
    if rc == 127 or any(marker in combined for marker in (
        "permission denied",
        "superuser privileges",
        "another app is currently holding the dnf lock",
        "could not obtain lock",
        "failed to obtain the transaction lock",
    )):
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.UNKNOWN,
            summary="DNF could not check the installed package database.",
            details=output or error,
        )

    has_problem = any(marker in combined for marker in (
        "problem:",
        "requires ",
        "missing requires",
        "conflicts with",
    ))
    if rc == 0 and not has_problem:
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.GREEN,
            summary="DNF found no package dependency problems.",
            details=output,
        )
    if not has_problem:
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.UNKNOWN,
            summary="DNF could not determine whether the package database is healthy.",
            details=output or error,
        )
    return CheckResult(
        id="package_manager",
        title="Package Manager Health",
        status=Status.RED,
        summary="DNF reported package dependency or consistency problems.",
        details="\n".join(part for part in (output, error) if part),
        fixes=[Fix(
            id=f"{prefix}_distro_sync",
            title="Synchronize packages with enabled repositories",
            explanation=(
                "DNF distro-sync aligns installed packages with the enabled "
                "repositories and may upgrade, downgrade, install, or remove "
                "packages. Review the transaction carefully."
            ),
            commands=["sudo dnf distro-sync --assumeyes"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.HIGH,
            reason="DNF reported a package consistency problem.",
            expected_changes=[
                "Synchronize installed package versions with enabled repositories",
                "The package transaction may install, downgrade, or remove packages",
            ],
        )],
    )


def _unneeded_dependency_packages() -> tuple[list[str] | None, str]:
    query = ["dnf", "repoquery", "--installed"]
    unneeded_rc, unneeded_output, unneeded_error = _run(
        [*query, "--unneeded", "--queryformat", "%{nevra}"]
    )
    user_rc, user_output, user_error = _run(
        [*query, "--userinstalled", "--queryformat", "%{nevra}"]
    )
    if unneeded_rc != 0 or user_rc != 0:
        return None, unneeded_error or user_error or unneeded_output or user_output

    package_pattern = re.compile(r"[A-Za-z0-9][A-Za-z0-9+_.:-]*")
    unneeded = {
        line.strip()
        for line in unneeded_output.splitlines()
        if package_pattern.fullmatch(line.strip())
    }
    explicitly_installed = {
        line.strip()
        for line in user_output.splitlines()
        if package_pattern.fullmatch(line.strip())
    }
    return sorted(unneeded - explicitly_installed), ""


def _check_unneeded_dependencies(prefix: str) -> CheckResult:
    packages, error = _unneeded_dependency_packages()
    check_id = f"{prefix}_unneeded_dependencies"
    if packages is None:
        return CheckResult(
            id=check_id,
            title="Unneeded Dependencies",
            status=Status.UNKNOWN,
            summary="DNF could not safely identify unused dependency packages.",
            details=error,
        )
    if not packages:
        return CheckResult(
            id=check_id,
            title="Unneeded Dependencies",
            status=Status.GREEN,
            summary="No unused dependency packages were found.",
        )
    return CheckResult(
        id=check_id,
        title="Unneeded Dependencies",
        status=Status.YELLOW,
        summary=f"{len(packages)} unused dependency package(s) were found.",
        details="\n".join(packages),
        fixes=[Fix(
            id=f"{prefix}_remove_orphans",
            title=f"Remove {len(packages)} unneeded package(s)",
            explanation=(
                "These packages were installed as dependencies and are no "
                "longer required. Packages explicitly installed by you are "
                "excluded. Review the list before removal."
            ),
            commands=[],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="DNF identified these packages as unneeded dependencies.",
            expected_changes=[f"Remove: {', '.join(packages)}"],
            options=[FixOption(id=name, label=name) for name in packages],
            command_template=(
                "sudo dnf remove --assumeyes "
                "--setopt=clean_requirements_on_remove=False {selected}"
            ),
        )],
    )


def _check_updates(prefix: str) -> CheckResult:
    rc, output, error = _run(["dnf", "check-update"])
    package_lines = [
        line for line in output.splitlines()
        if re.match(r"^\S+\.[A-Za-z0-9_]+\s+\S+", line)
    ]
    if rc not in (0, 100):
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.UNKNOWN,
            summary="DNF could not check for available updates.",
            details=error or output,
        )
    if not package_lines:
        if rc == 100:
            return CheckResult(
                id="updates",
                title="Available Updates",
                status=Status.UNKNOWN,
                summary="DNF reported updates but their package list could not be read.",
                details=error or output,
            )
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.GREEN,
            summary="No package updates were found in the enabled repositories.",
        )
    return CheckResult(
        id="updates",
        title="Available Updates",
        status=Status.YELLOW,
        summary=f"{len(package_lines)} package update(s) are available.",
        details="\n".join(package_lines[:30]),
        fixes=[Fix(
            id=f"{prefix}_upgrade",
            title=f"Install {len(package_lines)} available update(s)",
            explanation=(
                "DNF will refresh repository metadata and install available "
                "updates. Review the package transaction before continuing."
            ),
            commands=["sudo dnf upgrade --refresh --assumeyes"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="Updates are available from the enabled repositories.",
            expected_changes=[
                f"Upgrade: {', '.join(line.split()[0] for line in package_lines[:15])}",
                "Other dependencies may also be upgraded",
            ],
        )],
    )


def _check_package_cache(prefix: str) -> CheckResult:
    cache_dir = "/var/cache/dnf"
    check_id = f"{prefix}_package_cache"
    if not os.path.isdir(cache_dir):
        return CheckResult(
            id=check_id,
            title="DNF Package Cache",
            status=Status.UNKNOWN,
            summary="The DNF package cache directory was not found.",
        )
    rc, output, error = _run(["du", "-sb", cache_dir])
    if rc != 0:
        return CheckResult(
            id=check_id,
            title="DNF Package Cache",
            status=Status.UNKNOWN,
            summary="Could not measure the DNF package cache.",
            details=error,
        )
    try:
        size_bytes = int(output.split()[0])
    except (ValueError, IndexError):
        return CheckResult(
            id=check_id,
            title="DNF Package Cache",
            status=Status.UNKNOWN,
            summary="Could not parse the DNF package cache size.",
            details=output,
        )
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes < 500 * 1024 * 1024:
        return CheckResult(
            id=check_id,
            title="DNF Package Cache",
            status=Status.GREEN,
            summary=f"The DNF package cache is using {size_mb:.0f} MB.",
        )
    return CheckResult(
        id=check_id,
        title="DNF Package Cache",
        status=Status.YELLOW,
        summary=f"The DNF package cache is using {size_mb:.0f} MB.",
        fixes=[Fix(
            id=f"{prefix}_clean_package_cache",
            title="Clear the DNF package cache",
            explanation=(
                "DNF can clear cached packages and repository metadata. "
                "This does not remove installed software; metadata and "
                "packages will be downloaded again when needed."
            ),
            commands=["sudo dnf clean all"],
            severity=SeverityLevel.SAFE,
            risk=RiskLevel.LOW,
            reason=f"The DNF cache is using {size_mb:.0f} MB.",
            expected_changes=["Remove cached package files and repository metadata"],
        )],
    )


def _check_firewall(prefix: str) -> CheckResult:
    if shutil.which("ufw"):
        from grix.modules.diagnostics import check_security_basics

        return check_security_basics()
    if not shutil.which("firewall-cmd"):
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.UNKNOWN,
            summary=(
                "firewalld is not installed. Grix will not install or enable "
                "a firewall without an explicit user choice."
            ),
        )
    rc, output, error = _run(["firewall-cmd", "--state"])
    if rc == 0 and output == "running":
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.GREEN,
            summary="firewalld is active.",
        )
    active_rc, active_output, _ = _run(["systemctl", "is-active", "firewalld"])
    if active_rc == 127:
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.UNKNOWN,
            summary="Could not check whether firewalld is active.",
            details=error,
        )
    if active_output != "active":
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.YELLOW,
            summary="firewalld is installed but is not active.",
            fixes=[Fix(
                id=f"{prefix}_enable_firewalld",
                title="Enable firewalld",
                explanation=(
                    "Starting firewalld enables network filtering with its "
                    "current configuration. Check your firewall rules first "
                    "if this machine provides network services."
                ),
                commands=["sudo systemctl enable --now firewalld"],
                severity=SeverityLevel.APPROVAL,
                risk=RiskLevel.MEDIUM,
                reason="The installed firewalld service is not active.",
                expected_changes=[
                    "Enable firewalld at startup and start it now",
                    "Network connections may be affected by the configured rules",
                ],
            )],
        )
    return CheckResult(
        id="security",
        title="Firewall",
        status=Status.UNKNOWN,
        summary="firewalld did not report a usable firewall state.",
        details=error or output,
    )


def _check_old_kernels(prefix: str) -> CheckResult:
    rc, output, error = _run([
        "dnf", "repoquery", "--installed", "--installonly",
        "--latest-limit=-3", "--queryformat", "%{name}-%{version}-%{release}.%{arch}",
    ])
    if rc != 0:
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.UNKNOWN,
            summary="DNF could not identify old install-only kernel packages.",
            details=error or output,
        )
    current_rc, current, current_error = _run(["uname", "-r"])
    if current_rc != 0:
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.UNKNOWN,
            summary="Could not identify the currently running kernel.",
            details=current_error,
        )
    old_packages = [
        line.strip()
        for line in output.splitlines()
        if line.strip()
        and line.strip().split("-", 1)[0].startswith("kernel")
        and current.strip() not in line
    ]
    if not old_packages:
        return CheckResult(
            id="old_kernels",
            title="Old Kernel Versions",
            status=Status.GREEN,
            summary="No old install-only kernel packages need cleanup.",
        )
    return CheckResult(
        id="old_kernels",
        title="Old Kernel Versions",
        status=Status.YELLOW,
        summary=f"{len(old_packages)} old install-only kernel package(s) can be cleaned up.",
        details="Old packages:\n" + "\n".join(old_packages),
        fixes=[Fix(
            id=f"{prefix}_remove_old_kernels",
            title="Remove old install-only kernel packages",
            explanation=(
                "DNF removes older install-only packages according to its "
                "configured retention limit and protects the running kernel. "
                "Review the package list before confirming."
            ),
            commands=["sudo dnf remove --oldinstallonly --assumeyes"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="Several old install-only kernel packages were found.",
            expected_changes=[
                f"Remove old packages: {', '.join(old_packages)}",
                "Keep the currently running kernel and DNF's configured retained versions",
            ],
        )],
    )


def register_dnf_checks(
    api,
    supported_ids: Iterable[str],
    prefix: str,
) -> bool:
    """Register DNF checks when the current OS matches a plugin's targets."""
    if not set(supported_ids) & _distribution_ids() or not shutil.which("dnf"):
        return False

    def package_manager_check() -> CheckResult:
        return _check_package_manager(prefix)

    def unneeded_dependencies_check() -> CheckResult:
        return _check_unneeded_dependencies(prefix)

    def updates_check() -> CheckResult:
        return _check_updates(prefix)

    def package_cache_check() -> CheckResult:
        return _check_package_cache(prefix)

    def firewall_check() -> CheckResult:
        return _check_firewall(prefix)

    def old_kernels_check() -> CheckResult:
        return _check_old_kernels(prefix)

    checks = [
        (package_manager_check, ("package_manager",)),
        (updates_check, ("updates",)),
        (unneeded_dependencies_check, ()),
        (firewall_check, ("security",)),
        (old_kernels_check, ("old_kernels",)),
        (package_cache_check, ()),
    ]
    for check, replacements in checks:
        check.__name__ = f"check_{prefix}_{check.__name__}"
        api.register_check(check, replaces=replacements)
    return True
