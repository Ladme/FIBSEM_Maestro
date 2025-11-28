# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging

from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.text.text_logger import TextLogger


class SliceAwareTextLogger(TextLogger):
    """
    A text logger that automatically switches output files based on slice number.

    This logger writes messages to a file determined by the current slice number
    stored inside the associated LogContext. When the slice changes, the logger
    closes old handlers and installs a new FileHandler pointing to the new slice's log file.
    """

    def __init__(
        self,
        name: str,
        ctx: LogContext,
        log_level: int | None = None,
    ):
        """
        Initialize a slice-aware logger.

        Args:
            name: Name to use for the logger.
            ctx: The logging context providing directory paths and default log level.
            log_level: Optional override for the logger's log level. If None,
                the level from the LogContext is used.
        """
        self._ctx = ctx
        self._name = name
        self._log_level = log_level
        self._last_slice = None

    def info(self, msg: str):
        self._logger().info(msg)

    def warning(self, msg: str):
        self._logger().warning(msg)

    def error(self, msg: str):
        self._logger().error(msg)

    def debug(self, msg: str):
        self._logger().debug(msg)

    def _logger(self) -> logging.Logger:
        """
        Return a configured logger for the current slice.

        This method switches the underlying FileHandler whenever the active slice
        changes. Each slice writes to its own log file. When the slice remains
        unchanged, the existing handler is reused.

        Returns:
            The slice-aware `logging.Logger` instance.
        """
        logger = logging.getLogger(self._name)
        logger.propagate = False

        current_slice = self._ctx.slice_ctx.current_slice

        # only switch files when the cycle number changes
        if current_slice != self._last_slice:
            # close & remove old handlers for this class logger
            for h in list(logger.handlers):
                h.close()
                logger.removeHandler(h)

            # attach a new FileHandler for the current slice
            logfile = self._ctx.logs()
            handler = logging.FileHandler(logfile)
            handler.setFormatter(
                logging.Formatter("%(asctime)s: %(name)s - %(levelname)s - %(message)s")
            )
            logger.addHandler(handler)

            logger.setLevel(self._log_level or self._ctx.log_level)

            self._last_slice = current_slice

        return logger
