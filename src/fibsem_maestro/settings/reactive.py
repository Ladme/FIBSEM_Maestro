# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, PrivateAttr


class Reactive(BaseModel):
    """
    Reactive Pydantic model with per-node hooks and hierarchical event propagation.

    `Reactive` tracks changes to its fields and triggers callbacks whenever the
    model or any of its nested `Reactive` children is modified. Each node maintains
    a list of hooks and a reference to its parent, forming a tree of reactive
    objects. When a node changes, its own hooks are invoked along with the hooks of
    all ancestor nodes.

    Each `Reactive` instance acts as the root of its own subtree unless attached as
    a child of another instance. Parent links are automatically maintained, and
    nested `Reactive` objects inherit the correct ancestry whenever they are created,
    assigned, or updated.
    """

    # reference to parent node; None: this is a root
    _parent: Self | None = PrivateAttr(default=None)

    # hooks associated with this node
    _hooks: list[Callable[[Self], None]] = PrivateAttr(
        default_factory=list[Callable[[Self], None]]
    )

    def on_change(self, hook: Callable[[Self], None]) -> None:
        """
        Register a callback invoked when this node or any of its descendants changes.

        Args:
            hook: A callable receiving the node where the hook was registered.
        """
        self._hooks.append(hook)

    def update(self, other: Self):
        """
        Update this instance to match another instance.

        Updates model without firing per-field hooks; then re-parents children and
        fires hooks once.

        Args:
            other: Another `Reactive` instance whose values replace this one.
        """
        for field in type(self).model_fields:
            object.__setattr__(self, field, getattr(other, field))

        # re-propagate parent pointers for nested Reactive objects
        propagate_parent(self, self)

        self._call_hooks()

    def __setattr__(self, name: str, value: Any):
        """
        Assign a model field, re-parent children if needed, trigger hooks.
        """
        super().__setattr__(name, value)

        if name in type(self).model_fields:
            propagate_parent(self, self)
            self._call_hooks()

    def model_post_init(self, __context: Any):
        """
        Initialization hook called by Pydantic.

        Newly created object becomes its own root if not attached; propagate parent.
        """
        propagate_parent(self, self)

    def _call_hooks(self):
        """
        Call hooks on this object, then on all ancestors (root last).
        """
        node: Reactive | None = self

        while node is not None:
            for hook in node._hooks:
                hook(node)
            node = node._parent


def propagate_parent(parent: Reactive | None, value: Any) -> None:
    """
    Recursively assign parent to all nested Reactive objects.

    parent = the containing Reactive instance
    value  = the subtree being attached under parent
    """
    if isinstance(value, Reactive):
        if value is not parent:
            value._parent = parent

        for field in type(value).model_fields:
            propagate_parent(value, getattr(value, field))

    elif isinstance(value, dict):
        for item in value.values():  # type: ignore
            propagate_parent(parent, item)

    elif isinstance(value, list):
        for item in value:  # type: ignore
            propagate_parent(parent, item)
