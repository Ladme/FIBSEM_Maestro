# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Generator
from pathlib import Path

import numpy as np
import pytest
from fibsem_maestro.core.slice import SliceContext

from fibsem_maestro.autofocus.autofocus import Autofocus
from fibsem_maestro.autofocus.autofocus_context import AutofocusContext
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweep_step import SweepStep
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    AutoscriptMode,
    BasicMode,
    StepMode,
)
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingSettings,
)
from fibsem_maestro.store.frame.memory import MemoryFrameStore
from fibsem_maestro.store.props.memory import MemoryPropsStore


def _make_basic_autofocus_settings() -> AutofocusSettings:
    return AutofocusSettings(
        mode=BasicMode(
            sweeping=SweepingSettings(
                strategy=BasicStrategySettings(),
                range=(-1000.0, 1000.0),
                steps=3,
                cycles=1,
            ),
            criterion=CriterionSettings(
                sharpness_metric_fn="bandpass",
                detail=DetailBand(low=10.0, high=100.0),
            ),
        ),
        target_attribute="working_distance",
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )


def _make_autofocus(
    txt_log: MemoryTextLogger | None = None,
    settings: AutofocusSettings | None = None,
) -> Autofocus:
    txt_log = txt_log or MemoryTextLogger()
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
    settings = settings or _make_basic_autofocus_settings()
    imaging_settings = ImagingSettings()
    props_store = MemoryPropsStore(ctx)
    imaging = Imaging(
        name="test imaging",
        microscope=microscope,
        settings=imaging_settings,
        props_store=props_store,
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    return Autofocus(
        name="test autofocus",
        microscope=microscope,
        settings=settings,
        imaging=imaging,
        props_store=props_store,
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )


def test_constructor_stores_name():
    af = _make_autofocus()

    assert af._name == "test autofocus"


def test_constructor_creates_sweeping_for_basic_mode():
    af = _make_autofocus()

    assert af._sweeping is not None
    assert isinstance(af._sweeping, Sweeping)


def test_constructor_creates_criterion_for_basic_mode():
    af = _make_autofocus()

    assert af._criterion is not None
    assert isinstance(af._criterion, Criterion)


def test_constructor_sets_sweeping_and_criterion_to_none_for_autoscript_mode():
    settings = AutofocusSettings(
        mode=AutoscriptMode(),
        target_attribute="working_distance",
    )
    af = _make_autofocus(settings=settings)

    assert af._sweeping is None
    assert af._criterion is None


def test_constructor_initialises_active_gen_to_none():
    af = _make_autofocus()

    assert af._active_gen is None


def test_constructor_creates_autofocus_context():
    af = _make_autofocus()

    assert isinstance(af._ctx, AutofocusContext)


def test_constructor_creates_jobs_manager():
    af = _make_autofocus()

    assert isinstance(af._jobs, JobsManager)


def test_name_returns_configured_name():
    af = _make_autofocus()

    assert af.name == "test autofocus"


def test_name_with_underscores_replaces_spaces():
    af = _make_autofocus()

    assert af.name_with_underscores == "test_autofocus"


def test_props_file_returns_string_of_properties_file():
    af = _make_autofocus()

    assert af.props_file == str(
        AutofocusSettings(
            mode=AutoscriptMode(),
            target_attribute="working_distance",
        ).properties_file
    )


def test_beam_type_returns_configured_beam_type():
    af = _make_autofocus()

    assert af.beam_type == BeamType.ELECTRON


def test_microscope_returns_configured_microscope():
    af = _make_autofocus()

    assert isinstance(af.microscope, Microscope)


def test_txt_log_returns_configured_logger():
    txt_log = MemoryTextLogger()
    af = _make_autofocus(txt_log=txt_log)

    assert af.txt_log is txt_log


def test_props_to_collect_returns_empty_by_default():
    af = _make_autofocus()

    assert af.props_to_collect.microscope == []
    assert af.props_to_collect.electron_beam == []
    assert af.props_to_collect.ion_beam == []


def test_should_execute_returns_true_for_first_slice():
    af = _make_autofocus()

    assert af._should_execute(slice_number=1, image_sharpness=None) is True


def test_should_execute_logs_info_for_first_slice():
    txt_log = MemoryTextLogger()
    af = _make_autofocus(txt_log=txt_log)

    af._should_execute(slice_number=1, image_sharpness=None)

    assert any("first slice" in r.message for r in txt_log.records)


def test_should_execute_returns_true_when_slice_matches_execution_frequency():
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "execution_frequency": 5}
    )
    af = _make_autofocus(settings=settings)

    assert af._should_execute(slice_number=10, image_sharpness=None) is True


def test_should_execute_returns_false_when_slice_does_not_match_execution_frequency():
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "execution_frequency": 5}
    )
    af = _make_autofocus(settings=settings)

    assert af._should_execute(slice_number=7, image_sharpness=None) is False


def test_should_execute_returns_true_when_sharpness_below_limit():
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "sharpness_limit": 1.0}
    )
    af = _make_autofocus(settings=settings)

    assert af._should_execute(slice_number=5, image_sharpness=0.5) is True


