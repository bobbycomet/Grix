# Contributing to Grix

This document covers Grix's architecture, design philosophy, build
process, and how to extend it (new checks, new lessons, new Griffin
Suite integrations). For what Grix *is* and why it exists, see
[README.md](README.md).

Grix is a friendly Linux system troubleshooter and learning companion for
Debian/Ubuntu-based desktops, built with Python and PyQt6.

Grix has two halves:

- **System Sentinel** - a guided diagnostic and repair assistant. It
  detects common issues (broken packages, failed services, low disk
  space, available updates, network problems, old kernels, and more),
  explains what it found in plain language, and offers safe fixes that
  you review and approve before anything changes via a **Repair
  Preview**. Every applied fix is logged with a rollback hint.

- **Linux Academy** - three tracks, beginner through advanced, teaching
  the terminal, the filesystem, permissions, processes, services, logs,
  text processing, sandboxed apps, backups, secure remote access, and
  shell customization. Lessons include hands-on practice in a built-in
  sandbox terminal that simulates a filesystem, so nothing you try
  touches your real computer.

Grix's mascot changes mood depending on what's happening: sleepy when
idle, studying while scanning, working while applying a fix, and
green/yellow/red depending on overall system health. The same mood is
mirrored in a **system tray icon**, so you can see Grix's status at a
glance even when the window is closed.

The whole interface uses a Steam-inspired dark theme (deep blue-grey
backgrounds, soft blue accents) designed for clear contrast - no
white-on-white or black-on-black text.

## Design Philosophy

Grix follows a strict safety model:

1. **Detect** - read-only checks only.
2. **Explain** - every finding is described in plain language, not just
   raw error codes, with an optional **"Why did this happen?"** section
   giving background on the underlying cause.
3. **Offer (Repair Preview)** - suggested fixes are shown with: the
   exact command(s) that will run (always visible, even for "Safe"
   fixes), *why* Grix wants to do this, a risk level, and a bullet list
   of expected changes.
4. **Confirm** - nothing changes until you click "Apply Fix" in the
   Repair Preview dialog. Advanced/destructive actions require typing
   `CONFIRM`. Fixes that affect multiple items (like old kernels) use a
   checklist where protected items (like your running kernel) can't be
   selected.
5. **Log** - every applied fix is recorded in Repair History with a
   timestamp, the commands run, the result, and a rollback hint.

Fixes are categorized by both **severity** and **risk**:

- 🟢 **Safe** - clearing caches, refreshing package lists, trimming logs
- 🟡 **Requires approval** - restarting services, removing packages,
  installing updates, enabling the firewall, and removing old kernels
- 🔴 **Advanced** - reserved for higher-risk actions; requires typing
  `CONFIRM`

Risk levels (Low/Medium/High) are shown alongside severity in the Repair
Preview, independent of how much confirmation is required - e.g., enabling
the firewall is "Requires approval" + "Medium risk" because it could
affect things like local file sharing.

### Privileged commands (pkexec / PolicyKit)

Fixes that need administrator rights run through `pkexec` (PolicyKit) by
default, which shows a native graphical authentication prompt - this
works reliably from a GUI app even when there's no visible terminal for
`sudo` to prompt in, and is why checks like the firewall status check
can actually read protected state instead of silently failing. If
`pkexec` isn't available; Grix automatically falls back to `sudo`.

For an even narrower privilege scope, `policykit/install.sh` installs a
small `grix-helper` script plus a dedicated PolicyKit policy
(`com.griffinlinux.grix.policy`). Once installed, `pkexec` only ever
authorizes that helper - which itself only accepts a fixed, validated
set of subcommands matching Grix's built-in repairs (see
`policykit/grix-helper`) - rather than an arbitrary command string.
This is entirely optional; Grix works the same either way, just with a
slightly broader (still pkexec-gated) authorization if the helper isn't
installed.

Every Repair Preview also shows a plain `sudo` copy of the underlying
command, for anyone who'd rather paste it into their own terminal
instead of using the graphical prompt.

