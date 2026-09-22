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
        level: Severity - one of `debug`, `info`, `warning`, `error`.
        name: The logger name that emitted this record.
        message: The log message text.
    """

    slice_index: int
    level: str
    name: str
    message: str


class MemoryTextLogger(TextLogger):
    """
    `TextLogger` that stores records in memory rather than writing to disk.

    All instances sharing the same `_records` dict (i.e. created via
    `at()` or `next`) write into that shared dict, keyed by slice index.

    Args:
        slice_provider: Callable returning the current slice index.
        name: Logger name shown in each `LogRecord`.
        _records: Shared record store. When `None` a fresh dict is created,
            making this instance the root of a new record group.
        _close_state: Shared close flag. When `None` a fresh flag is created,
            paired with the new record group.
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        name: str = "",
        *,
        _records: dict[int, list[LogRecord]] | None = None,
        _close_state: _CloseState | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._name = name
        self._records: dict[int, list[LogRecord]] = (
            defaultdict(list) if _records is None else _records
        )

        self._close_state = _CloseState() if _close_state is None else _close_state

    @property
    def records(self) -> dict[int, list[LogRecord]]:
        """
        All log records emitted, grouped by slice index.

        Returns:
            A dict mapping slice index to the list of records emitted in
            that slice, across this logger and any navigated views.
        """
        return self._records

    def _append(self, level: str, msg: str) -> None:
        record = LogRecord(
            slice_index=self._slice_provider(),
            level=level,
            name=self._name,
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
        """Create a child logger sharing the same record store.

        Args:
            name: The suffix to append to this logger's name.

        Returns:
            A `MemoryTextLogger` sharing the same record store with name
            `"{this_name}.{name}"`.
        """
        child_name = f"{self._name}.{name}" if self._name else name
        return type(self)(
            self._slice_provider,
            child_name,
            _records=self._records,
            _close_state=self._close_state,
        )

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `MemoryTextLogger` sharing the same record store but writing
            to the given slice index.
        """
        return type(self)(
            lambda: slice_index,
            self._name,
            _records=self._records,
            _close_state=self._close_state,
        )

    @property
    def slice(self) -> int:
        return self._slice_provider()

    @property
    def closed(self) -> bool:
        """
        Whether `close` has been called on this logger or any view of it.

        Returns:
            True once any logger in this group has been closed.
        """
        return self._close_state.closed

    def close(self) -> None:
        """
        Record that this logger group was closed.

        Nothing is released - stored records stay readable and further calls
        still append, matching `FileTextLogger`, where logging after `close`
        reopens the handler.
        """
        self._close_state.closed = True


class _CloseState:
    """
    Close flag shared across a logger group.

    Mirrors `FileTextLogger`'s shared handler root: closing any view in a
    group marks the whole group closed.
    """

    def __init__(self) -> None:
        self.closed = False
