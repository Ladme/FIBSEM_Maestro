# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry


@SweepingRegistry.register("basic")
def basic_sweep_space(
    base: float, range: tuple[float, float], steps: int, repetition: int
) -> NDArray[np.floating]:
    """
    Generate a basic linear sweep space using a zig-zag pattern.

    This sweeping strategy produces a linearly spaced sequence of values
    around a base value. The sweep direction alternates between repetitions
    to reduce bias from time-dependent drift:

    - Even repetitions sweep from low to high values.
    - Odd repetitions sweep from high to low values.

    Args:
        base (float):
            The base (current) value of the parameter being swept.
        range (tuple[float, float]):
            Relative sweep range `(min_offset, max_offset)` applied to the base.
        steps (int):
            Number of sweep points to generate.
        repetition (int):
            Index of the current sweep repetition, used to determine sweep
            direction (zig-zag behavior).

    Returns:
        NDArray[np.floating]:
            A NumPy array of linearly spaced sweep values.
    """
    if repetition % 2 == 0:
        sweep_space = np.linspace(base + range[0], base + range[1], steps)
    else:
        sweep_space = np.linspace(base + range[1], base + range[0], steps)

    return sweep_space


@SweepingRegistry.register("basic_interleaved")
def basic_interleaved_sweep_space(
    base: float, range: tuple[float, float], steps: int, repetition: int
) -> NDArray[np.floating]:
    """
    Generate an interleaved sweep space with baseline values.

    This sweeping strategy generates a linear sweep around a base value and
    interleaves the base value between every sweep point:

        [base, s0, base, s1, base, s2, ...]

    The repetition index is ignored. To ensure clean interleaving, the number
    of sweep steps is forced to be even.

    Args:
        base (float):
            The base (current) value of the parameter being swept.
        range (tuple[float, float]):
            Relative sweep range `(min_offset, max_offset)` applied to the base.
        steps (int):
            Number of sweep points to generate. If odd, it is reduced by one
            to allow clean interleaving.
        repetition (int):
            Sweep repetition index (ignored by this strategy).

    Returns:
        NDArray[np.floating]:
            A NumPy array of interleaved base and sweep values.
    """
    _ = repetition

    # force an even number of steps for clean base-value interleaving
    if steps % 2 == 1:
        steps -= 1

    sweep_space = np.linspace(base + range[0], base + range[1], steps)

    interleave = np.ones(len(sweep_space)) * base

    # merge arrays in interleaved fashion
    return np.dstack((interleave, sweep_space)).reshape(-1)
