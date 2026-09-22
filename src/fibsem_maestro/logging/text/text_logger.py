# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Self


class TextLogger(ABC):
    """Abstract interface for text-based logging."""

    @abstractmethod
    def info(self, msg: str) -> None:
        """
        Log an informational message.

        Args:
            msg: The message to log.
        """

    @abstractmethod
    def warning(self, msg: str) -> None:
        """
        Log a warning message.

        Args:
            msg: The message to log.
        """

    @abstractmethod
    def error(self, msg: str) -> None:
        """
        Log an error message.

        Args:
            msg: The message to log.
        """

    @abstractmethod
    def exception(self, msg: str) -> None:
        """
        Log an error message together with the active exception's traceback.

        Must be called from inside an `except` block; outside one it behaves like `error`.

        Args:
            msg: The message to log.
        """

    @abstractmethod
    def debug(self, msg: str) -> None:
        """
        Log a debug-level message.

        Args:
            msg: The message to log.
        """

    @abstractmethod
    def derive(self, name: str) -> Self:
        """
        Create a child logger with a more specific name.

        The child logger shares the same destination and slice tracking as
        this logger, but records are emitted under a hierarchical name formed
        by appending `name` to this logger's name.

        Args:
            name: The suffix to append to this logger's name.

        Returns:
            A logger of the same concrete type with name
            `"{this_name}.{name}"`.
        """

    @abstractmethod
    def at(self, slice_index: int) -> TextLogger:
        """
        Return a view of this logger scoped to a specific slice.

        Args:
            slice_index: The slice index to address.

        Returns:
            A logger of the same concrete type writing to the given slice.
        """

    @property
    @abstractmethod
    def slice(self) -> int:
        """
        The slice index this logger is currently writing to.

        Returns:
            The current slice index.
        """

    def close(self) -> None:
        """
        Release any resources held by this logger.

        The default implementation does nothing. Loggers holding file handles
        or sockets override this. Logging after `close` is always valid;
        resources are reacquired as needed.
        """

    @property
    def next(self) -> TextLogger:
        """
        Return a view of this logger scoped to the next slice.

        Returns:
            A logger of the same concrete type writing to the slice after
            the current one.
        """
        return self.at(self.slice + 1)
