# Grix a Linux System Companion

---
<p align="center">
<img width="300" height="300" alt="Grix" src="https://github.com/user-attachments/assets/4dc225b4-21e0-4983-bec2-8a86209a3572" />
</p>

You switched to Linux, or you have been on it for years, and yet there is always *that moment*. Sound stops working after an update. A game crashes on launch for no obvious reason. Your controller connects but does nothing. You Google the error, land on a five-year-old forum thread, try three different commands, and an hour later, you still do not know if you fixed it or just got lucky.

Linux is powerful. It is also unforgiving in ways that have nothing to do with how smart you are. The knowledge required to diagnose a broken PipeWire session, a missing Vulkan ICD, or a Realtek WiFi chip with an out-of-tree driver is specialized, scattered across wikis, and changes with every kernel release. Most people should not have to know any of that just to use their computer.

**Grix exists because that gap is real, and it matters.** It is the tool that watches your system, speaks plainly about what it finds, and handles the fix, so you can get back to whatever you were actually trying to do.

---

<p align="center">
  <b>The system troubleshooter and learning companion Linux never shipped with.</b><br>
  Built for people who switched from Windows and want their computer to just work.

---

## What is Grix?

Grix is a desktop app for Debian and Ubuntu-based Linux systems that does two things most distros leave you to figure out yourself:

**It explains what's wrong and fixes it safely.** System Sentinel scans your system for common health issues, broken packages, failing services, disk bloat, outdated software, network problems, an inactive firewall, stale logs, and surfaces each one in plain language with a **Repair Preview** showing the exact command that will run, why it's needed, what will change, and the risk level. You approve every single action before anything happens. Nothing runs silently.

**It teaches you Linux while you use it.** Linux Academy walks you through 29 lessons across three skill tracks. Beginner, Intermediate, and Advanced, using a built-in practice terminal that simulates a real filesystem so you can try commands without risking anything on your actual system. Every lesson is written the way Grix explains repairs: in plain English, by a human, for a human.

The goal is simple: close the gap that sends new Linux users back to Windows when something breaks, not by hiding what's happening, but by explaining it well enough that you understand a little more every time.

---

## What Grix Does

### 🛡️ System Sentinel

Runs scheduled or on-demand scans of your system and reports findings in plain English, no raw error codes. Each finding has:

- **An explanation** of what's wrong and why it matters
- **A Repair Preview** with the exact command Grix will run, risk level, and what will change
- **Your approval** before anything happens, no silent changes, ever
- **A repair log** with rollback hints if something wasn't what you expected

Checks on every scan:

| Category | What it looks for |
|---|---|
| Package management | Broken dependencies, interrupted installs, available updates, APT lock conflicts. This works with your package manager; it does not replace it. I would suggest using your package manager for updates, as some updates will be phased or locked by Ubuntu until Ubuntu releases them. So, you may get a warning that one or more did not update. |
| Disk space | Root partition usage, APT cache, old kernels, unused Flatpak runtimes, old Snap revisions, oversized backup snapshots |
| Services | Failed systemd units, audio stack health (PipeWire / PulseAudio) |
| Networking | Internet connectivity, firewall (ufw) status |
| System logs | Journal size, recent error clusters |
| Files | Home directory files unexpectedly owned by root |
| Boot | Most recent boot time |

<img width="1920" height="1080" alt="Screenshot_20260706_145536" src="https://github.com/user-attachments/assets/63ea4d1a-5950-46b9-9be0-12fba4ff1f4a" />

Auto-scanning runs in the background on a schedule you control (hourly by default, or daily, weekly, or never). The mascot and tray icon update when results change — you don't need to open the app to know if something needs attention.

### 🎓 Linux Academy

Three tracks, 29 hands-on lessons, one sandboxed practice terminal per lesson. The sandbox simulates a complete Linux filesystem — everything you type there stays there, nothing touches your real system.

- **Beginner: Getting Comfortable** — the terminal, the filesystem, files and directories, permissions, common commands, software management
- **Intermediate: Thinking Like an Admin** — pipes, grep, processes, services, logs, systemd, networking basics, your first shell script
- **Advanced: System Mastery & Local Control** — text processing (find, sed, awk, xargs), Flatpak and sandboxed apps, backups with tar and rsync, SSH and key-based authentication, customizing your shell

