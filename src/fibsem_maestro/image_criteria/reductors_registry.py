# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import inspect
from collections.abc import Callable

import numpy as np

from fibsem_maestro.image_criteria.error import CriterionError

NumpyFunction = Callable[..., np.floating]


def has_numpy_reduction_signature(func: NumpyFunction) -> bool:
    """
    Determine whether a NumPy function has a reduction-like signature.

    A function is considered "reduction-like" if:
      - It is callable.
      - Its name does not begin with an underscore (i.e., it is public).
      - It accepts at least one positional parameter (typically the input array).

    This heuristic matches NumPy reduction/statistics functions such as
    `np.min`, `np.max`, `np.mean`, `np.std`, `np.nanmean` etc.
    Internal/private functions (names beginning with "_") are excluded.

    Args:
        func (NumpyFunction): The function to inspect.

    Returns:
        bool: `True` if the function resembles a NumPy reduction function,
        otherwise `False`.
    """
    name = getattr(func, "__name__", "")

    if not name or name.startswith("_"):
        return False

    try:
        sig = inspect.signature(func)
    except (TypeError, ValueError):
        return False

    params = list(sig.parameters.values())

    if not params:
        return False

    # check if the first argument is positional
    first = params[0]
    return first.kind in (
        inspect.Parameter.POSITIONAL_ONLY,
        inspect.Parameter.POSITIONAL_OR_KEYWORD,
    )


class ReductorsRegistry:
    """
    Registry of NumPy functions with reduction-like signatures.

    The registry contains a subset of the public functions available in the
    top-level `numpy` namespace. Only functions that resemble typical NumPy
    reduction/statistics operations (e.g., `min`, `max`, `mean`, `nanmean`)
    are included. Detection is performed dynamically via `has_numpy_reduction_signature`.
    """

    _registry: dict[str, NumpyFunction] = {}

    @classmethod
    def get(cls, name: str) -> NumpyFunction:
        """
        Return the registered reduction function associated with the given name.

        Args:
            name (str): The name of the reduction function to retrieve.

        Returns:
            NumpyFunction: The corresponding registered reduction function.

        Raises:
            CriterionError: If the name is not present in the registry.
        """
        if name not in cls._registry:
            raise CriterionError(f"Reduction function '{name}' is not registered.")
        return cls._registry[name]

    @classmethod
    def build(cls) -> None:
        """
        Populate the registry with compatible NumPy reduction functions.

        This scans the top-level `numpy` module and registers each public
        callable that satisfies `has_numpy_reduction_signature`.

        Note:
            This method should be called once at module import time to populate
            the registry.
        """
        for name in dir(np):
            attr = getattr(np, name)
            if callable(attr) and has_numpy_reduction_signature(attr):  # type: ignore
                cls._registry[name] = attr  # type: ignore

    @classmethod
    def allowed(cls) -> list[str]:
        """
        Return all registered reduction function names.

        Returns:
            list[str]: Sorted list of available function names in the registry.
        """
        return sorted(cls._registry.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """
        Check whether a name exists in the registry.

        Args:
            name (str): Name of the reduction function.

        Returns:
            bool: `True` if the function is registered, `False` otherwise.
        """
        return name in cls._registry


# build the registry of supported reduction functions
ReductorsRegistry.build()
