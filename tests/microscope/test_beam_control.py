# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import pytest

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.in_memory import InMemoryTextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.mock.beam_control import MockBeamControl
from fibsem_maestro.settings.beam_properties import BeamProperties


def create_test_beam_control() -> MockBeamControl:
    return MockBeamControl(InMemoryTextLogger())


def test_set_properties():
    beam_control = create_test_beam_control()
    beam_properties = BeamProperties(
        working_distance=10_000_000.0,
        stigmator=Stigmator(1.0, 2.0),
        lens_alignment=LensAlignment(3.0, 4.0),
        beam_shift=BeamShift(5.0, 6.0),
        detector_contrast=0.75,
        detector_brightness=0.25,
        source_tilt=SourceTilt(1.0, -1.0),
        line_integration=2,
        dwell_time=2e-6,
        bit_depth=12,
        resolution=Resolution(2048, 1024),
        horizontal_field_width=400_000.0,
        scanning_area=RelativeArea(RelativePoint(0.5, 0.5), 10.0, 12.0),
    )  # type: ignore
    setattr(beam_properties, "beam.custom_parameter", 0.7)
    setattr(beam_properties, "beam.inner.parameter", 2.1)

    beam_control.set_properties(beam_properties)

    assert beam_control.working_distance == 10_000_000.0
    assert beam_control.stigmator == Stigmator(1.0, 2.0)
    assert beam_control.lens_alignment == LensAlignment(3.0, 4.0)
    assert beam_control.beam_shift == BeamShift(5.0, 6.0)
    assert beam_control.detector_contrast == 0.75
    assert beam_control.detector_brightness == 0.25
    assert beam_control.source_tilt == SourceTilt(1.0, -1.0)
    assert beam_control.line_integration == 2
    assert beam_control.dwell_time == 2e-6
    assert beam_control.bit_depth == 12
    assert beam_control.resolution == Resolution(2048, 1024)
    assert beam_control.horizontal_field_width == 400_000.0
    assert beam_control.scanning_area == RelativeArea(
        RelativePoint(0.5, 0.5), 10.0, 12.0
    )
    assert beam_control.manufacturer_prop("beam.custom_parameter") == 0.7
    assert beam_control.manufacturer_prop("beam.inner.parameter") == 2.1


def test_set_properties_with_none_values():
    """
    Test that properties with None values are not set.
    """
    beam_control = create_test_beam_control()
    beam_properties = BeamProperties(
        working_distance=None,
        stigmator=None,
        lens_alignment=None,
        beam_shift=None,
        detector_contrast=None,
        detector_brightness=None,
        source_tilt=None,
        line_integration=None,
        dwell_time=None,
        bit_depth=None,
        resolution=None,
        horizontal_field_width=None,
        scanning_area=None,
    )  # type: ignore
    setattr(beam_properties, "beam.custom_parameter", None)
    setattr(beam_properties, "beam.inner.parameter", None)

    beam_control.set_properties(beam_properties)

    # check that properties remain at their initial values
    assert beam_control.working_distance == 0.0
    assert beam_control.stigmator == Stigmator(0.0, 0.0)
    assert beam_control.lens_alignment == LensAlignment(0.0, 0.0)
    assert beam_control.beam_shift == BeamShift(0.0, 0.0)
    assert beam_control.detector_contrast == 0.0
    assert beam_control.detector_brightness == 0.0
    assert beam_control.source_tilt == SourceTilt(0.0, 0.0)
    assert beam_control.line_integration == 1
    assert beam_control.dwell_time == 0.0
    assert beam_control.bit_depth == 8
    assert beam_control.resolution == Resolution(1, 1)
    assert beam_control.horizontal_field_width == 0.0
    assert beam_control.scanning_area.is_full_frame()
    assert beam_control.manufacturer_prop("beam.custom_parameter") == 0.0
    assert beam_control.manufacturer_prop("beam.inner.parameter") == 0.0


def test_set_properties_with_invalid_internal_property():
    beam_control = create_test_beam_control()
    beam_properties = BeamProperties(
        working_distance=10_000_000.0,
    )  # type: ignore
    setattr(beam_properties, "invalid_property", False)

    with pytest.raises(MicroscopeError):
        beam_control.set_properties(beam_properties)


def test_collect_properties():
    beam_control = create_test_beam_control()
    beam_control.working_distance = 10_000_000.0
    beam_control.stigmator = Stigmator(1.0, 2.0)
    beam_control.set_manufacturer_prop("beam.custom_parameter", 0.7)

    selected_properties = ["working_distance", "stigmator", "beam.custom_parameter"]
    collected_properties = beam_control.collect_properties(selected_properties)

    assert collected_properties.working_distance == 10_000_000.0
    assert collected_properties.stigmator == Stigmator(1.0, 2.0)
    assert getattr(collected_properties, "beam.custom_parameter") == 0.7


def test_collect_properties_with_unknown_properties():
    beam_control = create_test_beam_control()
    beam_control.working_distance = 10_000_000.0

    selected_properties = ["working_distance", "unknown_property"]
    collected_properties = beam_control.collect_properties(selected_properties)

    assert collected_properties.working_distance == 10_000_000.0

    assert len(beam_control.txt_log.warnings) == 1  # type: ignore
    assert "unknown" in beam_control.txt_log.warnings[0].lower()  # type: ignore


def test_collect_properties_empty_selection():
    beam_control = create_test_beam_control()
    collected_properties = beam_control.collect_properties([])

    properties_dict = collected_properties.model_dump()
    for field_name in BeamProperties.model_fields:
        assert field_name in properties_dict
        assert properties_dict[field_name] is None
