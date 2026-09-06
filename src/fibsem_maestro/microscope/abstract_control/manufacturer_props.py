# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from fibsem_maestro.microscope.error import MicroscopeError


@dataclass(frozen=True)
class ManufacturerProperty:
    """
    Represents a writable property on a specific object instance.

    A `ManufacturerProperty` identifies a property with a setter on an object, together
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


class ManufacturerPropertiesRegistry(ABC):
    """
    Interface for a registry of controllable microscope manufacturer properties.

    Implementations of this interface provide access to all reachable properties
    that define a setter in the underlying microscope/beam control library.

    Each entry in the registry represents a concrete, writable microscope/beam property,
    such as beam voltage, probe current, stage position, or detector settings.
    Properties are identified by a member-based path that reflects the microscope
    object hierarchy (e.g., "beams.electron_beam.stigmator.value").

    Implementations are responsible for building the registry from a root microscope/beam
    control object (e.g., an AutoScript microscope instance).
    """

    def __init__(self, root: object) -> None:
        """
        Create and populate the registry from a microscope/beam control object.

        Args:
            root (object): Root microscope/beam object provided by the control library.
        """
        self._registry: dict[str, ManufacturerProperty] = {}
        self._build(root)

    def get(self, name: str) -> ManufacturerProperty:
        """
        Retrieve a specific settable microscope/beam property.

        Args:
            name (str): Path to the microscope/beam property.

        Returns:
            InternalProperty: Handle for reading or setting the microscope/beam property.

        Raises:
            MicroscopeError: If the requested property is not available on this
                microscope/beam instance.
        """
        if name not in self._registry:
            raise MicroscopeError(f"Manufacturer property '{name}' is not registered.")
        return self._registry[name]

    def allowed(self) -> list[str]:
        """
        List all discovered settable manufacturer properties.

        Returns:
            list[str]: Sorted list of member-based property paths that can be set
            through the control library.
        """
        return sorted(self._registry.keys())

    def has(self, name: str) -> bool:
        """
        Check whether a manufacturer property is available and settable.

        Args:
            name (str): Path to the manufacturer property.

        Returns:
            bool: `True` if the property is registered and can be set, `False` otherwise.
        """
        return name in self._registry

    @abstractmethod
    def _build(self, root: object) -> None:
        """
        Discover and register all settable microscope/beam properties.

        Args:
            root (object): Root microscope/beam object from which writable properties will be discovered.
        """
        pass
