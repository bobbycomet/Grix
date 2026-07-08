"""
Grix - Plugin System
========================

Lets developers (or anyone comfortable editing a text file) extend
Grix without modifying its source: new System Sentinel checks, new
Linux Academy tracks/lessons, and new UI panels.

WHY THIS EXISTS
---------------
Earlier versions of Grix had a single hardcoded integration point
(grix/modules/griffin.py) that only recognized a fixed list of Griffin
Suite tool names. That meant nobody outside the Griffin Suite could
extend Grix, and adding a new official tool required editing Grix's
own source. This module replaces that with a real plugin architecture:
ANY developer can add checks, lessons, or UI - Griffin Suite tools
included, but no longer special-cased. See grix/plugins/griffin_suite/
for the Griffin Suite integration re-implemented as an ordinary plugin,
useful as a working example.

WHERE PLUGINS LIVE
-------------------
Plugins are loaded from (in order, later entries can't override
earlier ones - first plugin with a given id wins):

  1. ~/.local/share/grix/plugins/        - user-installed plugins
  2. <app bundle>/grix/plugins/          - plugins shipped with Grix
                                            itself (e.g. griffin_suite)

The user directory is always writable, including when Grix is running
from a read-only AppImage - that's the whole point of using a
host-filesystem path instead of anything inside the app bundle.

PLUGIN LAYOUT
-------------
A plugin is a directory containing:

  my_plugin/
  ├── plugin.json      - manifest (required)
  └── plugin.py         - entry point (required, see below)

plugin.json:
  {
    "id": "my_plugin",            (required, must match the directory name)
    "name": "My Plugin",          (required, shown in Settings)
    "version": "1.0.0",           (required)
    "author": "Your Name",        (optional)
    "description": "What this plugin adds.",   (optional)
    "grix_api_version": 1         (required - see API VERSIONING below)
  }

plugin.py must define a module-level function:

  def register(api: PluginAPI) -> None:
      api.register_check(my_check_function)
      api.register_dynamic_checks(my_variable_count_provider)
      api.register_lesson_track(my_track)
      api.register_panel("my_panel", "My Panel", MyPanelWidgetClass)

register() is called once at startup. Anything not registered there
simply doesn't happen - there's no other hook or magic naming
convention Grix looks for. register_check is for a check that always
produces exactly one CheckResult (the common case, and what every
built-in Grix check does); register_dynamic_checks is for a source
that can produce zero, one, or many results depending on its current
state (see grix/plugins/griffin_suite/plugin.py for a real example -
it surfaces a variable number of findings from other tools).

API VERSIONING
---------------
"grix_api_version" lets Grix refuse to load a plugin built against an
incompatible future API instead of crashing in some confusing way.
The current version is CURRENT_API_VERSION below; bump it (and document
what changed) whenever PluginAPI's method signatures change in a
backwards-incompatible way.

DEPENDENCIES
------------
A plugin that only uses Python's standard library works immediately.
A plugin needing third-party packages (requests, numpy, a non-bundled
Qt widget, etc.) needs one of:

  1. The package happens to already be bundled in Grix (PyQt6 and the
     standard library are always available; nothing else is guaranteed).
  2. The plugin author tells users to install the dependency into the
     plugin loader's extra path:
       pip install --target ~/.local/share/grix/plugins/lib <package>
     This module adds that lib/ directory to sys.path automatically if
     it exists (see _EXTRA_LIB_DIR below), so packages installed there
     become importable without any other setup.

This is a real limitation of running inside an AppImage - there is no
way around a plugin needing a dependency that isn't present somewhere
on disk. Grix does not auto-install plugin dependencies itself: doing
that silently would mean running arbitrary network/pip operations
without the kind of explicit, reviewable confirmation step Grix's
Repair Preview model is built around.

SAFETY
------
Plugins run with the same privileges as Grix itself - there is no
sandboxing. Only install plugins from sources you trust, the same way
you'd think about installing any other software. A broken or
exception-raising plugin is caught and reported in Settings without
crashing the rest of the app, but a *malicious* plugin is not
defended against; Grix assumes you vetted what you put in the plugins
folder, the same way Python assumes that of `pip install`.
"""

from __future__ import annotations

import importlib
import importlib.util
import json
import os
import sys
import traceback
from dataclasses import dataclass, field
from typing import Callable

CURRENT_API_VERSION = 1

USER_PLUGIN_DIR = os.path.expanduser("~/.local/share/grix/plugins")
_EXTRA_LIB_DIR = os.path.join(USER_PLUGIN_DIR, "lib")

# Bundled (built-in, shipped-with-Grix) plugins directory, e.g. for the
# Griffin Suite example plugin. Resolved relative to this file:
# grix/modules/plugins.py -> grix/ -> grix/plugins/
_BUNDLED_PLUGIN_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "plugins")
)


