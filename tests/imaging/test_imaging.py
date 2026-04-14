# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import threading
from pathlib import Path

import numpy as np
import pytest

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.criterion_settings import CriterionSettings
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.frame.memory import MemoryFrameStore
from fibsem_maestro.store.props.memory import MemoryPropsStore


def _make_imaging(
    txt_log: MemoryTextLogger,
    criterion_settings: CriterionSettings | None = None,
) -> Imaging:
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
    settings = ImagingSettings(criterion=criterion_settings)

    return Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )


def test_constructor_stores_name():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging._name == "test"


def test_constructor_creates_criterion_when_settings_provided():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )

    assert imaging._criterion is not None
    assert isinstance(imaging._criterion, Criterion)


def test_constructor_criterion_is_none_when_no_settings():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log, criterion_settings=None)

    assert imaging._criterion is None


def test_constructor_initialises_image_sharpness_to_none():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging._image_sharpness is None


def test_constructor_initialises_sharpness_thread_to_none():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging._sharpness_thread is None


def test_constructor_initialises_scanning_area_selected_to_false():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging._scanning_area_selected is False


def test_name_returns_configured_name():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging.name == "test"


def test_props_file_returns_string_of_properties_file_path():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging.props_file == str(ImagingSettings().properties_file)


def test_beam_type_returns_configured_beam_type():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging.beam_type == BeamType.ELECTRON


def test_microscope_returns_configured_microscope():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert isinstance(imaging.microscope, Microscope)


def test_txt_log_returns_configured_logger():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    assert imaging.txt_log is txt_log


def test_props_to_collect_returns_configured_properties():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    props = imaging.props_to_collect

    assert props.microscope == []
    assert props.electron_beam == []
    assert props.ion_beam == []


def test_calculate_sharpness_stores_result():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)

    imaging._calculate_sharpness(img)

    assert imaging._image_sharpness is not None
    assert isinstance(imaging._image_sharpness, float)


def test_calculate_sharpness_logs_warning_on_failure():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )

    assert imaging._criterion is not None

    def failing_metric(
        image: Image, s: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = image, s, log
        raise RuntimeError("metric failure")

    imaging._criterion._sharpness_metric_fn = failing_metric
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)

    imaging._calculate_sharpness(img)

    assert imaging._image_sharpness is not None
    assert np.isnan(imaging._image_sharpness)
    assert any(r.level == "warning" for r in txt_log.records)
    assert any("Resolution calculation failed" in r.message for r in txt_log.records)


def test_wait_for_sharpness_returns_none_when_no_criterion():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log, criterion_settings=None)

    result = imaging.wait_for_sharpness()

    assert result is None


def test_wait_for_sharpness_returns_calculated_value():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)

    imaging._sharpness_thread = threading.Thread(
        target=imaging._calculate_sharpness, args=(img,), daemon=True
    )
    imaging._sharpness_thread.start()

    result = imaging.wait_for_sharpness()

    assert result is not None
    assert isinstance(result, float)


def test_wait_for_sharpness_blocks_until_thread_completes():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)

    imaging._sharpness_thread = threading.Thread(
        target=imaging._calculate_sharpness, args=(img,), daemon=True
    )
    imaging._sharpness_thread.start()

    result = imaging.wait_for_sharpness()

    assert not imaging._sharpness_thread.is_alive()
    assert result == imaging._image_sharpness


def _make_imaging_extended(
    txt_log: MemoryTextLogger,
    scanning_area: RelativeArea | None = None,
) -> Imaging:
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1000.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = ImagingSettings(
        resolution_mode=ExtendedResolution(pixel_size=2.0),
        scanning_area=scanning_area,
    )

    return Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )


def test_set_extended_resolution_props_sets_pixel_size():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(txt_log)

    imaging._set_extended_resolution_props(new_pixel_size=5.0)

    assert np.isclose(imaging._microscope.beam.pixel_size, 5.0)


def test_set_extended_resolution_props_sets_scanning_area_to_full_frame():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(
        txt_log,
        scanning_area=RelativeArea(
            origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
        ),
    )

    imaging._set_extended_resolution_props(new_pixel_size=2.0)

    assert imaging._microscope.beam.scanning_area.is_full_frame()


