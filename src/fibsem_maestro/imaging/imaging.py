# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.context import LogContext
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)


class Imaging(Action):
    """
    Handles image acquisition for the electron microscope.
    """

    def __init__(
        self,
        microscope: Microscope,
        settings: ImagingSettings,
        log_ctx: LogContext,
        txt_log: TextLogger,
    ):
        """
        Initialize the Imaging instance.

        Args:
            microscope (Microscope): The microscope instance used for imaging.
            settings (ImagingSettings): Settings for image acquisition.
            slice_ctx (SliceContext): Context for the current slice being imaged.
            log_ctx (LogContext): Context for logging.
            txt_log (TextLogger): A textual logger.
        """
        self._microscope = microscope
        self._settings = settings
        self._log_ctx = log_ctx
        self._txt_log = txt_log

    def grab_frame(self) -> None:
        """
        Set the microscope properties and acquire an image.

        Loads microscope properties from an input file, acquires an image, saves it,
        and updates the saved microscope properties for subsequent imaging.

        Raises:
            ImagingError: If the image for the current slice already exists.
        """
        # set the properties of the microscope
        self.set_properties()

        # make sure that the image for the current slice does not exist
        if (image_path := self._construct_image_path()).exists():
            raise ImagingError(
                f"Image {str(image_path)} already exists. Unable to perform image acquisition."
            )

        # make sure that the directory for storing images exists
        if not self._settings.images_directory.exists():
            self._settings.images_directory.mkdir(parents=True, exist_ok=True)

        # grab the frame and save it
        self._microscope.beam.grab_frame(image_path)

        # update the saved microscope properties
        self.save_properties(slice=(self._log_ctx.slice_ctx.current_slice or 0) + 1)

    def set_properties(self) -> None:
        """
        Set the microscope properties.
        """
        # select the beam used for imaging
        self._microscope.set_beam(self._settings.beam_type)

        # set properties of the microscope
        properties_file = self._construct_props_path()
        self._txt_log.debug(
            f"Loading microscope properties from {str(properties_file)}."
        )
        props = GlobalProperties.from_file(properties_file)
        self._microscope.set_properties(props, beam=self._settings.beam_type)

    def save_properties(self, slice: int | None = None) -> None:
        """
        Save selected properties from the microscope to a file.

        Args:
            slice (int | None): The slice for which properties should be saved.
                                If `None`, the current slice is used.

        Collects the selected properties from the microscope and saves them to the
        properties file.
        """
        properties_file = self._construct_props_path(slice)
        self._txt_log.debug(f"Saving microscope properties to {str(properties_file)}.")

        # set bit depth, if specified in the settings
        if (bd := self._settings.bit_depth) is not None:
            self._microscope.beam.bit_depth = bd

        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        match self._settings.resolution_mode:
            case StandardResolution():
                pass
            case ExtendedResolution() as mode:
                beam_props = (
                    props.electron_beam
                    if self._settings.beam_type == BeamType.ELECTRON
                    else props.ion_beam
                )

                # image only the scanning area
                if (
                    beam_props is not None
                    and (area := beam_props.scanning_area) is not None
                    and not area.is_full_frame()
                ):
                    self._txt_log.debug(
                        "Setting scanning area using extended resolution."
                    )

                    # shift the beam to the center of the scanning area
                    img_res = self._microscope.beam.resolution
                    pixel_size = self._microscope.beam.pixel_size
                    area_nm = area.to_nanometers(img_res, pixel_size)
                    image_to_beam_shift = self._microscope.beam.image_to_beam_shift

                    shift = BeamShift(
                        image_to_beam_shift[0]
                        * (
                            area_nm.origin.x
                            - (img_res.width // 2 * pixel_size)
                            + area_nm.width / 2.0
                        ),
                        image_to_beam_shift[1]
                        * (
                            area_nm.origin.y
                            - (img_res.height // 2 * pixel_size)
                            + area_nm.height / 2.0
                        ),
                    )

                    self._microscope.add_beam_shift_with_verification(shift)

                    # set the FOV to the scanning area
                    self._microscope.beam.horizontal_field_width = area_nm.width
                    self._microscope.beam.vertical_field_width = area_nm.height
                    self._microscope.beam.scanning_area = RelativeArea.full()

                # set resolution based on the pixel size
                # this is done even if scanning area is not specified
                self._microscope.beam.pixel_size = mode.pixel_size

                # collect the updated properties
                props = self._microscope.collect_properties(
                    self._settings.properties_to_collect
                )

        # save the properties to a file
        props.to_file(properties_file)

    def _construct_image_path(self) -> Path:
        """
        Construct the path to the output image file.

        Returns:
            Path: The path to the output image file for the current slice.
        """
        return (
            self._settings.images_directory
            / f"slice_{self._log_ctx.slice_ctx.current_slice}.tif"
        )

    def _construct_props_path(self, slice: int | None = None) -> Path:
        """
        Construct the path to the microscope properties file for the specified slice
        or the current slice (if `slice` is None).

        The returned path can be used either to load existing microscope properties
        or to save updated properties.

        Returns:
            Path: Path to the microscope properties file.
        """
        return self._log_ctx.slice_dir(slice) / self._settings.properties_file
