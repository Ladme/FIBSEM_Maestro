# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

import numpy as np
import pytest

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.microscope.mock.beam_control import MockBeamControl
from fibsem_maestro.microscope.mock.microscope_control import MockMicroscopeControl
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames


def _make_microscope(txt_log: MemoryTextLogger | None = None) -> Microscope:
    txt_log = txt_log or MemoryTextLogger()
    settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    return Microscope(settings, txt_log)


def test_constructor_sets_active_beam_to_electron_beam():
    microscope = _make_microscope()

    assert microscope.beam is microscope.electron_beam


def test_constructor_instantiates_correct_control():
    microscope = _make_microscope()

    assert isinstance(microscope._control, MockMicroscopeControl)


def test_constructor_raises_for_unknown_control():
    with pytest.raises(Exception):
        Microscope(
            MicroscopeSettings(
                control="nonexistent",
                ip_address="localhost",
                beam_shift_tolerance=1.0,
                stage_tolerance=100.0,
                stage_trials=3,
                holder_pretilt=0.0,
            ),
            MemoryTextLogger(),
        )


def test_electron_beam_returns_beam_control():
    microscope = _make_microscope()

    assert isinstance(microscope.electron_beam, MockBeamControl)


def test_ion_beam_returns_beam_control():
    microscope = _make_microscope()

    assert isinstance(microscope.ion_beam, MockBeamControl)


def test_electron_beam_and_ion_beam_are_different():
    microscope = _make_microscope()

    assert microscope.electron_beam is not microscope.ion_beam


def test_set_beam_switches_beams():
    microscope = _make_microscope()
    microscope.set_beam(BeamType.ION)
    assert microscope.beam is microscope.ion_beam

    microscope.set_beam(BeamType.ELECTRON)
    assert microscope.beam is microscope.electron_beam


def test_set_stage_position_with_verification_sets_correct_position():
    microscope = _make_microscope()
    target = StagePosition(x=1000.0, y=2000.0)

    microscope.set_stage_position_with_verification(target)

    assert np.isclose(microscope._control.stage_position.x, 1000.0)
    assert np.isclose(microscope._control.stage_position.y, 2000.0)


def test_set_stage_position_with_verification_succeeds_within_tolerance():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)
    target = StagePosition(x=1000.0, y=2000.0)

    microscope.set_stage_position_with_verification(target)

    assert not any(r.level == "warning" for r in txt_log.records)


def test_set_stage_position_with_verification_logs_warning_when_out_of_tolerance():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)
    target = StagePosition(x=1000.0, y=2000.0)

    # return a position far from the target
    def inaccurate_set(pos: StagePosition) -> StagePosition:
        return StagePosition(x=pos.x + 10_000.0, y=pos.y + 10_000.0)

    microscope._control.try_set_stage_position = inaccurate_set

    microscope.set_stage_position_with_verification(target)

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("Stage off target" in r.message for r in txt_log.records)


def test_set_stage_position_with_verification_retries_up_to_stage_trials():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)
    target = StagePosition(x=1000.0, y=2000.0)
    call_count = 0

    def inaccurate_set(pos: StagePosition) -> StagePosition:
        nonlocal call_count
        call_count += 1
        return StagePosition(x=pos.x + 10_000.0, y=pos.y + 10_000.0)

    microscope._control.try_set_stage_position = inaccurate_set

    microscope.set_stage_position_with_verification(target)

    assert call_count == microscope._settings.stage_trials


def test_set_stage_position_with_verification_stops_retrying_on_success():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)
    target = StagePosition(x=1000.0, y=2000.0)
    call_count = 0

    def accurate_on_second_try(pos: StagePosition) -> StagePosition:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return StagePosition(x=pos.x + 10_000.0, y=pos.y + 10_000.0)
        return pos

    microscope._control.try_set_stage_position = accurate_on_second_try

    microscope.set_stage_position_with_verification(target)

    assert call_count == 2


def test_move_stage_position_with_verification_applies_delta():
    microscope = _make_microscope()
    microscope._control.try_set_stage_position(StagePosition(x=1000.0, y=2000.0))

    microscope.move_stage_position_with_verification(StagePosition(x=500.0, y=300.0))

    assert np.isclose(microscope._control.stage_position.x, 1500.0)
    assert np.isclose(microscope._control.stage_position.y, 2300.0)


