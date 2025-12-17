# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod


class TextLogger(ABC):
    """
    Abstract interface for text-based logging.

    This interface defines the minimal set of methods required for emitting
    textual log messages from domain-level components. Concrete implementations
    determine how and where messages are recorded.
    """

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
