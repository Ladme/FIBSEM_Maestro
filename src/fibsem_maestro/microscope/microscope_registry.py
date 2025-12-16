# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fibsem_maestro.microscope.abstract_control.microscope_control import (
        MicroscopeControl,
    )
from fibsem_maestro.microscope.error import MicroscopeError


class MicroscopeRegistry:
    """
    Registry for supported microscope control implementations.

    The registry maps string identifiers to concrete `MicroscopeControl` subclasses.
    Registered microscope classes can be retrieved by name and instantiated by client code.

    Attributes:
        _registry (dict[str, type[MicroscopeControl]]):
            Internal mapping from microscope names to their corresponding
            `MicroscopeControl` subclasses.
    """

    _registry: dict[str, type["MicroscopeControl"]] = {}

    @classmethod
    def get(cls, name: str) -> type["MicroscopeControl"]:
        """
        Return the registered microscope control class for the given name.

        Args:
            name (str): The name of the microscope type to retrieve.

        Returns:
            type[MicroscopeControl]: The registered microscope control class.

        Raises:
            MicroscopeError: If the given name is not registered.
        """
        if name not in cls._registry:
            raise MicroscopeError(f"Microscope '{name}' is not registered.")

        return cls._registry[name]

    @classmethod
    def register(
        cls, name: str
    ) -> Callable[[type["MicroscopeControl"]], type["MicroscopeControl"]]:
        """
        Decorator that registers a `MicroscopeControl` subclass under a given name.

        Args:
            name (str): The name under which to register the microscope control
                implementation.

        Returns:
            Callable[[type[MicroscopeControl]], type[MicroscopeControl]]:
                A class decorator that registers the microscope control class
                and returns it unchanged.

        Raises:
            MicroscopeError: If the given name is already registered.
        """

        def decorator(
            control_cls: type["MicroscopeControl"],
        ) -> type["MicroscopeControl"]:
            if name in cls._registry:
                raise MicroscopeError(f"Microscope '{name}' is already registered.")

            cls._registry[name] = control_cls
            return control_cls

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a microscope name is registered.

        Args:
            name (str): The microscope name to check.

        Returns:
            bool: True if the microscope name is registered, False otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered microscope names.

        Returns:
            list[str]: A list of microscope names currently registered.
        """
        return list(cls._registry)
