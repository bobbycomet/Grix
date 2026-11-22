# Grix distribution lesson plugins

These are user-installed Grix plugins. Each directory contains a
`plugin.json` manifest and a `plugin.py` entry point compatible with Grix
plugin API version 1. They add Linux Academy tracks; they do not edit or
replace Grix's built-in lessons.

## Install

Copy the plugin directory you want into Grix's user plugin directory:

```text
~/.local/share/grix/plugins/
```

For example, copy `arch_pacman/` so the final path is
`~/.local/share/grix/plugins/arch_pacman/`. Restart Grix or use **Reload
Plugins** in Settings. Plugins run with Grix's privileges; only install
code from sources you trust.

## Available plugins

### Arch Linux and pacman (`arch_pacman`)

Adds a package-management lesson for Arch Linux and pacman-based
distributions, plus an AUR lesson. The AUR lesson explains that AUR
packages are community-maintained, are not reviewed or supported by the
official Arch repositories, and can be compromised or contain malicious
code. It recommends checking the maintainer, `PKGBUILD`, and upstream
sources and using only trusted sources.

### Fedora and DNF (`fedora_dnf`)

Adds Fedora package-management lessons using DNF and introduces COPR.
The COPR lesson distinguishes community build repositories from Fedora's
official repositories and explains how to assess a project before
enabling it.

### RPM-based distributions (`rpm_family`)

Adds package-management guidance for RPM-based enterprise distributions,
using DNF for repository-aware installs and updates and the `rpm` command
to inspect installed packages. It explains why DNF is generally preferable
to manually installing a local RPM file.

## Wiki descriptions

The three descriptions above are ready to use on the Grix GitHub Wiki's
Plugins page. This repository's wiki is enabled, but its wiki Git
repository has not been created yet.