<img width="1920" height="1080" alt="Screenshot_20260706_145336" src="https://github.com/user-attachments/assets/d1b4e4be-5212-43e8-a402-b0282a57bb3a" />

### 🔍 Explain This Error

Paste any error message from a terminal, a log file, or a crash dialog, and Grix looks it up against a knowledge base of common Linux system errors (only the ones it knows about). You get a plain-language explanation of what it means, diagnosis steps, and what to try next. When something is outside what the knowledge base covers, app-specific bugs, Python tracebacks, hardware failures, Grix says so explicitly rather than guessing. The "What does this recognize?" panel always shows the exact current scope of what's covered.

### 📅 System Timeline

"My system was fine yesterday. What changed?" System Timeline correlates recent journal errors with recent package changes, so you're not guessing blind about what broke what.

### 🖥️ System Information

A live view of your hardware and configuration — hostname, distro, kernel, CPU, RAM, GPU, driver version — pulled from your system directly and, if Kernel Autotune is installed, enriched with its full tuning profile. When something goes wrong that Grix can't fix on its own, this page gives you everything you'd need to share when asking for help.

### 🦉 A mascot that actually tells you something

Grix's mascot changes mood based on what's happening: sleepy when idle, studying while scanning, working while applying a fix, and green/yellow/red depending on system health. The same state shows in the system tray icon, so you can see whether anything needs attention without opening the app.

---

## What Grix Doesn't Do

Being upfront about this matters as much as the feature list. Grix **does not**:

- Diagnose individual application crashes or bugs — it checks system-level health, not the internal behavior of every program you have installed
- Replace hardware diagnostic tools — it can surface relevant log entries, but tools like `smartctl` and `memtest86+` are the right choice for failing drives and RAM
- Act as a security scanner or intrusion detection system — the firewall check confirms ufw is active, nothing more
- Run on non-Debian/Ubuntu-based distros reliably — checks depend on `apt`/`dpkg` conventions
- Perform open-ended analysis — System Sentinel only runs its defined checks plus any installed plugins, nothing more

The same applies to Explain This Error: it covers Linux system errors (packages, permissions, disk, networking, services, shell), not application bugs, programming errors, or anything outside that defined scope.

---

## Grix Works With Your System, Not Against It

Grix is specifically designed to never compete with or undermine the tools your system already uses.

Every fix Grix suggests routes through **`pkexec`** — the same mechanism Linux desktop environments use for privileged actions — and shows you a graphical authentication prompt with a Grix-branded, narrowly scoped permission description. You always see exactly what will run before you authorize it, and you can copy any fix command and run it yourself in a terminal instead if you prefer.

When scheduling background scans, Grix checks whether APT or dpkg is actively running before starting and backs off if they are. Package management is never interrupted, never raced against, and never duplicated. Grix reads what the package manager knows; it doesn't try to replace it.

Nothing Grix does touches your system without your explicit approval — no silent background changes, no auto-applying fixes, no sending data anywhere. Everything stays local.

---

## The Plugin System

Grix is designed to grow without you having to wait for an official update. Any developer, or any power user comfortable writing a Python file, can add new System Sentinel checks, new Linux Academy lesson tracks, or entirely new UI panels by dropping a plugin folder into:

```
~/.local/share/grix/plugins/
```

That's it. Grix picks it up on the next launch (or when you click **Reload Plugins** in Settings); no reinstall needed. This works identically whether you're running Grix from source, a pip install, or an AppImage; the plugin directory is always on your real, writable filesystem.

### How plugins work

A plugin is a folder with two files:

```
my_plugin/
├── plugin.json   # name, version, author, description
└── plugin.py     # registers checks, lessons, or panels
```

`plugin.py` defines a single `register(api)` function. From there, the API gives you three extension points:

```python
def register(api):
    # Add a new System Sentinel check
    api.register_check(my_check_function)

    # Add a source with a variable number of findings per scan
    api.register_dynamic_checks(my_findings_provider)

    # Add a new Linux Academy lesson track
    api.register_lesson_track(my_track)

    # Add a new top-level UI panel with its own sidebar button
    api.register_panel("my_panel", "My Panel Label", MyPanelWidget)
```

