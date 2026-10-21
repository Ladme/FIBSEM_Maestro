# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Incremental reading of the per-slice `run.log` files of a workflow's sources."""

import contextlib
from collections.abc import Sequence
from pathlib import Path

from fibsem_maestro.ui.views.log_panel.parsing import LogLine, level_value, parse_line

WORKFLOW_SOURCE = "workflow"
"""Name of the workflow's own log source; every other source is an action name."""


class LogReader:
    """
    Reads the log lines of a workflow's sources, slice by slice.

    A source is an action name or `WORKFLOW_SOURCE`; its directory is
    `workflow_dir / name.replace(" ", "_")` and its log of slice N is
    `slice_NNNN/run.log` inside it. The reader remembers how far it has read
    each file, so `poll` returns only lines written since the last read. Only
    complete lines are returned: a last line still being written is returned,
    in full, by a later poll once its line break is there.

    Args:
        workflow_dir: Directory holding the workflow's `workflow/` and action directories.
    """

    def __init__(self, workflow_dir: Path) -> None:
        self._workflow_dir = workflow_dir
        # path -> byte offset just past the last complete line read
        self._file_positions: dict[Path, int] = {}

    @property
    def workflow_dir(self) -> Path:
        """Directory holding the workflow's `workflow/` and action directories."""
        return self._workflow_dir

    def set_workflow_dir(self, workflow_dir: Path) -> None:
        """
        Read another workflow's logs from now on.

        Args:
            workflow_dir: The new workflow directory.
        """
        self._workflow_dir = workflow_dir
        self._file_positions.clear()

    def source_dir(self, source: str) -> Path:
        """
        The directory of a source.

        Args:
            source: An action name or `WORKFLOW_SOURCE`.

        Returns:
            The source's root directory.
        """
        if source == WORKFLOW_SOURCE:
            return self._workflow_dir / "workflow"
        return self._workflow_dir / source.replace(" ", "_")

    def log_path(self, source: str, slice_index: int) -> Path:
        """
        The log file of a source for a slice.

        Args:
            source: An action name or `WORKFLOW_SOURCE`.
            slice_index: The slice.

        Returns:
            The path of the `run.log` file (which may not exist).
        """
        return self.source_dir(source) / f"slice_{slice_index:04d}" / "run.log"

    def slices(self, sources: Sequence[str]) -> list[int]:
        """
        Every slice for which some source has a directory.

        Args:
            sources: The sources to look in.

        Returns:
            The slice indices, ascending.
        """
        slice_indices: set[int] = set()
        for source in sources:
            source_dir = self.source_dir(source)
            if source_dir.exists():
                for d in source_dir.iterdir():
                    if d.is_dir() and d.name.startswith("slice_"):
                        with contextlib.suppress(IndexError, ValueError):
                            slice_indices.add(int(d.name.split("_")[1]))
        return sorted(slice_indices)

    def has_slice(self, sources: Sequence[str], slice_index: int) -> bool:
        """
        Check whether some source has a directory for a slice.

        Args:
            sources: The sources to look in.
            slice_index: The slice.

        Returns:
            True if `slice_NNNN` exists in some source's directory.
        """
        candidate = f"slice_{slice_index:04d}"
        return any((self.source_dir(s) / candidate).is_dir() for s in sources)

    def read(
        self, slice_index: int, sources: Sequence[str], min_level: int
    ) -> list[LogLine]:
        """
        Read the whole logs of a slice from scratch.

        Every remembered file position is reset, then the selected files are
        read to their end.

        Args:
            slice_index: The slice.
            sources: The sources whose logs are merged.
            min_level: Lines below this `logging` level are dropped.

        Returns:
            The parsed lines of all sources, sorted by timestamp.
        """
        self._file_positions.clear()
        return self._collect(slice_index, sources, min_level)

    def poll(
        self, slice_index: int, sources: Sequence[str], min_level: int
    ) -> list[LogLine]:
        """
        Read the lines written to a slice's logs since they were last read.

        A file not read before is read from its start.

        Args:
            slice_index: The slice.
            sources: The sources whose logs are merged.
            min_level: Lines below this `logging` level are dropped.

        Returns:
            The new parsed lines of all sources, sorted by timestamp.
        """
        return self._collect(slice_index, sources, min_level)

    def _collect(
        self, slice_index: int, sources: Sequence[str], min_level: int
    ) -> list[LogLine]:
        lines: list[LogLine] = []
        for source in sources:
            for raw in self._read_file(self.log_path(source, slice_index)):
                parsed = parse_line(raw)
                if parsed and level_value(parsed.level) >= min_level:
                    lines.append(parsed)

        lines.sort(key=lambda log: log.timestamp)
        return lines

    def _read_file(self, path: Path) -> list[str]:
        """
        Read the complete lines added to a file since it was last read.

        Args:
            path: The log file.

        Returns:
            The new complete lines, without line breaks; empty if the file is
            missing or unreadable.
        """
        if not path.exists():
            return []
        pos = self._file_positions.get(path, 0)
        try:
            # binary, so the position is a byte offset that can be advanced by
            # exactly the complete lines (a text file's tell() is opaque)
            with path.open("rb") as f:
                f.seek(pos)
                data = f.read()
        except OSError:
            return []

        end = data.rfind(b"\n") + 1
        if end == 0:
            return []
        self._file_positions[path] = pos + end
        # cut at a line break, so never inside a multi-byte character
        return data[:end].decode("utf-8", errors="replace").splitlines()