@dataclass
class PluginPanelSpec:
    key: str
    label: str
    factory: Callable[[], object]  # zero-arg callable returning a QWidget


@dataclass
class PluginInfo:
    """Metadata + load result for one discovered plugin."""
    id: str
    name: str
    version: str
    path: str
    author: str = ""
    description: str = ""
    loaded: bool = False
    error: str | None = None
    source: str = "user"  # "user" or "bundled"


@dataclass
class _Registry:
    checks: list[Callable[[], object]] = field(default_factory=list)
    dynamic_check_providers: list[Callable[[], list]] = field(default_factory=list)
    lesson_tracks: list[object] = field(default_factory=list)
    panels: list[PluginPanelSpec] = field(default_factory=list)


class PluginAPI:
    """Passed to each plugin's register() function. This is the ONLY
    surface plugins are expected to interact with - intentionally
    narrow, so Grix can evolve its internals without breaking plugins
    that stick to this API."""

    def __init__(self, registry: _Registry, plugin_id: str):
        self._registry = registry
        self._plugin_id = plugin_id

    def register_check(self, check_fn: Callable[[], object]) -> None:
        """Register a new System Sentinel check. check_fn must take no
        arguments and return a grix.modules.diagnostics.CheckResult,
        exactly like Grix's own built-in checks. It will be called
        once per scan, on the scan background thread - the same
        try/except safety net that protects built-in checks also
        wraps plugin checks, so a buggy check can't crash a scan."""
        self._registry.checks.append(check_fn)

    def register_dynamic_checks(self, provider_fn: Callable[[], list]) -> None:
        """Register a source that can produce a VARIABLE number of
        CheckResults per scan (zero, one, or many) - for example, a
        plugin that surfaces findings from another tool's status file,
        where the number of findings depends on that tool's current
        state. provider_fn must take no arguments and return a list of
        grix.modules.diagnostics.CheckResult (an empty list is fine).
        Unlike register_check, provider_fn is called fresh on every
        scan - nothing is cached at registration time."""
        self._registry.dynamic_check_providers.append(provider_fn)

    def register_lesson_track(self, track: object) -> None:
        """Register a new Linux Academy track. `track` must be a
        grix.modules.lessons.Track instance. It's appended after
        Grix's built-in tracks in the Academy sidebar."""
        self._registry.lesson_tracks.append(track)

    def register_panel(self, key: str, label: str, widget_factory: Callable[[], object]) -> None:
        """Register a new top-level UI panel, shown as an additional
        item in Grix's sidebar navigation. `widget_factory` is a
        zero-argument callable returning a QWidget (typically just the
        widget class itself, e.g. MyPanel) - it's called once, lazily,
        the first time the panel needs to be constructed."""
        self._registry.panels.append(PluginPanelSpec(key=key, label=label, factory=widget_factory))


def _ensure_user_plugin_dir() -> None:
    os.makedirs(USER_PLUGIN_DIR, exist_ok=True)


def _candidate_plugin_dirs() -> list[tuple[str, str]]:
    """Return [(plugin_root_dir, source)] in load-priority order."""
    dirs = []
    if os.path.isdir(USER_PLUGIN_DIR):
        dirs.append((USER_PLUGIN_DIR, "user"))
    if os.path.isdir(_BUNDLED_PLUGIN_DIR):
        dirs.append((_BUNDLED_PLUGIN_DIR, "bundled"))
    return dirs


def _read_manifest(plugin_path: str) -> dict | None:
    manifest_path = os.path.join(plugin_path, "plugin.json")
    if not os.path.isfile(manifest_path):
        return None
    try:
        with open(manifest_path, "r") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return None


def discover_plugins() -> list[PluginInfo]:
    """Find every plugin directory with a valid manifest, without
    importing any code yet. Used by Settings to list plugins (loaded
    or not) and by load_all_plugins() below."""
    _ensure_user_plugin_dir()
    found: dict[str, PluginInfo] = {}

    for root_dir, source in _candidate_plugin_dirs():
        try:
            entries = sorted(os.listdir(root_dir))
        except OSError:
            continue
        for entry in entries:
            plugin_path = os.path.join(root_dir, entry)
            if not os.path.isdir(plugin_path):
                continue
            manifest = _read_manifest(plugin_path)
            if manifest is None:
                continue

            plugin_id = str(manifest.get("id", "")).strip()
            if not plugin_id or plugin_id != entry:
                # The manifest's id must match its folder name - this
                # keeps plugin identity unambiguous and prevents two
                # different folders from silently claiming the same id.
                found.setdefault(entry, PluginInfo(
                    id=entry, name=entry, version="?", path=plugin_path,
                    source=source, error="plugin.json's \"id\" must match the folder name",
                ))
                continue

            if plugin_id in found:
                continue  # earlier (higher-priority) source already claimed this id

            found[plugin_id] = PluginInfo(
                id=plugin_id,
                name=str(manifest.get("name", plugin_id)),
                version=str(manifest.get("version", "?")),
                author=str(manifest.get("author", "")),
                description=str(manifest.get("description", "")),
                path=plugin_path,
                source=source,
            )

    return list(found.values())