def test_move_stage_position_with_verification_from_zero():
    microscope = _make_microscope()

    microscope.move_stage_position_with_verification(StagePosition(x=400.0, y=800.0))

    assert np.isclose(microscope._control.stage_position.x, 400.0)
    assert np.isclose(microscope._control.stage_position.y, 800.0)


def test_set_beam_shift_with_verification_returns_true_when_within_tolerance():
    microscope = _make_microscope()

    result = microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))

    assert result is True


def test_set_beam_shift_with_verification_applies_beam_shift():
    microscope = _make_microscope()

    microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))

    assert np.isclose(microscope.beam.beam_shift.x, 10.0)
    assert np.isclose(microscope.beam.beam_shift.y, 20.0)


def test_set_beam_shift_with_verification_uses_specified_beam():
    microscope = _make_microscope()

    microscope.set_beam_shift_with_verification(
        BeamShift(10.0, 20.0), microscope.ion_beam
    )

    assert np.isclose(microscope.ion_beam.beam_shift.x, 10.0)
    assert np.isclose(microscope.ion_beam.beam_shift.y, 20.0)
    assert np.isclose(microscope.electron_beam.beam_shift.x, 0.0)


def test_set_beam_shift_with_verification_returns_false_when_actual_shift_is_inaccurate():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)
    requested = BeamShift(10.0, 20.0)

    original_type = type(microscope.beam)
    original_property = original_type.beam_shift
    actual_shift_storage = [BeamShift(0.0, 0.0)]

    def inaccurate_set(self_inner: Any, value: BeamShift) -> None:
        _ = self_inner
        actual_shift_storage[0] = BeamShift(value.x + 10_000.0, value.y + 10_000.0)

    def inaccurate_get(self_inner: Any) -> BeamShift:
        _ = self_inner
        return actual_shift_storage[0]

    original_type.beam_shift = property(inaccurate_get, inaccurate_set)  # type: ignore

    try:
        result = microscope.set_beam_shift_with_verification(requested)
    finally:
        original_type.beam_shift = original_property  # type: ignore

    assert result is False


def test_set_beam_shift_with_verification_returns_false_when_setter_raises():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)

    original_type = type(microscope.beam)
    original_property = original_type.beam_shift
    call_count = [0]

    def raising_on_first_set(self_inner: Any, value: BeamShift) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Beam shift out of range")
        original_property.fset(self_inner, value)  # type: ignore

    original_type.beam_shift = property(original_property.fget, raising_on_first_set)  # type: ignore

    try:
        result = microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))
    finally:
        original_type.beam_shift = original_property  # type: ignore

    assert result is False


def test_set_beam_shift_with_verification_logs_warning_on_fallback():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)

    original_type = type(microscope.beam)
    original_property = original_type.beam_shift
    call_count = [0]

    def raising_on_first_set(self_inner: Any, value: BeamShift) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Beam shift out of range")
        original_property.fset(self_inner, value)  # type: ignore

    original_type.beam_shift = property(original_property.fget, raising_on_first_set)  # type: ignore

    try:
        microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))
    finally:
        original_type.beam_shift = original_property  # type: ignore

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("Beam shift error" in r.message for r in txt_log.records)


def test_set_beam_shift_with_verification_resets_beam_shift_to_zero_on_fallback():
    microscope = _make_microscope()

    original_type = type(microscope.beam)
    original_property = original_type.beam_shift
    call_count = [0]

    def raising_on_first_set(self_inner: Any, value: BeamShift) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Beam shift out of range")
        original_property.fset(self_inner, value)  # type: ignore

    original_type.beam_shift = property(original_property.fget, raising_on_first_set)  # type: ignore

    try:
        microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))
    finally:
        original_type.beam_shift = original_property  # type: ignore

    assert np.isclose(microscope.beam.beam_shift.x, 0.0)
    assert np.isclose(microscope.beam.beam_shift.y, 0.0)


def test_set_beam_shift_with_verification_moves_stage_on_fallback():
    microscope = _make_microscope()
    initial_position = microscope._control.stage_position

    original_type = type(microscope.beam)
    original_property = original_type.beam_shift
    call_count = [0]

    def raising_on_first_set(self_inner: Any, value: BeamShift) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Beam shift out of range")
        original_property.fset(self_inner, value)  # type: ignore

    original_type.beam_shift = property(original_property.fget, raising_on_first_set)  # type: ignore

    try:
        microscope.set_beam_shift_with_verification(BeamShift(10.0, 20.0))
    finally:
        original_type.beam_shift = original_property  # type: ignore

    final_position = microscope._control.stage_position
    assert not np.isclose(final_position.x, initial_position.x) or not np.isclose(
        final_position.y, initial_position.y
    )


