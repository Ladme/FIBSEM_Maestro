# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.error import AutofunctionError

SweepingSpaceFunction = Callable[
    [float, tuple[float, float], int, int], NDArray[np.floating]
]


class SweepingRegistry:
    """
    Registry for sweeping space generation functions.

    The registry stores functions that generate sweeping spaces for microscope
    auto-functions. Each registered function defines how candidate parameter
    values are generated around a base value (e.g., linear, zig-zag, interleaved).

    Each sweeping function must have the signature:

        (base: float,
         sweep_range: tuple[float, float],
         steps: int,
         repetition: int) -> NDArray[np.floating]

    Example:

        @SweepingRegistry.register("basic")
        def basic_sweep(base, sweep_range, steps, repetition):
            ...

        sweep_fn = SweepingRegistry.get("basic")
        values = sweep_fn(base, sweep_range, steps, repetition)

    Attributes:
        _registry (dict[str, SweepingSpaceFunction]):
            Internal dictionary mapping sweeping strategy names to their functions.
    """

    _registry: dict[str, SweepingSpaceFunction] = {}

    @classmethod
    def get(cls, name: str) -> SweepingSpaceFunction:
        """
        Return the registered sweeping function associated with the given name.

        Args:
            name (str): The name of the sweeping strategy to retrieve.

        Returns:
            SweepingSpaceFunction:
                The corresponding registered sweeping space function.

        Raises:
            AutofunctionError:
                If the given name is not registered.
        """
        if name not in cls._registry:
            raise AutofunctionError(f"Sweeping strategy '{name}' is not registered.")

        return cls._registry[name]

    @classmethod
    def register(
        cls, name: str
    ) -> Callable[[SweepingSpaceFunction], SweepingSpaceFunction]:
        """
        Decorator that registers a sweeping space function under a given name.

        Args:
            name (str):
                The name under which to register the sweeping strategy.

        Returns:
            Callable[[SweepingSpaceFunction], SweepingSpaceFunction]:
                A decorator that registers the function and returns it unchanged.

        Raises:
            AutofunctionError:
                If a sweeping strategy with the given name is already registered.
        """

        def decorator(
            sweeping_cls: SweepingSpaceFunction,
        ) -> SweepingSpaceFunction:
            if name in cls._registry:
                raise AutofunctionError(
                    f"Sweeping strategy '{name}' is already registered."
                )

            cls._registry[name] = sweeping_cls
            return sweeping_cls

        return decorator

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a sweeping strategy name is registered.

        Args:
            name (str): The name to check.

        Returns:
            bool:
                True if the sweeping strategy is registered, False otherwise.
        """
        return name in cls._registry

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return a list of all registered sweeping strategy names.

        Returns:
            list[str]:
                A list of sweeping strategy names currently registered.
        """
        return list(cls._registry)
