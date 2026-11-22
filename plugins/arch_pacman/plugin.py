"""Arch Linux package-management lessons for Grix."""

import os
import re
import shutil
import subprocess

from grix.modules.diagnostics import (
    CheckResult,
    Fix,
    FixOption,
    RiskLevel,
    SeverityLevel,
    Status,
)
from grix.modules.lessons import Lesson, Track


def _run(args: list[str], timeout: int = 30) -> tuple[int, str, str]:
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


def _is_arch_based() -> bool:
    return bool({"arch"} & _distribution_ids()) and shutil.which("pacman") is not None


def check_arch_package_manager() -> CheckResult:
    rc, output, error = _run(["pacman", "-Dk"])
    combined = f"{output}\n{error}".lower()
    if rc == 127 or any(marker in combined for marker in (
        "could not lock database",
        "database is locked",
        "unable to lock database",
    )):
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.UNKNOWN,
            summary="pacman is unavailable or currently in use, so package health was not checked.",
            details=error or output,
        )

    issues = []
    fixes = []
    dependency_issue = rc != 0 or "warning:" in combined
    if dependency_issue:
        issues.append("pacman reported package dependency or database issues.")
        fixes.append(Fix(
            id="arch_sync_repair",
            title="Synchronize and upgrade the system",
            explanation=(
                "Arch systems should be upgraded as a whole. A full "
                "synchronization can resolve dependency inconsistencies; "
                "review pacman's transaction before it runs."
            ),
            commands=["sudo pacman -Syu --noconfirm"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="pacman reported dependency or database inconsistencies.",
            expected_changes=[
                "Synchronize package databases and upgrade installed packages",
                "pacman may install or remove packages to resolve dependencies",
            ],
        ))

    orphan_rc, orphan_output, orphan_error = _run(["pacman", "-Qtdq"])
    orphan_query_failed = orphan_rc not in (0, 1)
    orphan_names = [
        line.strip()
        for line in orphan_output.splitlines()
        if re.fullmatch(r"[A-Za-z0-9@._+:-]+", line.strip())
    ]
    if orphan_query_failed and not dependency_issue:
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.UNKNOWN,
            summary="pacman could not check for unused dependency packages.",
            details=orphan_error or orphan_output,
        )
    if orphan_names:
        issues.append(
            f"{len(orphan_names)} unneeded dependency package(s) were found."
        )
        fixes.append(Fix(
            id="arch_remove_orphans",
            title=f"Remove {len(orphan_names)} unneeded package(s)",
            explanation=(
                "These packages were installed as dependencies and are no "
                "longer required. Review the selected package names; a "
                "package may still be useful even if nothing currently "
                "depends on it."
            ),
            commands=[],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="pacman marked these packages as unneeded dependencies.",
            expected_changes=[f"Remove: {', '.join(orphan_names)}"],
            options=[FixOption(id=name, label=name) for name in orphan_names],
            command_template="sudo pacman -Rns {selected}",
        ))

    if not issues:
        return CheckResult(
            id="package_manager",
            title="Package Manager Health",
            status=Status.GREEN,
            summary="pacman found no package database or dependency issues.",
            details=output,
        )
    return CheckResult(
        id="package_manager",
        title="Package Manager Health",
        status=Status.RED if dependency_issue else Status.YELLOW,
        summary=" ".join(issues + (
            ["pacman could not check for unused dependency packages."]
            if orphan_query_failed else []
        )),
        details="\n".join(
            part for part in (output, error, orphan_output, orphan_error) if part
        ),
        fixes=fixes,
    )


