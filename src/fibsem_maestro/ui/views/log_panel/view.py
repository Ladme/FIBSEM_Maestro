# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The bottom panel streaming the per-slice log files of the selected sources."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.ui.views.log_panel.parsing import LEVEL_COLORS, LEVELS, level_value
from fibsem_maestro.ui.views.log_panel.reader import WORKFLOW_SOURCE, LogReader

if TYPE_CHECKING:
    from fibsem_maestro.ui.app.run_controller import RunController
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.views.log_panel.parsing import LogLine

CURRENT = "current"
"""Slice choice following the slice the workflow as a whole is in."""

ALL = "all"
"""Source choice merging every source."""


def _bold_label(text: str) -> QLabel:
    label = QLabel(text)
    font = label.font()
    font.setBold(True)
    label.setFont(font)
    return label


class LogPanel(QWidget):
    """
    Bottom panel that streams per-slice log files from selected actions.

    Controls:
        - Slice selector: the current slice or any slice found on disk.
        - Source selector: all sources, one action, or the workflow.
        - Level selector: minimum log level to display.

    Log lines from all selected sources are merged and sorted by timestamp.
    A timer polls the selected slice's files every second for new lines,
    whichever slice is selected.

    Args:
        session: The workflow session (action names, directory, slice).
        run: The run controller (finished slices).
        parent: Parent widget.
    """

    _POLL_INTERVAL_MS = 1000

    def __init__(
        self,
        session: WorkflowSession,
        run: RunController,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._session = session
        self._reader = LogReader(session.workflow_dir)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        controls = QHBoxLayout()
        controls.setSpacing(8)

        controls.addWidget(_bold_label("Slice"))
        self._slice_combo = QComboBox()
        self._slice_combo.setMinimumWidth(100)
        self._slice_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._slice_combo)

        controls.addWidget(_bold_label("Source"))
        self._source_combo = QComboBox()
        self._source_combo.setMinimumWidth(200)
        self._source_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._source_combo)

        controls.addWidget(_bold_label("Level"))
        self._level_combo = QComboBox()
        for level in LEVELS:
            self._level_combo.addItem(level)
        self._level_combo.setFixedWidth(150)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._level_combo)

        controls.addStretch()
        layout.addLayout(controls)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setStyleSheet(
            "QPlainTextEdit { background: #1a1a1a; color: #cccccc; font-family: monospace; font-size: 11px; }"
        )
        layout.addWidget(self._log_view)

        self._rebuild_sources()
        self._rebuild_slices()

        self._timer = QTimer(self)
        self._timer.setInterval(self._POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._on_poll)
        self._timer.start()

        session.structure_changed.connect(self._on_sources_changed)
        session.action_renamed.connect(self._on_sources_changed)
        session.workflow_replaced.connect(self._on_workflow_replaced)
        session.workflow_reset.connect(self._on_slices_changed)
        run.slice_finished.connect(self._on_slices_changed)

    @property
    def log_view(self) -> QPlainTextEdit:
        """The text view showing the lines."""
        return self._log_view

    @property
    def slice_combo(self) -> QComboBox:
        """The slice selector."""
        return self._slice_combo

    @property
    def source_combo(self) -> QComboBox:
        """The source selector."""
        return self._source_combo

    def _on_slices_changed(self, *_: object) -> None:
        self._rebuild_slices()
        # if user is watching "current", follow automatically
        if self._slice_combo.currentText() == CURRENT:
            self._refresh()

    def _on_sources_changed(self, *_: object) -> None:
        self._rebuild_sources()
        self._refresh()

    def _on_workflow_replaced(self) -> None:
        self._reader.set_workflow_dir(self._session.workflow_dir)
        self._rebuild_sources()
        self._rebuild_slices()
        self._refresh()

    def _source_names(self) -> list[str]:
        """All source names: action names + 'workflow'."""
        names = [action.name for action in self._session.actions]
        names.append(WORKFLOW_SOURCE)
        return names

    def _rebuild_sources(self) -> None:
        """Rebuild the source combo."""
        current = self._source_combo.currentText()
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        self._source_combo.addItem(ALL)
        for name in self._source_names():
            self._source_combo.addItem(name)
        restore_idx = self._source_combo.findText(current)
        self._source_combo.setCurrentIndex(max(0, restore_idx))
        self._source_combo.blockSignals(False)

    def _selected_sources(self) -> list[str]:
        if self._source_combo.currentText() == ALL:
            return self._source_names()
        return [self._source_combo.currentText()]

    def _rebuild_slices(self) -> None:
        """Rebuild the slice combo to include all slices found on disk."""
        current = self._slice_combo.currentText()
        self._slice_combo.blockSignals(True)
        self._slice_combo.clear()
        self._slice_combo.addItem(CURRENT)

        for idx in self._reader.slices(self._source_names()):
            self._slice_combo.addItem(str(idx))

        # restore selection
        restore_idx = self._slice_combo.findText(current)
        self._slice_combo.setCurrentIndex(max(0, restore_idx))
        self._slice_combo.blockSignals(False)

    def _selected_slice_index(self) -> int:
        """The slice shown: the workflow's for "current", else the chosen one."""
        text = self._slice_combo.currentText()
        if text == CURRENT:
            return self._session.slice
        try:
            return int(text)
        except ValueError:
            return self._session.slice

    def _selected_level_value(self) -> int:
        return level_value(self._level_combo.currentText())

    def _refresh(self, *_: object) -> None:
        """Reload all selected log files from scratch and redisplay."""
        self._log_view.clear()
        lines = self._reader.read(
            self._selected_slice_index(),
            self._selected_sources(),
            self._selected_level_value(),
        )
        for line in lines:
            self._append_line(line)

    def _on_poll(self) -> None:
        """Offer newly created slices, and append the selected slice's new lines."""
        if self._has_new_slice():
            self._rebuild_slices()

        # every slice is polled, not only "current": a slice chosen explicitly
        # (e.g. the next one while paused) may still be written to (D19)
        new_lines = self._reader.poll(
            self._selected_slice_index(),
            self._selected_sources(),
            self._selected_level_value(),
        )
        for line in new_lines:
            self._append_line(line)

    def _has_new_slice(self) -> bool:
        """
        Check whether a slice directory beyond the listed ones has appeared.

        Actions advance their own slice counters, and a slice directory is
        created by the first file written into it, e.g. a log line written
        while the workflow is paused. Only the slice after the highest listed
        one is looked for, so the check costs one lookup per source.
        """
        listed = [
            int(text)
            for i in range(self._slice_combo.count())
            if (text := self._slice_combo.itemText(i)).isdigit()
        ]
        return self._reader.has_slice(self._source_names(), max(listed, default=-1) + 1)

    def _append_line(self, line: LogLine) -> None:
        color = LEVEL_COLORS.get(line.level, "#cccccc")
        html = (
            f'<span style="color:{color}">'
            f"{line.raw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}"
            f"</span>"
        )
        self._log_view.appendHtml(html)
