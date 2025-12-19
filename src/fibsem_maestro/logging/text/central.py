# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging

from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.text.text_logger import TextLogger


class CentralTextLogger(TextLogger):
    """
    Centralized text logger that writes all messages into a single, non-slice-aware log file.

    This logger does not react to slice changes and maintains a single
    FileHandler for the entire lifetime of the object. Messages are emitted
    under a logger with the specified name.
    """

    def __init__(
        self,
        name: str,
        ctx: LogContext,
        log_level: int | None = None,
    ):
        """
        Initialize a centralized text logger.

        Args:
            name: Name to use for the logger.
            ctx: The logging context providing directory paths and default log level.
            log_level: Optional override for the logger's log level. If None,
                the level from the LogContext is used.
        """
        self._ctx = ctx
        self._name = name or ""
        self._log_level = log_level

        self._logger = logging.getLogger(name)
        self._logger.propagate = False

        handler = logging.FileHandler(self._ctx.central_logs())
        handler.setFormatter(
            logging.Formatter("%(asctime)s: %(name)s - %(levelname)s - %(message)s")
        )
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level or self._ctx.log_level)

    def derive(self, name: str) -> "CentralTextLogger":
        return CentralTextLogger(f"{self._name} > {name}", self._ctx, self._log_level)

    def info(self, msg: str) -> None:
        self._logger.info(msg)

    def warning(self, msg: str) -> None:
        self._logger.warning(msg)

    def error(self, msg: str) -> None:
        self._logger.error(msg)

    def debug(self, msg: str) -> None:
        self._logger.debug(msg)
