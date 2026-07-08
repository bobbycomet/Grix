"""
Grix System Sentinel - Timeline Background Worker
=====================================================

Reading apt history logs and journal output can take a moment, so the
timeline is built on a background thread.
"""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal

from ..modules import timeline as timeline_module


class TimelineWorker(QThread):
    finished_timeline = pyqtSignal(list, list)  # events, correlations

    def __init__(self, max_age_days: int, parent=None):
        super().__init__(parent)
        self.max_age_days = max_age_days

    def run(self) -> None:
        try:
            events = timeline_module.build_timeline(self.max_age_days)
            correlations = timeline_module.correlate_errors_with_packages(events)
        except Exception:  # pragma: no cover - never crash the UI
            events, correlations = [], []
        self.finished_timeline.emit(events, correlations)
