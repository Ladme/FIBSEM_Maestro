# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import Generic, TypeVar

OnChange = Callable[[], None]


def _noop() -> None:
    """A do-nothing default `on_change`."""


T = TypeVar("T")


# this cannot be ABC due to some metaclass conflicts
class BaseWidget(Generic[T]):
    """Base interface for field widgets."""

    def __init__(self) -> None:
        self._change_hooks: list[OnChange] = []

    def on_change(self, hook: OnChange) -> None:
        """Register a callback fired when this widget's own state changes."""
        self._change_hooks.append(hook)

    def _emit(self) -> None:
        """Fire this widget's callbacks."""
        for hook in self._change_hooks:
            hook()

    def get_value(self) -> T:
        raise NotImplementedError(
            f"get_value not implemented for {type(self).__name__}"
        )

    def set_value(self, value: T) -> None:
        raise NotImplementedError(
            f"set_value not implemented for {type(self).__name__}"
        )

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError(
            f"set_read_only not implemented for {type(self).__name__}"
        )
