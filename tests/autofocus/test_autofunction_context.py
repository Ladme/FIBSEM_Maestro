# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import contextlib
from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import pytest

from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
from fibsem_maestro.autofocus.error import AutofunctionError
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.microscope.mock.beam_control import MockBeamControl
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)
from fibsem_maestro.store.frame.memory import MemoryFrameStore
from fibsem_maestro.store.props.memory import MemoryPropsStore


def _make_microscope(txt_log: MemoryTextLogger) -> Microscope:
    settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0,
    )
    return Microscope(settings, txt_log)


def _make_sweeping(txt_log: MemoryTextLogger) -> Sweeping:
    beam = MockBeamControl(txt_log)
    settings = SweepingSettings(
        strategy=BasicStrategySettings(),
        range=(-1000.0, 1000.0),
        steps=3,
        cycles=1,
        target="working_distance",
    )
    return Sweeping(beam, settings, txt_log)


def _make_criterion(txt_log: MemoryTextLogger) -> Criterion:
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    return Criterion("test", settings, txt_log, MemoryImageLogger())


def _make_imaging(txt_log: MemoryTextLogger) -> Imaging:
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = ImagingSettings()

    return Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )


def _make_ctx(txt_log: MemoryTextLogger, delta_x: float = 0.0) -> AutofunctionContext:
    microscope = _make_microscope(txt_log)
    sweeping = _make_sweeping(txt_log)
    criterion = _make_criterion(txt_log)
    imaging = _make_imaging(txt_log)
    settings = MagicMock()
    settings.delta_x = delta_x
    return AutofunctionContext(
        microscope, sweeping, criterion, imaging, settings, txt_log
    )


def test_temporary_stage_x_offset_moves_stage_before_yield():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log, delta_x=500.0)

    with ctx.temporary_stage_x_offset():
        position = ctx.microscope._control.stage_position
        assert np.isclose(position.x, -500.0)


def test_temporary_stage_x_offset_restores_stage_after_yield():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log, delta_x=500.0)

    with ctx.temporary_stage_x_offset():
        pass

    assert np.isclose(ctx.microscope._control.stage_position.x, 0.0)


def test_temporary_stage_x_offset_restores_stage_on_exception():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log, delta_x=500.0)

    with contextlib.suppress(RuntimeError), ctx.temporary_stage_x_offset():
        raise RuntimeError("simulated failure")

    assert np.isclose(ctx.microscope._control.stage_position.x, 0.0)


def test_temporary_stage_x_offset_logs_move_and_restore():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log, delta_x=500.0)

    with ctx.temporary_stage_x_offset():
        pass

    messages = [r.message for r in txt_log.records]
    assert any("focusing area" in m for m in messages)
    assert any("Restoring" in m for m in messages)


def test_make_sharpness_job_returns_callable():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log)
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    sweep = SweepStep(repetition=0, value=1000.0, index=0)

    job = ctx.make_sharpness_job(img, sweep)

    assert callable(job)


def test_make_sharpness_job_returns_autofocus_result_with_correct_sweep():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log)
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    sweep = SweepStep(repetition=0, value=1000.0, index=0)

    result = ctx.make_sharpness_job(img, sweep)()

    assert isinstance(result, AutofocusResult)
    assert result.sweep is sweep


def test_make_sharpness_job_raises_and_logs_warning_on_failure():
    txt_log = MemoryTextLogger()
    ctx = _make_ctx(txt_log)
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    sweep = SweepStep(repetition=0, value=1000.0, index=0)

    def failing_metric(
        image: Image, s: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = image, s, log
        raise RuntimeError("metric failure")

    ctx._criterion._sharpness_metric_fn = failing_metric

    with pytest.raises(AutofunctionError):
        ctx.make_sharpness_job(img, sweep)()

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("failed" in r.message for r in txt_log.records)
