# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
import pytest
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.error import AutofunctionError
from fibsem_maestro.autofunctions.result import AutofocusResult
from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry
from fibsem_maestro.autofunctions.sweeping_strategy import (
    BasicSweepingStrategy,
    InterleavedSweepingStrategy,
)
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    InterleavedStrategySettings,
)


@pytest.mark.parametrize(
    "repetition, expected",
    [
        (0, np.array([9.0, 10.0, 11.0])),  # even -> low to high
        (2, np.array([9.0, 10.0, 11.0])),  # even -> low to high
        (1, np.array([11.0, 10.0, 9.0])),  # odd  -> high to low
        (3, np.array([11.0, 10.0, 9.0])),  # odd  -> high to low
    ],
)
def test_basic_sweeping_strategy_generate_zigzag(
    repetition: int, expected: NDArray[np.floating]
):
    out = BasicSweepingStrategy(BasicStrategySettings()).generate(
        10.0, (-1.0, 1.0), 3, repetition
    )
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, expected)


def test_basic_sweeping_strategy_evaluate_simple():
    strategy = BasicSweepingStrategy(BasicStrategySettings())

    results = [
        AutofocusResult(resolution=10.0, sweep_value=1.0, sweep_index=0),
        AutofocusResult(resolution=11.0, sweep_value=3.0, sweep_index=2),
        AutofocusResult(resolution=12.0, sweep_value=2.0, sweep_index=1),
    ]

    best = strategy.evaluate(results)
    assert best == 2.0


def test_basic_sweeping_strategy_evaluate_groups_by_sweep_value():
    strategy = BasicSweepingStrategy(BasicStrategySettings())

    results = [
        AutofocusResult(resolution=13.0, sweep_value=2.0, sweep_index=2),
        AutofocusResult(resolution=13.0, sweep_value=2.0, sweep_index=3),
        AutofocusResult(resolution=10.0, sweep_value=1.0, sweep_index=0),
        AutofocusResult(resolution=14.0, sweep_value=1.0, sweep_index=1),
    ]

    best = strategy.evaluate(results)
    assert best == 2.0


def test_basic_sweeping_strategy_evaluate_raises_on_empty_results():
    strategy = BasicSweepingStrategy(BasicStrategySettings())

    with pytest.raises(AutofunctionError, match="No autofocus results provided"):
        strategy.evaluate([])


def test_basic_sweep_space_matches_registry_entry():
    obj = SweepingRegistry.get("basic")
    assert obj is BasicSweepingStrategy


def test_basic_interleaved_sweeping_strategy_generate_forces_even_steps():
    # steps=5 -> forced to 4 -> output length should be 2*4 = 8
    out = InterleavedSweepingStrategy(
        InterleavedStrategySettings(min_diff=0.1)
    ).generate(10.0, (-1.0, 1.0), 5, 0)
    assert isinstance(out, np.ndarray)
    assert len(out) == 8


@pytest.mark.parametrize("repetition", [0, 1, 7])
def test_basic_interleaved_sweeping_strategy_generate_ignores_repetition(
    repetition: int,
):
    base = 10.0
    r = (-1.0, 1.0)
    steps = 6

    out0 = InterleavedSweepingStrategy(
        InterleavedStrategySettings(min_diff=0.1)
    ).generate(base, r, steps, 0)
    outx = InterleavedSweepingStrategy(
        InterleavedStrategySettings(min_diff=0.1)
    ).generate(base, r, steps, repetition)

    assert np.allclose(out0, outx)


def test_basic_interleaved_sweeping_strategy_generate_interleaves_base_and_sweep_values():
    base = 10.0
    r = (-1.0, 1.0)
    steps = 4  # already even; output length 8

    sweep = np.linspace(base + r[0], base + r[1], steps)
    out = InterleavedSweepingStrategy(
        InterleavedStrategySettings(min_diff=0.1)
    ).generate(base, r, steps, 123)

    # even indices are base
    assert np.allclose(out[0::2], np.full(steps, base))
    # odd indices are the sweep values
    assert np.allclose(out[1::2], sweep)


def test_interleaved_sweeping_strategy_evaluate_raises_on_too_few_results():
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.1))

    with pytest.raises(
        AutofunctionError,
        match="Need at least two results to compute delta resolutions",
    ):
        strategy.evaluate(
            [AutofocusResult(resolution=10.0, sweep_value=1.0, sweep_index=0)]
        )


def test_interleaved_sweeping_strategy_evaluate_simple():
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.1))

    results = [
        AutofocusResult(resolution=10.0, sweep_value=10.0, sweep_index=0),  # baseline
        AutofocusResult(resolution=12.0, sweep_value=11.0, sweep_index=1),  # candidate
    ]

    best = strategy.evaluate(results)
    assert best == 11.0


def test_interleaved_sweeping_strategy_evaluate_multiple_pairs_and_sorts_by_sweep_index():
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.1))

    results = [
        AutofocusResult(resolution=13.0, sweep_value=12.0, sweep_index=3),  # candidate
        AutofocusResult(resolution=10.0, sweep_value=10.0, sweep_index=2),  # baseline
        AutofocusResult(resolution=12.0, sweep_value=11.0, sweep_index=1),  # candidate
        AutofocusResult(resolution=10.0, sweep_value=10.0, sweep_index=0),  # baseline
    ]

    best = strategy.evaluate(results)
    assert best == 12.0


def test_interleaved_sweeping_strategy_evaluate_multiple_pairs_discards_some():
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.1))

    results = [
        AutofocusResult(resolution=13.0, sweep_value=12.0, sweep_index=3),  # candidate
        AutofocusResult(resolution=10.0, sweep_value=10.0, sweep_index=2),  # baseline
        AutofocusResult(resolution=12.0, sweep_value=11.0, sweep_index=1),  # candidate
        AutofocusResult(resolution=10.0, sweep_value=10.0, sweep_index=0),  # baseline
        AutofocusResult(
            resolution=8.0, sweep_value=12.0, sweep_index=5
        ),  # candidate (discarded)
        AutofocusResult(resolution=11.0, sweep_value=10.0, sweep_index=4),  # baseline
    ]

    best = strategy.evaluate(results)
    assert best == 12.0


def test_interleaved_sweeping_strategy_evaluate_falls_back_to_baseline():
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.1))

    results = [
        AutofocusResult(resolution=100.0, sweep_value=10.0, sweep_index=0),  # baseline
        AutofocusResult(
            resolution=105.0, sweep_value=11.0, sweep_index=1
        ),  # candidate (discard)
        AutofocusResult(resolution=100.0, sweep_value=10.0, sweep_index=2),  # baseline
        AutofocusResult(
            resolution=109.0, sweep_value=12.0, sweep_index=3
        ),  # candidate (discard)
    ]

    best = strategy.evaluate(results)
    assert best == 10.0


def test_basic_interleaved_sweeping_strategy_generate_matches_registry_entry():
    obj = SweepingRegistry.get("interleaved")
    assert obj is InterleavedSweepingStrategy
