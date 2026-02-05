# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
import pytest

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.scanning_area import RelativeScanningArea
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.simulated.beam_control import SimulatedBeamControl
from fibsem_maestro.microscope.simulated.sample import SimulatedSample
from fibsem_maestro.settings.beam_properties import BeamProperties


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


def create_test_beam_control() -> SimulatedBeamControl:
    """Create a test instance of SimulatedBeamControl."""
    txt_log = InMemoryTextLogger()
    rng = np.random.default_rng(42)
    return SimulatedBeamControl(
        name="TestBeam",
        sample=SimulatedSample(rng, 1, 1),
        stage_position=StagePosition(),
        txt_log=txt_log,
        rng=rng,
    )


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
        scanning_area=RelativeScanningArea(RelativePoint(0.5, 0.5), 10.0, 12.0),
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
    assert beam_control.scanning_area == RelativeScanningArea(
        RelativePoint(0.5, 0.5), 10.0, 12.0
    )
    assert beam_control.manufacturer_prop("beam.custom_parameter") == 0.7
    assert beam_control.manufacturer_prop("beam.inner.parameter") == 2.1

    assert len(beam_control.txt_log.debugs) > 0  # type: ignore


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
    assert beam_control.working_distance == 5_000_000.0
    assert beam_control.stigmator == Stigmator(0.0, 0.0)
    assert beam_control.lens_alignment == LensAlignment(0.0, 0.0)
    assert beam_control.beam_shift == BeamShift(0.0, 0.0)
    assert beam_control.detector_contrast == 0.5
    assert beam_control.detector_brightness == 0.5
    assert beam_control.source_tilt == SourceTilt(0.0, 0.0)
    assert beam_control.line_integration == 1
    assert beam_control.dwell_time == 1e-6
    assert beam_control.bit_depth == 8
    assert beam_control.resolution == Resolution(1024, 768)
    assert beam_control.horizontal_field_width == 20_000.0
    assert beam_control.scanning_area is None
    assert beam_control.manufacturer_prop("beam.custom_parameter") == 1.0
    assert beam_control.manufacturer_prop("beam.inner.parameter") == 0.5


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
