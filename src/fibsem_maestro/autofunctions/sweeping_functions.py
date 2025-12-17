# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry


@SweepingRegistry.register("basic")
def basic_sweep_space(
    base: float, range: tuple[float, float], steps: int, repetition: int
) -> NDArray[np.floating]:
    # zig-zag
    if repetition % 2 == 0:
        sweep_space = np.linspace(base + range[0], base + range[1], steps)
    else:
        sweep_space = np.linspace(base + range[1], base + range[0], steps)

    return sweep_space


@SweepingRegistry.register("basic_interleaved")
def basic_interleaved_sweep_space(
    base: float, range: tuple[float, float], steps: int, repetition: int
) -> NDArray[np.floating]:
    _ = repetition

    # force an even number of steps for clean base-value interleaving
    if steps % 2 == 1:
        steps -= 1

    sweep_space = np.linspace(base + range[0], base + range[1], steps)

    interleave = np.ones(len(sweep_space)) * base

    # merge arrays in interleaved fashion
    return np.dstack((interleave, sweep_space)).reshape(-1)
