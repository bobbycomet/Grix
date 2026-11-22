# Grix distribution lesson plugins

These are user-installed Grix plugins. Each directory contains a
`plugin.json` manifest and a `plugin.py` entry point compatible with Grix
plugin API version 1. In addition to Linux Academy tracks, the
distribution plugin for the running OS adds package-health, update,
package-cache, firewall, and (where safe) old-kernel checks with
user-approved repairs. Grix's generic checks continue to run alongside
them.

## Install

Copy the plugin directory you want into Grix's user plugin directory:

```text
~/.local/share/grix/plugins/
```

For example, Arch is standalone:

```text
~/.local/share/grix/plugins/arch_pacman/
```

The Fedora and RPM-family plugins also need the shared `_shared/`
directory:

```text
~/.local/share/grix/plugins/_shared/
~/.local/share/grix/plugins/fedora_dnf/
```

Copy both directories for the distro plugin you install. Restart Grix
or use **Reload Plugins** in Settings. Plugins run with Grix's
privileges; only install code from sources you trust.

The Sentinel repairs require a Grix build that includes plugin check
replacement support and the corresponding PolicyKit helper actions.

## Available plugins

### Arch Linux and pacman (`arch_pacman`)

Adds a package-management lesson for Arch Linux and pacman-based
distributions, plus an AUR lesson. The AUR lesson explains that AUR
packages are community-maintained, are not reviewed or supported by the
official Arch repositories, and can be compromised or contain malicious
code. It recommends checking the maintainer, `PKGBUILD`, and upstream
sources and using only trusted sources. Sentinel checks pacman dependency
health, available updates, unneeded dependencies, and package-cache size.
It can offer a full-system upgrade, reviewed orphan removal, and cleanup
of uncached package archives. Firewall checks are only performed when
UFW or firewalld is present. Arch kernel flavors are not removed
automatically because multiple installed flavors may be intentional.

### Fedora and DNF (`fedora_dnf`)

Adds Fedora package-management lessons using DNF and introduces COPR.
The COPR lesson distinguishes community build repositories from Fedora's
official repositories and explains how to assess a project before
enabling it. Sentinel checks DNF package consistency, updates, unneeded
dependencies, package-cache size, firewalld, and old install-only kernel
packages. Repairs are shown for approval before execution.

### RPM-based distributions (`rpm_family`)

Adds package-management guidance for RPM-based enterprise distributions,
using DNF for repository-aware installs and updates and the `rpm` command
to inspect installed packages. It explains why DNF is generally preferable
to manually installing a local RPM file. Sentinel provides matching DNF,
firewalld, and kernel-maintenance checks for RHEL-compatible distributions
with DNF installed. Yum-only releases are not currently supported.

## Wiki descriptions

The three descriptions above are ready to use on the Grix GitHub Wiki's
Plugins page. This repository's wiki is enabled, but its wiki Git
repository has not been created yet.
