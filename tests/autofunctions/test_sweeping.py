# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np

from fibsem_maestro.autofunctions.sweeping import Sweeping
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.in_memory import InMemoryTextLogger
from fibsem_maestro.microscope.mock.microscope_control import MockMicroscopeControl
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)


def test_construct_selects_electron_beam_and_attribute():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )

    sweeping = Sweeping(microscope, settings, txt_log)

    assert sweeping._beam is microscope.electron_beam
    assert sweeping._sweep_attribute == "working_distance"


def test_update_switches_to_ion_beam():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)

    assert sweeping._beam is microscope.electron_beam

    settings.target_beam = BeamType.ION

    assert sweeping._beam is microscope.ion_beam


def test_get_attribute_value_reads_current_beam_state():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    eb = microscope.electron_beam
    eb.working_distance = 5_000_000.0

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(0.0, 0.0),
        steps=1,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)

    assert sweeping.get_attribute_value() == 5_000_000.0


def test_set_attribute_value_sets_beam_state():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    eb = microscope.electron_beam
    eb.working_distance = 5_000_000.0

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(0.0, 0.0),
        steps=1,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)
    sweeping.set_attribute_value(1_000_000.0)

    assert eb.working_distance == 1_000_000.0


def test_sweep_yields_expected_zigzag_sequence_when_in_range():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    eb = microscope.electron_beam
    base = 10_000_000.0
    eb.working_distance = base

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-2000.0, 2000.0),
        steps=5,
        cycles=2,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)

    steps = list(sweeping.sweep())
    assert len(steps) == settings.cycles * settings.steps

    reps = [x.repetition for x in steps]
    assert reps[: settings.steps] == [0] * settings.steps
    assert reps[settings.steps :] == [1] * settings.steps

    vals0 = [x.value for x in steps if x.repetition == 0]
    vals1 = [x.value for x in steps if x.repetition == 1]

    assert np.allclose(vals0, np.linspace(base - 2000.0, base + 2000.0, settings.steps))
    assert np.allclose(vals1, np.linspace(base + 2000.0, base - 2000.0, settings.steps))

    assert any("Sweep cycle 0" in m for m in txt_log.infos)
    assert any("Sweep cycle 1" in m for m in txt_log.infos)


def test_sweep_filters_out_of_range_values_and_logs_warning():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    eb = microscope.electron_beam
    lo, hi = eb.limits("working_distance")

    # place base at mid-range so large ranges exceed both ends
    eb.working_distance = (lo + hi) / 2

    big = (hi - lo) * 2
    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-big, big),
        steps=9,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)

    steps = list(sweeping.sweep())
    yielded = [x.value for x in steps]

    assert all(lo <= v <= hi for v in yielded)
    assert len(yielded) < settings.steps
    assert len(txt_log.warnings) >= 1
    assert "out of range" in txt_log.warnings[0].lower()


def test_sweep_does_not_refresh_base():
    txt_log = InMemoryTextLogger()
    microscope = MockMicroscopeControl("127.0.0.1", txt_log)

    eb = microscope.electron_beam
    original_base = 1_000_000.0
    eb.working_distance = original_base

    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target_beam=BeamType.ELECTRON,
        target_attribute="working_distance",
    )
    sweeping = Sweeping(microscope, settings, txt_log)

    # base should not be re-read
    eb.working_distance = 20_000_000.0

    steps = list(sweeping.sweep())
    vals = [x.value for x in steps]

    assert np.allclose(
        vals, np.array([original_base - 1000.0, original_base, original_base + 1000.0])
    )