def test_add_beam_shift_with_verification_adds_to_current_shift():
    microscope = _make_microscope()
    microscope.beam.beam_shift = BeamShift(10.0, 20.0)

    microscope.add_beam_shift_with_verification(BeamShift(5.0, 3.0))

    assert np.isclose(microscope.beam.beam_shift.x, 15.0)
    assert np.isclose(microscope.beam.beam_shift.y, 23.0)


def test_add_beam_shift_with_verification_returns_true_within_tolerance():
    microscope = _make_microscope()

    result = microscope.add_beam_shift_with_verification(BeamShift(5.0, 3.0))

    assert result is True


def test_add_beam_shift_with_verification_uses_specified_beam():
    microscope = _make_microscope()
    microscope.ion_beam.beam_shift = BeamShift(10.0, 0.0)

    microscope.add_beam_shift_with_verification(
        BeamShift(5.0, 0.0), microscope.ion_beam
    )

    assert np.isclose(microscope.ion_beam.beam_shift.x, 15.0)
    assert np.isclose(microscope.electron_beam.beam_shift.x, 0.0)


def test_prop_names_returns_property_names_instance():
    microscope = _make_microscope()

    result = microscope.prop_names

    assert isinstance(result, PropertyNames)


def test_prop_names_microscope_includes_model_fields():
    microscope = _make_microscope()

    result = microscope.prop_names

    assert "stage_position" in result.microscope


def test_prop_names_microscope_includes_manufacturer_properties():
    microscope = _make_microscope()

    result = microscope.prop_names

    assert "microscope.custom_parameter" in result.microscope
    assert "microscope.inner.parameter" in result.microscope


def test_prop_names_electron_beam_contains_beam_properties():
    microscope = _make_microscope()

    result = microscope.prop_names

    assert "beam.custom_parameter" in result.electron_beam
    assert "beam.inner.parameter" in result.electron_beam


def test_prop_names_ion_beam_contains_beam_properties():
    microscope = _make_microscope()

    result = microscope.prop_names

    assert "beam.custom_parameter" in result.ion_beam
    assert "beam.inner.parameter" in result.ion_beam


def test_set_properties_sets_stage_position():
    microscope = _make_microscope()
    props = GlobalProperties(
        microscope=MicroscopeProperties(
            stage_position=StagePosition(x=1000.0, y=2000.0)
        )
    )

    microscope.set_properties(props, beam=None)

    assert np.isclose(microscope._control.stage_position.x, 1000.0)
    assert np.isclose(microscope._control.stage_position.y, 2000.0)


def test_set_properties_sets_manufacturer_property():
    microscope = _make_microscope()
    props = GlobalProperties(
        microscope=MicroscopeProperties(**{"microscope.custom_parameter": 42.0})  # type: ignore
    )

    microscope.set_properties(props, beam=None)

    assert np.isclose(
        microscope._control.manufacturer_prop("microscope.custom_parameter"), 42.0
    )


def test_set_properties_raises_on_invalid_manufacturer_property():
    microscope = _make_microscope()

    original_set = microscope._control.set_manufacturer_prop

    def raising_set(name: str, value: Any) -> None:
        _ = name, value
        raise RuntimeError("hardware error")

    microscope._control.set_manufacturer_prop = raising_set

    try:
        props = GlobalProperties(
            microscope=MicroscopeProperties(**{"microscope.custom_parameter": 42.0})  # type: ignore
        )
        with pytest.raises(MicroscopeError):
            microscope.set_properties(props, beam=None)
    finally:
        microscope._control.set_manufacturer_prop = original_set


def test_set_properties_sets_electron_beam_properties():
    microscope = _make_microscope()
    props = GlobalProperties(electron_beam=BeamProperties(working_distance=5_000_000.0))

    microscope.set_properties(props, beam=BeamType.ELECTRON)

    assert np.isclose(microscope.electron_beam.working_distance, 5_000_000.0)