**A note for anyone touching this code:** when running from an
AppImage, the bundled `grix-helper`/policy files live inside the
AppImage's FUSE mount (e.g. `/tmp/.mount_Grix-XXXXXX/...`). FUSE
mounts block access from any user other than the one who created the
mount - **including root** - regardless of the file's own permission
bits. Since `pkexec` runs the install/uninstall step as root, pointing
it directly at a path under that mount always fails with a flat
"Permission denied", no matter what. `grix/modules/policykit.py`'s
`install()` (and the equivalent logic baked into `AppRun` by
`build_appimage.sh`) works around this by first copying the bundled
files into a plain temp directory **as the current user** - who can
read the mount - and only then runs `pkexec` against that staged copy.
Any future code path that has `pkexec` (or anything else running as a
different user) read a file bundled inside the AppImage needs to do
the same staging step first.

## Additional Features

- **Explain This Error** - paste any error message (from a terminal, a
  log, or a crash dialog) and Grix matches it against a local knowledge
  base to explain what it likely means, suggest next steps, and link to
  the relevant System Sentinel check or Academy lesson. Nothing is run
  automatically - this is pure pattern matching against text you provide.

- **System Timeline** - "my system was fine yesterday, what changed?"
  Builds a read-only, time-sorted view from your APT history, recent
  reboots, and systemd journal errors, and highlights cases where an
  error appeared shortly after a package change (presented as a
  possible connection, not a proven cause).

- **Learn from this repair** - after a fix completes, or from the
  Repair Preview itself, Grix can open the relevant Linux Academy lesson
  so you understand *why* the fix worked, not just that it did.

- **Griffin Linux Suite integration** - if other Griffin Suite tools
  (Kernel Autotune, Fan Hub, Process Sentry, etc.) are installed and
  write a status file, Grix surfaces their findings using the exact same
  explain/preview/confirm/log pipeline as its own checks. Entirely
  optional - Grix is fully useful standalone. See
  `grix/modules/griffin.py` for the status file format.

- **Local Insights (opt-in)** - off by default. If enabled, Grix keeps a
  small local record of which checks come back with issues most often
  and which fixes get applied, to help prioritize what Grix surfaces and
  which lessons might help. This data never leaves your computer, is
  never transmitted anywhere, contains no ads/telemetry, and only
  records check/fix identifiers - never file paths, package names, or
  error text. View or clear it any time from Settings.

- **System Tray Icon** - Grix lives in your system tray, with the icon
  reflecting overall health (green/yellow/red/sleeping/studying) even
  when the main window is closed. Right-click for **Show Grix**,
  **Quick Scan** (opens System Sentinel and starts a scan immediately),
  and **Quit Grix**. Closing the main window minimizes Grix to the tray
  rather than exiting; use "Quit Grix" from the tray menu to fully close
  the app.

- **Ignoring non-urgent checks** - any check that isn't currently
  urgent (not red, and not flagged as critical by the check itself) can
  be ignored for a week or ignored indefinitely via the "Ignore" button
  on its card. Ignored checks move into a collapsed "currently ignored"
  summary instead of disappearing entirely, and Settings has a full
  "Ignored Checks" list where anything can be brought back early.
  Critical situations always break through an ignore automatically -
  for example, Disk Space reappears the moment usage reaches 95%, no
  matter how it was dismissed.

## Requirements

- Python 3.10+
- PyQt6
- A Debian/Ubuntu-based Linux system (some checks degrade gracefully on
  other distros, reporting "not checked" rather than failing)

## Running from source

```bash
cd grix_app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 -m grix.main
```

## Installing

```bash
cd grix_app
pip install --user .
grix
```

To add a desktop launcher, copy `grix.desktop` to
`~/.local/share/applications/` and update the `Icon=` line to point at
`grix/assets/grix_icon.png` (or install it to your icon theme).

```bash
cp grix.desktop ~/.local/share/applications/
```

### Optional: PolicyKit integration

Grix runs privileged commands through `pkexec` automatically with no
setup required - this step is only for the narrower, helper-scoped
authorization described above.

