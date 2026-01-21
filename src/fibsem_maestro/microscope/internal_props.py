# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import builtins
import inspect
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any

from fibsem_maestro.microscope.error import MicroscopeError


@dataclass(frozen=True)
class InternalProperty:
    """
    Represents a writable property on a specific object instance.

    A `InternalProperty` identifies a property with a setter on an object, together
    with the member-based path from a root object to that instance.

    Attributes:
        owner (object): The object instance that owns the property.
        owner_path (str | None): Dotted path of member variable names from the
            root object to the owner. `None` if the property is on the root.
        name (str): Name of the property on the owner.
    """

    owner: object
    owner_path: str | None
    name: str

    def __str__(self) -> str:
        """
        Return the full member-based path of the property.

        Returns:
            str: Dotted path to the property (e.g. "property.property.value"),
            or just the property name if it belongs to the root object.
        """
        return f"{self.owner_path}.{self.name}" if self.owner_path else self.name

    __repr__ = __str__

    def get(self) -> Any:
        """
        Get the current value of the property.

        Returns:
            Any: The current property value.
        """
        return getattr(self.owner, self.name)

    def set(self, value: Any) -> None:
        """
        Set the value of the property.

        Args:
            value (Any): The value to assign to the property.
        """
        setattr(self.owner, self.name, value)


class InternalPropertiesRegistry:
    """
    Registry of controllable microscope internal properties.

    This registry is built from a root microscope control object (for example,
    an AutoScript microscope instance) and contains all reachable properties
    that define a setter in the underlying control library.

    Each entry represents a concrete, writable microscope property such as
    beam voltage, probe current, stage position, or detector settings. Properties
    are identified by a member-based path that reflects the microscope object
    hierarchy (e.g. "beams.electron_beam.stigmator.value").
    """

    def __init__(self, microscope: Any) -> None:
        """
        Create and populate the registry from a microscope control object.

        Args:
            microscope (Any): Root microscope object provided by the control library.
        """
        self._registry: dict[str, InternalProperty] = {}
        self._build(microscope)

    def _build(self, root: Any) -> None:
        """
        Discover and register all settable microscope properties.

        Args:
            root (Any): Root microscope object from which writable properties will be discovered.
        """
        reg: dict[str, InternalProperty] = {}
        for prop in find_custom_properties(root):
            reg[str(prop)] = prop
        self._registry = reg

    def get(self, name: str) -> InternalProperty:
        """
        Retrieve a specific settable microscope property.

        Args:
            name (str): Path to the microscope property.

        Returns:
            InternalProperty: Handle for reading or setting the microscope property.

        Raises:
            MicroscopeError: If the requested property is not available on this
                microscope instance.
        """
        if name not in self._registry:
            raise MicroscopeError(f"Internal property '{name}' is not registered.")
        return self._registry[name]

    def allowed(self) -> list[str]:
        """
        List all settable microscope properties discovered on this instance.

        Returns:
            list[str]: Sorted list of member-based proeprty paths that can be set
            through the control library.
        """
        return sorted(self._registry.keys())

    def has(self, name: str) -> bool:
        """
        Check whether a microscope property is available and settable.

        Args:
            name (str): Path to the microscope property.

        Returns:
            bool: `True` if the property is registered and can be set, `False` otherwise.
        """
        return name in self._registry


def _clean_member_name(raw_name: str, owner_cls: type) -> str:
    """
    Normalize an instance attribute name to a public member name.

    This removes Python name-mangling and strips all leading underscores so that
    member names can be used consistently in object paths.

    Examples:
        "_x" -> "x"
        "__x" -> "x"
        "_Class__x" -> "x"

    Args:
        raw_name (str): Raw attribute name as stored on the instance.
        owner_cls (type): Class of the owning instance, used to resolve
            name-mangled attributes.

    Returns:
        str: Cleaned member name without leading underscores.
    """
    # unmangle "_Class__x" -> "__x" by stripping the "_Class" part if present
    for base in inspect.getmro(owner_cls):
        prefix = f"_{base.__name__}__"
        if raw_name.startswith(prefix):
            raw_name = "__" + raw_name[len(prefix) :]
            break

    # remove all leading underscores
    return raw_name.lstrip("_")


