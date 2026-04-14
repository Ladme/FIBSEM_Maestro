# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

import numpy as np

from fibsem_maestro.autofocus.autofocus import BasicMode
from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.frame.memory import MemoryFrameStore
from fibsem_maestro.store.props.memory import MemoryPropsStore


def _make_autofunction_settings(delta_x: float = 0.0) -> AutofunctionSettings:
    return AutofunctionSettings(
        delta_x=delta_x,
        sweeping=SweepingSettings(
            strategy=BasicStrategySettings(),
            range=(-1000.0, 1000.0),
            steps=3,
            cycles=1,
            target="working_distance",
        ),
        criterion=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )


def _make_ctx_for_basic_mode(
    txt_log: MemoryTextLogger,
    steps: int = 3,
    cycles: int = 1,
    delta_x: float = 0.0,
) -> AutofunctionContext:
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0,
    )
    microscope = Microscope(microscope_settings, txt_log)

    beam = microscope.electron_beam
    beam.working_distance = 5_000_000.0

    sweeping_settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=steps,
        cycles=cycles,
        target="working_distance",
    )
    sweeping = Sweeping(beam, sweeping_settings, txt_log)

    criterion_settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion("test", criterion_settings, txt_log, MemoryImageLogger())

    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)

    imaging = Imaging(
        name="test",
        microscope=microscope,
        settings=ImagingSettings(),
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    autofunction_settings = _make_autofunction_settings(delta_x=delta_x)

    return AutofunctionContext(
        microscope, sweeping, criterion, imaging, autofunction_settings, txt_log
    )


def test_basic_mode_submits_one_job_per_sweep_step():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=3, cycles=1)

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))
        results = jobs.wait_and_collect()

    assert len(results) == 3


def test_basic_mode_submits_jobs_for_all_cycles():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=3, cycles=2)

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))
        results = jobs.wait_and_collect()

    assert len(results) == 6


def test_basic_mode_sets_beam_attribute_for_each_step():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=3, cycles=1)
    visited_values: list[float] = []

    original_set = ctx.sweeping.set_attribute_value

    def tracking_set(value: float) -> None:
        visited_values.append(value)
        original_set(value)

    ctx.sweeping.set_attribute_value = tracking_set

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))

    assert len(visited_values) == 3


def test_basic_mode_moves_and_restores_stage_with_offset():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=1, cycles=1, delta_x=500.0)
    control = ctx.microscope._control
    positions_during_sweep: list[float] = []

    original_grab = ctx.microscope.beam.grab_frame

    def tracking_grab_frame(frame_store: FrameStore | None = None) -> Image:
        positions_during_sweep.append(control.stage_position.x)
        return original_grab(frame_store)

    ctx.microscope.beam.grab_frame = tracking_grab_frame

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))

    assert all(np.isclose(x, -500.0) for x in positions_during_sweep)
    assert np.isclose(control.stage_position.x, 0.0)


def test_basic_mode_logs_each_sweep_step():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=3, cycles=1)

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))

    step_messages = [
        r.message for r in txt_log.records if "Autofunction step" in r.message
    ]
    assert len(step_messages) == 3


def test_basic_mode_grabs_frame_for_each_sweep_step():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx_for_basic_mode(txt_log, steps=3, cycles=1)
    grabbed_frames: list[Image] = []

    original_grab = ctx.microscope.beam.grab_frame

    def tracking_grab_frame(frame_store: FrameStore | None = None) -> Image:
        frame = original_grab(frame_store)
        grabbed_frames.append(frame)
        return frame

    ctx.microscope.beam.grab_frame = tracking_grab_frame

    with JobsManager() as jobs:
        list(BasicMode().execute(ctx, jobs))

    assert len(grabbed_frames) == 3
    assert all(isinstance(f, Image) for f in grabbed_frames)
