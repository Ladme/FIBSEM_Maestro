# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import contextlib
from pathlib import Path

from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.log_panel._common import (
    LEVEL_COLORS,
    LEVELS,
    bold_label,
    level_value,
    parse_line,
)
from fibsem_maestro.gui.log_panel._log_line import LogLine
from fibsem_maestro.gui.workflow_manager import WorkflowManager


class LogPanel(QWidget):
    """
    Bottom panel that streams per-slice log files from selected actions.

    Controls:
        - Slice selector: current slice or any past slice.
        - Action selector: multi-select checkboxes for each action + workflow.
        - Level selector: minimum log level to display.

    Log lines from all selected sources are merged and sorted by timestamp.
    A QTimer polls the files every second to pick up new lines.
    """

    _POLL_INTERVAL_MS = 1000

    def __init__(
        self,
        workflow_manager: WorkflowManager,
        workflow_dir: Path,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._manager = workflow_manager
        self._workflow_dir = workflow_dir

        # file positions for streaming: path -> bytes read so far
        self._file_positions: dict[Path, int] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(4)

        # row with controls
        controls = QHBoxLayout()
        controls.setSpacing(8)

        # slice selector
        controls.addWidget(bold_label("Slice"))
        self._slice_combo = QComboBox()
        self._slice_combo.setMinimumWidth(100)
        self._slice_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._slice_combo)

        # action selector
        controls.addWidget(bold_label("Source"))
        self._source_combo = QComboBox()
        self._source_combo.setMinimumWidth(200)
        self._source_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._source_combo)

        # level selector
        controls.addWidget(bold_label("Level"))
        self._level_combo = QComboBox()
        for level in LEVELS:
            self._level_combo.addItem(level)
        self._level_combo.setFixedWidth(150)
        self._level_combo.setCurrentText("INFO")
        self._level_combo.currentIndexChanged.connect(self._refresh)
        controls.addWidget(self._level_combo)

        controls.addStretch()
        layout.addLayout(controls)

        # log view
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMaximumBlockCount(5000)
        self._log_view.setStyleSheet(
            "QPlainTextEdit { background: #1a1a1a; color: #cccccc; font-family: monospace; font-size: 11px; }"
        )
        layout.addWidget(self._log_view)

        # populate controls
        self._rebuild_sources()
        self._rebuild_slices()

        # poll timer
        self._timer = QTimer(self)
        self._timer.setInterval(self._POLL_INTERVAL_MS)
        self._timer.timeout.connect(self._on_poll)
        self._timer.start()

        self._manager.new_workflow.connect(self._on_new_workflow)

    def on_slice_changed(self, slice_index: int) -> None:
        """Called by WorkflowManager.slice_finished to update slice list."""
        _ = slice_index
        self._rebuild_slices()
        # if user is watching "current", follow automatically
        if self._slice_combo.currentText() == "current":
            self._refresh()

    def on_actions_changed(self) -> None:
        """Called when actions are added/removed."""
        self._rebuild_sources()
        self._refresh()

    def on_action_renamed(self, action: Action) -> None:
        _ = action
        self._rebuild_sources()
        self._refresh()

    def _on_new_workflow(self, workflow_dir: Path) -> None:
        """Update the log panel when a new workflow is opened."""
        self._workflow_dir = workflow_dir
        self._rebuild_sources()
        self._refresh()

    def _source_names(self) -> list[str]:
        """All source names: action names + 'workflow'."""
        names = [action.name for action in self._manager.workflow.actions]
        names.append("workflow")
        return names

    def _rebuild_sources(self) -> None:
        """Rebuild the source combo."""
        current = self._source_combo.currentText()
        self._source_combo.blockSignals(True)
        self._source_combo.clear()
        self._source_combo.addItem("all")
        for name in self._source_names():
            self._source_combo.addItem(name)
        restore_idx = self._source_combo.findText(current)
        self._source_combo.setCurrentIndex(max(0, restore_idx))
        self._source_combo.blockSignals(False)

    def _selected_sources(self) -> list[str]:
        if self._source_combo.currentText() == "all":
            return self._source_names()
        return [self._source_combo.currentText()]

    def _rebuild_slices(self) -> None:
        """Rebuild the slice combo to include all slices found on disk."""
        current = self._slice_combo.currentText()
        self._slice_combo.blockSignals(True)
        self._slice_combo.clear()
        self._slice_combo.addItem("current")

        # find all slice directories across all action dirs
        slice_indices: set[int] = set()
        for source in self._source_names():
            source_dir = self._source_dir(source)
            if source_dir and source_dir.exists():
                for d in source_dir.iterdir():
                    if d.is_dir() and d.name.startswith("slice_"):
                        with contextlib.suppress(IndexError, ValueError):
                            slice_indices.add(int(d.name.split("_")[1]))

        for idx in sorted(slice_indices):
            self._slice_combo.addItem(str(idx))

        # restore selection
        restore_idx = self._slice_combo.findText(current)
        self._slice_combo.setCurrentIndex(max(0, restore_idx))
        self._slice_combo.blockSignals(False)

    def _source_dir(self, source: str) -> Path | None:
        """Return the action root directory for a source name."""
        if source == "workflow":
            return self._workflow_dir / "workflow"
        name_with_underscores = source.replace(" ", "_")
        return self._workflow_dir / name_with_underscores

    def _log_path(self, source: str, slice_index: int) -> Path | None:
        """Return the log file path for a source and slice index."""
        d = self._source_dir(source)
        if d is None:
            return None
        return d / f"slice_{slice_index:04d}" / "run.log"

    def _current_slice_index(self) -> int:
        return self._manager.workflow.ctx.slice

    def _selected_slice_index(self) -> int:
        text = self._slice_combo.currentText()
        if text == "current":
            return self._current_slice_index()
        try:
            return int(text)
        except ValueError:
            return self._current_slice_index()

    def _selected_level_value(self) -> int:
        return level_value(self._level_combo.currentText())

    def _read_file(self, path: Path) -> list[str]:
        """Read new lines from a file, tracking position for streaming."""
        if not path.exists():
            return []
        pos = self._file_positions.get(path, 0)
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                f.seek(pos)
                lines = f.readlines()
                self._file_positions[path] = f.tell()
            return lines
        except OSError:
            return []

    def _read_file_full(self, path: Path) -> list[str]:
        """Read entire file contents (used on slice/source change)."""
        if not path.exists():
            return []
        try:
            with path.open("r", encoding="utf-8", errors="replace") as f:
                lines = f.readlines()
                self._file_positions[path] = f.tell()
            return lines
        except OSError:
            return []

    def _refresh(self) -> None:
        """Reload all selected log files from scratch and redisplay."""
        # reset positions so we re-read everything
        self._file_positions.clear()
        self._log_view.clear()

        slice_index = self._selected_slice_index()
        sources = self._selected_sources()
        min_level = self._selected_level_value()

        lines: list[LogLine] = []
        for source in sources:
            path = self._log_path(source, slice_index)
            if path is None:
                continue
            for raw in self._read_file_full(path):
                parsed = parse_line(raw)
                if parsed and level_value(parsed.level) >= min_level:
                    lines.append(parsed)

        lines.sort(key=lambda log: log.timestamp)
        for line in lines:
            self._append_line(line)

    def _on_poll(self) -> None:
        """Poll log files for new lines (only when watching current slice)."""
        if self._slice_combo.currentText() != "current":
            return

        slice_index = self._selected_slice_index()
        sources = self._selected_sources()
        min_level = self._selected_level_value()

        new_lines: list[LogLine] = []
        for source in sources:
            path = self._log_path(source, slice_index)
            if path is None:
                continue
            for raw in self._read_file(path):
                parsed = parse_line(raw)
                if parsed and level_value(parsed.level) >= min_level:
                    new_lines.append(parsed)

        if not new_lines:
            return

        new_lines.sort(key=lambda log: log.timestamp)
        for line in new_lines:
            self._append_line(line)

    def _append_line(self, line: LogLine) -> None:
        color = LEVEL_COLORS.get(line.level, "#cccccc")
        html = (
            f'<span style="color:{color}">'
            f"{line.raw.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}"
            f"</span>"
        )
        self._log_view.appendHtml(html)
