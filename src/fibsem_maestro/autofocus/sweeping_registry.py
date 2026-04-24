# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.autofocus.error import AutofocusError

if TYPE_CHECKING:
    from fibsem_maestro.autofocus.sweeping_strategy import SweepingStrategy

SweepingSpaceFunction = Callable[
    [float, tuple[float, float], int, int], NDArray[np.floating]
]


class SweepingRegistry:
    """
    Registry for supported sweeping strategy implementations.

    The registry maps string identifiers to concrete `SweepingStrategy` subclasses.
    Registered sweeping strategy classes can be retrieved by name and instantiated by client code.

    Attributes:
        _registry (dict[str, type[SweepingStrategy]]):
            Internal mapping from sweeping strategy names to their corresponding
            `SweepingStrategy` subclasses.
    """

    _registry: dict[str, type["SweepingStrategy"]] = {}

    @classmethod
    def get(cls, name: str) -> type["SweepingStrategy"]:
        """
        Return the registered sweeping strategy class for the given name.

        Args:
            name (str): The name of the sweeping strategy to retrieve.

        Returns:
            type[SweepingStrategy]: The registered sweeping strategy class.

        Raises:
            AutofocusError: If the given name is not registered.
        """
        if name not in cls._registry:
            raise AutofocusError(f"Sweeping strategy '{name}' is not registered.")

        return cls._registry[name]

    @classmethod
    def register(
        cls, name: str
    ) -> Callable[[type["SweepingStrategy"]], type["SweepingStrategy"]]:
        """
        Decorator that registers a `SweepingStrategy` subclass under a given name.

        Args:
            name (str): The name under which to register the sweeping strategy
                implementation.

        Returns:
            Callable[[type[SweepingStrategy]], type[SweepingStrategy]]:
                A class decorator that registers the sweeping strategy class
                and returns it unchanged.

        Raises:
            AutofocusError: If the given name is already registered.
        """

        def decorator(
            control_cls: type["SweepingStrategy"],
        ) -> type["SweepingStrategy"]:
            if name in cls._registry:
                raise AutofocusError(
                    f"Sweeping strategy '{name}' is already registered."
                )

            cls._registry[name] = control_cls
            return control_cls

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a name of a sweeping strategy is registered.

        Args:
            name (str): The sweeping strategy name to check.

        Returns:
            bool: True if the sweeping strategy name is registered, False otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered sweeping strategy names.

        Returns:
            list[str]: A list of sweeping strategy names currently registered.
        """
        return list(cls._registry)
