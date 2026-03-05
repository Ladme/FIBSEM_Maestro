# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging
from typing import TYPE_CHECKING, Self

from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.logging.text.text_logger import TextLogger

if TYPE_CHECKING:
    from pathlib import Path


class _SliceAwareFileHandler(logging.Handler):
    """
    A logging handler that transparently rotates to each new slice's log file.

    On every `emit` call, the handler compares the current log path
    from the `SliceContext` against the one it last opened.
    When the path changes (i.e. the slice has been incremented), the
    old file is closed and a new `logging.FileHandler` is opened
    automatically.

    Args:
        ctx: The slice context used to resolve the active log file path.
    """

    def __init__(self, ctx: SliceContext) -> None:
        super().__init__()
        self._ctx = ctx
        self._active_path: Path | None = None
        self._active_handler: logging.FileHandler | None = None

    def _get_handler(self) -> logging.FileHandler:
        """
        Return a FileHandler for the current log path, rotating if needed.

        Returns:
            An open `logging.FileHandler` pointed at the active log file.
        """
        path = self._ctx.logs()
        if path != self._active_path:
            if self._active_handler is not None:
                self._active_handler.close()
            self._active_handler = logging.FileHandler(path)
            self._active_handler.setFormatter(self.formatter)
            self._active_path = path
        return self._active_handler  # type: ignore[return-value]

    def emit(self, record: logging.LogRecord) -> None:
        """
        Emit a log record to the current slice's log file.

        Args:
            record: The log record to emit.
        """
        self._get_handler().emit(record)

    def close(self) -> None:
        """Close the underlying file handler and release resources."""
        if self._active_handler is not None:
            self._active_handler.close()
        super().close()


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


class FileTextLogger(TextLogger):
    """
    TextLogger that writes to the current slice's `app.log` file.

    Args:
        ctx: Slice context used to resolve the active log file path.
        name: Logger name. Child loggers created via `derive` extend
            this name hierarchically.
        lavel: Logging level. Defaults to INFO.
    """

    _FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"

    def __init__(
        self, ctx: SliceContext, name: str = "", level: int = logging.INFO
    ) -> None:
        self._ctx = ctx
        self._name = name

        # one root logger per SliceContext instance, identified by object id
        # to avoid collisions between independent runs
        root_name = f"slice_ctx_{id(ctx)}"
        root = logging.getLogger(root_name)
        if not root.handlers:
            handler = _SliceAwareFileHandler(ctx)
            handler.setFormatter(
                _PrefixStrippingFormatter(f"{root_name}.", self._FORMAT)
            )
            root.addHandler(handler)
            root.setLevel(level)
            root.propagate = False

        full_name = f"{root_name}.{name}" if name else root_name
        self._logger = logging.getLogger(full_name)

    def derive(self, name: str) -> Self:
        """
        Create a child logger with a hierarchical name.

        Args:
            name: The name suffix appended to this logger's name.

        Returns:
            A new `FileTextLogger` sharing the same slice context.
        """
        child_name = f"{self._name}.{name}" if self._name else name
        return type(self)(self._ctx, child_name)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)
