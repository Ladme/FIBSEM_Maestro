# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

import logging
import sys
import weakref
from typing import TYPE_CHECKING, Self

from fibsem_maestro.logging.text.text_logger import TextLogger

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path
    from types import TracebackType

    from fibsem_maestro.slice.slice_view import SliceView


class FileTextLogger(TextLogger):
    """
    `TextLogger` that writes to a per-slice log file on disk.

    Each slice directory gets its own log file. The active file is determined
    at each log call by invoking `view_provider`, so rotating to a new slice
    requires only updating what `view_provider` returns.

    All loggers produced by `derive()` share the same underlying
    `_FileTextLoggerRoot` and therefore the same open `FileHandler`.
    Records are emitted directly to the handler with the display name set
    per-record, so no Python logger registry entries are created for derived loggers.


    Args:
        view_provider: Callable returning the `SliceView` to write to.
        name: Logger name embedded in each log record.
        filename: Name of the log file within the slice directory. Defaults to `run.log`.
        level: Logging level. Defaults to `logging.INFO`.
    """

    def __init__(
        self,
        view_provider: Callable[[], SliceView],
        name: str,
        filename: str = "run.log",
        level: int = logging.DEBUG,
        *,
        _root: _FileTextLoggerRoot | None = None,
    ) -> None:
        self._view_provider = view_provider
        self._name = name
        self._filename = filename
        self._level = level
        self._root = (
            _root if _root is not None else _FileTextLoggerRoot(filename, level)
        )

    def _emit(
        self,
        level: int,
        msg: str,
        exc_info: tuple[type[BaseException], BaseException, TracebackType]
        | None = None,
    ) -> None:
        """
        Write a record to the current slice's log file.

        Args:
            level: The `logging` level of the record.
            msg: The message to log.
            exc_info: Exception triple to render after the message, or None.
        """
        if level < self._level:
            return

        handler = self._root.get_handler(self._view_provider())
        record = logging.LogRecord(
            name=self._name,
            level=level,
            pathname="",
            lineno=0,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )
        handler.handle(record)

    def info(self, msg: str) -> None:
        self._emit(logging.INFO, msg)

    def warning(self, msg: str) -> None:
        self._emit(logging.WARNING, msg)

    def error(self, msg: str) -> None:
        self._emit(logging.ERROR, msg)

    def exception(self, msg: str) -> None:
        exc_info = sys.exc_info()
        self._emit(logging.ERROR, msg, None if exc_info[0] is None else exc_info)

    def debug(self, msg: str) -> None:
        self._emit(logging.DEBUG, msg)

    def derive(self, name: str) -> Self:
        """
        Create a child logger writing to the same file.

        The child shares the same handler root so no additional file handles
        are opened. Only the name embedded in each record differs.

        Args:
            name: The suffix to append to this logger's name.

        Returns:
            A `FileTextLogger` sharing the same `view_provider` and log
            file, with name `"{this_name}.{name}"`.
        """
        child_name = f"{self._name}.{name}" if self._name else name
        return type(self)(
            self._view_provider,
            child_name,
            self._filename,
            self._level,
            _root=self._root,
        )

    def at(self, slice_index: int) -> Self:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A `FileTextLogger` writing to the given slice directory.
        """
        view = self._view_provider()
        fixed = type(view)(view.action_dir, slice_index)

        return type(self)(
            lambda: fixed,
            self._name,
            self._filename,
            self._level,
            _root=self._root,
        )

    @property
    def slice(self) -> int:
        return self._view_provider().slice_index

    def close(self) -> None:
        self._root.close()


class _FileTextLoggerRoot:
    """
    Owns the single `FileHandler` shared across a `FileTextLogger` and
    all loggers derived from it.

    This object holds all mutable handler state. Derived loggers hold a
    reference to the root and delegate handler management here, ensuring
    only one handler is ever open at a time regardless of how many derived
    loggers exist.

    Args:
        view_provider: Callable returning the `SliceView` to write to.
        filename: Name of the log file within the slice directory.
        level: Logging level threshold.
    """

    _FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    # registry of all live roots, so close_all() can release every open file handle at once
    # weak refs let unused roots (e.g. throwaway ones from at()/next)
    # be garbage-collected normally instead of being pinned here
    _instances: weakref.WeakSet[_FileTextLoggerRoot] = weakref.WeakSet()

    def __init__(self, filename: str, level: int) -> None:
        self._filename = filename
        self._level = level
        self._active_path: Path | None = None
        self._active_handler: logging.FileHandler | None = None
        _FileTextLoggerRoot._instances.add(self)

    def get_handler(self, view: SliceView) -> logging.FileHandler:
        """
        Return a `FileHandler` for the given slice, rotating if needed.

        Args:
            view: The slice view whose directory the handler writes into.

        Returns:
            An open `FileHandler` pointed at that slice's log file.
        """
        path = view.path() / self._filename

        if self._active_handler is not None and path == self._active_path:
            return self._active_handler

        if self._active_handler is not None:
            self._active_handler.close()

        handler = logging.FileHandler(path)
        handler.setLevel(self._level)
        handler.setFormatter(logging.Formatter(self._FORMAT))
        self._active_handler = handler
        self._active_path = path
        return handler

    def close(self) -> None:
        """
        Close the open file handler, releasing its OS file handle.

        The next log call reopens a handler for the then-current slice, so
        closing is safe at any time. It merely releases the file until the next write.
        """
        if self._active_handler is not None:
            self._active_handler.close()
        self._active_handler = None
        self._active_path = None

    @classmethod
    def close_all(cls) -> None:
        """
        Close every live per-slice file handler across all logger roots.

        Snapshots the registry first so handlers reopening during iteration do
        not disturb the sweep. Handlers reopen lazily on the next log call.
        """
        for root in list(cls._instances):
            root.close()


class _PrefixStrippingFormatter(logging.Formatter):
    """
    Formatter that removes an internal root prefix from the logger name.

    Args:
        prefix: The root prefix string to strip, including the trailing dot.
        fmt: The format string passed to `logging.Formatter`.
    """

    def __init__(self, prefix: str, fmt: str) -> None:
        super().__init__(fmt)
        self._prefix = prefix

    def format(self, record: logging.LogRecord) -> str:
        """
        Format *record*, stripping the root prefix from its name.

        Args:
            record: The log record to format.

        Returns:
            The formatted log string with the prefix removed from the name field.
        """
        # mutate a copy so the original record is not modified (it may be
        # handled by other handlers or inspected after this call).
        record = logging.makeLogRecord(record.__dict__)
        record.name = record.name.removeprefix(self._prefix) or "root"
        return super().format(record)


def close_all_log_files() -> None:
    """
    Close all open per-slice log file handles.

    Call before deleting or moving slice directories (e.g. on workflow reset)
    so no open handle blocks removal on Windows. Handlers reopen automatically
    on the next log write.
    """
    _FileTextLoggerRoot.close_all()
