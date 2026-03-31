# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from collections import defaultdict

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.autofocus.error import AutofunctionError
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweeping_registry import SweepingRegistry
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    InterleavedStrategySettings,
    SweepingStrategySettings,
)


class SweepingStrategy(ABC):
    """
    Abstract base class for autofocus sweeping strategies.

    A sweeping strategy is responsible for:
      - Generating a sequence of sweep values to test.
      - Evaluating autofocus results produced from those sweep values
         and selecting the best parameter value.
    """

    @abstractmethod
    def __init__(self, settings: SweepingStrategySettings):
        """
        Initialize the sweeping strategy.

        Args:
            settings (SweepingStrategySettings):
                Strategy-specific configuration parameters.
        """
        pass

    @abstractmethod
    def generate(
        self, base: float, range: tuple[float, float], steps: int, repetition: int
    ) -> NDArray[np.floating]:
        """
        Generate a sweep space using the given strategy.

        Args:
            base (float):
                The base (current) value of the parameter being swept.
            range (tuple[float, float]):
                Relative sweep range `(min_offset, max_offset)` applied to the base.
            steps (int):
                Number of sweep points to generate.
            repetition (int):
                Sweep repetition index, used by some strategies to modify
                sweep ordering (e.g. zig-zag behavior).

        Returns:
            NDArray[np.floating]:
                A NumPy array of sweep values.
        """
        pass

    @abstractmethod
    def evaluate(self, results: list[AutofocusResult]) -> float:
        """
        Evaluate autofocus results and select the best sweep value.

        Args:
            results (list[AutofocusResult]):
                Measured resolutions.

        Returns:
            float:
                The sweep value determined to be optimal by the strategy.
        """
        pass


@SweepingRegistry.register("basic")
class BasicSweepingStrategy(SweepingStrategy):
    """
    Basic linear sweeping strategy.
    """

    def __init__(self, settings: BasicStrategySettings):
        self._settings = settings

    def generate(
        self, base: float, range: tuple[float, float], steps: int, repetition: int
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
            return np.linspace(base + range[0], base + range[1], steps)

        return np.linspace(base + range[1], base + range[0], steps)

    def evaluate(self, results: list[AutofocusResult]) -> float:
        """
        Evaluate autofocus results by selecting the sweep value with the
        highest mean resolution.

        All results corresponding to the same sweep value are grouped,
        their resolutions are averaged, and the sweep value with the
        highest mean resolution is selected.

        Args:
            results (list[AutofocusResult]):
                Measured resolutions.

        Returns:
            float:
                The sweep value with the highest mean resolution.

        Raises:
            AutofunctionError:
                If no autofocus results are provided.
        """
        resolution_sum: dict[float, float] = defaultdict(float)
        resolution_count: dict[float, int] = defaultdict(int)

        # collect resolutions obtained for the same sweep value
        for r in results:
            resolution_sum[r.sweep.value] += r.sharpness
            resolution_count[r.sweep.value] += 1

        if not resolution_sum:
            raise AutofunctionError("No autofocus results provided")

        # calculate mean resolution for each sweep value
        mean_by_sweep = {
            sweep: resolution_sum[sweep] / resolution_count[sweep]
            for sweep in resolution_sum
        }

        # select the sweep value with the highest mean resolution
        return max(mean_by_sweep, key=lambda k: mean_by_sweep[k])


@SweepingRegistry.register("interleaved")
class InterleavedSweepingStrategy(SweepingStrategy):
    """
    Interleaved sweeping strategy with baseline values.
    """

    def __init__(self, settings: InterleavedStrategySettings):
        self._settings = settings

    def generate(
        self, base: float, range: tuple[float, float], steps: int, repetition: int
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

    def evaluate(self, results: list[AutofocusResult]) -> float:
        """
        Evaluate autofocus results using baseline-relative resolution improvements.

        For each candidate, the resolution improvement relative to the
        preceding baseline is computed. Only improvements exceeding a
        minimum relative threshold are considered.

        Args:
            results (list[AutofocusResult]):
                Measured resolutions.

        Returns:
            float:
                The sweep value with the highest mean resolution improvement.
                If no sweep value shows a significant improvement, the
                baseline sweep value is returned.

        Raises:
            AutofunctionError:
                If fewer than two results are provided.
        """
        # sort results based on sweep index so that each result can
        # be compared to an immediately preceeding result
        sorted_results = sorted(results, key=lambda r: r.sweep.index)

        if len(sorted_results) < 2:
            raise AutofunctionError(
                "Need at least two results to compute delta resolutions."
            )

        delta_sum: dict[float, float] = defaultdict(float)
        delta_count: dict[float, int] = defaultdict(int)

        # iterate over consecutive (baseline, candidate) result pairs
        for base, curr in zip(sorted_results[:-1], sorted_results[1:]):
            # calculate resolution improvement relative to the preceding baseline
            delta = curr.sharpness - base.sharpness

            # keep only improvements that exceed the minimum relative threshold
            if delta > base.sharpness * self._settings.min_diff:
                delta_sum[curr.sweep.value] += delta
                delta_count[curr.sweep.value] += 1

        # if no sweep value produced a significant improvement over its baseline, fall back to base
        if not delta_sum:
            return sorted_results[0].sweep.value

        # calculate mean resolution for each sweep value
        mean_delta_by_sweep = {
            sweep: delta_sum[sweep] / delta_count[sweep] for sweep in delta_sum
        }

        # select the sweep value with the highest mean resolution improvement
        return max(mean_delta_by_sweep, key=lambda k: mean_delta_by_sweep[k])
