# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
import pytest
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.sweeping_functions import (
    basic_interleaved_sweep_space,
    basic_sweep_space,
)
from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry


@pytest.mark.parametrize(
    "repetition, expected",
    [
        (0, np.array([9.0, 10.0, 11.0])),  # even -> low to high
        (2, np.array([9.0, 10.0, 11.0])),  # even -> low to high
        (1, np.array([11.0, 10.0, 9.0])),  # odd  -> high to low
        (3, np.array([11.0, 10.0, 9.0])),  # odd  -> high to low
    ],
)
def test_basic_sweep_space_zigzag(repetition: int, expected: NDArray[np.floating]):
    out = basic_sweep_space(10.0, (-1.0, 1.0), 3, repetition)
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, expected)


def test_basic_sweep_space_matches_registry_entry():
    fn = SweepingRegistry.get("basic")
    assert fn is basic_sweep_space


def test_basic_interleaved_sweep_space_forces_even_steps():
    # steps=5 -> forced to 4 -> output length should be 2*4 = 8
    out = basic_interleaved_sweep_space(10.0, (-1.0, 1.0), 5, 0)
    assert isinstance(out, np.ndarray)
    assert len(out) == 8


@pytest.mark.parametrize("repetition", [0, 1, 7])
def test_basic_interleaved_sweep_space_ignores_repetition(repetition: int):
    base = 10.0
    r = (-1.0, 1.0)
    steps = 6

    out0 = basic_interleaved_sweep_space(base, r, steps, 0)
    outx = basic_interleaved_sweep_space(base, r, steps, repetition)

    assert np.allclose(out0, outx)


def test_basic_interleaved_sweep_space_interleaves_base_and_sweep_values():
    base = 10.0
    r = (-1.0, 1.0)
    steps = 4  # already even; output length 8

    sweep = np.linspace(base + r[0], base + r[1], steps)
    out = basic_interleaved_sweep_space(base, r, steps, 123)

    # even indices are base
    assert np.allclose(out[0::2], np.full(steps, base))
    # odd indices are the sweep values
    assert np.allclose(out[1::2], sweep)


def test_basic_interleaved_matches_registry_entry():
    fn = SweepingRegistry.get("basic_interleaved")
    assert fn is basic_interleaved_sweep_space