```bash
sudo bash policykit/install.sh
```

To remove it later (Grix falls back to authorizing `pkexec` directly):

```bash
sudo bash policykit/install.sh --uninstall
```

## Updating

If you cloned Grix from git, `update.sh` pulls the latest version and
reinstalls it. It never touches your data in
`~/.local/share/grix/` (scan history, lesson progress, settings).

```bash
bash update.sh            # check for and install updates
bash update.sh --check    # only check if an update is available
bash update.sh --force    # reinstall even if already up to date
```

If you're using a virtual environment at `grix_app/.venv`, the script
uses it automatically; otherwise it installs to your user
site-packages.

## Building an AppImage

`build_appimage.sh` packages Grix into a single portable `.AppImage`
file that runs on most Linux distributions without installation.

Requires [appimagetool](https://github.com/AppImage/appimagetool/releases)
to be in your `PATH` or in the project directory:

```bash
# Download appimagetool once:
wget https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage
chmod +x appimagetool-x86_64.AppImage

# Build:
bash build_appimage.sh
# Output: dist/Grix-x86_64.AppImage

# Run it:
chmod +x dist/Grix-x86_64.AppImage
./dist/Grix-x86_64.AppImage
```

Use `--output <name>` to change the output filename, or `--arch <arch>`
for a different target architecture.

## Project Layout

```
grix_app/
├── grix/
│   ├── main.py                  # entry point: theme, tray icon, app wiring
│   ├── assets/                  # mascot artwork (all 8 mood states)
│   ├── modules/
│   │   ├── diagnostics.py       # all checks + fixes (System Sentinel backend)
│   │   ├── error_explainer.py   # "Explain This Error" knowledge base
│   │   ├── timeline.py          # "System Timeline" (apt history + journal)
│   │   ├── griffin.py           # Griffin Suite integration adapter
│   │   ├── analytics.py         # opt-in local-only Local Insights
│   │   ├── history.py           # repair history log
│   │   ├── snooze.py            # "Ignore for a week"/"Ignore forever" persistence
│   │   ├── lessons.py           # Linux Academy lesson content
│   │   ├── progress.py          # lesson completion tracking
│   │   └── sandbox.py           # simulated filesystem for practice
│   └── ui/
│       ├── theme.py             # Steam-inspired dark palette + global stylesheet
│       ├── main_window.py       # sidebar nav + window + lesson navigation
│       ├── dashboard.py         # home screen
│       ├── sentinel.py          # System Sentinel panel (+ Why/Explain/Timeline tabs, ignore controls)
│       ├── explain_error.py     # "Explain This Error" panel
│       ├── timeline_panel.py    # "System Timeline" panel
│       ├── settings_panel.py    # Local Insights + Ignored Checks + Griffin status
│       ├── academy.py           # Linux Academy panel
│       ├── sandbox_widget.py    # embedded practice terminal
│       ├── mascot.py            # Grix mood widget
│       ├── fix_dialog.py        # Repair Preview / fix confirmation dialog
│       ├── result_dialog.py     # fix result dialog + "Learn from this repair"
│       ├── workers.py           # background threads for scans/fixes
│       └── workers_timeline.py  # background thread for timeline building
├── policykit/
│   ├── grix-helper               # allowlisted privileged-action wrapper script
│   ├── com.griffinlinux.grix.policy   # PolicyKit policy for grix-helper
│   └── install.sh                # installs/uninstalls the above (needs sudo)
├── requirements.txt
├── setup.py
├── update.sh                    # pulls latest version + reinstalls
├── build_appimage.sh            # builds a portable .AppImage
└── grix.desktop
```

## Extending Grix

### Adding a new diagnostic check

Add a function to `grix/modules/diagnostics.py` that returns a
`CheckResult`, and register it in `ALL_CHECKS`. A `CheckResult` can
include:

- `why` - an optional plain-language "Why did this happen?" explanation
  shown in a collapsible section.
- `force_override` - set this to `True` only when the check's current
  result represents a genuine emergency that should break through an
  active "ignore" (see `check_disk_space()`'s 95%-full threshold for an
  example). Leave it `False` for anything snoozable.
- zero or more `Fix` objects, each with:
  - `severity` (`SeverityLevel.SAFE` / `APPROVAL` / `ADVANCED`) -
    controls confirmation requirements
  - `risk` (`RiskLevel.LOW` / `MEDIUM` / `HIGH`) - shown as a badge in
    the Repair Preview
  - `reason` - "why Grix wants to do this"
  - `expected_changes` - a bullet list shown in the Repair Preview
  - `rollback_hint`, `related_lesson` (for "Learn about this")
  - for multi-item fixes (e.g. removing old kernels), `options` (a list
    of `FixOption`, where `protected=True` items can't be selected) and
    `command_template` with a `{selected}` placeholder

**Avoid unconditional "Safe" fixes.** A `Fix` appended to the list
regardless of whether there's an actual problem will resurface on every
single scan even after a user resolves it some other way - this was a
real bug in earlier versions (`apt_update`/`apt_clean` were always
suggested). Always gate a `Fix` behind a real condition (a size
threshold, a non-empty list of affected items, an actual stale/broken
state) so a clean system produces zero suggestions for that fix.

**Don't trust an unprivileged command's exit code alone.** Several
built-in checks run tools like `apt-get check` without root, since
checks are meant to be read-only. Some such tools return a non-zero
exit purely because of a permission or lock-file error - not because
anything is actually broken - which caused another real bug (broken
dependencies were "detected" and re-suggested forever, even right
after a user confirmed nothing needed fixing). When a tool's exit code
can be ambiguous like this, corroborate with a second, more reliable
signal (`check_package_manager()` uses `dpkg --audit`, which only
reads dpkg's own status database and needs no locks or root) and/or
inspect the actual output text for language that describes a real
problem before flagging one.

**A fix's command list must cover everything it claims to fix.** If a
`Fix`'s title/summary says "Remove 15 old Snap revisions" but
`commands` only actually contains 10 `snap remove` calls (e.g. from an
arbitrary `[:10]` slice meant to keep the list "reasonable"), applying
the fix leaves 5 behind - and since the underlying condition never
fully clears, the very next scan re-detects those 5 and shows the
exact same finding again. From the user's perspective, the fix
silently "didn't work." If a fix's scope must be capped for some
reason, the displayed count and the actual command list need to agree,
and the title needs to say so explicitly (e.g. "Remove the first 10 of
15 old Snap revisions") - never let the two silently diverge.

**Parse a command's actual output structure, not just keyword
presence.** `check_flatpak_snap_bloat()`'s Flatpak detection had a
real bug here: `flatpak uninstall --unused --dry-run` lists *pinned*
runtimes (which will never actually be removed) in the same output as
genuinely removable ones, and on a system with any pinned runtimes
(common - Steam's Proton-GE, MangoHud, etc. are often pinned), the old
parsing counted those pinned lines as "removable," so the fix
appeared to be available forever, even immediately after running it
successfully. The fix was to match the command's actual row format
(`^\s*\d+\.\s` - flatpak's removal table is numbered; the pinned list
above it isn't) instead of a loose "any non-empty, non-header line"
heuristic, and to treat the tool's own explicit "nothing to do"
message (`"Nothing unused to uninstall"`) as authoritative regardless
of exit code. When parsing any command's output to decide whether a
problem still exists, prefer matching the structural pattern of an
actual finding over excluding known-bad lines by keyword - the latter
is a denylist that silently passes through anything you didn't think
of (like a pinned-items header).

**A check that's currently healthy (status == GREEN) must have zero
fixes.** `check_journal()` had a subtler version of the unconditional-
fix bug above: it built its fix list unconditionally, then only
*partially* gated it (`fixes if status != GREEN else [fixes[0]]`) -
still attaching one fix even when the journal was small and healthy.
A GREEN result with a non-empty `fixes` list will always look like it
"still needs attention" to a user re-checking after applying that very
fix. The fix list should be `[]` outright whenever `status ==
Status.GREEN`, full stop - no exceptions for "well, it's a Safe fix
anyway."

### Letting users ignore a check

Any check with `status != RED` and `force_override=False` automatically
gets an "Ignore" control in System Sentinel (handled generically in
`sentinel.py`'s `CheckCard` - no per-check code needed). Snoozes are
stored by `grix/modules/snooze.py` keyed on `CheckResult.id` and persist
across restarts; "week" snoozes expire automatically, "forever" ones
don't unless unsnoozed from Settings. If a check has a meaningful
"this is now an emergency" threshold, set `force_override=True` on the
`CheckResult` once that threshold is crossed so it's never permanently
hidden.

### Adding a new error pattern

Add an entry to `grix/modules/error_explainer.py` via `_register(regex,
ErrorExplanation(...))`. Patterns are matched in order, case-insensitive,
against pasted text. Link to a `related_check_id` (a `CheckResult.id`)
and/or `related_lesson` to connect it back into Sentinel/Academy.

### Adding a new lesson

Add a `Lesson` to `beginner_lessons` or `intermediate_lessons` in
`grix/modules/lessons.py`. Lessons are built from ordered "blocks":

- `("text", "...")` - markdown-ish prose (supports `**bold**`,
  `` `code` ``, bullet lists, and fenced code blocks)
- `("command", "command here", "explanation")` - a highlighted example
  command with an explanation
- `("quiz", "question?", [options], correct_index, "explanation")` -
  multiple choice with feedback
- `("practice", "prompt", "expected command" or [list of commands],
  "hint")` - a hands-on exercise checked against the sandbox terminal

### Extending the sandbox terminal

`grix/modules/sandbox.py` implements a small simulated filesystem and a
dispatch table of `_cmd_*` methods. Add a new method following the same
pattern to support additional commands in lessons.

### Customizing the theme

All colors live in the `COLORS` dict at the top of `grix/ui/theme.py`.
Change a value there and it propagates everywhere - the global
stylesheet, status badges, code blocks, and helper functions
(`code_box_style()`, `status_badge_style()`, etc.) all reference this
single source of truth. Avoid hardcoding hex colors directly in panel
files; import from `theme.py` instead so contrast stays consistent.

### Adding a lesson or track to Linux Academy

Each `Lesson` in `grix/modules/lessons.py` has an `id`, `title`,
`summary`, and a list of `blocks`. A block is a tuple starting with its
kind:

- `("text", markdown_string)` - supports `**bold**`, `` `inline code` ``,
  and fenced ` ``` ` code blocks
- `("command", "the command", "explanation")` - a styled, non-executed
  reference (use for things the sandbox can't meaningfully simulate,
  like `flatpak list`)
- `("quiz", question, [options], correct_index, explanation)` - keep
  individual options reasonably short where possible; long options
  still wrap correctly (`QuizBlock` pairs each radio button with a
  separate word-wrapping label specifically to support this), but short
  options scan faster
- `("practice", prompt, expected_command_or_list, hint)` - graded by
  exact (whitespace-normalized) match against what the user types in
  the embedded sandbox terminal; `expected_command_or_list` can be a
  single string or a list of commands for a multi-step practice

A new track is a `Track(id=..., title=..., description=..., lessons=[...])`
appended to `TRACKS` - `progress.py`, `academy.py`, and lesson
navigation are all written generically against `TRACKS`, so no other
code needs to change. If a lesson's practice blocks need a command the
sandbox doesn't support yet, add a `_cmd_<name>` method to
`SandboxTerminal` in `grix/modules/sandbox.py` (hyphenated commands
like `ssh-keygen` map to `_cmd_ssh_keygen`, with hyphens replaced by
underscores).

### The plugin system

Grix can be extended by anyone - new System Sentinel checks, new Linux
Academy lesson tracks, or new top-level UI panels - without touching
Grix's own source. This replaced an earlier, more limited integration
that only recognized a hardcoded list of Griffin Suite tool names;
that hardcoded list is gone, and the Griffin Suite integration itself
is now an ordinary plugin (`grix/plugins/griffin_suite/`), useful as a
real, working example.

**Where plugins live:** `~/.local/share/grix/plugins/<plugin-id>/` -
always a real, writable host-filesystem path, including when Grix is
running from a read-only AppImage. Grix also loads whatever ships in
its own `grix/plugins/` directory (bundled plugins, like Griffin Suite
integration) from the same loader, with the same API - there's no
separate "built-in plugin" code path.

**Plugin layout:**

```
my_plugin/
├── plugin.json   # manifest (required)
└── plugin.py     # entry point (required)
```

`plugin.json`:
```json
{
  "id": "my_plugin",
  "name": "My Plugin",
  "version": "1.0.0",
  "author": "Your Name",
  "description": "What this plugin adds.",
  "grix_api_version": 1
}
```
`id` must exactly match the plugin's folder name - this keeps plugin
identity unambiguous.

`plugin.py`:
```python
from grix.modules.diagnostics import CheckResult, Status

def my_check():
    return CheckResult(
        id="my_plugin_check", title="My Check",
        status=Status.GREEN, summary="Everything's fine.",
    )

def register(api):
    api.register_check(my_check)
```

`register(api)` is called once at startup (or when the user clicks
"Reload Plugins" in Settings). It's the only hook Grix looks for -
nothing else about a plugin file is treated as magic.

**The plugin API** (everything `register(api)` can call):

- `api.register_check(fn)` - `fn` takes no arguments and returns one
  `CheckResult`, exactly like a built-in check in `diagnostics.py`.
  Called fresh on every System Sentinel scan.
- `api.register_dynamic_checks(fn)` - for a source that can produce a
  *variable* number of results per scan (zero, one, or many) depending
  on its current state - `fn` takes no arguments and returns a
  `list[CheckResult]`. This is what the Griffin Suite plugin uses,
  since the number of findings depends on what other tools currently
  have to report. Also re-evaluated fresh every scan - nothing about a
  plugin's checks is cached across scans, only the plugin's *code* is
  loaded once.
- `api.register_lesson_track(track)` - `track` is a
  `grix.modules.lessons.Track` (same dataclass Grix's own Beginner/
  Intermediate/Advanced tracks use). Appended after Grix's built-in
  tracks in the Academy sidebar.
- `api.register_panel(key, label, widget_factory)` - adds a new
  top-level sidebar item. `widget_factory` is a zero-argument callable
  returning a `QWidget` (usually just the widget class itself).

A plugin check should follow the same gating discipline as built-in
checks - see "Avoid unconditional Safe fixes" above. A plugin whose
manifest is invalid, whose `plugin.py` raises, or whose API version
doesn't match `CURRENT_API_VERSION` in `grix/modules/plugins.py` is
skipped with a recorded error (visible in Settings) rather than
crashing anything else - a broken plugin can't take down Grix or other
plugins. There is no sandboxing, though: a plugin runs with the same
privileges as Grix itself, so only install plugins you trust, the same
way you'd think about installing any other software.

**Dependencies:** a plugin using only the Python standard library
works immediately. A plugin needing a third-party package (something
not already bundled with Grix - PyQt6 and the stdlib are the only
guarantees) needs that package installed into:

```bash
pip install --target ~/.local/share/grix/plugins/lib <package>
```

Grix automatically adds that `lib/` directory to `sys.path` if it
exists, so anything installed there becomes importable with no other
setup. Grix does not install plugin dependencies itself - doing that
silently would mean running arbitrary network/install operations
without the kind of explicit, reviewable confirmation step the rest of
Grix's safety model (Repair Preview) is built around.

**Migrating from the old Griffin-only integration:** if you previously
had a tool write to `~/.local/share/griffin/<tool>/status.json`
expecting Grix's hardcoded `KNOWN_COMPONENTS` list to pick it up,
nothing changes on your end - the same status-file format is still
read, and there's no longer a fixed list of recognized tool names at
all. Any subdirectory under `~/.local/share/griffin/` with a
`status.json` is picked up automatically; see
`grix/plugins/griffin_suite/plugin.py` for the exact format.