def test_set_extended_resolution_props_marks_scanning_area_selected():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(
        txt_log,
        scanning_area=RelativeArea(
            origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
        ),
    )

    imaging._set_extended_resolution_props(new_pixel_size=2.0)

    assert imaging._scanning_area_selected is True


def test_set_extended_resolution_props_does_not_reapply_beam_shift_on_second_call():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(
        txt_log,
        scanning_area=RelativeArea(
            origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
        ),
    )

    imaging._set_extended_resolution_props(new_pixel_size=2.0)
    beam_shift_after_first = imaging._microscope.beam.beam_shift

    imaging._set_extended_resolution_props(new_pixel_size=2.0)
    beam_shift_after_second = imaging._microscope.beam.beam_shift

    assert beam_shift_after_first.x == beam_shift_after_second.x
    assert beam_shift_after_first.y == beam_shift_after_second.y


def test_set_extended_resolution_props_sets_fov_to_scanning_area_dimensions():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(
        txt_log,
        scanning_area=RelativeArea(
            origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
        ),
    )
    beam = imaging._microscope.beam
    area_nm = RelativeArea(
        origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
    ).to_nanometers(beam.resolution, beam.pixel_size)

    imaging._set_extended_resolution_props(new_pixel_size=2.0)

    assert np.isclose(beam.horizontal_field_width, area_nm.width)
    assert np.isclose(beam.vertical_field_width, area_nm.height)


def test_set_extended_resolution_props_skips_beam_shift_for_full_frame_area():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(
        txt_log,
        scanning_area=RelativeArea.full(),
    )
    initial_beam_shift = imaging._microscope.beam.beam_shift

    imaging._set_extended_resolution_props(new_pixel_size=2.0)

    assert imaging._microscope.beam.beam_shift.x == initial_beam_shift.x
    assert imaging._microscope.beam.beam_shift.y == initial_beam_shift.y
    assert imaging._scanning_area_selected is False


def test_set_extended_resolution_props_skips_beam_shift_when_no_scanning_area():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging_extended(txt_log, scanning_area=None)
    initial_beam_shift = imaging._microscope.beam.beam_shift

    imaging._set_extended_resolution_props(new_pixel_size=2.0)

    assert imaging._microscope.beam.beam_shift.x == initial_beam_shift.x
    assert imaging._microscope.beam.beam_shift.y == initial_beam_shift.y
    assert imaging._scanning_area_selected is False


def test_collect_and_write_properties_writes_to_props_store():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryPropsStore(ctx)

    imaging.collect_and_write_properties(store)

    assert store.exists(str(ImagingSettings().properties_file))


def test_collect_and_write_properties_uses_own_store_when_none_provided():
    txt_log = MemoryTextLogger()
    imaging = _make_imaging(txt_log)

    imaging.collect_and_write_properties()

    assert imaging._props_store.exists(str(ImagingSettings().properties_file))