A check function takes no arguments and returns a `CheckResult` — the same dataclass Grix's own 13 built-in checks use, with status, summary, explanation, suggested fix commands, risk level, and rollback hint. Your check goes through exactly the same Repair Preview and approval workflow as a built-in check.

**Dependency handling:** plugins that only use Python's standard library work immediately. If a plugin needs a third-party package, install it into the plugin lib directory:

```bash
pip install --target ~/.local/share/grix/plugins/lib <package>
```

Grix adds that directory to `sys.path` automatically if it exists.

**Safety:** a plugin runs with the same privileges as Grix itself — there's no sandboxing, so only install plugins from sources you trust. A plugin that fails to load, has a missing manifest, raises during `register()`, or was built against a different API version is skipped with a recorded error visible in **Settings → Plugins** — it never crashes the rest of the app.

The **Griffin Linux Suite integration is itself an ordinary plugin** (`grix/plugins/griffin_suite/`), useful as a working example. It reads status files from `~/.local/share/griffin/<tool-name>/status.json` and surfaces findings as System Sentinel checks. Any tool that writes a file in that format gets picked up automatically — no fixed list of recognized tool names.

See [CONTRIBUTING.md](CONTRIBUTING.md#the-plugin-system) for the full plugin API reference.

---

## Grix Is Standalone, but Works Best With the Griffin Linux Suite

Grix is completely self-contained and useful on any Debian/Ubuntu system with nothing else installed. But if you want a more complete experience built around the same idea — no terminal required, plain-language explanations, safe by default, designed for the Windows switcher — the rest of the Griffin Linux Suite fits together with Grix naturally.

Each tool is independent. Install any one of them, all of them, or none of them. They don't require each other to function.

---

### [Kernel Autotune](https://github.com/bobbycomet/kernel-autotune-V2)

Intelligently tunes Linux kernel parameters for your specific hardware: swappiness, dirty ratios, VFS cache pressure, CPU governor, TCP congestion control, ZRAM/Zswap configuration, and I/O scheduler. Detects whether you're on a desktop, laptop, or handheld, identifies your kernel (XanMod, Liquorix, Zen, CachyOS, or mainline), and applies a tailored profile automatically. Works as a systemd service with no ongoing configuration needed.

**With Grix:** Grix reads Kernel Autotune's `state.json` to show your current tuning profile under **Settings → System Info**, so you always know what your kernel is doing and can share that context when asking for help. If Kernel Autotune detects a problem (a governor not applied, a step that failed), its findings can surface as System Sentinel checks through the plugin system.

---

### [Process Sentry](https://github.com/bobbycomet/Process-Sentry)

A predictive, adaptive process priority daemon. Quietly watches in the background and throttles processes that are hogging CPU, memory, or I/O before they make your desktop sluggish — without ever killing anything. Learns which programs are repeat offenders over time and gets faster at reining them in. Automatically backs off during games and is aware of Appify PWA apps, so those are never throttled.

**With Grix:** Process Sentry runs as a systemd service that Grix's failed-service check can monitor and can report findings through the plugin system the same way Kernel Autotune does.

---

### [XKM — Multi-Kernel Manager](https://github.com/bobbycomet/XKM-Multi-Kernel-Manager)

A graphical kernel manager for Ubuntu-based systems. Browse, install, hold, and remove kernels — XanMod, Liquorix, and mainline — without touching the terminal. Handles repository setup, DKMS, bootloader updates, and kernel pinning from one clean interface. Includes an auto-remove button that keeps your active and most recent kernels and cleans up the rest.

**With Grix:** Grix's old-kernels check detects accumulated kernel versions taking up disk space and points toward cleaning them up. XKM is exactly the tool to do that cleanup with full visibility into which kernels are installed and which is currently running.

---

### [Appify](https://github.com/bobbycomet/Appify)

Turns any website into a real desktop app in under a second. Each app gets an isolated browser profile, its own taskbar icon and application menu entry, and optional extension presets. Supports every browser you have installed (native, Flatpak, and Snap), works correctly on both Wayland and X11, and includes cloud gaming-aware kiosk mode with gamepad support. No userChrome.css, no fragile hacks.

**With Grix:** Appify apps are automatically recognized by Process Sentry and exempt from throttling. Grix's Flatpak and Snap checks are aware of the kinds of browser runtimes Appify-launched apps use.

---

## [Griffin Updater](https://github.com/bobbycomet/GriffinUpdater/tree/main)

Griffin ships with a dedicated updater for all of its tools. It checks each tool's GitHub repo for updates and lets you update from a simple GUI, no terminal required. There's no auto-update by design; you choose when to update, so you can see how a release lands before committing.

If a Griffin tool isn't installed yet, Griffin Updater handles that too. Click Install next to any tool, and it takes care of the rest. For tools available in both AppImage and Deb formats, choose your preference once, and the updater remembers it.

- **AppImage** (Deb also available where noted): Appify, Griffin Hub, Grix, Fan Hub, Griffin Updater, XKM
- **Deb only**: Griffin Persona

---

### [Fan Hub](https://github.com/bobbycomet/Fan-Hub)

Graphical fan curve editor for Linux. Fine-grained control over fan behavior per-sensor, without needing to drop to a terminal or edit config files by hand.

**With Grix:** Fan Hub will report its status through the same Griffin plugin format, surfacing any fan control issues directly in System Sentinel alongside Grix's own health checks.

---

## Getting Started

```bash
git clone https://github.com/bobbycomet/Grix
cd grix
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python3 -m grix.main
```

For a full install, AppImage packaging, and the optional PolicyKit integration (which gives Grix-branded, narrowly-scoped admin prompts instead of a generic `pkexec` dialog), see [CONTRIBUTING.md](CONTRIBUTING.md#requirements).

**Requirements:** Python 3.10+, a Debian/Ubuntu-based system (Ubuntu, Mint, Pop!_OS, Zorin OS, elementary OS, and similar).

---

## Contributing and Community

Bug reports, feature requests, plugin ideas, and pull requests are all welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for the full architecture guide, how the Repair Preview safety model works, how to write a plugin, and documented gotchas that have caused real bugs (worth reading before adding a new check).

For help with your system, questions about the Griffin Linux Suite, or just to share what you've built with the plugin system:

**[Join the Griffin Linux Discord →](https://discord.gg/fMCpeNCxhv)**

---

## Licensing and Branding

Grix is released under the **GNU General Public License v3 (GPLv3)**. The GPLv3 was chosen specifically because the name **Grix** and all associated icons and visual identity are part of the **Griffin Linux** branding. The copyleft terms of GPLv3 ensure that if anyone distributes a modified version of Grix, they must do so under the same license and cannot rebrand it as a proprietary product built on Griffin Linux's work.

Plugins you write for your own use are not affected by this; the plugin API is intentionally simple and does not create a derivative work of Grix itself under normal use.

---

## Distribution

Grix will be distributed as an **AppImage** when released. An AppImage is a single self-contained file that runs on any modern Linux distribution without installation. Download it, make it executable (`chmod +x Grix-*.AppImage`), and run it. No package manager, no root, no system changes required for the application itself.

AppImage requires FUSE to mount the image at runtime. Grix itself checks for both libfuse2 and libfuse3, so if your system is missing one, Grix will tell you and offer to install it.

---

## Technical Reference

### Requirements

- Python 3.10+
- PyQt6
- A systemd-based Linux distribution (Debian/Ubuntu)
- KDE
- JetBrains Mono font (optional but recommended; used for terminal-style detail views)

---

## Community and Support

- **Discord:** [Join Here](https://discord.gg/7fEt5W7DPh)
- **Patreon (Beta Builds):** [Patreon](https://www.patreon.com/c/BobbyComet/membership)
- **Support the Griffin Project:** [Ko-fi](https://ko-fi.com/bobby60908)

<div align="center">
  <img src="https://raw.githubusercontent.com/bobbycomet/Appify/main/Griffin-G.png" alt="Griffin Linux" width="15%"/>
  <p><strong>Griffin Linux. Where power meets simplicity.</strong><br/>
  Made with Windows switchers in mind. Built for everyone who wants a better PC.</p>
</div>

*Grix is part of the Griffin Linux project. The name Grix, the Griffin Linux name, and associated icons are protected under the GPLv3 to preserve the integrity of the branding in all distributed versions.*