def test_should_execute_returns_false_when_sharpness_above_limit():
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "sharpness_limit": 1.0}
    )
    af = _make_autofocus(settings=settings)

    assert af._should_execute(slice_number=5, image_sharpness=2.0) is False


def test_should_execute_returns_false_when_sharpness_is_none_and_limit_configured():
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "sharpness_limit": 1.0}
    )
    af = _make_autofocus(settings=settings)

    assert af._should_execute(slice_number=5, image_sharpness=None) is False


def test_should_execute_returns_false_when_no_conditions_met():
    af = _make_autofocus()

    assert af._should_execute(slice_number=5, image_sharpness=None) is False


def test_should_execute_logs_skipping_when_no_conditions_met():
    txt_log = MemoryTextLogger()
    af = _make_autofocus(txt_log=txt_log)

    af._should_execute(slice_number=5, image_sharpness=None)

    assert any("Skipping autofocus" in r.message for r in txt_log.records)


def test_should_execute_ignores_sharpness_limit_when_not_configured():
    af = _make_autofocus()

    assert af._should_execute(slice_number=5, image_sharpness=0.0) is False


def test_advance_calls_next_on_active_generator():
    af = _make_autofocus()
    steps = []

    def simple_gen() -> Generator[None, None, None]:
        steps.append("step")
        yield

    af._active_gen = simple_gen()
    af._advance()

    assert steps == ["step"]


def test_advance_clears_active_gen_on_stop_iteration():
    af = _make_autofocus()
    step = SweepStep(repetition=0, value=5_000_000.0, index=0)
    af._jobs.submit(lambda: AutofocusResult(sharpness=0.9, sweep=step))

    def single_step_gen() -> Generator[None, None, None]:
        yield

    af._active_gen = single_step_gen()
    af._advance()
    af._advance()

    assert af._active_gen is None


def test_advance_sets_best_attribute_value_on_stop_iteration():
    af = _make_autofocus()
    step_a = SweepStep(repetition=0, value=5_000_000.0, index=0)
    step_b = SweepStep(repetition=0, value=6_000_000.0, index=1)
    af._jobs.submit(lambda: AutofocusResult(sharpness=0.5, sweep=step_a))
    af._jobs.submit(lambda: AutofocusResult(sharpness=0.9, sweep=step_b))

    def single_step_gen() -> Generator[None, None, None]:
        yield

    af._active_gen = single_step_gen()
    af._advance()
    af._advance()

    assert np.isclose(af._microscope.electron_beam.working_distance, 6_000_000.0)


def test_advance_writes_properties_on_stop_iteration():
    af = _make_autofocus()
    step = SweepStep(repetition=0, value=5_000_000.0, index=0)
    af._jobs.submit(lambda: AutofocusResult(sharpness=0.9, sweep=step))

    def single_step_gen() -> Generator[None, None, None]:
        yield

    af._active_gen = single_step_gen()
    af._advance()
    af._advance()

    assert af._props_store.next.exists(af.props_file)


def test_advance_clears_active_gen_and_reraises_on_exception():
    af = _make_autofocus()

    def failing_gen() -> Generator[None, None, None]:
        yield
        raise RuntimeError("simulated failure")

    af._active_gen = failing_gen()
    af._advance()  # consumes the yield

    with pytest.raises(RuntimeError, match="simulated failure"):
        af._advance()  # triggers the raise

    assert af._active_gen is None


def test_advance_does_not_evaluate_sweep_for_autoscript_mode():
    settings = AutofocusSettings(
        mode=AutoscriptMode(),
        target_attribute="working_distance",
    )
    af = _make_autofocus(settings=settings)

    def single_step_gen() -> Generator[None, None, None]:
        yield

    af._active_gen = single_step_gen()
    af._advance()
    af._advance()

    assert af._active_gen is None


def test_advance_writes_props_file_for_autoscript_mode():
    settings = AutofocusSettings(
        mode=AutoscriptMode(),
        target_attribute="working_distance",
    )
    af = _make_autofocus(settings=settings)

    def single_step_gen() -> Generator[None, None, None]:
        yield

    af._active_gen = single_step_gen()
    af._advance()
    af._advance()

    assert af._props_store.next.exists(af.props_file)


def _make_autofocus_with_props(
    txt_log: MemoryTextLogger | None = None,
    settings: AutofocusSettings | None = None,
) -> Autofocus:
    txt_log = txt_log or MemoryTextLogger()
    af = _make_autofocus(txt_log=txt_log, settings=settings)
    af._props_store.write(
        af.props_file,
        GlobalProperties(electron_beam=BeamProperties(working_distance=5_000_000.0)),
    )
    return af


def test_perform_autofocus_runs_on_first_slice():
    txt_log = MemoryTextLogger()
    af = _make_autofocus_with_props(txt_log=txt_log)

    af.perform_autofocus(slice_number=1)

    assert any("Executing autofocus" in r.message for r in txt_log.records)


def test_perform_autofocus_skips_when_conditions_not_met():
    txt_log = MemoryTextLogger()
    af = _make_autofocus_with_props(txt_log=txt_log)

    af.perform_autofocus(slice_number=5)

    assert any("Skipping autofocus" in r.message for r in txt_log.records)


