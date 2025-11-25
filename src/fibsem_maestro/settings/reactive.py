# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, PrivateAttr


class Reactive(BaseModel):
    """
    Reactive Pydantic model with a single shared event root.

    `Reactive` tracks changes to its fields and triggers callbacks whenever the
    model or any of its nested `Reactive` children is modified. All nodes in a
    settings tree share a single `_root`, which stores the hook list. Any change
    anywhere in the tree invokes the hooks exactly once per operation.
    """

    # root node of the model
    _root: Self | None = PrivateAttr(default=None)

    # all reqistered hooks
    _hooks: list[Callable[[Self], None]] = PrivateAttr(
        default_factory=list[Callable[[Self], None]]
    )

    def on_change(self, hook: Callable[[Self], None]) -> None:
        """
        Register a callback invoked when the settings tree changes.

        The callback is stored on the shared root node. It is executed whenever
        any reactive field (in this instance or any nested instance) is updated.

        Args:
            hook: A callable receiving the root instance after a change.
        """
        assert self._root is not None

        self._root._hooks.append(hook)

    def update(self, other: Self):
        """
        Update this instance to match another instance.

        All model fields are copied from `other` without triggering per-field hook calls.
        After copying, `_propagate_root()` re-establishes the correct shared root
        for all nested nodes, and hooks are fired once.

        Args:
            other: Another `Reactive` instance whose values replace this one.
        """
        for field in type(self).model_fields:
            # bypass __setattr__ to avoid triggering signals per-field
            object.__setattr__(self, field, getattr(other, field))

        # re-propagate the root into newly assigned nested models
        assert self._root is not None
        propagate_root(self._root, self)

        # hooks are called only once
        self._call_hooks()

    def __setattr__(self, name: str, value: Any):
        """
        Assign a model field and trigger change hooks.

        Hooks are triggered only when setting a declared model field. Changing
        private attributes or internal state does not emit notifications.

        Args:
            name: The attribute name to assign.
            value: The new attribute value.
        """
        # set the field as normal
        super().__setattr__(name, value)

        # ensure reactive children inherit the root
        assert self._root is not None
        if name in type(self).model_fields:
            propagate_root(self._root, self)
            self._call_hooks()

    def model_post_init(self, __context: Any):
        """
        Initialization hook called by Pydantic.

        Ensures each newly created object becomes a root unless added as a
        nested node, and propagates the root into nested `Reactive` children.
        """
        # the instance is its own root unless assigned into a parent later
        if self._root is None:
            self._root = self

        propagate_root(self._root, self)

    def _call_hooks(self) -> None:
        """Invoke all callbacks registered on the root instance."""
        assert self._root is not None

        for hook in self._root._hooks:
            hook(self._root)


def propagate_root(root: Reactive, value: Any) -> None:
    """Recursively assign root to any nested Reactive objects."""

    if isinstance(value, Reactive):
        value._root = root
        for field in type(value).model_fields:
            propagate_root(root, getattr(value, field))

    elif isinstance(value, dict):
        for item in value.values():  # type: ignore
            propagate_root(root, item)

    elif isinstance(value, list):
        for item in value:  # type: ignore
            propagate_root(root, item)
