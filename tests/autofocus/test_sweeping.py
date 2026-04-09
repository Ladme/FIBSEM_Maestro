# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from unittest.mock import MagicMock

import numpy as np

from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.mock.beam_control import MockBeamControl
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)


def test_construct_selects_attribute():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target="working_distance",
    )

    sweeping = Sweeping(beam, settings, txt_log)

    assert sweeping._sweep_attribute == "working_distance"
    assert sweeping.sweep_attribute == "working_distance"


def test_get_attribute_value_reads_current_beam_state():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    beam.working_distance = 5_000_000.0

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(0.0, 0.0),
        steps=1,
        cycles=1,
        target="working_distance",
    )
    sweeping = Sweeping(beam, settings, txt_log)

    assert sweeping.get_attribute_value() == 5_000_000.0


def test_set_attribute_value_sets_beam_state():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    beam.working_distance = 5_000_000.0

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(0.0, 0.0),
        steps=1,
        cycles=1,
        target="working_distance",
    )
    sweeping = Sweeping(beam, settings, txt_log)
    sweeping.set_attribute_value(1_000_000.0)

    assert beam.working_distance == 1_000_000.0


def test_sweep_yields_expected_zigzag_sequence_when_in_range():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    base = 10_000_000.0
    beam.working_distance = base

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-2000.0, 2000.0),
        steps=5,
        cycles=2,
        target="working_distance",
    )
    sweeping = Sweeping(beam, settings, txt_log)

    steps = list(sweeping.sweep())
    assert len(steps) == settings.cycles * settings.steps

    reps = [x.repetition for x in steps]
    assert reps[: settings.steps] == [0] * settings.steps
    assert reps[settings.steps :] == [1] * settings.steps

    vals0 = [x.value for x in steps if x.repetition == 0]
    vals1 = [x.value for x in steps if x.repetition == 1]

    assert np.allclose(vals0, np.linspace(base - 2000.0, base + 2000.0, settings.steps))
    assert np.allclose(vals1, np.linspace(base + 2000.0, base - 2000.0, settings.steps))

    assert any("Sweep cycle 1/2" in m.message for m in txt_log.records)
    assert any("Sweep cycle 2/2" in m.message for m in txt_log.records)


def test_sweep_filters_out_of_range_values_and_logs_warning():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    lo, hi = beam.limits("working_distance")

    # place base at mid-range so large ranges exceed both ends
    beam.working_distance = (lo + hi) / 2

    big = (hi - lo) * 2
    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-big, big),
        steps=9,
        cycles=1,
        target="working_distance",
    )
    sweeping = Sweeping(beam, settings, txt_log)

    steps = list(sweeping.sweep())
    yielded = [x.value for x in steps]

    assert all(lo <= v <= hi for v in yielded)
    assert len(yielded) < settings.steps
    assert len([m for m in txt_log.records if m.level == "warning"]) >= 1
    assert "out of range" in txt_log.records[0].message.lower()


def test_evaluate_best_sweep_delegates_to_strategy_and_returns_its_result():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)
    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target="working_distance",
    )
    sweeping = Sweeping(beam, settings, txt_log)
    results = [
        AutofocusResult(
            sharpness=0.8, sweep=SweepStep(repetition=0, value=1000.0, index=0)
        ),
        AutofocusResult(
            sharpness=0.9, sweep=SweepStep(repetition=0, value=2000.0, index=1)
        ),
    ]
    sweeping._sweeping_strategy.evaluate = MagicMock(return_value=42.0)

    result = sweeping.evaluate_best_sweep(results)

    sweeping._sweeping_strategy.evaluate.assert_called_once_with(results)
    assert result == 42.0
