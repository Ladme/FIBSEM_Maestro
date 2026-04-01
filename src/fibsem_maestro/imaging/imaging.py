# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import threading

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.props.props_store import PropsStore


class Imaging(Action):
    """
    Handles image acquisition for the electron microscope.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: ImagingSettings,
        props_store: PropsStore,
        frame_store: FrameStore,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        """
        Initialize the Imaging instance.

        Args:
            name (str): Identifier of this Imaging object.
            microscope (Microscope): The microscope instance used for imaging.
            settings (ImagingSettings): Settings for image acquisition.
            props_store (PropsStore): Handler for storing microscope properties.
            frame_store (FrameStore): Handler for storing acquired frames.
            txt_log (TextLogger): A textual logger.
            img_log (ImageLogger): An image logger.
        """
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._frame_store = frame_store
        self._txt_log = txt_log

        if criterion_settings := self._settings.criterion:
            self._criterion = Criterion(
                f"{self._name} criterion",
                criterion_settings,
                self._txt_log.derive("criterion"),
                img_log,
            )
        else:
            self._criterion = None

        # was scanning area selected using extended resolution
        # necessary to avoid shrinking the selected area in subsequent imagings
        self._scanning_area_selected = False

        # sharpness of the acquired image
        self._image_sharpness: float | None = None
        self._sharpness_thread: threading.Thread | None = None

    @property
    def name(self) -> str:
        return self._name

    @property
    def props_file(self) -> str:
        return str(self._settings.properties_file)

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

    @property
    def beam_type(self) -> BeamType:
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log

    def grab_frame(self) -> None:
        """
        Set the microscope properties and acquire an image.

        Loads microscope properties from an input file, acquires an image, saves it,
        and updates the saved microscope properties for subsequent imaging.

        If a `Criterion` is configured, image sharpness is calculated
        asynchronously on a background thread. The result is stored in
        `image_sharpness` once the calculation completes.
        Use `wait_for_sharpness` to block until the value is available.

        Raises:
            ImagingError: If the image for the current slice already exists.
        """
        # set the properties of the microscope
        self.read_and_set_properties()

        # make sure that the image for the current slice does not exist
        self._frame_store.raise_if_exists(ImagingError)

        # grab the frame and save it
        image = self._microscope.beam.grab_frame(self._frame_store)

        # update the saved microscope properties for the next frame
        self.collect_and_write_properties(self._props_store.next)

        # calculate image sharpness in a separate thread
        self._image_sharpness = None
        if self._criterion is not None:
            self._sharpness_thread = threading.Thread(
                target=self._calculate_sharpness,
                args=(image,),
                daemon=True,
            )
            self._sharpness_thread.start()
        else:
            self._txt_log.debug(
                f"Criterion is not configured for {self._name}. Image sharpness will not be calculated."
            )

    def collect_and_write_properties(self, store: PropsStore | None = None) -> None:
        """
        Save selected properties from the microscope to a file.

        Args:
            store (PropsStore | None): Handler specifying the slice
                for which microscope properties should be saved.
                If `None`, the properties are saved for the current slice.
        """
        store = store or self._props_store
        self._txt_log.debug("Saving microscope properties for imaging.")

        self._microscope.set_beam(self._settings.beam_type)

        # store the current scanning area
        backup_scanning_area = self._microscope.beam.scanning_area

        # set bit depth, if specified in the settings
        if (bd := self._settings.bit_depth) is not None:
            self._microscope.beam.bit_depth = bd

        match self._settings.resolution_mode:
            case StandardResolution():
                # set the scanning area, if specified in the settings
                if (area := self._settings.scanning_area) is not None:
                    self._microscope.beam.scanning_area = area
                # otherwise set the scanning area to full frame to override any external set up
                else:
                    self._microscope.beam.scanning_area = RelativeArea.full()
            case ExtendedResolution() as mode:
                self._set_extended_resolution_props(mode.pixel_size)

        # collect the microscope properties
        props = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

        # save the properties to a file
        store.write(str(self._settings.properties_file), props)

        # set the original scanning area
        self._microscope.beam.scanning_area = backup_scanning_area

    def wait_for_sharpness(self) -> float | None:
        """
        Block until the background sharpness calculation finishes.

        Returns:
            The calculated sharpness value, or `None` if no criterion is
            configured or the calculation failed.
        """
        if self._sharpness_thread is not None:
            self._sharpness_thread.join()
        return self._image_sharpness

    def _set_extended_resolution_props(self, new_pixel_size: float) -> None:
        # image only the scanning area
        if (
            (area := self._settings.scanning_area) is not None
            and not area.is_full_frame()
            and not self._scanning_area_selected
        ):
            self._txt_log.debug("Setting scanning area using extended resolution.")

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

            self._scanning_area_selected = True

        # always set scanning area to full frame
        self._microscope.beam.scanning_area = RelativeArea.full()

        # set resolution based on the new pixel size
        # this is done even if scanning area is not specified
        self._microscope.beam.pixel_size = new_pixel_size

    def _calculate_sharpness(self, image: Image) -> None:
        """
        Calculate the sharpness of `image` via the configured criterion.

        Intended to run on a background thread. The result is stored in
        `self._image_sharpness`. Any exception is caught and logged as a
        warning so that a failed sharpness calculation cannot crash the thread.
        """
        assert self._criterion is not None

        try:
            self._image_sharpness = self._criterion.calculate_sharpness(image)
            self._txt_log.debug(f"Image sharpness: {self._image_sharpness}.")
        except Exception as e:
            self._txt_log.warning(f"Could not calculate image sharpness: {e}")
