# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import functools
from collections.abc import Callable, Generator
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any

from fibsem_maestro.logging.text.text_logger import TextLogger

_current_text_logger: ContextVar[TextLogger | None] = ContextVar(
    "_current_text_logger", default=None
)


def set_current_logger(logger: TextLogger) -> Token:
    """
    Set the active `TextLogger` for the current execution context.

    Stores `logger` in a contextvars' `ContextVar` so that any
    `ContextualTextLogger` active in the same thread (or async task)
    will delegate to it.

    Args:
        logger: The logger to make active.

    Returns:
        A reset token that can be passed to `reset_current_logger` to
        restore the previous value.
    """
    return _current_text_logger.set(logger)


def reset_current_logger(token: Token) -> None:
    """
    Restore the `TextLogger` active before a `set_current_logger` call.

    Args:
        token: The token returned by the corresponding `set_current_logger` call.
    """
    _current_text_logger.reset(token)


def get_current_logger() -> TextLogger | None:
    """
    Return the `TextLogger` currently active in this execution context.

    Returns:
        The active logger, or `None` if none has been set.
    """
    return _current_text_logger.get()


@contextmanager
def logging_context(logger: TextLogger) -> Generator[None, None, None]:
    """
    Context manager that temporarily sets the active `TextLogger`.

    Args:
        logger: The logger to activate for the duration of the block.

    Yields:
        Nothing.
    """
    token = set_current_logger(logger)
    try:
        yield
    finally:
        reset_current_logger(token)


def with_logging_context(method: Callable[..., Any]):
    """
    Decorator that runs a method inside a `logging_context` for `self.ctx.text_logger`.

    Equivalent to wrapping the entire method body in
    `with logging_context(self.ctx.text_logger)`, ensuring that any
    `ContextualTextLogger` instances active during the call - including the
    one held by the `Microscope` - route records to this action's logger.

    Args:
        method: The method to wrap.

    Returns:
        The wrapped method with identical signature and return type.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        with logging_context(self.ctx.text_logger):
            return method(self, *args, **kwargs)

    return wrapper