def test_set_properties_sets_ion_beam_properties():
    microscope = _make_microscope()
    props = GlobalProperties(ion_beam=BeamProperties(working_distance=3_000_000.0))

    microscope.set_properties(props, beam=BeamType.ION)

    assert np.isclose(microscope.ion_beam.working_distance, 3_000_000.0)


def test_set_properties_skips_electron_beam_when_ion_beam_selected():
    microscope = _make_microscope()
    props = GlobalProperties(
        electron_beam=BeamProperties(working_distance=5_000_000.0),
        ion_beam=BeamProperties(working_distance=3_000_000.0),
    )

    microscope.set_properties(props, beam=BeamType.ION)

    assert np.isclose(microscope.electron_beam.working_distance, 0.0)
    assert np.isclose(microscope.ion_beam.working_distance, 3_000_000.0)


def test_set_properties_skips_ion_beam_when_electron_beam_selected():
    microscope = _make_microscope()
    props = GlobalProperties(
        electron_beam=BeamProperties(working_distance=5_000_000.0),
        ion_beam=BeamProperties(working_distance=3_000_000.0),
    )

    microscope.set_properties(props, beam=BeamType.ELECTRON)

    assert np.isclose(microscope.electron_beam.working_distance, 5_000_000.0)
    assert np.isclose(microscope.ion_beam.working_distance, 0.0)


def test_set_properties_sets_both_beams_when_beam_is_none():
    microscope = _make_microscope()
    props = GlobalProperties(
        electron_beam=BeamProperties(working_distance=5_000_000.0),
        ion_beam=BeamProperties(working_distance=3_000_000.0),
    )

    microscope.set_properties(props, beam=None)

    assert np.isclose(microscope.electron_beam.working_distance, 5_000_000.0)
    assert np.isclose(microscope.ion_beam.working_distance, 3_000_000.0)


def test_set_properties_handles_beam_shift_for_electron_beam():
    microscope = _make_microscope()
    props = GlobalProperties(
        electron_beam=BeamProperties(beam_shift=BeamShift(10.0, 20.0))
    )

    microscope.set_properties(props, beam=BeamType.ELECTRON)

    assert np.isclose(microscope.electron_beam.beam_shift.x, 10.0)
    assert np.isclose(microscope.electron_beam.beam_shift.y, 20.0)


def test_set_properties_clears_beam_shift_from_properties_after_applying():
    microscope = _make_microscope()
    props = GlobalProperties(
        electron_beam=BeamProperties(beam_shift=BeamShift(10.0, 20.0))
    )

    microscope.set_properties(props, beam=BeamType.ELECTRON)

    assert props.electron_beam is not None
    assert props.electron_beam.beam_shift is None


def test_collect_properties_returns_global_properties_instance():
    microscope = _make_microscope()

    result = microscope.collect_properties(PropertyNames())

    assert isinstance(result, GlobalProperties)


def test_collect_properties_collects_stage_position():
    microscope = _make_microscope()
    microscope._control.try_set_stage_position(StagePosition(x=1000.0, y=2000.0))

    result = microscope.collect_properties(PropertyNames(microscope=["stage_position"]))

    assert result.microscope is not None
    assert result.microscope.stage_position is not None
    assert np.isclose(result.microscope.stage_position.x, 1000.0)
    assert np.isclose(result.microscope.stage_position.y, 2000.0)


def test_collect_properties_collects_manufacturer_property():
    microscope = _make_microscope()
    microscope._control.set_manufacturer_prop("microscope.custom_parameter", 99.0)

    result = microscope.collect_properties(
        PropertyNames(microscope=["microscope.custom_parameter"])
    )

    assert np.isclose(getattr(result.microscope, "microscope.custom_parameter"), 99.0)


def test_collect_properties_skips_properties_not_in_list():
    microscope = _make_microscope()
    microscope._control.try_set_stage_position(StagePosition(x=1000.0, y=2000.0))

    result = microscope.collect_properties(PropertyNames(microscope=[]))

    assert result.microscope is not None
    assert result.microscope.stage_position is None


def test_collect_properties_logs_warning_for_unknown_properties():
    txt_log = MemoryTextLogger()
    microscope = _make_microscope(txt_log)

    microscope.collect_properties(PropertyNames(microscope=["nonexistent_property"]))

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("nonexistent_property" in r.message for r in txt_log.records)


