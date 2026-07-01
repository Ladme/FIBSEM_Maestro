# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties


def test_microscope_properties_get_property_names_returns_empty_when_all_none():
    props = MicroscopeProperties()

    assert props.get_property_names() == []


def test_microscope_properties_get_property_names_returns_set_fields():
    props = MicroscopeProperties(stage_position=StagePosition(x=1000.0, y=2000.0))

    assert props.get_property_names() == ["stage_position"]
