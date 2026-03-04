# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import fields

import numpy as np
from numpy.typing import NDArray
from scipy.spatial import distance  # pyright: ignore[reportMissingTypeStubs]

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames


class Microscope:
    def __init__(
        self,
        settings: MicroscopeSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._txt_log = txt_log
        self._img_log = img_log

        self._apply_settings(settings)
        self._settings.on_change(self._update)

    def _apply_settings(self, settings: MicroscopeSettings) -> None:
        self._settings = settings
        self._control = MicroscopeRegistry.get(settings.control)(
            self._settings.ip_address, self._txt_log
        )
        self.beam = self._control.electron_beam

    def _update(self, settings: MicroscopeSettings) -> None:
        self._apply_settings(settings)

    def export_imaging_settings(self) -> ImagingSettings:
        values = {f.name: getattr(self, f.name) for f in fields(ImagingSettings)}
        return ImagingSettings(**values)

    def set_stage_position_with_verification(
        self, new_stage_position: StagePosition
    ) -> None:
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
        self.set_stage_position_with_verification(self._control.stage_position + delta)

    def set_beam_shift_with_verification(self, new_beam_shift: BeamShift) -> None:
        # try setting beam shift
        try:
            self.beam.beam_shift = new_beam_shift
            actual_beam_shift = self.beam.beam_shift

            dist = distance.euclidean(
                actual_beam_shift.to_tuple(), new_beam_shift.to_tuple()
            )

            if dist > self._settings.beam_shift_tolerance:
                raise MicroscopeError("Beam shift out of range.")
        except Exception as e:
            self._txt_log.warning(f"Beam shift error: {e}. Adjusting stage position.")

            beam_shift_array = np.array([new_beam_shift.x, new_beam_shift.y])
            new_stage_move = self._beam_shift_to_stage_move() @ beam_shift_array

            # move stage
            self._control.try_move_stage_position(
                StagePosition(x=float(new_stage_move[0]), y=float(new_stage_move[1]))
            )
            # set beam shift to zero
            self.beam.beam_shift = BeamShift(0.0, 0.0)

    def add_beam_shift_with_verification(self, delta: BeamShift) -> None:
        self.set_beam_shift_with_verification(self.beam.beam_shift + delta)

    def set_properties(
        self, properties: GlobalProperties, beam: BeamType | None
    ) -> None:
        """
        Load the provided properties to the microscope.

        If a beam type is specified, only the properties of the selected beam and the general
        properties of the microscope are loaded.

        Args:
            properties (GlobalProperties): The properties to be loaded to the microscope.
            beam (BeamType | None): The type of beam for which properties should be loaded.
                                If None, properties for all beams are loaded.
        """
        self._control.set_properties(properties, beam)

    def collect_properties(
        self, properties_to_collect: PropertyNames
    ) -> GlobalProperties:
        """
        Collect specified properties of the microscope.

        Args:
            properties_to_collect (PropertyNames): The names of the properties to be collected.

        Returns:
            GlobalProperties: The collected properties of the microscope.
        """
        return self._control.collect_properties(properties_to_collect)

    def get_property_names(self) -> PropertyNames:
        """
        Retrieve the names of all properties of the microscope and its beams.

        Returns:
            PropertyNames: The names of all properties available on the microscope and its beams.
        """
        return self._control.prop_names

    def set_beam(self, type: BeamType) -> None:
        """
        Set the active beam to electron or ion beam.
        """
        match type:
            case BeamType.ELECTRON:
                self.beam = self._control.electron_beam
            case BeamType.ION:
                self.beam = self._control.ion_beam

    def _beam_shift_to_stage_move(self) -> NDArray[np.floating]:
        """
        Return a 2x2 matrix converting beam shift to stage move.
        Takes stage tilt and rotation and sample holder pretilt into consideration when calculating.

        Returns:
            A (2, 2) numpy array representing the linear transformation matrix.

        Raises:
            MicroscopeError: If effective tilt is too close to 90°.
        """
        # get the tilt angle
        effective_tilt = (
            self._settings.holder_pretilt + self._control.stage_position.tilt
        )
        theta = np.radians(effective_tilt)

        if (cos_theta := np.cos(theta)) < 1e-4:
            raise MicroscopeError(
                f"Effective tilt ({effective_tilt:.3f}°) is too close to 90°. Conversion unstable."
            )

        stretch = 1.0 / cos_theta

        # construct matrix for stretching along the tilt direction
        stretch_matrix = np.array(
            [[1.0, 0.0], [0.0, stretch]],
            dtype=float,
        )

        conversion_matrix = -stretch_matrix
        self._txt_log.debug(
            f"Beam shift to stage move conversion matrix: {list(conversion_matrix)}"
        )

        return conversion_matrix
