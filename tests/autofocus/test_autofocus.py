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


def test_interleaved_picks_candidate_sharper_than_base() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    # -2 is much worse than the base, +2 is the only value sharper than the base
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 11.0}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 2.0


def test_interleaved_keeps_base_when_nothing_is_sharper() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 9.0}
    assert strategy.evaluate(_interleaved_results(values, sharpness)) == 0.0


def test_interleaved_tolerates_a_missing_result() -> None:
    strategy = InterleavedSweepingStrategy(InterleavedStrategySettings(min_diff=0.0))
    values = [float(v) for v in strategy.generate(0.0, (-2.0, 2.0), 3, 0)]
    sharpness = {0.0: 10.0, -2.0: 2.0, 2.0: 11.0}
    results = _interleaved_results(values, sharpness)
    # the job scoring the second base frame failed and was dropped
    del results[2]
    assert strategy.evaluate(results) == 2.0
