# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Any

from autoscript_sdb_microscope_client.sdb_microscope_client import SdbMicroscopeClient

from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.microscope.autoscript_control.beam_control import (
    AutoscriptElectronBeamControl,
    AutoscriptIonBeamControl,
)
from fibsem_maestro.microscope.internal_params import InternalParametersRegistry
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry


@MicroscopeRegistry.register("autoscript")
class AutoscriptMicroscopeControl(MicroscopeControl):
    def __init__(self, ip_address: str, txt_log: TextLogger):
        self._txt_log = txt_log
        self._microscope = SdbMicroscopeClient()
        if ":" in ip_address:
            ip_address, port = ip_address.split(":")

            try:
                port = int(port)
            except ValueError as e:
                raise MicroscopeError(f"Invalid port number {port}") from e

            self._microscope.connect(ip_address, port)
            self._txt_log.info(f"Connecting to {ip_address}:{port}.")
        else:
            self._microscope.connect(ip_address)
            self._txt_log.info(f"Connecting to {ip_address}.")

        self._custom_properties = InternalParametersRegistry(self._microscope)

        self._electron_beam: BeamControl = AutoscriptElectronBeamControl(
            self._microscope,
            self._custom_properties,
            self._txt_log,
        )
        self._ion_beam: BeamControl = AutoscriptIonBeamControl(
            self._microscope,
            self._custom_properties,
            self._txt_log,
        )

    @property
    def stage_position(self):
        self._microscope.specimen.stage.unlink()

        p = StagePosition.from_stage_position_autoscript(
            self._microscope.specimen.stage.current_position
        )

        self._txt_log.debug(f"Getting stage position {p}.")
        return p

    @property
    def electron_beam(self) -> BeamControl:
        return self._electron_beam

    @electron_beam.setter
    def electron_beam(self, beam: BeamControl):
        self._electron_beam = beam

    @property
    def ion_beam(self) -> BeamControl:
        return self._ion_beam

    @ion_beam.setter
    def ion_beam(self, beam: BeamControl):
        self._ion_beam = beam

    def custom(self, name: str) -> Any:
        property = self._custom_properties.get(name)
        return property.get()

    def set_custom(self, name: str, value: Any) -> Any:
        property = self._custom_properties.get(name)
        property.set(value)

    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        self._microscope.specimen.stage.unlink()
        pos_autoscript = pos.to_stage_position_autoscript()

        self._microscope.specimen.stage.absolute_move(pos_autoscript)
        self._txt_log.debug(f"Moving stage to {pos}.")

        return self.stage_position

    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        # TODO: shouldn't the stage be unlinked?
        delta_autoscript = delta.to_stage_position_autoscript()
        self._microscope.specimen.stage.relative_move(delta_autoscript)

        self._txt_log.debug(f"Moving stage by {delta}.")
        return self.stage_position
