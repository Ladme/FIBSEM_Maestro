# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fibsem_maestro.autofocus.autofocus import AutofocusMode
from fibsem_maestro.autofocus.error import AutofunctionError


class AutofocusRegistry:
    """
    Registry for supported autofocus mode implementations.

    The registry maps string identifiers to concrete `AutofocusMode` subclasses.
    Registered autofocus classes can be retrieved by name and instantiated by client code.

    Attributes:
        _registry (dict[str, type[AutofocusMode]]):
            Internal mapping from autofocus names to their corresponding
            `AutofocusMode` subclasses.
    """

    _registry: dict[str, type["AutofocusMode"]] = {}

    @classmethod
    def get(cls, name: str) -> type["AutofocusMode"]:
        """
        Return the registered autofocus class for the given name.

        Args:
            name (str): The name of the autofocus mode to retrieve.

        Returns:
            type[AutofocusMode]: The registered autofocus class.

        Raises:
            AutofunctionError: If the given name is not registered.
        """
        if name not in cls._registry:
            raise AutofunctionError(f"Autofocus mode '{name}' is not registered.")

        return cls._registry[name]

    @classmethod
    def register(
        cls, name: str
    ) -> Callable[[type["AutofocusMode"]], type["AutofocusMode"]]:
        """
        Decorator that registers an `AutofocusMode` subclass under a given name.

        Args:
            name (str): The name under which to register the autofocus mode
                implementation.

        Returns:
            Callable[[type[AutofocusMode]], type[AutofocusMode]]:
                A class decorator that registers the autofocus mode class
                and returns it unchanged.

        Raises:
            AutofunctionError: If the given name is already registered.
        """

        def decorator(
            control_cls: type["AutofocusMode"],
        ) -> type["AutofocusMode"]:
            if name in cls._registry:
                raise AutofunctionError(
                    f"Autofocus mode '{name}' is already registered."
                )

            cls._registry[name] = control_cls
            return control_cls

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a name of an autofocus mode is registered.

        Args:
            name (str): The autofocus name to check.

        Returns:
            bool: True if the autofocus name is registered, False otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered autofocus names.

        Returns:
            list[str]: A list of autofocus names currently registered.
        """
        return list(cls._registry)
