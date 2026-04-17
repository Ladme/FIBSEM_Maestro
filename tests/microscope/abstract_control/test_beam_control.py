# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

import numpy as np
import pytest

from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.mock.beam_control import MockBeamControl
from fibsem_maestro.properties.beam_properties import BeamProperties


def _make_beam() -> MockBeamControl:
    return MockBeamControl(MemoryTextLogger())


def test_stigmator_x_getter_returns_x_component():
    beam = _make_beam()
    beam.stigmator = Stigmator(0.3, 0.7)

    assert np.isclose(beam.stigmator_x, 0.3)


def test_stigmator_x_setter_updates_x_preserves_y():
    beam = _make_beam()
    beam.stigmator = Stigmator(0.1, 0.5)

    beam.stigmator_x = 0.9

    assert np.isclose(beam.stigmator.x, 0.9)
    assert np.isclose(beam.stigmator.y, 0.5)


def test_stigmator_y_getter_returns_y_component():
    beam = _make_beam()
    beam.stigmator = Stigmator(0.3, 0.7)

    assert np.isclose(beam.stigmator_y, 0.7)


def test_stigmator_y_setter_updates_y_preserves_x():
    beam = _make_beam()
    beam.stigmator = Stigmator(0.1, 0.5)

    beam.stigmator_y = 0.8

    assert np.isclose(beam.stigmator.y, 0.8)
    assert np.isclose(beam.stigmator.x, 0.1)


def test_lens_alignment_x_getter_returns_x_component():
    beam = _make_beam()
    beam.lens_alignment = LensAlignment(100.0, 200.0)

    assert np.isclose(beam.lens_alignment_x, 100.0)


def test_lens_alignment_x_setter_updates_x_preserves_y():
    beam = _make_beam()
    beam.lens_alignment = LensAlignment(100.0, 200.0)

    beam.lens_alignment_x = 300.0

    assert np.isclose(beam.lens_alignment.x, 300.0)
    assert np.isclose(beam.lens_alignment.y, 200.0)


def test_lens_alignment_y_getter_returns_y_component():
    beam = _make_beam()
    beam.lens_alignment = LensAlignment(100.0, 200.0)

    assert np.isclose(beam.lens_alignment_y, 200.0)


def test_lens_alignment_y_setter_updates_y_preserves_x():
    beam = _make_beam()
    beam.lens_alignment = LensAlignment(100.0, 200.0)

    beam.lens_alignment_y = 400.0

    assert np.isclose(beam.lens_alignment.y, 400.0)
    assert np.isclose(beam.lens_alignment.x, 100.0)


def test_total_blanked_sets_contrast_and_brightness_to_zero():
    beam = _make_beam()
    beam.detector_contrast = 0.8
    beam.detector_brightness = 0.6

    with beam.total_blanked():
        assert np.isclose(beam.detector_contrast, 0.0)
        assert np.isclose(beam.detector_brightness, 0.0)


def test_total_blanked_blanks_beam_during_block():
    beam = _make_beam()

    with beam.total_blanked():
        assert beam._blanked is True


def test_total_blanked_restores_contrast_and_brightness_after_block():
    beam = _make_beam()
    beam.detector_contrast = 0.8
    beam.detector_brightness = 0.6

    with beam.total_blanked():
        pass

    assert np.isclose(beam.detector_contrast, 0.8)
    assert np.isclose(beam.detector_brightness, 0.6)


def test_total_blanked_unblanks_beam_after_block():
    beam = _make_beam()

    with beam.total_blanked():
        pass

    assert beam._blanked is False


def test_total_blanked_restores_state_on_exception():
    beam = _make_beam()
    beam.detector_contrast = 0.8
    beam.detector_brightness = 0.6

    with pytest.raises(RuntimeError), beam.total_blanked():
        raise RuntimeError("simulated failure")

    assert np.isclose(beam.detector_contrast, 0.8)
    assert np.isclose(beam.detector_brightness, 0.6)
    assert beam._blanked is False


def test_get_property_names_returns_list_of_strings():
    result = MockBeamControl.get_property_names()

    assert isinstance(result, list)
    assert all(isinstance(name, str) for name in result)


def test_get_property_names_includes_known_properties():
    result = MockBeamControl.get_property_names()

    assert "working_distance" in result
    assert "pixel_size" in result
    assert "beam_shift" in result


def test_prop_names_includes_beam_properties_fields():
    beam = _make_beam()

    assert "working_distance" in beam.prop_names
    assert "pixel_size" in beam.prop_names


def test_prop_names_includes_manufacturer_properties():
    beam = _make_beam()

    assert "beam.custom_parameter" in beam.prop_names
    assert "beam.inner.parameter" in beam.prop_names


def test_set_properties_applies_standard_property():
    beam = _make_beam()

    beam.set_properties(BeamProperties(working_distance=5_000_000.0))

    assert np.isclose(beam.working_distance, 5_000_000.0)


def test_set_properties_applies_manufacturer_property():
    beam = _make_beam()

    beam.set_properties(BeamProperties(**{"beam.custom_parameter": 42.0}))  # type: ignore

    assert np.isclose(beam.manufacturer_prop("beam.custom_parameter"), 42.0)


def test_set_properties_skips_none_values():
    beam = _make_beam()
    beam.working_distance = 5_000_000.0

    beam.set_properties(BeamProperties(working_distance=None))

    assert np.isclose(beam.working_distance, 5_000_000.0)


def test_set_properties_raises_on_failed_manufacturer_property():
    beam = _make_beam()

    original = beam.set_manufacturer_prop

    def failing_set(name: str, value: Any) -> None:
        _ = name, value
        raise RuntimeError("hardware error")

    beam.set_manufacturer_prop = failing_set

    try:
        with pytest.raises(MicroscopeError):
            beam.set_properties(BeamProperties(**{"beam.custom_parameter": 1.0}))  # type: ignore
    finally:
        beam.set_manufacturer_prop = original


def test_collect_properties_returns_beam_properties_instance():
    beam = _make_beam()

    result = beam.collect_properties([])

    assert isinstance(result, BeamProperties)


def test_collect_properties_collects_selected_property():
    beam = _make_beam()
    beam.working_distance = 5_000_000.0

    result = beam.collect_properties(["working_distance"])

    assert result.working_distance is not None
    assert np.isclose(result.working_distance, 5_000_000.0)


def test_collect_properties_skips_unselected_properties():
    beam = _make_beam()
    beam.working_distance = 5_000_000.0

    result = beam.collect_properties([])

    assert result.working_distance is None


def test_collect_properties_collects_manufacturer_property():
    beam = _make_beam()
    beam.set_manufacturer_prop("beam.custom_parameter", 99.0)

    result = beam.collect_properties(["beam.custom_parameter"])

    assert np.isclose(getattr(result, "beam.custom_parameter"), 99.0)


def test_collect_properties_logs_warning_for_unknown_property():
    txt_log = MemoryTextLogger()
    beam = MockBeamControl(txt_log)

    beam.collect_properties(["nonexistent_property"])

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("nonexistent_property" in r.message for r in txt_log.records)
