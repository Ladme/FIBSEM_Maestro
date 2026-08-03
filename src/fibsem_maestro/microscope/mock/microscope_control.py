# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Any

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.microscope.mock.beam_control import (
    MockElectronBeamControl,
    MockIonBeamControl,
)
from fibsem_maestro.microscope.registry import MICROSCOPE_CONTROLS


@MICROSCOPE_CONTROLS.register("mock")
class MockMicroscopeControl(MicroscopeControl):
    """Minimal mock implementation of MicroscopeControl for testing."""

    def __init__(self, ip_address: str, port: int | None, txt_log: TextLogger):
        self._ip_address = ip_address
        self._port = port
        self._txt_log = txt_log

        self._stage_position = StagePosition(
            x=0.0, y=0.0, z=0.0, rotation=0.0, tilt=0.0
        )

        self._electron_beam = MockElectronBeamControl(
            self._txt_log.derive("electron_beam")
        )
        self._ion_beam = MockIonBeamControl(self._txt_log.derive("ion_beam"))

        self._manufacturer_properties: dict[str, Any] = {
            "microscope.custom_parameter": 0.0,
            "microscope.inner.parameter": 0.0,
        }

    @property
    def stage_position(self) -> StagePosition:
        return self._stage_position

    @property
    def electron_beam(self) -> BeamControl:
        return self._electron_beam

    @electron_beam.setter
    def electron_beam(self, beam: BeamControl) -> None:
        self._electron_beam = beam

    @property
    def ion_beam(self) -> BeamControl:
        return self._ion_beam

    @ion_beam.setter
    def ion_beam(self, beam: BeamControl) -> None:
        self._ion_beam = beam

    def manufacturer_prop(self, name: str) -> Any:
        return self._manufacturer_properties[name]

    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        self._manufacturer_properties[name] = value

    @property
    def manufacturer_prop_names(self) -> list[str]:
        return list(self._manufacturer_properties.keys())

    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        self._stage_position = pos
        return self._stage_position

    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        self._stage_position = StagePosition(
            x=self._stage_position.x + delta.x,
            y=self._stage_position.y + delta.y,
            z=self._stage_position.z + delta.z,
            rotation=self._stage_position.rotation + delta.rotation,
            tilt=self._stage_position.tilt + delta.tilt,
        )
        return self._stage_position

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log
