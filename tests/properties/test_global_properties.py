# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import pytest

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties


def test_accumulate_property_creates_electron_beam_from_none():
    props = GlobalProperties.model_validate({})
    assert props.electron_beam is None

    props.accumulate_property("dwell_time", 1.5e-6, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.dwell_time == pytest.approx(1.5e-6)


def test_accumulate_property_creates_ion_beam_from_none():
    props = GlobalProperties.model_validate({})
    assert props.ion_beam is None

    props.accumulate_property("dwell_time", 2.0e-6, beam_type=BeamType.ION)

    assert props.ion_beam is not None
    assert props.ion_beam.dwell_time == pytest.approx(2.0e-6)


def test_accumulate_property_creates_microscope_from_none():
    props = GlobalProperties.model_validate({})
    assert props.microscope is None

    props.accumulate_property("stage_position", StagePosition(x=100.0), beam_type=None)

    assert props.microscope is not None
    assert props.microscope.stage_position.x == pytest.approx(100.0)


def test_accumulate_property_adds_to_existing_numeric():
    props = GlobalProperties.model_validate({})
    props.accumulate_property("dwell_time", 1.0e-6, beam_type=BeamType.ELECTRON)
    props.accumulate_property("dwell_time", 2.0e-6, beam_type=BeamType.ELECTRON)
    props.accumulate_property("dwell_time", 1.5e-6, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.dwell_time == pytest.approx(4.5e-6)


def test_accumulate_property_sets_when_attribute_none():
    props = GlobalProperties.model_validate({})
    props.electron_beam = BeamProperties.model_validate({})
    assert props.electron_beam.dwell_time is None

    props.accumulate_property("dwell_time", 1.0e-6, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.dwell_time == pytest.approx(1.0e-6)

    props.accumulate_property("dwell_time", 0.5e-6, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.dwell_time == pytest.approx(1.5e-6)


def test_accumulate_property_sets_stage_position_when_none():
    props = GlobalProperties.model_validate({})
    props.microscope = MicroscopeProperties.model_validate({})
    assert props.microscope.stage_position is None

    props.accumulate_property("stage_position", StagePosition(x=1000.0), beam_type=None)
    assert props.microscope.stage_position is not None
    assert props.microscope.stage_position.x == pytest.approx(1000.0)

    props.accumulate_property("stage_position", StagePosition(x=500.0), beam_type=None)
    assert props.microscope.stage_position is not None
    assert props.microscope.stage_position.x == pytest.approx(1500.0)


def test_accumulate_property_line_integration_multiple_calls():
    props = GlobalProperties.model_validate({})

    for _ in range(5):
        props.accumulate_property("line_integration", 4, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.line_integration == 20


def test_accumulate_property_bit_depth_accumulates():
    props = GlobalProperties.model_validate({})
    props.accumulate_property("bit_depth", 8, beam_type=BeamType.ELECTRON)
    props.accumulate_property("bit_depth", 8, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.bit_depth == 16


def test_accumulate_property():
    props = GlobalProperties.model_validate({})
    props.accumulate_property(
        "beam_shift", BeamShift(x=100.0, y=-20.0), beam_type=BeamType.ELECTRON
    )
    props.accumulate_property(
        "beam_shift", BeamShift(x=80.0, y=25.0), beam_type=BeamType.ELECTRON
    )

    assert props.electron_beam is not None
    assert props.electron_beam.beam_shift is not None
    assert props.electron_beam.beam_shift.x == pytest.approx(180.0)
    assert props.electron_beam.beam_shift.y == pytest.approx(5.0)


def test_accumulate_property_raises_on_nonexistent_property():
    props = GlobalProperties.model_validate({})
    props.electron_beam = BeamProperties.model_validate({})

    with pytest.raises(ValueError) as exc_info:
        props.accumulate_property(
            "nonexistent_property", 10.0, beam_type=BeamType.ELECTRON
        )

    assert "nonexistent_property" not in exc_info.value.args[
        0
    ] or "does not exist" in str(exc_info.value)


def test_accumulate_property_mixed_none_and_values():
    """Properties can be mixed: some None, some with values."""
    props = GlobalProperties.model_validate({})
    props.electron_beam = BeamProperties.model_validate(
        {"dwell_time": 1.0e-6, "bit_depth": None}
    )

    props.accumulate_property("dwell_time", 0.5e-6, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.dwell_time == pytest.approx(1.5e-6)

    props.accumulate_property("bit_depth", 8, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.bit_depth == 8


def test_set_property_creates_electron_beam_from_none():
    props = GlobalProperties.model_validate({})
    assert props.electron_beam is None

    props.set_property("dwell_time", 2.5e-6, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.dwell_time == pytest.approx(2.5e-6)


def test_set_property_creates_ion_beam_from_none():
    props = GlobalProperties.model_validate({})
    assert props.ion_beam is None

    props.set_property("line_integration", 8, beam_type=BeamType.ION)

    assert props.ion_beam is not None
    assert props.ion_beam.line_integration == 8


def test_set_property_creates_microscope_from_none():
    props = GlobalProperties.model_validate({})
    assert props.microscope is None

    props.set_property("working_distance", 4800.0, beam_type=None)

    assert props.microscope is not None
    assert props.microscope.working_distance == pytest.approx(4800.0)


def test_set_property_replaces_existing_value():
    props = GlobalProperties.model_validate({})
    props.accumulate_property("dwell_time", 5.0e-6, beam_type=BeamType.ELECTRON)

    props.set_property("dwell_time", 3.0e-6, beam_type=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.dwell_time == pytest.approx(3.0e-6)


def test_set_property_multiple_updates():
    props = GlobalProperties.model_validate({})

    props.set_property("line_integration", 2, beam_type=BeamType.ELECTRON)
    assert props.electron_beam is not None
    assert props.electron_beam.line_integration == 2

    props.set_property("line_integration", 4, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.line_integration == 4

    props.set_property("line_integration", 8, beam_type=BeamType.ELECTRON)
    assert props.electron_beam.line_integration == 8


def test_set_property_raises_on_nonexistent_property():
    props = GlobalProperties.model_validate({})
    props.electron_beam = BeamProperties.model_validate({})

    with pytest.raises(ValueError) as exc_info:
        props.set_property("fake_property", 10.0, beam_type=BeamType.ELECTRON)

    assert "fake_property" not in str(exc_info.value) or "does not exist" in str(
        exc_info.value
    )
