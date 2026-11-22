"""Fedora DNF and COPR lessons for Grix."""

from grix.modules.lessons import Lesson, Track


def register(api) -> None:
    api.register_lesson_track(
        Track(
            id="fedora_package_management",
            title="Fedora: DNF & COPR",
            description=(
                "Learn Fedora package-management basics and how to assess "
                "community COPR repositories."
            ),
            lessons=[
                Lesson(
                    id="fedora_dnf_basics",
                    title="Managing Software with DNF",
                    summary="Refresh metadata, update Fedora, and install or remove software with DNF.",
                    blocks=[
                        (
                            "text",
                            "Fedora uses **DNF** to manage RPM packages from "
                            "configured repositories. DNF can refresh repository "
                            "metadata and apply updates in one operation with "
                            "`sudo dnf upgrade --refresh`. You can also refresh "
                            "metadata separately with `sudo dnf makecache "
                            "--refresh` before reviewing available updates.",
                        ),
                        (
                            "text",
                            "Common commands:\n\n"
                            "- `sudo dnf upgrade --refresh` - refresh metadata "
                            "and upgrade installed packages\n"
                            "- `sudo dnf install packagename` - install a package\n"
                            "- `sudo dnf remove packagename` - remove a package\n"
                            "- `dnf search keyword` - search enabled repositories\n\n"
                            "Review the proposed changes before confirming an "
                            "operation. Some Fedora releases use DNF5; command "
                            "availability can vary by release and installed "
                            "plugins.",
                        ),
                        (
                            "quiz",
                            "Which DNF command refreshes metadata and applies package updates?",
                            [
                                "sudo dnf search --refresh",
                                "sudo dnf upgrade --refresh",
                                "sudo dnf remove --refresh",
                                "dnf list --install",
                            ],
                            1,
                            "`dnf upgrade --refresh` refreshes repository "
                            "metadata and then upgrades packages, rather than "
                            "only updating a catalog.",
                        ),
                    ],
                ),
                Lesson(
                    id="fedora_copr_safety",
                    title="Fedora COPR: Community Repositories",
                    summary="Learn what COPR provides and how to make an informed decision before enabling a project.",
                    blocks=[
                        (
                            "text",
                            "**COPR** is a Fedora build service where "
                            "individuals and groups can build packages in "
                            "additional repositories. COPR projects are "
                            "community-provided, not part of Fedora's official "
                            "repositories, and may vary in maintenance and "
                            "review. A repository can receive package "
                            "updates with the same privileges as other "
                            "software sources you enable.",
                        ),
                        (
                            "text",
                            "Before enabling a COPR project, verify the "
                            "project owner and purpose, check its build "
                            "instructions and source links, and consider "
                            "whether you trust that maintainer to distribute "
                            "software for your system. Prefer Fedora's official "
                            "repositories when possible. Disable a COPR "
                            "repository when you no longer need it.",
                        ),
                        (
                            "text",
                            "On Fedora systems with the COPR DNF plugin "
                            "available, the usual workflow is:\n\n"
                            "```\n"
                            "sudo dnf copr enable owner/project\n"
                            "sudo dnf install packagename\n"
                            "sudo dnf copr disable owner/project\n"
                            "```\n\n"
                            "The exact plugin package or command may differ "
                            "between Fedora releases and DNF versions. Check "
                            "Fedora's documentation for your release before "
                            "installing or enabling a project.",
                        ),
                        (
                            "quiz",
                            "How should you treat a COPR project?",
                            [
                                "As an official Fedora repository",
                                "As a community source to evaluate before enabling",
                                "As a source that cannot update installed software",
                                "As safe whenever a command uses DNF",
                            ],
                            1,
                            "COPR is a community build service. Evaluate the "
                            "maintainer, project, and sources before enabling "
                            "it, just as you would any additional software source.",
                        ),
                    ],
                ),
            ],
        )
    )
