# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable
from typing import Any


class WidgetWrapper:
    """
    Base interface for field widgets.

    Widgets form a parent/child tree mirroring the settings hierarchy they
    edit. Any widget can call `_notify_changed()` when its value changes;
    this bubbles upward through `_parent` so a single top-level listener
    can react to any change anywhere in the tree, regardless of nesting.
    """

    _parent: "WidgetWrapper | None" = None
    _change_hooks: list[Callable[[], None]]

    def __init__(self) -> None:
        self._change_hooks = []
        self._parent = None

    def on_change(self, hook: Callable[[], None]) -> None:
        """Register a callback invoked when this widget or any descendant changes."""
        self._change_hooks.append(hook)

    def _notify_changed(self) -> None:
        """Fire change hooks on this widget and all ancestor widgets, bottom-up."""
        node: WidgetWrapper | None = self
        while node is not None:
            for hook in node._change_hooks:
                hook()
            node = node._parent

    def get_value(self) -> Any:
        raise NotImplementedError(
            f"get_value is not implemented for {self.__class__.__name__}"
        )

    def set_value(self, value: Any) -> None:
        raise NotImplementedError(
            f"set_value is not implemented for {self.__class__.__name__}"
        )

    def set_read_only(self, read_only: bool) -> None:
        raise NotImplementedError(
            f"set_read_only is not implemented for {self.__class__.__name__}"
        )
