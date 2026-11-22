"""Arch Linux package-management lessons for Grix."""

from grix.modules.lessons import Lesson, Track


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
