# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod
from typing import Any

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.microscope_properties import (
    MicroscopeProperties,
)
from fibsem_maestro.settings.property_names import (
    PropertyNames,
)


class MicroscopeControl(ABC):
    """
    Abstract interface for controlling a microscope and its major subsystems.
    """

    @abstractmethod
    def __init__(self, ip_address: str, txt_log: TextLogger):
        """
        Initialize the microscope control interface.

        Args:
            ip_address (str): Network address of the microscope.
            txt_log (TextLogger): Logger for recording events.
        """
        pass

    @property
    @abstractmethod
    def stage_position(self) -> StagePosition:
        """
        Get the current stage position.

        Returns:
            StagePosition: Current stage position.
        """
        pass

    @property
    @abstractmethod
    def electron_beam(self) -> BeamControl:
        """
        Get the electron beam control interface.

        Returns:
            BeamControl: Electron beam control.
        """
        pass

    @electron_beam.setter
    @abstractmethod
    def electron_beam(self, beam: BeamControl) -> None:
        """
        Set the electron beam control interface.

        Args:
            beam (BeamControl): Electron beam control.
        """
        pass

    @property
    @abstractmethod
    def ion_beam(self) -> BeamControl:
        """
        Get the ion beam control interface.

        Returns:
            BeamControl: Ion beam control.
        """
        pass

    @ion_beam.setter
    @abstractmethod
    def ion_beam(self, beam: BeamControl) -> None:
        """
        Set the ion beam control interface.

        Args:
            beam (BeamControl): Ion beam control.
        """
        pass

    @abstractmethod
    def manufacturer_prop(self, name: str) -> Any:
        """
        Get a manufacturer microscope property.

        Args:
            name (str): Property name.

        Returns:
            Any: Property value.
        """
        pass

    @abstractmethod
    def set_manufacturer_prop(self, name: str, value: Any) -> None:
        """
        Set a manufacturer microscope property.

        Args:
            name (str): Property name.
            value (Any): Property value.
        """
        pass

    @property
    @abstractmethod
    def manufacturer_prop_names(self) -> list[str]:
        """
        Get a list of all manufacturer properties of the microscope.

        Returns:
            list[str]: List of all manufacturer properties of the microscope.
        """
        pass

    @abstractmethod
    def try_set_stage_position(self, pos: StagePosition) -> StagePosition:
        """
        Attempt to set the stage to an absolute position.

        Args:
            pos (StagePosition): Target stage position.

        Returns:
            StagePosition: Actual stage position after the operation.
        """
        pass

    @abstractmethod
    def try_move_stage_position(self, delta: StagePosition) -> StagePosition:
        """
        Attempt to move the stage by a relative offset.

        Args:
            delta (StagePosition): Relative stage movement.

        Returns:
            StagePosition: Actual stage position after the operation.
        """
        pass

    @abstractmethod
    def try_set_beam_shift(self, shift: BeamShift) -> BeamShift:
        """
        Attempt to set the beam shift.

        Args:
            shift (BeamShift): Desired beam shift.

        Returns:
            BeamShift: Actual beam shift after the operation.
        """
        pass

    @property
    @abstractmethod
    def txt_log(self) -> TextLogger:
        pass

    @property
    def prop_names(self) -> PropertyNames:
        """
        Get a collection of all properties of the microscope and its beams,
        including the inner properties.

        Return:
            MicroscopePropertyNames: Collection of all the properties of the microscope and its beams.
        """
        properties = list(MicroscopeProperties.model_fields.keys())
        properties.extend(self.manufacturer_prop_names)

        electron_properties = self.electron_beam.prop_names
        ion_properties = self.ion_beam.prop_names

        return PropertyNames(
            microscope=properties,
            electron_beam=electron_properties,
            ion_beam=ion_properties,
        )

    def set_properties(
        self, properties: GlobalProperties, beam: BeamType | None
    ) -> None:
        """
        Apply properties to the microscope.

        Uses this control interface to set the microscope state to the values
        provided in the given properties container.

        Args:
            properties (GlobalProperties): Container of all the property values to apply.
            beam (BeamType): Type of the beam which properties should be set.
                Properties for the other beam are not set.
                If `None`, properties of both beams are set.
        """
        if (microscope := properties.microscope) is not None:
            if (stage_position := microscope.stage_position) is not None:
                self.try_set_stage_position(stage_position)

            # set manufacturer properties of the microscope
            for field_name in filter(
                lambda x: x in self.manufacturer_prop_names,
                microscope.model_dump(exclude_none=True).keys(),
            ):
                try:
                    value = getattr(microscope, field_name)
                    self.set_manufacturer_prop(field_name, value)
                    continue
                except Exception as e:
                    raise MicroscopeError(
                        f"Could not set manufacturer property '{field_name}': {e}"
                    ) from e

        if properties.electron_beam is not None and (
            beam is None or beam is BeamType.ELECTRON
        ):
            self.electron_beam.set_properties(properties.electron_beam)

        if properties.ion_beam is not None and (beam is None or beam is BeamType.ION):
            self.ion_beam.set_properties(properties.ion_beam)

    def collect_properties(
        self, selected_properties: PropertyNames
    ) -> GlobalProperties:
        # get field names to write out
        field_names = list(
            filter(
                lambda x: x in selected_properties.microscope,
                MicroscopeProperties.model_fields.keys(),
            )
        )

        # collect the values of the properties
        values = {}
        for field_name in field_names:
            values[field_name] = getattr(self, field_name)

        # collect internal properties
        for field_name in filter(
            lambda x: x in selected_properties.microscope, self.manufacturer_prop_names
        ):
            values[field_name] = self.manufacturer_prop(field_name)

        # get unknown properties
        unknown = [
            prop for prop in selected_properties.microscope if prop not in values
        ]
        if len(unknown) > 0:
            self.txt_log.warning(
                f"The following selected microscope properties are not known: {' '.join(unknown)}"
            )

        electron_beam_properties = self.electron_beam.collect_properties(
            selected_properties.electron_beam
        )
        ion_beam_properties = self.ion_beam.collect_properties(
            selected_properties.ion_beam
        )

        return GlobalProperties(
            microscope=MicroscopeProperties(**values),
            electron_beam=electron_beam_properties,
            ion_beam=ion_beam_properties,
        )
