# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Self

from fibsem_maestro.logging.text.text_logger import TextLogger


@dataclass
class LogRecord:
    """
    A single captured log entry produced by `MemoryTextLogger`.

    Attributes:
        level: Severity string - one of `debug`, `info`,
            `warning`, or `error`.
        name: The logger name that emitted this record.
        message: The log message text.
    """

    level: str
    name: str
    message: str


class MemoryTextLogger(TextLogger):
    """
    TextLogger that stores records in memory rather than writing to disk.

    Args:
        name: Optional logger name shown in each `LogRecord`.
    """

    def __init__(
        self,
        name: str = "",
        *,
        _records: list[LogRecord] | None = None,
    ) -> None:
        self._name = name
        self._records: list[LogRecord] = [] if _records is None else _records

    @property
    def records(self) -> list[LogRecord]:
        """All log records emitted by this logger and any of its children."""
        return self._records

    def _append(self, level: str, msg: str) -> None:
        self._records.append(LogRecord(level=level, name=self._name, message=msg))

    def derive(self, name: str) -> Self:
        """
        Create a child logger that shares this logger's record list.

        Args:
            name: The name suffix appended to this logger's name.

        Returns:
            A new `MemoryTextLogger` sharing the same record list.
        """
        child_name = f"{self._name}.{name}" if self._name else name
        return type(self)(child_name, _records=self._records)

    def info(self, msg: str) -> None:
        self._append("info", msg)

    def warning(self, msg: str) -> None:
        self._append("warning", msg)

    def error(self, msg: str) -> None:
        self._append("error", msg)

    def debug(self, msg: str) -> None:
        self._append("debug", msg)
