# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging

from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.text.text_logger import TextLogger


class CentralTextLogger(TextLogger):
    """
    Centralized text logger that writes all messages for a given class
    into a single, non-slice-aware log file.

    This logger does not react to slice changes and maintains a single
    FileHandler for the entire lifetime of the object. Messages are emitted
    under a logger whose name matches the owning domain class.
    """

    def __init__(self, owner_cls: type, ctx: LogContext, log_level: int | None = None):
        """
        Initialize a centralized text logger.

        Args:
            owner_cls: The domain class whose name will be used as the logger name.
            ctx: The logging context providing directory paths and default log level.
            log_level: Optional override for the logger's log level. If None,
                the level from the LogContext is used.
        """
        self._ctx = ctx
        self._logger_name = owner_cls.__name__

        self._logger = logging.getLogger(self._logger_name)
        self._logger.propagate = False

        handler = logging.FileHandler(self._ctx.central_logs())
        handler.setFormatter(
            logging.Formatter("%(asctime)s: %(name)s - %(levelname)s - %(message)s")
        )
        self._logger.addHandler(handler)
        self._logger.setLevel(log_level or self._ctx.log_level)

    def info(self, msg: str):
        self._logger.info(msg)

    def warning(self, msg: str):
        self._logger.warning(msg)

    def error(self, msg: str):
        self._logger.error(msg)

    def debug(self, msg: str):
        self._logger.debug(msg)