def _iter_instance_members(obj: object) -> Iterable[tuple[str, object]]:
    """
    Iterate over member variables stored directly on an instance.

    This yields cleaned member names and their values without invoking property
    getters. Both `__dict__` attributes and `__slots__` (including name-mangled
    slots) are supported.

    Args:
        obj (object): Instance whose member variables should be inspected.

    Yields:
        tuple[str, object]: Pairs of `(member_name, value)` where `member_name`
        has no leading underscores.
    """
    owner_cls = type(obj)

    # __dict__
    d = getattr(obj, "__dict__", None)
    if isinstance(d, dict):
        for k, v in d.items():
            yield _clean_member_name(str(k), owner_cls), v

    # __slots__
    for base in inspect.getmro(owner_cls):
        slots = getattr(base, "__slots__", ())
        if not slots:
            continue
        if isinstance(slots, str):
            slots = (slots,)

        for slot in slots:
            if slot in ("__dict__", "__weakref__"):
                continue

            # access name may be mangled; declared name is `slot`
            access_name = slot
            if slot.startswith("__") and not slot.endswith("__"):
                access_name = f"_{base.__name__}{slot}"

            try:
                value = getattr(obj, access_name)
            except AttributeError:
                continue
            except Exception:
                continue

            yield _clean_member_name(slot, owner_cls), value


def _is_traversable_instance(x: object) -> bool:
    """
    Determine whether a value should be traversed as part of the object graph.

    This filters out primitives, containers, modules, functions, methods, and
    classes, leaving only user-defined object instances.

    Args:
        x (object): Value to test.

    Returns:
        bool: `True` if the value should be traversed, `False` otherwise.
    """
    if x is None:
        return False
    if isinstance(x, (str, bytes, bytearray, int, float, bool, complex)):
        return False
    if isinstance(x, (list, tuple, set, frozenset, dict)):
        return False

    return not (
        inspect.ismodule(x)
        or inspect.isfunction(x)
        or inspect.ismethod(x)
        or inspect.isclass(x)
    )


def _properties_with_setters(cls: type) -> list[str]:
    """
    Return names of properties on a class that define a setter.

    The method walks the class MRO and collects property names whose descriptors
    include a non-`None` setter function.

    Args:
        cls (type): Class to inspect.

    Returns:
        list[str]: Names of properties that have setters.
    """
    names: list[str] = []
    seen: set[str] = set()
    for base in inspect.getmro(cls):
        for name, attr in vars(base).items():
            if name in seen:
                continue
            seen.add(name)
            if isinstance(attr, builtins.property) and attr.fset is not None:
                names.append(name)
    return names


def find_custom_properties(root: object) -> list[InternalProperty]:
    """
    Discover writable properties reachable from a root object.

    The object graph is traversed through member variables only.
    Paths are constructed using member names without leading underscores
    and contain no class or type names.

    Args:
        root (object): Root object from which traversal begins.

    Returns:
        list[InternalProperty]: All discovered writable properties with their
        associated owners and member-based paths.
    """
    out: list[InternalProperty] = []
    visited: set[int] = set()
    stack: list[tuple[object, str]] = [(root, "")]  # (instance, path_of_member_names)

    while stack:
        obj, obj_path = stack.pop()
        oid = id(obj)
        if oid in visited:
            continue
        visited.add(oid)

        for prop_name in _properties_with_setters(type(obj)):
            out.append(InternalProperty(owner=obj, owner_path=obj_path, name=prop_name))

        for member_name, child in _iter_instance_members(obj):
            if _is_traversable_instance(child):
                child_path = f"{obj_path}.{member_name}" if obj_path else member_name
                stack.append((child, child_path))

    return out
