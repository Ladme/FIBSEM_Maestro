# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.properties.beam_properties import BeamProperties


def test_beam_properties_get_property_names_returns_empty_when_all_none():
    props = BeamProperties()

    assert props.get_property_names() == []


def test_beam_properties_get_property_names_returns_set_fields():
    props = BeamProperties(working_distance=5_000_000.0, pixel_size=2.0)

    names = props.get_property_names()

    assert "working_distance" in names
    assert "pixel_size" in names


def test_beam_properties_get_property_names_excludes_none_fields():
    props = BeamProperties(working_distance=5_000_000.0)

    names = props.get_property_names()

    assert "pixel_size" not in names
    assert "working_distance" in names


def test_beam_properties_get_property_names_returns_all_set_fields():
    props = BeamProperties(
        working_distance=5_000_000.0,
        pixel_size=2.0,
        detector_contrast=0.5,
        detector_brightness=0.6,
    )

    names = props.get_property_names()

    assert len(names) == 4
    assert set(names) == {
        "working_distance",
        "pixel_size",
        "detector_contrast",
        "detector_brightness",
    }
