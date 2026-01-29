# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.core.stigmator import Stigmator
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.simulated.microscope_control import (
    SimulatedMicroscopeControl,
)
from fibsem_maestro.settings.beam_properties import BeamProperties
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.property_names import PropertyNames


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


def create_test_microscope_control() -> SimulatedMicroscopeControl:
    """Create a test instance of SimulatedMicroscopeControl."""
    txt_log = InMemoryTextLogger()
    return SimulatedMicroscopeControl(ip_address="127.0.0.1", txt_log=txt_log, seed=42)  # type: ignore


def test_set_properties_microscope_only():
    """
    Test setting microscope properties only.
    """
    microscope_control = create_test_microscope_control()
    microscope_properties = MicroscopeProperties(
        stage_position=StagePosition(x=1.0, y=2.0, z=3.0, rotation=4.0, tilt=5.0),
    )
    setattr(microscope_properties, "microscope.custom_parameter", 0.7)
    setattr(microscope_properties, "microscope.inner.parameter", 2.1)
    properties = GlobalProperties(
        microscope=microscope_properties,
        electron_beam=None,
        ion_beam=None,
    )

    microscope_control.set_properties(properties, beam=None)

    stage_position = microscope_control.stage_position
    assert abs(stage_position.x - 1.0) < 0.5  # allowing for noise
    assert abs(stage_position.y - 2.0) < 0.5
    assert abs(stage_position.z - 3.0) < 0.5
    assert abs(stage_position.rotation - 4.0) < 0.005
    assert abs(stage_position.tilt - 5.0) < 0.005

    assert microscope_control.manufacturer_prop("microscope.custom_parameter") == 0.7
    assert microscope_control.manufacturer_prop("microscope.inner.parameter") == 2.1


def test_set_properties_electron_beam_only():
    microscope_control = create_test_microscope_control()
    electron_beam_properties = BeamProperties(
        working_distance=10_000_000.0,
        stigmator=Stigmator(1.0, 2.0),
    )  # type: ignore
    setattr(electron_beam_properties, "beam.custom_parameter", 0.7)

    properties = GlobalProperties(
        microscope=None, electron_beam=electron_beam_properties, ion_beam=None
    )

    microscope_control.set_properties(properties, beam=BeamType.ELECTRON)

    electron_beam = microscope_control.electron_beam
    assert electron_beam.working_distance == 10_000_000.0
    assert electron_beam.stigmator == Stigmator(1.0, 2.0)
    assert electron_beam.manufacturer_prop("beam.custom_parameter") == 0.7


def test_set_properties_ion_beam_only():
    microscope_control = create_test_microscope_control()
    ion_beam_properties = BeamProperties(
        working_distance=10_000_000.0,
        stigmator=Stigmator(1.0, 2.0),
    )  # type: ignore
    setattr(ion_beam_properties, "beam.custom_parameter", 0.7)

    properties = GlobalProperties(
        microscope=None, electron_beam=None, ion_beam=ion_beam_properties
    )

    microscope_control.set_properties(properties, beam=BeamType.ION)

    ion_beam = microscope_control.ion_beam
    assert ion_beam.working_distance == 10_000_000.0
    assert ion_beam.stigmator == Stigmator(1.0, 2.0)
    assert ion_beam.manufacturer_prop("beam.custom_parameter") == 0.7


def test_set_properties_both_beams():
    microscope_control = create_test_microscope_control()
    electron_beam_properties = BeamProperties(
        working_distance=10_000_000.0,
        stigmator=Stigmator(1.0, 2.0),
    )  # type: ignore
    setattr(electron_beam_properties, "beam.custom_parameter", 0.7)

    ion_beam_properties = BeamProperties(
        working_distance=10_000_000.0,
        stigmator=Stigmator(3.0, 4.0),
    )  # type: ignore
    setattr(ion_beam_properties, "beam.custom_parameter", 0.9)

    properties = GlobalProperties(
        microscope=None,
        electron_beam=electron_beam_properties,
        ion_beam=ion_beam_properties,
    )

    microscope_control.set_properties(properties, beam=None)

    electron_beam = microscope_control.electron_beam
    assert electron_beam.working_distance == 10_000_000.0
    assert electron_beam.stigmator == Stigmator(1.0, 2.0)
    assert electron_beam.manufacturer_prop("beam.custom_parameter") == 0.7

    ion_beam = microscope_control.ion_beam
    assert ion_beam.working_distance == 10_000_000.0
    assert ion_beam.stigmator == Stigmator(3.0, 4.0)
    assert ion_beam.manufacturer_prop("beam.custom_parameter") == 0.9


def test_collect_properties():
    microscope_control = create_test_microscope_control()
    microscope_control.try_set_stage_position(
        StagePosition(x=1.0, y=2.0, z=3.0, rotation=4.0, tilt=5.0)
    )
    microscope_control.set_manufacturer_prop("microscope.custom_parameter", 0.7)

    electron_beam = microscope_control.electron_beam
    electron_beam.working_distance = 10_000_000.0
    electron_beam.stigmator = Stigmator(1.0, 2.0)
    electron_beam.set_manufacturer_prop("beam.custom_parameter", 0.7)

    ion_beam = microscope_control.ion_beam
    ion_beam.working_distance = 10_000_000.0
    ion_beam.stigmator = Stigmator(3.0, 4.0)
    ion_beam.set_manufacturer_prop("beam.custom_parameter", 0.9)

    selected_properties = PropertyNames(
        microscope=["stage_position", "microscope.custom_parameter"],
        electron_beam=["working_distance", "beam.custom_parameter"],
        ion_beam=["stigmator", "beam.custom_parameter"],
    )

    collected_properties = microscope_control.collect_properties(selected_properties)

    stage_position = microscope_control.stage_position
    assert abs(stage_position.x - 1.0) < 0.5  # allowing for noise
    assert abs(stage_position.y - 2.0) < 0.5
    assert abs(stage_position.z - 3.0) < 0.5
    assert abs(stage_position.rotation - 4.0) < 0.005
    assert abs(stage_position.tilt - 5.0) < 0.005
    assert (
        getattr(collected_properties.microscope, "microscope.custom_parameter") == 0.7
    )

    assert (
        getattr(collected_properties.electron_beam, "working_distance") == 10_000_000.0
    )
    assert getattr(collected_properties.electron_beam, "stigmator") is None
    assert getattr(collected_properties.electron_beam, "beam.custom_parameter") == 0.7

    assert getattr(collected_properties.ion_beam, "working_distance") is None
    assert getattr(collected_properties.ion_beam, "stigmator") == Stigmator(3.0, 4.0)
    assert getattr(collected_properties.ion_beam, "beam.custom_parameter") == 0.9
