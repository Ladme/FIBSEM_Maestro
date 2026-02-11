# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.scanning_area import RelativeScanningArea
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.global_properties import GlobalProperties
from fibsem_maestro.settings.imaging_settings import ImagingSettings


class Imaging:
    """
    Handles image acquisition for the electron microscope.
    """

    def __init__(
        self,
        microscope: Microscope,
        settings: ImagingSettings,
        slice_ctx: SliceContext,
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
        self._slice_ctx = slice_ctx
        self._log_ctx = log_ctx
        self._txt_log = txt_log

    def grab_frame(self) -> None:
        """
        Set the microscope parameters and acquire an image.

        Loads microscope properties from an input file, acquires an image, saves it,
        increments the slice counter and updates the saved microscope properties for subsequent imaging.

        Raises:
            ImagingError: If the image for the current slice already exists.
        """
        # set properties of the microscope
        properties_file = self._construct_props_path()

        self._txt_log.debug(
            f"Loading microscope properties from {str(properties_file)}."
        )
        props = GlobalProperties.from_file(properties_file)
        # TODO: should we load all properties or just the properties of the electron beam?
        self._microscope.set_properties(props, beam=None)

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

        # increment the slice counter
        self._slice_ctx.increment()

        # update the saved microscope properties
        self.save_properties()

    def save_properties(self) -> None:
        """
        Save selected properties from the microscope to a file.

        Collects the selected properties from the microscope and saves them to the
        properties file.
        """
        properties_file = self._construct_props_path()
        self._txt_log.debug(f"Saving microscope properties to {str(properties_file)}.")
        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        # if extended resolution is allowed and scanning area is set,
        # scan only the selected area using extended resolution
        if (
            self._settings.use_extended_resolution
            # TODO: we assume that the properties are specified in parameters of the electron beam
            and (eb := props.electron_beam) is not None
            and (area := eb.scanning_area) is not None
        ):
            # shift the beam to the center of the scanned area
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

            # change the resolution and FOV to the scanned area
            pixel_area = area.to_pixels(img_res)
            self._microscope.beam.horizontal_field_width = area_nm.width
            self._microscope.beam.resolution = Resolution(
                pixel_area.width, pixel_area.height
            )

            self._microscope.beam.scanning_area = RelativeScanningArea.full()

            # collect the updated properties
            props = self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

        props.to_file(properties_file)

    def _construct_image_path(self) -> Path:
        """
        Construct the path to the output image file.

        Returns:
            Path: The path to the output image file for the current slice.
        """
        return (
            self._settings.images_directory
            / f"slice_{self._slice_ctx.current_slice}.{self._settings.acquired_images_extension}"
        )

    def _construct_props_path(self) -> Path:
        """
        Construct the path to the microscope properties file.

        The returned path can be used either to load existing microscope properties
        or to save updated properties.

        Returns:
            Path: Path to the microscope properties file.
        """
        return self._log_ctx.slice_dir() / self._settings.properties_file
