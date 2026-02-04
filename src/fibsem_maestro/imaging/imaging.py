# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.context import SliceContext
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
        txt_log: TextLogger,
    ):
        """
        Initialize the Imaging instance.

        Args:
            microscope (Microscope): The microscope instance used for imaging.
            settings (ImagingSettings): Settings for image acquisition.
            slice_ctx (SliceContext): Context for the current slice being imaged.
            txt_log (TextLogger): A textual logger.
        """
        self._microscope = microscope
        self._settings = settings
        self._slice_ctx = slice_ctx
        self._txt_log = txt_log

    def grab_frame(self) -> None:
        """
        Set the microscope parameters and acquire an image.

        Loads microscope properties from an input file, acquires an image, saves it,
        and updates the microscope properties for subsequent imaging.

        Raises:
            ImagingError: If the image for the current slice already exists.
        """
        # set properties of the microscope
        self._txt_log.debug(
            f"Loading microscope properties from {str(self._settings.properties_file)}."
        )
        props = GlobalProperties.from_file(self._settings.properties_file)
        # TODO: or should we load all properties?
        self._microscope.set_properties(props, beam=BeamType.ELECTRON)

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

        # update microscope properties
        self.save_properties()

    def save_properties(self) -> None:
        """
        Save selected properties from the microscope to a file.

        Collects the selected properties from the microscope and saves them to the
        properties file.
        """
        self._txt_log.debug(
            f"Saving microscope properties to {str(self._settings.properties_file)}."
        )
        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        # TODO: handle extended resolution & other preprocessing
        props.to_file(self._settings.properties_file)

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
