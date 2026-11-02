# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.autofocus import InterleavedSweepingStrategy
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.settings.sweeping_settings import InterleavedStrategySettings


def _interleaved_results(
    values: list[float], sharpness: dict[float, float]
) -> list[AutofocusResult]:
    return [
        AutofocusResult(sharpness[v], SweepStep(0, v, i)) for i, v in enumerate(values)
    ]


def test_interleaved_min_diff_is_an_absolute_sharpness_difference() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.5))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    # +2 beats the base by 0.4 (< min_diff) although that is 4 % of the base
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 10.4}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 0.0
    # +2 beats the base by 0.6 (> min_diff) although that is only 0.06 % of the base
    sharpness = {0.0: 1000.0, -2.0: 2.0, 2.0: 1000.6}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 2.0
