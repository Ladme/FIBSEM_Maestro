# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Self

from fibsem_maestro.logging.logging import get_current_logger
from fibsem_maestro.logging.text.text_logger import TextLogger


class ContextualTextLogger(TextLogger):
    """
    `TextLogger` that delegates to whichever logger is active in the
    current execution context.

    This logger holds no fixed destination - on every call it reads
    the `ContextVar` set by `ActionContext.advance()` and forwards to
    whatever `TextLogger` is currently active there.

    If no logger is active in the current context, calls are forwarded to
    `fallback`.

    Views returned by `at()` and `next` are resolved from the logger active
    at the moment of the call and stay bound to it, so they keep writing to
    that action's directory even after the context advances.

    This logger owns neither the active logger nor the fallback, so `close()`
    is a no-op; close the underlying loggers through whatever created them.

    Args:
        fallback: Logger to use when no action context is active.
        _suffix: Internal name suffix accumulated via `derive()`.
            Not intended to be set directly.
    """

    def __init__(self, fallback: TextLogger, _suffix: str = "") -> None:
        self._fallback = fallback
        self._suffix = _suffix

    def _active(self) -> TextLogger:
        logger = get_current_logger()
        base = logger if logger is not None else self._fallback
        return base.derive(self._suffix) if self._suffix else base

    def info(self, msg: str) -> None:
        self._active().info(msg)

    def warning(self, msg: str) -> None:
        self._active().warning(msg)

    def error(self, msg: str) -> None:
        self._active().error(msg)

    def debug(self, msg: str) -> None:
        self._active().debug(msg)

    def exception(self, msg: str) -> None:
        self._active().exception(msg)

    def derive(self, name: str) -> Self:
        """
        Create a child logger that appends `name` to the active logger's name.

        The suffix is accumulated and applied on every call, so
        `contextual.derive("microscope").derive("beam")` produces records
        named `"{action}.microscope.beam"` regardless of which action is active.

        Args:
            name: The suffix to append.

        Returns:
            A `ContextualTextLogger` with the extended suffix.
        """
        new_suffix = f"{self._suffix}.{name}" if self._suffix else name
        return type(self)(self._fallback, new_suffix)

    def at(self, slice_index: int) -> TextLogger:
        """
        Return a view of the active logger scoped to a specific slice.

        The view is bound to the logger active at the time of this call, not
        re-resolved later. If no logger is active, the fallback's view is returned.

        Args:
            slice_index: The slice index to address.

        Returns:
            A scoped view from the currently active logger.
        """
        return self._active().at(slice_index)

    @property
    def next(self) -> TextLogger:
        """
        Return a view of the active logger scoped to the next slice.

        Overrides the base implementation so the context is read once rather
        than twice. Resolving `self.slice` and `self.at()` separately could
        straddle an `ActionContext.advance()` and mix two actions.

        Returns:
            A scoped view from the currently active logger.
        """
        return self._active().next

    @property
    def slice(self) -> int:
        return self._active().slice

    def close(self) -> None:
        """
        Do nothing; this logger owns no resources.

        Both the active logger and the fallback are owned by whatever created
        them. Closing them here would release file handles still in use by
        the running action.
        """
