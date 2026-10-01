# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from collections.abc import Callable, Hashable, Iterable
from typing import Any, Generic, Self, SupportsIndex, TypeVar

from pydantic import BaseModel, PrivateAttr
from pydantic_core import core_schema


class ReactiveNode:
    """
    Base class providing shared reactive behavior for models and containers.

    A `ReactiveNode` participates in a hierarchical tree of reactive objects.
    Each node maintains:

    - A reference to its parent node (which is `None` if it is the root)
    - A list of change hooks (callbacks) that should fire when the node or any
      of its reactive descendants is modified
    """

    _parent: ReactiveNode | None
    _hooks: list[Callable[[Self], None]]

    def __init__(self):
        """
        Initialize the reactive node.

        Sets up empty hook storage and ensures that the node begins with no parent.
        Subclasses should call this explicitly if they override `__init__`.
        """
        self._hooks = []
        self._parent = None

    def on_change(self, hook: Callable[[Self], None]):
        """
        Register a callback invoked when this node or any of its reactive descendants changes.

        Args:
            hook: A callable receiving the node where the hook was registered.
        """
        self._hooks.append(hook)

    def _call_hooks(self) -> None:
        """Invoke hooks on this node and all ancestor nodes, bottom-up."""
        node: ReactiveNode | None = self
        while node is not None:
            node._call_local_hooks()
            node = node._parent

    def _call_local_hooks(self) -> None:
        """Invoke hooks registered on this node only, without notifying ancestors."""
        for hook in self._hooks:
            hook(self)


class ReactiveModel(BaseModel, ReactiveNode):
    """
    Pydantic model with hierarchical reactive behavior.

    `ReactiveModel` extends `BaseModel` by integrating with the `ReactiveNode`
    event system. Each instance participates in a tree of reactive objects,
    allowing changes deep within nested structures to trigger callbacks on
    parent nodes.
    """

    _hooks: list[Callable] = PrivateAttr(default_factory=list)
    _parent: ReactiveNode | None = PrivateAttr(default=None)

    def __init__(self, **data: Any):
        """
        Initialize a reactive Pydantic model.

        After initialization, `model_post_init` will attach appropriate parent
        relationships for any reactive children.

        Args:
            data:
                The field values to populate the Pydantic model with.
        """
        # run pydantic
        super().__init__(**data)

    def update(self, other: Self):
        """
        Update this instance to match another instance.

        Updates model without firing per-field hooks; then re-parents children and
        fires hooks once.

        Args:
            other: Another `ReactiveModel` instance whose values replace this one.
        """
        for field in type(self).model_fields:
            object.__setattr__(self, field, getattr(other, field))

        # re-propagate parent pointers for nested Reactive objects
        propagate_parent(self, self)

        self._call_hooks()

    def patch(self, other: Self) -> None:
        """
        Partially update this instance from another, skipping None fields.

        Only fields that are not None in `other` are applied to `self`.
        Fields that are None in `other` retain their current value. Nested
        reactive models are patched in place, so their identity and their
        registered hooks are preserved.

        Hooks on each patched node fire exactly once, and the ancestor chain
        is notified exactly once, regardless of nesting depth.

        Args:
            other: Another instance whose non-None values replace this one's.

        Raises:
            ValueError: If a nested field is None on `self` and the
                corresponding model on `other` cannot be constructed from
                defaults.
        """
        patched = self._patch_fields(other)

        propagate_parent(self, self)

        for node in patched:
            node._call_local_hooks()
        self._call_hooks()

    def _patch_fields(self, other: Self) -> list[ReactiveModel]:
        """
        Apply non-None fields of `other` to `self` without firing any hooks.

        Nested models already present on `self` are patched in place, keeping
        their identity and hooks. Everything else is copied, so `self` and
        `other` never share reactive state.

        Returns:
            The nested models that were patched in place, excluding `self`,
            in depth-first order.
        """
        patched: list[ReactiveModel] = []

        for field in type(self).model_fields:
            value = getattr(other, field)
            if value is None:
                continue

            if isinstance(value, ReactiveModel):
                current = getattr(self, field)
                if current is None:
                    # nothing to patch into, and nothing is subscribed to it yet
                    object.__setattr__(self, field, _reactive_copy(value))
                    continue
                patched.append(current)
                patched.extend(current._patch_fields(value))
            else:
                object.__setattr__(self, field, _reactive_copy(value))

        return patched

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

    def __eq__(self, other: object) -> bool:
        """
        Compare by field values, ignoring reactive bookkeeping.

        Pydantic's default compares private attributes too, which for a
        reactive model means comparing `_parent` - and that walks back up to
        the object being compared, recursing without end. Registered hooks are
        likewise not part of a model's value.

        Args:
            other: The object to compare against.

        Returns:
            True if `other` is the same class and holds equal field values.
        """
        if other.__class__ is not self.__class__:
            return NotImplemented

        return (
            self.__dict__ == other.__dict__
            and self.__pydantic_extra__ == other.__pydantic_extra__
        )


K = TypeVar("K", bound=Hashable)
T = TypeVar("T", bound=Any)


