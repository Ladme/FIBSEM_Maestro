# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from collections import defaultdict
from typing import TYPE_CHECKING, Any

import numpy as np

from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.core.registry import Registry

if TYPE_CHECKING:
    from numpy.typing import NDArray

    from fibsem_maestro.autofocus.result import AutofocusResult
    from fibsem_maestro.settings.sweeping_settings import (
        BasicStrategySettings,
        InterleavedStrategySettings,
        SweepingStrategySettings,
    )

# registry of sweeping strategies
SWEEPING_STRATEGIES = Registry[type["SweepingStrategy"]]("sweeping strategy")


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
    ) -> NDArray[np.floating[Any]]:
        """
        Generate a sweep space using the given strategy.

        Args:
            base: The base (current) value of the parameter being swept.
            range: Relative sweep range `(min_offset, max_offset)` applied to the base.
            steps: Number of sweep points to generate.
            repetition: Sweep repetition index, used by some strategies to modify
                sweep ordering (e.g. zig-zag behavior).

        Returns:
            An array of sweep values.
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


@SWEEPING_STRATEGIES.register("basic")
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
            AutofocusError:
                If no autofocus results are provided.
        """
        resolution_sum: dict[float, float] = defaultdict(float)
        resolution_count: dict[float, int] = defaultdict(int)

        # collect resolutions obtained for the same sweep value
        for r in results:
            resolution_sum[r.sweep.value] += r.sharpness
            resolution_count[r.sweep.value] += 1

        if not resolution_sum:
            raise AutofocusError("No autofocus results provided")

        # calculate mean resolution for each sweep value
        mean_by_sweep = {
            sweep: resolution_sum[sweep] / resolution_count[sweep]
            for sweep in resolution_sum
        }

        # select the sweep value with the highest mean resolution
        return max(mean_by_sweep, key=lambda k: mean_by_sweep[k])


@SWEEPING_STRATEGIES.register("interleaved")
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

        The repetition index is ignored. Any sweep point coinciding with the base
        value is dropped to avoid redundant measurements, so the output may contain
        fewer than `2 * steps` elements.

        Args:
            base (float):
                The base (current) value of the parameter being swept.
            range (tuple[float, float]):
                Relative sweep range `(min_offset, max_offset)` applied to the base.
            steps (int):
                Number of sweep points to generate before filtering.
            repetition (int):
                Sweep repetition index (ignored by this strategy).

        Returns:
            NDArray[np.floating]:
                A NumPy array of interleaved base and sweep values.
        """
        _ = repetition

        sweep_space = np.linspace(base + range[0], base + range[1], steps)

        # drop any sweep point coinciding with base to avoid redundant measurements
        sweep_space = sweep_space[~np.isclose(sweep_space, base)]

        interleave = np.ones(len(sweep_space)) * base

        return np.dstack((interleave, sweep_space)).reshape(-1)

    def evaluate(self, results: list[AutofocusResult]) -> float:
        """
        Select the sweep value that is clearly sharper than the base around it.

        Each candidate step is compared with the mean sharpness of the nearest
        base steps before and after it, so that slow drift during the sweep
        cancels out. Results sharing a step (line mode) are averaged first. A
        candidate counts only if it beats that baseline by more than
        `min_diff` relative to it. Missing results (failed jobs) are tolerated.

        The base value is the value measured most often; ties go to the
        earliest step, which is a base step by construction.

        Args:
            results: Results collected during the sweep.

        Returns:
            The candidate with the highest mean improvement, or the base value
            if no candidate is clearly sharper.

        Raises:
            AutofocusError: If no results are provided.
        """
        if not results:
            raise AutofocusError("No autofocus results provided")

        # average the results of each sweep step (line mode yields one result per line)
        by_step: dict[int, list[AutofocusResult]] = defaultdict(list)
        for r in results:
            by_step[r.sweep.index].append(r)
        steps = sorted(by_step)
        value_of = {i: by_step[i][0].sweep.value for i in steps}
        sharpness_of = {
            i: float(np.mean([r.sharpness for r in by_step[i]])) for i in steps
        }

        # the base is measured between all candidates, so it is the most frequent value;
        # on a tie, the value measured first wins, since every sweep starts with the base
        counts: dict[float, int] = defaultdict(int)
        for i in steps:
            counts[value_of[i]] += 1
        base = max(counts, key=lambda v: (counts[v], -_first_step(value_of, v)))
        base_steps = [i for i in steps if value_of[i] == base]

        improvement_sum: dict[float, float] = defaultdict(float)
        improvement_count: dict[float, int] = defaultdict(int)
        for i in steps:
            if value_of[i] == base:
                continue

            # compare with the nearest base step on each side, so that slow drift
            # during the sweep cancels out; either may be missing (sweep end, failed job)
            before = [b for b in base_steps if b < i]
            after = [b for b in base_steps if b > i]
            neighbours = ([before[-1]] if before else []) + (
                [after[0]] if after else []
            )
            if not neighbours:
                continue

            baseline = float(np.mean([sharpness_of[b] for b in neighbours]))
            improvement = sharpness_of[i] - baseline

            # only clearly sharper candidates count; abs() keeps the threshold
            # positive for metrics that can be negative
            if improvement > abs(baseline) * self._settings.min_diff:
                # a value is measured once per cycle, so collect all of its improvements
                improvement_sum[value_of[i]] += improvement
                improvement_count[value_of[i]] += 1

        # nothing is clearly sharper: keep the base
        if not improvement_sum:
            return base

        mean_improvement = {
            v: improvement_sum[v] / improvement_count[v] for v in improvement_sum
        }
        return max(mean_improvement, key=lambda v: mean_improvement[v])


def _first_step(value_of: dict[int, float], value: float) -> int:  # module level
    """Return the first sweep step measured at `value`."""
    return min(i for i, v in value_of.items() if v == value)
