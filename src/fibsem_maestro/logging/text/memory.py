# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from typing import TYPE_CHECKING, Self

from fibsem_maestro.logging.text.text_logger import TextLogger

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class LogRecord:
    """
    A single captured log entry produced by `MemoryTextLogger`.

    Attributes:
        slice_index: The slice during which this record was emitted.
        level: Severity - one of `debug`, `info`, `warning`, `error`,
            `exception`.
        name: The full logger name at the time the record was emitted; a
            later rename does not change it.
        message: The log message text.
    """

    slice_index: int
    level: str
    name: str
    message: str


class MemoryTextLogger(TextLogger):
    """
    `TextLogger` that stores records in memory rather than writing to disk.

    A logger created directly is the root of a logger group; loggers produced
    by `derive()`, `at()` and `next` join its group. A group shares the record
    store, keyed by slice index, and a `_GroupState` holding the close flag
    and the base name. Each logger stores only its own suffix and resolves its
    full name on every record, so `rename()` on any logger renames the whole
    group, including derived loggers created earlier.

    Args:
        slice_provider: Callable returning the current slice index.
        name: Name shown in each `LogRecord`. For a logger joining an existing
            group (`_group` given), the suffix appended to the group's base
            name instead.
        _records: Shared record store. Internal; set by `derive()` and `at()`.
            When `None`, a fresh store is created.
        _group: Group to join. Internal; set by `derive()` and `at()`. When
            `None`, this logger becomes the root of a new group named `name`.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        name: str = "",
        *,
        _records: dict[int, list[LogRecord]] | None = None,
        _group: _GroupState | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._records: dict[int, list[LogRecord]] = (
            defaultdict(list) if _records is None else _records
        )
        if _group is None:
            self._group = _GroupState(name)
            self._suffix = ""
        else:
            self._group = _group
            self._suffix = name

    @property
    def name(self) -> str:
        """
        The full name shown in each record.

        Resolved on every call, so a rename of the group takes effect
        immediately for every logger in it.

        Returns:
            The group's base name followed by this logger's suffix.
        """
        base = self._group.name
        if not self._suffix:
            return base
        return f"{base}.{self._suffix}" if base else self._suffix

    @property
    def records(self) -> dict[int, list[LogRecord]]:
        """
        All log records emitted, grouped by slice index.

        Returns:
            A dict mapping slice index to the list of records emitted in
            that slice, across every logger in this group.
        """
        return self._records

    def rename(self, name: str) -> None:
        """
        Change the base name of this logger's group.

        Every logger in the group keeps its suffix and uses the new base name
        from its next record on. Records already stored keep their names.

        Args:
            name: The new base name.
        """
        self._group.name = name

    def _append(self, level: str, msg: str) -> None:
        """
        Store a record for the current slice.

        Args:
            level: Severity of the record.
            msg: The message to store.
        """
        record = LogRecord(
            slice_index=self._slice_provider(),
            level=level,
            name=self.name,
            message=msg,
        )
        self._records[record.slice_index].append(record)

    def info(self, msg: str) -> None:
        self._append("info", msg)

    def warning(self, msg: str) -> None:
        self._append("warning", msg)

    def error(self, msg: str) -> None:
        self._append("error", msg)

    def debug(self, msg: str) -> None:
        self._append("debug", msg)

    def exception(self, msg: str) -> None:
        self._append("exception", msg)

    def derive(self, name: str) -> Self:
        """
        Create a child logger in this logger's group.

        The child shares the record store and the base name, so it follows
        renames of the group.

        Args:
            name: The suffix to append to this logger's name.

        Returns:
            A `MemoryTextLogger` sharing the same record store with name
            `"{this_name}.{name}"`.
        """
        suffix = f"{self._suffix}.{name}" if self._suffix else name
        return type(self)(
            self._slice_provider,
            suffix,
            _records=self._records,
            _group=self._group,
        )

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        The view joins this logger's group, so it keeps this logger's name
        and follows renames of the group.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryTextLogger` sharing the same record store but writing
            to the given slice index.
        """
        return type(self)(
            lambda: slice_index,
            self._suffix,
            _records=self._records,
            _group=self._group,
        )

    @property
    def slice(self) -> int:
        return self._slice_provider()

    @property
    def closed(self) -> bool:
        """
        Whether `close` has been called on any logger in this group.

        Returns:
            True once any logger in this group has been closed.
        """
        return self._group.closed

    def close(self) -> None:
        """
        Record that this logger group was closed.

        Nothing is released - stored records stay readable and further calls
        still append, matching `FileTextLogger`, where logging after `close`
        reopens the handler.
        """
        self._group.closed = True


class _GroupState:
    """
    State shared across a `MemoryTextLogger` group.

    Mirrors `FileTextLogger`'s shared handler root: closing any logger in the
    group marks the whole group closed, and renaming any logger renames the
    whole group.

    Args:
        name: Base name of the group.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.closed = False
