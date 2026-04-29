# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from typing import TYPE_CHECKING

from fibsem_maestro.drift_correction.error import DriftCorrectionError

if TYPE_CHECKING:
    from fibsem_maestro.drift_correction.drift_calculation_mode import (
        DriftCalculationMode,
    )


class DriftCalculationRegistry:
    """Registry for supported drift calculation mode implementations.

    Maps string identifiers to concrete `DriftCalculationMode` subclasses.
    Registered classes can be retrieved by name and instantiated by client code.

    Attributes:
        _registry: Internal mapping from drift calculation mode names to their
            corresponding `DriftCalculationMode` subclasses.
    """

    _registry: dict[str, type["DriftCalculationMode"]] = {}

    @classmethod
    def get(cls, name: str) -> type["DriftCalculationMode"]:
        """
        Return the registered drift calculation mode class for the given name.

        Args:
            name: The name of the drift calculation mode to retrieve.

        Returns:
            The registered drift calculation mode class.

        Raises:
            DriftCorrectionError: If the given name is not registered.
        """
        if name not in cls._registry:
            raise DriftCorrectionError(
                f"Drift calculation mode '{name}' is not registered."
            )

        return cls._registry[name]

    @classmethod
    def register(
        cls, name: str
    ) -> Callable[[type["DriftCalculationMode"]], type["DriftCalculationMode"]]:
        """
        Decorator that registers a `DriftCalculationMode` subclass under a given name.

        Args:
            name: The name under which to register the drift calculation mode
                implementation.

        Returns:
            A class decorator that registers the drift calculation mode class
            and returns it unchanged.

        Raises:
            DriftCorrectionError: If the given name is already registered.
        """

        def decorator(
            control_cls: type["DriftCalculationMode"],
        ) -> type["DriftCalculationMode"]:
            if name in cls._registry:
                raise DriftCorrectionError(
                    f"Drift calculation mode '{name}' is already registered."
                )

            cls._registry[name] = control_cls
            return control_cls

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a drift calculation mode name is registered.

        Args:
            name: The drift calculation mode name to check.

        Returns:
            `True` if the name is registered, `False` otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered drift calculation mode names.

        Returns:
            A list of drift calculation mode names currently registered.
        """
        return list(cls._registry)
