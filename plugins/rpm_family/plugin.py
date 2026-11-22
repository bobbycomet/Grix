"""RPM-family DNF lessons and Sentinel checks for Grix."""

from _shared.dnf_support import register_dnf_checks
from grix.modules.lessons import Lesson, Track


_SUPPORTED_IDS = {
    "rhel",
    "rocky",
    "almalinux",
    "centos",
    "ol",
    "oracle",
    "oraclelinux",
    "amzn",
}


def register(api) -> None:
    register_dnf_checks(api, _SUPPORTED_IDS, "rpm")
    api.register_lesson_track(
        Track(
            id="rpm_family_package_management",
            title="RPM-Based Systems: DNF & RPM",
            description=(
                "Learn repository-aware package management with DNF and "
                "package inspection with the RPM command."
            ),
            lessons=[
                Lesson(
                    id="rpm_family_dnf_basics",
                    title="Managing Packages on RPM-Based Systems",
                    summary="Use DNF for updates and repository-aware package operations on RHEL-compatible distributions.",
                    blocks=[
                        (
                            "text",
                            "Distributions such as RHEL, Rocky Linux, and "
                            "AlmaLinux use the **RPM** package format. On "
                            "current releases, **DNF** is typically the "
                            "higher-level package manager: it uses configured "
                            "repositories and resolves dependencies. This "
                            "plugin's repair checks require DNF; yum-only "
                            "releases are not currently supported.",
                        ),
                        (
                            "text",
                            "Common DNF commands:\n\n"
                            "- `sudo dnf check-update` - check configured "
                            "repositories for available updates\n"
                            "- `sudo dnf upgrade` - apply package updates\n"
                            "- `sudo dnf install packagename` - install a package\n"
                            "- `sudo dnf remove packagename` - remove a package\n"
                            "- `dnf search keyword` - search enabled repositories\n\n"
                            "Review the proposed transaction before confirming "
                            "it, especially on a server with production workloads.",
                        ),
                        (
                            "quiz",
                            "Which tool normally resolves dependencies for a repository package on a modern RPM-based system?",
                            [
                                "rpm -i",
                                "dnf install",
                                "tar -xf",
                                "systemctl install",
                            ],
                            1,
                            "DNF uses repository metadata and resolves "
                            "dependencies. The lower-level `rpm` command "
                            "inspects and operates on individual RPM packages.",
                        ),
                    ],
                ),
                Lesson(
                    id="rpm_inspecting_packages",
                    title="Inspecting Installed RPM Packages",
                    summary="Use read-only rpm queries to identify package details, contents, and file ownership.",
                    blocks=[
                        (
                            "text",
                            "The `rpm` command can query the RPM database "
                            "without changing installed software:\n\n"
                            "- `rpm -qi packagename` - show package details\n"
                            "- `rpm -ql packagename` - list files installed "
                            "by a package\n"
                            "- `rpm -qf /path/to/file` - identify which "
                            "installed package owns a file\n\n"
                            "For installing or updating software from "
                            "repositories, prefer DNF so dependencies can be "
                            "resolved. If you have a local RPM file, "
                            "`sudo dnf install ./package.rpm` is generally "
                            "safer than installing it directly with `rpm` "
                            "because DNF can resolve dependencies.",
                        ),
                        (
                            "quiz",
                            "Which command identifies the installed package that owns a file?",
                            [
                                "rpm -qf /path/to/file",
                                "rpm -qlf /path/to/file",
                                "dnf -R /path/to/file",
                                "rpm --remove /path/to/file",
                            ],
                            0,
                            "`rpm -qf` queries the installed package database "
                            "for the owner of the specified file.",
                        ),
                    ],
                ),
            ],
        )
    )