def test_perform_autofocus_always_writes_props_to_next_slice_when_skipped():
    af = _make_autofocus_with_props()

    af.perform_autofocus(slice_number=5)

    assert af._props_store.next.exists(af.props_file)


def test_perform_autofocus_always_writes_props_to_next_slice_when_executed():
    af = _make_autofocus_with_props()

    af.perform_autofocus(slice_number=1)

    assert af._props_store.next.exists(af.props_file)


def test_perform_autofocus_basic_mode_completes_in_single_call():
    af = _make_autofocus_with_props()

    af.perform_autofocus(slice_number=1)

    assert af._active_gen is None


def test_perform_autofocus_step_mode_remains_active_across_calls():
    settings = AutofocusSettings(
        mode=StepMode(
            sweeping=SweepingSettings(
                strategy=BasicStrategySettings(),
                range=(-1000.0, 1000.0),
                steps=3,
                cycles=1,
            ),
            criterion=CriterionSettings(
                sharpness_metric_fn="bandpass",
                detail=DetailBand(low=10.0, high=100.0),
            ),
        ),
        target_attribute="working_distance",
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )
    af = _make_autofocus_with_props(settings=settings)

    af.perform_autofocus(slice_number=1)

    # step mode yields once per step so active_gen should still be running
    assert af._active_gen is not None


def test_perform_autofocus_step_mode_resumes_without_gating():
    settings = AutofocusSettings(
        mode=StepMode(
            sweeping=SweepingSettings(
                strategy=BasicStrategySettings(),
                range=(-1000.0, 1000.0),
                steps=3,
                cycles=1,
            ),
            criterion=CriterionSettings(
                sharpness_metric_fn="bandpass",
                detail=DetailBand(low=10.0, high=100.0),
            ),
        ),
        target_attribute="working_distance",
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )
    af = _make_autofocus_with_props(settings=settings)

    af.perform_autofocus(slice_number=1)  # starts step mode
    af.perform_autofocus(slice_number=5)  # should resume regardless of gating

    assert af._active_gen is not None


def test_perform_autofocus_writes_props_to_next_slice_when_resuming_active_gen():
    settings = AutofocusSettings(
        mode=StepMode(
            sweeping=SweepingSettings(
                strategy=BasicStrategySettings(),
                range=(-1000.0, 1000.0),
                steps=3,
                cycles=1,
            ),
            criterion=CriterionSettings(
                sharpness_metric_fn="bandpass",
                detail=DetailBand(low=10.0, high=100.0),
            ),
        ),
        target_attribute="working_distance",
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )
    af = _make_autofocus_with_props(settings=settings)

    af.perform_autofocus(slice_number=1)
    assert af._active_gen is not None
    af.perform_autofocus(slice_number=2)

    assert af._props_store.next.exists(af.props_file)


def test_perform_autofocus_clears_previous_results_before_starting():
    af = _make_autofocus_with_props()
    step = SweepStep(repetition=0, value=6_000_000.0, index=0)
    af._jobs.submit(lambda: AutofocusResult(sharpness=0.9, sweep=step))
    af._jobs.wait_and_collect()

    af.perform_autofocus(slice_number=1)

    # jobs from the previous call should have been cleared before execution
    results = af._jobs.wait_and_collect()
    assert all(r.sweep.value != 6_000_000.0 for r in results)


def test_perform_autofocus_runs_when_sharpness_below_limit():
    txt_log = MemoryTextLogger()
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "sharpness_limit": 1.0}
    )
    af = _make_autofocus_with_props(txt_log=txt_log, settings=settings)
    af._imaging._image_sharpness = 0.3

    af.perform_autofocus(slice_number=5)

    assert any("Executing autofocus" in r.message for r in txt_log.records)


def test_perform_autofocus_runs_when_execution_frequency_matches():
    txt_log = MemoryTextLogger()
    settings = AutofocusSettings(
        **{**_make_basic_autofocus_settings().model_dump(), "execution_frequency": 5}
    )
    af = _make_autofocus_with_props(txt_log=txt_log, settings=settings)

    af.perform_autofocus(slice_number=10)

    assert any("Executing autofocus" in r.message for r in txt_log.records)


def test_perform_autofocus_writes_props_to_next_slice_after_starting_long_running_sweep():
    settings = AutofocusSettings(
        mode=StepMode(
            sweeping=SweepingSettings(
                strategy=BasicStrategySettings(),
                range=(-1000.0, 1000.0),
                steps=3,
                cycles=1,
            ),
            criterion=CriterionSettings(
                sharpness_metric_fn="bandpass",
                detail=DetailBand(low=10.0, high=100.0),
            ),
        ),
        target_attribute="working_distance",
        properties_to_collect=PropertyNames(),
        beam_type=BeamType.ELECTRON,
    )
    af = _make_autofocus_with_props(settings=settings)

    af.perform_autofocus(slice_number=1)  # starts step mode

    # active_gen is still running after first call
    assert af._active_gen is not None
    assert af._props_store.next.exists(af.props_file)