def check_arch_updates() -> CheckResult:
    rc, output, error = _run(["pacman", "-Qu"])
    if rc != 0:
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.UNKNOWN,
            summary="pacman could not check for available updates.",
            details=error or output,
        )
    packages = [line for line in output.splitlines() if line.strip()]
    if not packages:
        return CheckResult(
            id="updates",
            title="Available Updates",
            status=Status.GREEN,
            summary="No updates were found in pacman's current sync databases.",
        )
    return CheckResult(
        id="updates",
        title="Available Updates",
        status=Status.YELLOW,
        summary=f"{len(packages)} package update(s) are available.",
        details="\n".join(packages[:30]),
        fixes=[Fix(
            id="arch_upgrade",
            title=f"Install {len(packages)} available update(s)",
            explanation=(
                "Arch Linux is a rolling release. Update the whole system "
                "together rather than upgrading selected packages."
            ),
            commands=["sudo pacman -Syu --noconfirm"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason="Updates are available from the currently synchronized repositories.",
            expected_changes=[
                f"Upgrade: {', '.join(line.split()[0] for line in packages[:15])}",
                "Other dependencies may also be upgraded",
            ],
        )],
    )


def check_arch_package_cache() -> CheckResult:
    cache_dir = "/var/cache/pacman/pkg"
    if not os.path.isdir(cache_dir):
        return CheckResult(
            id="arch_package_cache",
            title="Pacman Package Cache",
            status=Status.UNKNOWN,
            summary="The pacman package cache directory was not found.",
        )
    rc, output, error = _run(["du", "-sb", cache_dir])
    if rc != 0:
        return CheckResult(
            id="arch_package_cache",
            title="Pacman Package Cache",
            status=Status.UNKNOWN,
            summary="Could not measure the pacman package cache.",
            details=error,
        )
    try:
        size_bytes = int(output.split()[0])
    except (ValueError, IndexError):
        return CheckResult(
            id="arch_package_cache",
            title="Pacman Package Cache",
            status=Status.UNKNOWN,
            summary="Could not parse the pacman package cache size.",
            details=output,
        )
    size_mb = size_bytes / (1024 * 1024)
    if size_bytes < 500 * 1024 * 1024:
        return CheckResult(
            id="arch_package_cache",
            title="Pacman Package Cache",
            status=Status.GREEN,
            summary=f"The pacman package cache is using {size_mb:.0f} MB.",
        )
    return CheckResult(
        id="arch_package_cache",
        title="Pacman Package Cache",
        status=Status.YELLOW,
        summary=f"The pacman package cache is using {size_mb:.0f} MB.",
        fixes=[Fix(
            id="arch_clean_package_cache",
            title="Clear cached packages not currently installed",
            explanation=(
                "pacman can remove cached package archives that are not "
                "currently installed. Older cached versions will no longer "
                "be available for a quick local downgrade."
            ),
            commands=["sudo pacman -Sc --noconfirm"],
            severity=SeverityLevel.APPROVAL,
            risk=RiskLevel.MEDIUM,
            reason=f"The package cache is using {size_mb:.0f} MB.",
            expected_changes=[
                "Remove cached package archives for packages not currently installed",
                "Installed software is not changed",
            ],
        )],
    )


def check_arch_firewall() -> CheckResult:
    if shutil.which("ufw"):
        from grix.modules.diagnostics import check_security_basics

        return check_security_basics()
    if not shutil.which("firewall-cmd"):
        return CheckResult(
            id="security",
            title="Firewall",
            status=Status.UNKNOWN,
            summary=(
                "No supported firewall command was found. Grix does not "
                "assume that an absent firewall service should be installed."
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
                id="arch_enable_firewalld",
                title="Enable firewalld",
                explanation=(
                    "Starting firewalld enables network filtering using "
                    "its current configuration. Check your firewall rules "
                    "first if this machine provides network services."
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


def check_arch_old_kernels() -> CheckResult:
    return CheckResult(
        id="old_kernels",
        title="Old Kernel Versions",
        status=Status.UNKNOWN,
        summary=(
            "Arch kernel packages are rolling-release packages, and multiple "
            "kernel flavors may be intentional fallbacks. Grix will not "
            "remove one without a reliable way to distinguish old versions "
            "from kernels you chose to keep."
        ),
    )


def register(api) -> None:
    api.register_lesson_track(
        Track(
            id="arch_package_management",
            title="Arch Linux: Packages & the AUR",
            description=(
                "Learn to manage software with pacman and evaluate "
                "community packages from the Arch User Repository."
            ),
            lessons=[
                Lesson(
                    id="arch_pacman_basics",
                    title="Managing Software with pacman",
                    summary="Install, update, remove, and search for packages with pacman.",
                    blocks=[
                        (
                            "text",
                            "Arch Linux and many Arch-based distributions use "
                            "**pacman** with the official repositories. Keep "
                            "the package database and installed packages in "
                            "sync with `sudo pacman -Syu`. Arch is a rolling "
                            "release distribution; avoid partial upgrades "
                            "such as upgrading selected packages without "
                            "updating the rest of the system.",
                        ),
                        (
                            "text",
                            "Common commands:\n\n"
                            "- `sudo pacman -Syu` - synchronize repositories "
                            "and upgrade the whole system\n"
                            "- `sudo pacman -S packagename` - install a package\n"
                            "- `sudo pacman -R packagename` - remove a package\n"
                            "- `pacman -Ss keyword` - search repository packages\n\n"
                            "Read the transaction summary before confirming "
                            "a package operation.",
                        ),
                        (
                            "quiz",
                            "Which command is the normal full system upgrade on Arch?",
                            [
                                "sudo pacman -Sy",
                                "sudo pacman -Syu",
                                "sudo pacman -Ryu",
                                "pacman -Ss",
                            ],
                            1,
                            "`sudo pacman -Syu` synchronizes repository "
                            "databases and upgrades installed packages "
                            "together, avoiding a partial system upgrade.",
                        ),
                    ],
                ),
                Lesson(
                    id="arch_aur_safety",
                    title="The AUR: Community Packages and Safety",
                    summary="Understand the AUR's community-maintained model and how to assess packages before building them.",
                    blocks=[
                        (
                            "text",
                            "The **Arch User Repository (AUR)** is a community "
                            "collection of build recipes, usually `PKGBUILD` "
                            "files. It is not an official Arch repository, and "
                            "AUR packages are not vetted or supported by Arch "
                            "Linux in the same way as official repository "
                            "packages. AUR maintainers can change, accounts "
                            "and sources can be compromised, and a recipe can "
                            "contain malicious code. Treat every AUR package "
                            "as code you are choosing to run.",
                        ),
                        (
                            "text",
                            "Before building an AUR package, check that its "
                            "maintainer and upstream project are sources you "
                            "trust. Read the `PKGBUILD` and review its source "
                            "URLs, checksums, and install steps. Do not blindly "
                            "approve changes shown by an AUR helper, and do "
                            "not run a build or install script you have not "
                            "inspected. Prefer an official repository package "
                            "when one meets your needs.",
                        ),
                        (
                            "text",
                            "A manual review workflow starts by downloading "
                            "the recipe, inspecting it, and building it as your "
                            "regular user:\n\n"
                            "```\n"
                            "git clone https://aur.archlinux.org/package-name.git\n"
                            "cd package-name\n"
                            "less PKGBUILD\n"
                            "makepkg -si\n"
                            "```\n\n"
                            "`makepkg -si` should not be run with `sudo`; it "
                            "builds as your user and requests privileges only "
                            "when installing the resulting package. These "
                            "commands do not make an untrusted recipe safe: "
                            "inspect it first and use only sources you trust.",
                        ),
                        (
                            "quiz",
                            "What is the safest assumption when considering an AUR package?",
                            [
                                "It is reviewed by the Arch security team",
                                "It is community-provided code that must be checked before use",
                                "It cannot run installation scripts",
                                "An AUR helper makes every package trustworthy",
                            ],
                            1,
                            "AUR recipes are community-maintained and can "
                            "change or become compromised. Review the recipe "
                            "and its sources, and use only sources you trust.",
                        ),
                    ],
                ),
            ],
        )
    )
    if _is_arch_based():
        api.register_check(check_arch_package_manager, replaces=("package_manager",))
        api.register_check(check_arch_updates, replaces=("updates",))
        api.register_check(check_arch_firewall, replaces=("security",))
        api.register_check(check_arch_old_kernels, replaces=("old_kernels",))
        api.register_check(check_arch_package_cache)
