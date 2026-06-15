# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from scipy.spatial import distance  # pyright: ignore[reportMissingTypeStubs]

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl
from fibsem_maestro.microscope.abstract_control.microscope_control import (
    MicroscopeControl,
)
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.registry import MICROSCOPE_CONTROLS
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames


class Microscope:
    """
    Central abstraction layer for controlling an electron microscope.

    Args:
        settings: Microscope configuration including the control type, IP address,
            stage tolerances, and holder pretilt.
        txt_log: Logger for diagnostic and status messages.
    """

    def __init__(
        self,
        settings: MicroscopeSettings,
        txt_log: TextLogger,
    ):
        self._txt_log = txt_log

        self._settings = settings

        if self._settings.port:
            try:
                port_int: int | None = int(self._settings.port)
            except ValueError:
                raise MicroscopeError("Invalid port: must be an integer or empty.")
        else:
            port_int: int | None = None

        self._control = MICROSCOPE_CONTROLS.get(settings.control)(
            self._settings.ip_address, port_int, self._txt_log
        )
        self.beam = self._control.electron_beam

    @property
    def electron_beam(self) -> BeamControl:
        """The electron beam control interface."""
        return self._control.electron_beam

    @property
    def ion_beam(self) -> BeamControl:
        """The ion beam control interface."""
        return self._control.ion_beam

    @property
    def control(self) -> MicroscopeControl:
        """The microscope control interface."""
        return self._control

    @property
    def settings(self) -> MicroscopeSettings:
        """The microscope settings."""
        return self._settings

    def set_beam(self, type: BeamType) -> None:
        """Set the active beam to the electron or ion beam.

        Updates `self.beam` to point to the selected beam control interface.
        Subsequent operations that use `self.beam` will act on the selected beam.

        Args:
            type: The beam type to activate, either `BeamType.ELECTRON` or `BeamType.ION`.
        """
        match type:
            case BeamType.ELECTRON:
                self.beam = self._control.electron_beam
            case BeamType.ION:
                self.beam = self._control.ion_beam

    def set_stage_position_with_verification(
        self, new_stage_position: StagePosition
    ) -> None:
        """
        Move the stage to an absolute position and verify the result.

        Attempts to set the stage position up to `stage_trials` times. After
        each attempt the Euclidean distance between the actual and target XY
        position is checked against `stage_tolerance`. If the distance is
        within tolerance the method returns immediately. If all attempts fail,
        a warning is logged for each failed attempt but no exception is raised.

        Args:
            new_stage_position: The target stage position in nanometers and degrees.
        """
        for attempt in range(1, self._settings.stage_trials + 1):
            # set position
            actual_position = self._control.try_set_stage_position(new_stage_position)

            # check whether the movement is within tolerance
            dist = distance.euclidean(
                actual_position.to_xy(), new_stage_position.to_xy()
            )

            if dist <= self._settings.stage_tolerance:
                # success
                return

            self._txt_log.warning(
                f"Stage off target (attempt {attempt}/{self._settings.stage_trials}): "
                f"target={new_stage_position}, actual={actual_position}, dist={dist:.3f} > tol={self._settings.stage_tolerance}"
            )

    def move_stage_position_with_verification(self, delta: StagePosition) -> None:
        """
        Move the stage by a relative offset and verify the result.

        Adds `delta` to the current stage position and delegates to
        `set_stage_position_with_verification`.

        Args:
            delta: The relative stage movement in nanometers and degrees.
        """
        self.set_stage_position_with_verification(self._control.stage_position + delta)

    def set_beam_shift_with_verification(
        self, new_beam_shift: BeamShift, beam: BeamControl | None = None
    ) -> bool:
        """
        Apply a beam shift and verify that it is within tolerance.

        Attempts to set the beam shift on the given beam.

        If the Euclidean distance between the requested and actual shift exceeds
        `beam_shift_tolerance` or if setting the beam shift fails internally,
        falls back to an equivalent stage move and resets the beam shift to zero.

        Args:
            new_beam_shift: The desired beam shift in nanometers.
            beam: The beam to shift. Defaults to the currently active beam.

        Returns:
            `True` if the beam shift was applied within tolerance, `False`
            if the fallback stage move was used instead.
        """
        beam = beam or self.beam
        beam_type = beam.beam_type()

        # try setting beam shift
        try:
            beam.beam_shift = new_beam_shift
            actual_beam_shift = beam.beam_shift

            dist = distance.euclidean(
                actual_beam_shift.to_tuple(), new_beam_shift.to_tuple()
            )

            if dist > self._settings.beam_shift_tolerance:
                raise MicroscopeError("Beam shift out of range.")

            return True
        except Exception as e:
            self._txt_log.warning(f"Beam shift error: {e}. Adjusting stage position.")

            beam_shift_to_stage_move = (
                self._settings.beam_shift_to_stage_move_electron
                if beam_type == BeamType.ELECTRON
                else self._settings.beam_shift_to_stage_move_ion
            )

            stage_move = [
                new_beam_shift.x * beam_shift_to_stage_move[0],
                new_beam_shift.y * beam_shift_to_stage_move[1],
            ]
            # move stage
            self.move_stage_position_with_verification(
                StagePosition(x=stage_move[0], y=stage_move[1])
            )
            # set beam shift to zero
            beam.beam_shift = BeamShift(0.0, 0.0)

            return False

    def add_beam_shift_with_verification(
        self, delta: BeamShift, beam: BeamControl | None = None
    ) -> bool:
        """
        Add a beam shift delta to the current shift and verify the result.

        Adds `delta` to the current beam shift and delegates to `set_beam_shift_with_verification`.

        Args:
            delta: The beam shift increment in nanometers.
            beam: The beam to shift. Defaults to the currently active beam.

        Returns:
            `True` if the resulting beam shift was applied within tolerance,
            `False` if the fallback stage move was used instead.
        """
        beam = beam or self.beam
        return self.set_beam_shift_with_verification(beam.beam_shift + delta, beam)

    @property
    def prop_names(self) -> PropertyNames:
        """
        All available property names across the microscope and both beams.

        Includes standard `MicroscopeProperties` fields, manufacturer-specific
        properties exposed by the control, and the property names of both beams.

        Returns:
            A `PropertyNames` instance listing all available property names.
        """
        properties = list(MicroscopeProperties.model_fields.keys())
        properties.extend(self._control.manufacturer_prop_names)

        electron_properties = self._control.electron_beam.prop_names
        ion_properties = self._control.ion_beam.prop_names

        return PropertyNames(
            microscope=properties,
            electron_beam=electron_properties,
            ion_beam=ion_properties,
        )

    def set_properties(
        self, properties: GlobalProperties, beam: BeamType | None
    ) -> None:
        """
        Apply a set of properties to the microscope and its beams.

        Sets stage position, manufacturer properties, and beam properties for
        the selected beam type. Beam shift is handled at this level rather than
        delegating to the beam control, since it may require a stage move as a
        fallback. After handling beam shift, the remaining beam properties are
        delegated to the beam control.

        Args:
            properties: The properties to apply to the microscope.
            beam: If specified, only properties for the selected beam and the
                microscope itself are applied. If `None`, properties for all
                beams are applied.

        Raises:
            MicroscopeError: If a manufacturer property cannot be set.
        """
        if (microscope := properties.microscope) is not None:
            if (stage_position := microscope.stage_position) is not None:
                self.set_stage_position_with_verification(stage_position)

            # set manufacturer properties of the microscope
            for field_name in filter(
                lambda x: x in self._control.manufacturer_prop_names,
                microscope.model_dump(exclude_none=True).keys(),
            ):
                try:
                    value = getattr(microscope, field_name)
                    self._control.set_manufacturer_prop(field_name, value)
                    continue
                except Exception as e:
                    raise MicroscopeError(
                        f"Could not set manufacturer property '{field_name}': {e}"
                    ) from e

        # set properties of the electron beam
        if properties.electron_beam is not None and (
            beam is None or beam is BeamType.ELECTRON
        ):
            # beam shift has to be handled on this level since stage movement can be required
            if (beam_shift := properties.electron_beam.beam_shift) is not None:
                self.set_beam_shift_with_verification(
                    beam_shift, self._control.electron_beam
                )
                properties.electron_beam.beam_shift = None

            self._control.electron_beam.set_properties(properties.electron_beam)

        # set properties of the ion beam
        if properties.ion_beam is not None and (beam is None or beam is BeamType.ION):
            if (beam_shift := properties.ion_beam.beam_shift) is not None:
                self.set_beam_shift_with_verification(
                    beam_shift, self._control.ion_beam
                )
                properties.ion_beam.beam_shift = None

            self._control.ion_beam.set_properties(properties.ion_beam)

    def collect_properties(
        self, properties_to_collect: PropertyNames
    ) -> GlobalProperties:
        """
        Read the current microscope state into a `GlobalProperties` instance.

        Collects only the properties listed in `properties_to_collect`.

        Standard `MicroscopeProperties` fields are read from the control
        directly; manufacturer-specific properties are retrieved via
        `manufacturer_prop`. Unknown property names are logged as warnings
        and excluded from the result.

        Args:
            properties_to_collect: The names of the properties to collect from
                the microscope and each beam.

        Returns:
            A `GlobalProperties` instance containing the collected values.
        """
        # get field names to write out
        field_names = list(
            filter(
                lambda x: x in properties_to_collect.microscope,
                MicroscopeProperties.model_fields.keys(),
            )
        )

        # collect the values of the properties
        values = {}
        for field_name in field_names:
            values[field_name] = getattr(self._control, field_name)

        # collect internal properties
        for field_name in filter(
            lambda x: x in properties_to_collect.microscope,
            self._control.manufacturer_prop_names,
        ):
            values[field_name] = self._control.manufacturer_prop(field_name)

        # get unknown properties
        unknown = [
            prop for prop in properties_to_collect.microscope if prop not in values
        ]
        if len(unknown) > 0:
            self._txt_log.warning(
                f"The following selected microscope properties are not known: {' '.join(unknown)}"
            )

        electron_beam_properties = self._control.electron_beam.collect_properties(
            properties_to_collect.electron_beam
        )
        ion_beam_properties = self._control.ion_beam.collect_properties(
            properties_to_collect.ion_beam
        )

        return GlobalProperties(
            microscope=MicroscopeProperties(**values),
            electron_beam=electron_beam_properties,
            ion_beam=ion_beam_properties,
        )

    @contextmanager
    def set_temporary_properties(self, props: GlobalProperties) -> Iterator[None]:
        """
        Temporarily set the microscope properties to the given values, and restore them when done.
        """
        backup = self.collect_properties(props.get_property_names())
        self.set_properties(props, None)
        try:
            yield
        finally:
            self.set_properties(backup, None)

    @contextmanager
    def set_temporary_beam_property(
        self, property: str, value: Any, beam: BeamType | None = None
    ) -> Iterator[None]:
        """
        Temporarily set a single property of the given beam to the given value, and restore it when done.

        Args:
            property: The name of the property to set.
            value: The value to set the property to.
            beam: The beam to set the property on, or `None` to use the current beam.
        """
        match beam:
            case BeamType.ELECTRON:
                beam_control = self.control.electron_beam
            case BeamType.ION:
                beam_control = self.control.ion_beam
            case _:
                beam_control = self.beam

        backup = getattr(beam_control, property)
        setattr(beam_control, property, value)

        try:
            yield
        finally:
            try:
                setattr(beam_control, property, backup)
            except Exception as e:
                self._txt_log.warning(f"Could not restore property {property}: {e}")
