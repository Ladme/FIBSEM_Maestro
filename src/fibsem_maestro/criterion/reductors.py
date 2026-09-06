# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

import inspect
from collections.abc import Callable

import numpy as np

from fibsem_maestro.core.registry import Registry

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


# registry of reduction functions
REDUCTORS = Registry[NumpyFunction]("reduction function")

for _name in dir(np):
    _attr = getattr(np, _name)
    if callable(_attr) and has_numpy_reduction_signature(_attr):
        REDUCTORS.add(_name, _attr)