def test_collect_and_write_properties_sets_bit_depth_when_configured():
    txt_log = MemoryTextLogger()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = ImagingSettings(bit_depth=8)
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    imaging = Imaging(
        name="test",
        microscope=Microscope(microscope_settings, txt_log),
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    imaging.collect_and_write_properties()

    assert imaging._microscope.beam.bit_depth == 8


def test_collect_and_write_properties_restores_scanning_area_after_write():
    txt_log = MemoryTextLogger()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    original_area = RelativeArea(origin=RelativePoint(0.1, 0.1), width=0.8, height=0.8)
    settings = ImagingSettings(
        scanning_area=RelativeArea(
            origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
        )
    )
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    microscope.beam.scanning_area = original_area
    imaging = Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    imaging.collect_and_write_properties()

    assert np.isclose(microscope.beam.scanning_area.origin.x, original_area.origin.x)
    assert np.isclose(microscope.beam.scanning_area.origin.y, original_area.origin.y)
    assert np.isclose(microscope.beam.scanning_area.width, original_area.width)
    assert np.isclose(microscope.beam.scanning_area.height, original_area.height)


def test_collect_and_write_properties_standard_mode_sets_configured_scanning_area():
    txt_log = MemoryTextLogger()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    configured_area = RelativeArea(
        origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5
    )
    settings = ImagingSettings(
        resolution_mode=StandardResolution(),
        scanning_area=configured_area,
    )
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    imaging = Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    # capture the scanning area at the moment of collection
    collected_area = None
    original_collect = microscope.collect_properties

    def capturing_collect(props: PropertyNames) -> GlobalProperties:
        nonlocal collected_area
        collected_area = microscope.beam.scanning_area
        return original_collect(props)

    microscope.collect_properties = capturing_collect  # type: ignore

    imaging.collect_and_write_properties()

    assert collected_area is not None
    assert np.isclose(collected_area.origin.x, configured_area.origin.x)
    assert np.isclose(collected_area.origin.y, configured_area.origin.y)
    assert np.isclose(collected_area.width, configured_area.width)
    assert np.isclose(collected_area.height, configured_area.height)


def test_collect_and_write_properties_standard_mode_sets_full_frame_when_no_area():
    txt_log = MemoryTextLogger()
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = ImagingSettings(
        resolution_mode=StandardResolution(),
        scanning_area=None,
    )
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    imaging = Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=MemoryPropsStore(ctx),
        frame_store=MemoryFrameStore(ctx),
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    collected_area = None
    original_collect = microscope.collect_properties

    def capturing_collect(props: PropertyNames) -> GlobalProperties:
        nonlocal collected_area
        collected_area = microscope.beam.scanning_area
        return original_collect(props)

    microscope.collect_properties = capturing_collect  # type: ignore

    imaging.collect_and_write_properties()

    assert collected_area is not None
    assert collected_area.is_full_frame()


def _make_global_properties() -> GlobalProperties:
    return GlobalProperties(
        electron_beam=BeamProperties(
            working_distance=5_000_000.0,
            pixel_size=2.0,
            detector_brightness=0.5,
            detector_contrast=0.5,
        )
    )


def _prepare_imaging_for_grab_frame(
    txt_log: MemoryTextLogger,
    criterion_settings: CriterionSettings | None = None,
) -> Imaging:
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
    settings = ImagingSettings(criterion=criterion_settings)
    props_store = MemoryPropsStore(ctx)
    frame_store = MemoryFrameStore(ctx)

    imaging = Imaging(
        name="test",
        microscope=microscope,
        settings=settings,
        props_store=props_store,
        frame_store=frame_store,
        txt_log=txt_log,
        img_log=MemoryImageLogger(),
    )

    # pre-populate props store so read_and_set_properties succeeds
    props_store.write(str(settings.properties_file), _make_global_properties())

    return imaging


def test_grab_frame_raises_imaging_error_when_frame_already_exists():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log)

    imaging.grab_frame()

    with pytest.raises(ImagingError):
        imaging.grab_frame()


def test_grab_frame_starts_sharpness_thread_when_criterion_configured():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )

    imaging.grab_frame()

    assert imaging._sharpness_thread is not None


def test_grab_frame_does_not_start_sharpness_thread_when_no_criterion():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log, criterion_settings=None)

    imaging.grab_frame()

    assert imaging._sharpness_thread is None


def test_grab_frame_resets_image_sharpness_to_none_before_calculation():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log, criterion_settings=None)
    imaging._image_sharpness = 99.0

    imaging.grab_frame()

    assert imaging._image_sharpness is None


def test_grab_frame_writes_properties_for_next_slice():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log)

    imaging.grab_frame()

    assert imaging._props_store.next.exists(str(ImagingSettings().properties_file))


def test_grab_frame_logs_debug_when_no_criterion():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log, criterion_settings=None)

    imaging.grab_frame()

    assert any(
        "Image sharpness will not be calculated" in r.message for r in txt_log.records
    )


def test_grab_frame_sharpness_is_available_after_wait():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(
        txt_log,
        criterion_settings=CriterionSettings(
            sharpness_metric_fn="bandpass",
            detail=DetailBand(low=10.0, high=100.0),
        ),
    )

    imaging.grab_frame()
    result = imaging.wait_for_sharpness()

    assert result is not None
    assert isinstance(result, float)


def test_grab_frame_saves_frame_to_frame_store():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log)

    imaging.grab_frame()

    assert imaging._frame_store.exists()


def test_grab_frame_saved_frame_is_image_instance():
    txt_log = MemoryTextLogger()
    imaging = _prepare_imaging_for_grab_frame(txt_log)

    imaging.grab_frame()

    saved = imaging._frame_store.frames[0]  # type: ignore
    assert isinstance(saved, Image)
