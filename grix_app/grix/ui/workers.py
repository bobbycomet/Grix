"""
Grix System Sentinel - Background Workers
=============================================

Diagnostic checks and fixes can take a few seconds (network pings,
apt operations, etc.), so they run on a QThread to keep the UI
responsive. Grix's mascot animates to "study" while a scan runs and
"fix" while a repair is being applied.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..modules import diagnostics, plugins
from ..modules.diagnostics import CheckResult, Fix


# Convenience re-exports so UI code can `from .workers import
# get_plugin_registry` etc. without needing to know the registry
# itself is cached inside grix.modules.plugins. The actual cache lives
# there (not here) so non-UI modules can use it too without importing
# anything from the ui/ package.
get_plugin_registry = plugins.get_plugin_registry
get_plugin_infos = plugins.get_plugin_infos
reload_plugins = plugins.reload_plugins


class ScanWorker(QThread):
    """Runs all diagnostic checks (built-in + any loaded plugin
    checks) on a background thread."""

    check_started = pyqtSignal(str)          # check title
    check_finished = pyqtSignal(object)       # CheckResult
    all_finished = pyqtSignal(list)           # list[CheckResult]

    def run(self) -> None:
        results: list[CheckResult] = []
        for check_fn in diagnostics.ALL_CHECKS:
            # Best-effort friendly name before running
            self.check_started.emit(check_fn.__name__)
            try:
                result = check_fn()
            except Exception as exc:  # pragma: no cover - defensive
                result = CheckResult(
                    id=check_fn.__name__,
                    title=check_fn.__name__.replace("check_", "").replace("_", " ").title(),
                    status=diagnostics.Status.UNKNOWN,
                    summary=f"This check could not run: {exc}",
                )
            results.append(result)
            self.check_finished.emit(result)

        # Run any checks registered by plugins (this is also how the
        # built-in Griffin Suite integration works now - see
        # grix/plugins/griffin_suite/ - there's no special-casing of
        # any particular plugin here, Griffin's included or not).
        try:
            registry = get_plugin_registry()
            for check_fn in registry.checks:
                try:
                    result = check_fn()
                except Exception as exc:
                    result = CheckResult(
                        id=getattr(check_fn, "__name__", "plugin_check"),
                        title=getattr(check_fn, "__name__", "Plugin Check").replace("_", " ").title(),
                        status=diagnostics.Status.UNKNOWN,
                        summary=f"This plugin check could not run: {exc}",
                    )
                results.append(result)
                self.check_finished.emit(result)

            # Dynamic providers can each return any number of results
            # (e.g. one per finding from another tool's status file) -
            # re-evaluated fresh on every scan, never cached.
            for provider_fn in registry.dynamic_check_providers:
                try:
                    dynamic_results = provider_fn() or []
                except Exception as exc:
                    dynamic_results = [CheckResult(
                        id=getattr(provider_fn, "__name__", "plugin_dynamic_check"),
                        title="Plugin Check",
                        status=diagnostics.Status.UNKNOWN,
                        summary=f"This plugin check could not run: {exc}",
                    )]
                for result in dynamic_results:
                    results.append(result)
                    self.check_finished.emit(result)
        except Exception:  # pragma: no cover - never let plugin loading break a scan
            pass

        self.all_finished.emit(results)


class FixWorker(QThread):
    """Applies a single Fix on a background thread."""

    finished_fix = pyqtSignal(object, bool, str)  # Fix, success, output

    def __init__(self, fix: Fix, selected_option_ids: list[str] | None = None, parent=None):
        super().__init__(parent)
        self.fix = fix
        self.selected_option_ids = selected_option_ids or []

    def run(self) -> None:
        success, output = diagnostics.apply_fix(self.fix, self.selected_option_ids)
        self.finished_fix.emit(self.fix, success, output)