def load_all_plugins() -> tuple[_Registry, list[PluginInfo]]:
    """Discover, validate, and import every plugin, calling its
    register() function. Returns (registry, plugin_infos) - the
    registry holds everything plugins registered (checks, lesson
    tracks, panels); plugin_infos reports load success/failure for
    every discovered plugin, for display in Settings.

    A plugin that fails to import, has a missing/invalid manifest, or
    raises inside register() is recorded with its error and skipped -
    it never prevents other plugins (or Grix itself) from loading.
    """
    _ensure_user_plugin_dir()
    if os.path.isdir(_EXTRA_LIB_DIR) and _EXTRA_LIB_DIR not in sys.path:
        sys.path.insert(0, _EXTRA_LIB_DIR)
    if USER_PLUGIN_DIR not in sys.path:
        sys.path.insert(0, USER_PLUGIN_DIR)

    registry = _Registry()
    infos = discover_plugins()

    for info in infos:
        if info.error:
            continue  # already invalid (e.g. id/folder mismatch) - nothing to load

        manifest = _read_manifest(info.path)
        api_version = manifest.get("grix_api_version") if manifest else None
        if api_version != CURRENT_API_VERSION:
            info.error = (
                f"built for plugin API version {api_version!r}, but Grix "
                f"is running API version {CURRENT_API_VERSION} - skipped "
                f"for safety. Check if an updated version of this plugin "
                f"is available."
            )
            continue

        entry_path = os.path.join(info.path, "plugin.py")
        if not os.path.isfile(entry_path):
            info.error = "missing plugin.py entry point"
            continue

        try:
            spec = importlib.util.spec_from_file_location(
                f"grix_plugin_{info.id}", entry_path
            )
            if spec is None or spec.loader is None:
                info.error = "could not load plugin.py"
                continue
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)

            register_fn = getattr(module, "register", None)
            if register_fn is None:
                info.error = "plugin.py has no register(api) function"
                continue

            api = PluginAPI(registry, info.id)
            register_fn(api)
            info.loaded = True

        except Exception as exc:  # noqa: BLE001 - intentionally broad: a
            # plugin's code is third-party and must never be able to take
            # down the rest of Grix, regardless of what kind of error it
            # raises.
            info.error = f"{type(exc).__name__}: {exc}"
            # Keep a short traceback available for Settings' "show details"
            # without dumping a huge stack trace into the summary string.
            info.loaded = False
            _LAST_TRACEBACKS[info.id] = traceback.format_exc()

    return registry, infos


_LAST_TRACEBACKS: dict[str, str] = {}


def get_traceback(plugin_id: str) -> str | None:
    return _LAST_TRACEBACKS.get(plugin_id)


# ---------------------------------------------------------------------------
# Cached, app-wide plugin registry
# ---------------------------------------------------------------------------
# Plugins are loaded once per app run (not every time something needs
# them) and cached here. Re-importing every plugin module on every
# call would be wasteful and could misbehave for any plugin whose
# register() isn't safely idempotent (e.g. one that appends to a
# module-level list each time it runs). This lives in plugins.py
# itself (rather than e.g. grix/ui/workers.py) so any layer - the
# diagnostics scan worker, the Academy panel, Settings, MainWindow -
# can all share exactly the same loaded set without modules/ needing
# to import anything from ui/.

_cached_registry: _Registry | None = None
_cached_infos: list[PluginInfo] = []


def get_plugin_registry() -> _Registry:
    """Return the cached plugin registry, loading plugins on first
    call. Call reload_plugins() instead if you need to pick up changes
    made to the plugins folder since startup."""
    global _cached_registry, _cached_infos
    if _cached_registry is None:
        _cached_registry, _cached_infos = load_all_plugins()
    return _cached_registry


def get_plugin_infos() -> list[PluginInfo]:
    """Return PluginInfo for every discovered plugin (loaded or not),
    loading plugins on first call if not already done."""
    get_plugin_registry()
    return _cached_infos


def reload_plugins() -> tuple[_Registry, list[PluginInfo]]:
    """Force a fresh discovery + load pass, e.g. after the user adds
    or removes a plugin and clicks 'Reload Plugins' in Settings."""
    global _cached_registry, _cached_infos
    _cached_registry, _cached_infos = load_all_plugins()
    return _cached_registry, _cached_infos