class ReactiveDict(dict[K, T], ReactiveNode, Generic[K, T]):
    """
    A reactive dictionary that behaves like a standard Python dictionary,
    but integrates with the reactive event system provided by `ReactiveNode`.
    """

    def __init__(self, *args: Any, **kwargs: T):
        """
        Initialize the reactive dictionary and attach parent pointers to all reactive values.
        """
        ReactiveNode.__init__(self)
        dict.__init__(self, *args, **kwargs)
        for v in self.values():
            if isinstance(v, ReactiveNode):
                propagate_parent(self, v)

    def __setitem__(self, key: Any, value: T):
        """
        Insert or replace a value, then propagate reactive state and fire hooks.

        Args:
            key:
                The key to modify.
            value:
                A value to store under the given key.
        """
        super().__setitem__(key, value)
        if isinstance(value, ReactiveNode):
            propagate_parent(self, value)
        self._call_hooks()

    def update(self, *args: Any, **kwargs: T):
        """
        Update the dictionary with multiple key/value pairs and trigger one event.
        """
        super().update(*args, **kwargs)
        for v in self.values():
            if isinstance(v, ReactiveNode):
                propagate_parent(self, v)
        self._call_hooks()

    def pop(self, key: Any, *a: Any) -> T:
        """
        Remove a key/value pair and trigger reactive hooks.
        """
        res = super().pop(key, *a)
        self._call_hooks()
        return res

    def clear(self) -> None:
        """
        Remove all items from the dictionary and fire reactive hooks.
        """
        super().clear()
        self._call_hooks()

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any):
        """
        Integrate ReactiveDict with pydantic.
        """
        # use the standard Python schema for dicts
        return core_schema.no_info_plain_validator_function(cls)


class ReactiveList(list[T], ReactiveNode, Generic[T]):
    """
    A reactive list that behaves like a standard Python list
    but integrates with the reactive event system provided by `ReactiveNode`.
    """

    def __init__(self, iterable: Iterable[T] = ()):
        """
        Initialize the reactive list and attach parent pointers to all reactive items.
        """
        ReactiveNode.__init__(self)
        list.__init__(self, iterable)
        for item in self:
            if isinstance(item, ReactiveNode):
                propagate_parent(self, item)

    def append(self, value: T) -> None:
        """
        Append an item to the end of the list.
        """
        super().append(value)
        if isinstance(value, ReactiveNode):
            propagate_parent(self, value)
        self._call_hooks()

    def extend(self, values: Iterable[T]) -> None:
        """
        Extend the list by appending multiple items.
        """
        super().extend(values)
        for v in values:
            if isinstance(v, ReactiveNode):
                propagate_parent(self, v)
        self._call_hooks()

    def insert(self, index: SupportsIndex, value: T) -> None:
        """
        Insert an item at a specific index.
        """
        super().insert(index, value)
        if isinstance(value, ReactiveNode):
            propagate_parent(self, value)
        self._call_hooks()

    def __setitem__(self, idx: Any, value: Any) -> None:
        """
        Assign to a list position or slice and trigger reactive propagation.
        """
        super().__setitem__(idx, value)

        # basic assignment
        if isinstance(value, ReactiveNode):
            propagate_parent(self, value)
        # slice assignment
        elif isinstance(idx, slice):
            for item in self[idx]:
                if isinstance(item, ReactiveNode):
                    propagate_parent(self, item)
        self._call_hooks()

    def pop(self, *args: Any, **kwargs: Any) -> T:
        """
        Remove and return an element, while emitting a reactive event.

        Args:
            *args, **kwargs:
                Passed directly to `list.pop`.

        Returns:
            The removed reactive element.
        """
        result = super().pop(*args, **kwargs)
        self._call_hooks()
        return result

    def remove(self, value: T) -> None:
        """
        Remove the first occurrence of a reactive element and emit a reactive event.

        Args:
            value:
                The `ReactiveNode` instance to remove.
        """
        super().remove(value)
        self._call_hooks()

    def clear(self) -> None:
        """
        Remove all elements from the list and fire a single reactive event.
        """
        super().clear()
        self._call_hooks()

    @classmethod
    def __get_pydantic_core_schema__(cls, source: Any, handler: Any):
        """
        Integrate ReactiveList with pydantic.
        """
        # use the standard Python schema for lists
        return core_schema.no_info_plain_validator_function(cls)


def propagate_parent(parent: ReactiveNode, value: Any):
    """
    Recursively assign parent pointers for nested reactive objects.

    Args:
        parent: The node that should be set as the parent.
        value: The reactive object or container being attached.
    """
    if isinstance(value, ReactiveModel):
        if value is not parent:
            value._parent = parent
        for field in type(value).model_fields:
            propagate_parent(value, getattr(value, field))

    elif isinstance(value, ReactiveList):
        value._parent = parent
        for item in value:
            propagate_parent(value, item)

    elif isinstance(value, ReactiveDict):
        value._parent = parent
        for item in value.values():
            propagate_parent(value, item)

    elif isinstance(value, ReactiveNode):
        value._parent = parent


def _reactive_copy(value: Any) -> Any:
    """
    Return a copy of a reactive value that shares no state with the original.

    Reactive models and containers are rebuilt so the copy has its own hooks
    and parent pointer; every other value is returned unchanged. Models are
    rebuilt with `model_construct`, which skips validation - callers must pass
    values that have already been validated.

    Args:
        value: The value to copy.

    Returns:
        An independent copy for reactive models and containers, otherwise the value itself.
    """
    if isinstance(value, ReactiveModel):
        return type(value).model_construct(
            **{
                name: _reactive_copy(getattr(value, name))
                for name in type(value).model_fields
            }
        )
    if isinstance(value, ReactiveList):
        return type(value)(_reactive_copy(item) for item in value)
    if isinstance(value, ReactiveDict):
        return type(value)({key: _reactive_copy(v) for key, v in value.items()})
    return value
