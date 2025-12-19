# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Self


class TextLogger(ABC):
    """
    Abstract interface for text-based logging.

    This interface defines the minimal set of methods required for emitting
    textual log messages from domain-level components. Concrete implementations
    determine how and where messages are recorded.
    """

    @abstractmethod
    def derive(self, name: str) -> Self:
        """
        Create a child logger derived from this logger.

        The child logger inherits this logger's configuration and context, but
        uses a hierarchical name composed from the parent's name and the provided
        child name.

        Args:
            name: The name of the child logger. This value is appended to the
                parent logger's name to form a hierarchical identifier.

        Returns:
            A new logger instance of the same concrete type as this logger.
        """
        pass

    @abstractmethod
    def info(self, msg: str) -> None:
        """
        Log an informational message.

        Args:
            msg: The message to be written to the log backend.
        """
        pass

    @abstractmethod
    def warning(self, msg: str) -> None:
        """
        Log a warning message.

        Args:
            msg: The message describing a recoverable issue or abnormal event.
        """
        pass

    @abstractmethod
    def error(self, msg: str) -> None:
        """
        Log an error message.

        Args:
            msg: The message describing a non-recoverable or critical error.
        """
        pass

    @abstractmethod
    def debug(self, msg: str) -> None:
        """
        Log a debug-level message.

        Args:
            msg: The message providing diagnostic information for development
                or troubleshooting.
        """
        pass
