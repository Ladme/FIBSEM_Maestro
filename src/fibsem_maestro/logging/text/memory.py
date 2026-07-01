# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections import defaultdict
from collections.abc import Callable
from dataclasses import dataclass
from typing import Self

from fibsem_maestro.logging.text.text_logger import TextLogger


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
    """

    def __init__(
        self,
        slice_provider: Callable[[], int],
        name: str = "",
        *,
        _records: dict[int, list[LogRecord]] | None = None,
    ) -> None:
        self._slice_provider = slice_provider
        self._name = name
        self._records: dict[int, list[LogRecord]] = (
            defaultdict(list) if _records is None else _records
        )

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
        )

    @property
    def next(self) -> Self:
        """
        Return a view of this logger scoped to the next slice.

        Returns:
            A `MemoryTextLogger` writing to the slice after the current one.
        """
        next_index = self._slice_provider() + 1
        return type(self)(
            lambda: next_index,
            self._name,
            _records=self._records,
        )

    @property
    def slice(self) -> int:
        return self._slice_provider()
