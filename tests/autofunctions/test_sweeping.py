# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np

from fibsem_maestro.autofunctions.sweeping import Sweeping
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.simulated.microscope_control import (
    SimulatedMicroscopeControl,
)
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)


class InMemoryTextLogger(TextLogger):
    """Simple logger that records messages."""

    def __init__(self) -> None:
        self.debugs: list[str] = []
        self.infos: list[str] = []
        self.warnings: list[str] = []
        self.errors: list[str] = []

    def derive(self, name: str) -> "InMemoryTextLogger":
        _ = name
        return InMemoryTextLogger()

    def debug(self, msg: str) -> None:
        self.debugs.append(msg)

    def info(self, msg: str) -> None:
        self.infos.append(msg)

    def warning(self, msg: str) -> None:
        self.warnings.append(msg)

    def error(self, msg: str) -> None:
        self.errors.append(msg)


def test_construct_selects_electron_beam_and_attribute():
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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

    out = list(sweeping.sweep())
    assert len(out) == settings.cycles * settings.steps

    reps = [r for r, _ in out]
    assert reps[: settings.steps] == [0] * settings.steps
    assert reps[settings.steps :] == [1] * settings.steps

    vals0 = [v for r, v in out if r == 0]
    vals1 = [v for r, v in out if r == 1]

    assert np.allclose(vals0, np.linspace(base - 2000.0, base + 2000.0, settings.steps))
    assert np.allclose(vals1, np.linspace(base + 2000.0, base - 2000.0, settings.steps))

    assert any("Sweep cycle 0" in m for m in txt_log.infos)
    assert any("Sweep cycle 1" in m for m in txt_log.infos)


def test_sweep_filters_out_of_range_values_and_logs_warning():
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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

    out = list(sweeping.sweep())
    yielded = [v for _, v in out]

    assert all(lo <= v <= hi for v in yielded)
    assert len(yielded) < settings.steps
    assert len(txt_log.warnings) >= 1
    assert "out of range" in txt_log.warnings[0].lower()


def test_sweep_does_not_refresh_base():
    microscope = SimulatedMicroscopeControl("127.0.0.1", seed=123)  # pyright: ignore[reportCallIssue]
    txt_log = InMemoryTextLogger()

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

    out = list(sweeping.sweep())
    vals = [v for _, v in out]

    assert np.allclose(
        vals, np.array([original_base - 1000.0, original_base, original_base + 1000.0])
    )
