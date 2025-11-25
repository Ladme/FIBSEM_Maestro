# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import Any, Self

from pydantic import BaseModel, PrivateAttr


class Reactive(BaseModel):
    """
    Base class providing reactive behavior for Pydantic models.

    Reactive objects track changes to their fields and invoke registered hook
    functions whenever any field is modified. Hooks receive the updated instance
    as their only argument.

    Bulk updates using `update()` trigger one notification.
    """

    _hooks: list[Callable[[Self], None]] = PrivateAttr(
        default_factory=list[Callable[[Self], None]]
    )

    def on_change(self, hook: Callable[[Self], None]) -> None:
        """
        Register a callback invoked whenever the model changes.

        Args:
            hook: A callable accepting the updated model instance. It will be
                executed each time one or more model fields change.
        """
        self._hooks.append(hook)

    def update(self, other: "Reactive"):
        """
        Update this instance using values from another instance.

        All model fields are copied from `other` without triggering per-field
        change notifications. After the update completes, registered hooks are
        called once.

        Args:
            other: Another Reactive instance whose field values are copied into
                this instance.
        """
        for field in Reactive.model_fields:
            # bypass __setattr__ to avoid triggering signals per-field
            object.__setattr__(self, field, getattr(other, field))

        # hooks are called only once
        self._call_hooks()

    def __setattr__(self, name: str, value: Any):
        """
        Set an attribute and trigger change hooks when appropriate.

        Hooks are called only when `name` corresponds to a Pydantic model
        field. Private attributes and internal assignments do not trigger
        notifications.

        Args:
            name: The attribute name to set.
            value: The new value for the attribute.
        """
        # set the field as normal
        super().__setattr__(name, value)

        # call hooks only if this is actually a model field
        if name in Reactive.model_fields:
            self._call_hooks()

    def _call_hooks(self) -> None:
        """Invoke all registered change hooks."""
        for hook in self._hooks:
            hook(self)