def test_collect_properties_collects_electron_beam_properties():
    microscope = _make_microscope()
    microscope.electron_beam.working_distance = 5_000_000.0

    result = microscope.collect_properties(
        PropertyNames(electron_beam=["working_distance"])
    )

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert np.isclose(result.electron_beam.working_distance, 5_000_000.0)


def test_collect_properties_collects_ion_beam_properties():
    microscope = _make_microscope()
    microscope.ion_beam.working_distance = 3_000_000.0

    result = microscope.collect_properties(PropertyNames(ion_beam=["working_distance"]))

    assert result.ion_beam is not None
    assert result.ion_beam.working_distance is not None
    assert np.isclose(result.ion_beam.working_distance, 3_000_000.0)


def test_collect_properties_collects_both_beams_independently():
    microscope = _make_microscope()
    microscope.electron_beam.working_distance = 5_000_000.0
    microscope.ion_beam.working_distance = 3_000_000.0

    result = microscope.collect_properties(
        PropertyNames(
            electron_beam=["working_distance"],
            ion_beam=["working_distance"],
        )
    )

    assert result.electron_beam is not None
    assert result.electron_beam.working_distance is not None
    assert result.ion_beam is not None
    assert result.ion_beam.working_distance is not None
    assert np.isclose(result.electron_beam.working_distance, 5_000_000.0)
    assert np.isclose(result.ion_beam.working_distance, 3_000_000.0)


def _make_microscope_with_stage_position(
    tilt: float = 0.0,
    rotation: float = 0.0,
    pretilt: float = 0.0,
) -> Microscope:
    settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=pretilt,
    )
    microscope = Microscope(settings, MemoryTextLogger())

    microscope.set_stage_position_with_verification(
        StagePosition(x=0, y=0, z=0, rotation=rotation, tilt=tilt)
    )

    return microscope


def test_beam_shift_to_stage_move_returns_2x2_matrix():
    microscope = _make_microscope_with_stage_position()

    matrix = microscope._beam_shift_to_stage_move()

    assert matrix.shape == (2, 2)


def test_beam_shift_to_stage_move_zero_tilt_and_rotation_returns_identity():
    microscope = _make_microscope_with_stage_position()

    matrix = microscope._beam_shift_to_stage_move()

    np.testing.assert_allclose(matrix, np.eye(2))


def test_beam_shift_to_stage_move_pure_tilt_scales_y_only():
    tilt = 60.0
    microscope = _make_microscope_with_stage_position(tilt=tilt)

    matrix = microscope._beam_shift_to_stage_move()

    expected = np.array([[1.0, 0.0], [0.0, 1.0 / np.cos(np.radians(tilt))]])

    np.testing.assert_allclose(matrix, expected)


def test_beam_shift_to_stage_move_holder_pretilt_is_added():
    stage_tilt = 20.0
    pretilt = 30.0
    effective = stage_tilt + pretilt

    microscope = _make_microscope_with_stage_position(
        tilt=stage_tilt,
        pretilt=pretilt,
    )

    matrix = microscope._beam_shift_to_stage_move()

    expected_scale = 1.0 / np.cos(np.radians(effective))
    assert np.isclose(matrix[1, 1], expected_scale)


def test_beam_shift_to_stage_move_rotation_only_returns_identity():
    microscope = _make_microscope_with_stage_position(rotation=45.0)

    matrix = microscope._beam_shift_to_stage_move()

    np.testing.assert_allclose(matrix, np.eye(2), atol=1e-6)


def test_beam_shift_to_stage_matrix_effective_tilt_near_90_raises() -> None:
    microscope = _make_microscope_with_stage_position(tilt=89.999)

    with pytest.raises(MicroscopeError):
        microscope._beam_shift_to_stage_move()


def test_beam_shift_to_stage_matrix_pretilt_can_trigger_singularity() -> None:
    microscope = _make_microscope_with_stage_position(
        tilt=30.0,
        pretilt=60.0,
    )

    with pytest.raises(MicroscopeError):
        microscope._beam_shift_to_stage_move()


def test_beam_shift_to_stage_move_custom_scale_factors_are_applied():
    microscope = _make_microscope_with_stage_position()
    microscope._control.electron_beam._beam_shift_to_stage_move = (2.0, 3.0)  # type: ignore

    matrix = microscope._beam_shift_to_stage_move()

    assert np.isclose(matrix[0, 0], 2.0)
    assert np.isclose(matrix[1, 1], 3.0)
