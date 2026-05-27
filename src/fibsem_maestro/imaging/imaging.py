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
from fibsem_maestro.properties.global_properties import GlobalProperties
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
    Orchestrates a single image acquisition cycle on the electron microscope.

    Args:
        name: Human-readable identifier for this imaging instance.
        microscope: The microscope instance used for image acquisition.
        settings: Configuration for image acquisition.
        props_store: Store for reading and writing microscope properties.
        frame_store: Store for persisting acquired frames.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for saving helper images.
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

        # save the last acquired image
        self._last_acquired_image: Image | None = None

    @property
    def name(self) -> str:
        """Human-readable identifier for this imaging instance."""
        return self._name

    @property
    def props_file(self) -> str:
        """Filename used to read and write microscope properties."""
        return str(self._settings.properties_file)

    @property
    def props_store(self) -> PropsStore:
        """Store used for reading and writing microscope properties."""
        return self._props_store

    @property
    def beam_type(self) -> BeamType:
        """Beam type used for acquisition, either electron or ion."""
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        """Names of microscope properties relevant for the image acquisition."""
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        """The microscope instance used for the imaging."""
        return self._microscope

    @property
    def txt_log(self) -> TextLogger:
        """Logger for diagnostic and status messages."""
        return self._txt_log

    @property
    def external_props(self) -> GlobalProperties:
        """External properties to use for this imaging action."""
        return self._settings.external_props

    @property
    def last_acquired_image(self) -> Image | None:
        """Get the last image acquired by this imaging."""
        return self._last_acquired_image

    def grab_frame(self, slice_number: int) -> None:
        """
        Execute the full image acquisition pipeline for the current slice.

        Loads stored microscope properties and applies them to the beam,
        acquires a frame and persists it via the frame store, writes updated
        properties to the next slice's store, and optionally launches a
        background thread to evaluate image sharpness.

        Call `wait_for_sharpness` after this method to block until the
        sharpness result is available.

        Args:
            slice_number: The current slice index.

        Raises:
            ImagingError: If a frame for the current slice already exists in the frame store.
        """
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping imaging for slice {slice_number}.")
            # even if imaging is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
            return

        # set the properties of the microscope
        self.read_and_set_properties()

        # make sure that the image for the current slice does not exist
        self._frame_store.raise_if_exists(ImagingError)

        # grab the frame and save it
        self._last_acquired_image = self._microscope.beam.grab_frame(self._frame_store)

        # update the saved microscope properties for the next frame
        self.collect_and_write_properties(self._props_store.next)

        # calculate image sharpness in a separate thread
        self._image_sharpness = None
        if self._criterion is not None:
            self._sharpness_thread = threading.Thread(
                target=self._calculate_sharpness,
                args=(self._last_acquired_image,),
                daemon=True,
            )
            self._sharpness_thread.start()
        else:
            self._txt_log.debug(
                f"Criterion is not configured for {self._name}. Image sharpness will not be calculated."
            )

    def collect_and_write_properties(
        self,
        store: PropsStore | None = None,
    ) -> None:
        """
        Collect and save the relevant properties of the microscope.

        Args:
            store: Store to write properties to. If `None`, the current slice's store is used.
        """
        store = store or self._props_store
        self._txt_log.debug("Saving microscope properties for imaging.")

        self._microscope.set_beam(self._settings.beam_type)

        # set external microscope properties such as scanning area or bit depth
        with self._microscope.set_temporary_properties(self.external_props):
            match self._settings.resolution_mode:
                case StandardResolution():
                    pass
                case ExtendedResolution() as mode:
                    self._set_extended_resolution_props(
                        mode.pixel_size,
                    )

            # collect the microscope properties
            props = self._microscope.collect_properties(
                self._settings.properties_to_collect
            )

            # save the properties to a file
            store.write(str(self._settings.properties_file), props)

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
        """
        Configure the beam for extended resolution imaging.

        When a non-full-frame scanning area is configured, shifts the beam
        to the centre of that area and resizes the field of view to match its physical dimensions.

        The scanning area is always reset to full frame after the adjustment,
        since the beam shift and FOV take over the role of area selection in
        extended resolution mode. The pixel size is always updated to
        `new_pixel_size`, regardless of whether a scanning area is configured.

        Args:
            new_pixel_size: The target pixel size in nanometers.
        """
        # get external properties for the relevant beam
        props = (
            self._settings.external_props.electron_beam
            if self._settings.beam_type == BeamType.ELECTRON
            else self._settings.external_props.ion_beam
        )

        # image only the scanning area
        if (
            props is not None
            and (area := props.scanning_area) is not None
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
        Evaluate image sharpness on a background thread.

        Computes the sharpness score via the configured criterion and stores
        the result in `_image_sharpness`. Any exception raised during
        calculation is caught and logged as a warning so that a failure cannot
        crash the background thread.

        Args:
            image: The image to evaluate.
        """
        assert self._criterion is not None

        try:
            self._image_sharpness = self._criterion.calculate_sharpness(image)
            self._txt_log.debug(f"Image sharpness: {self._image_sharpness}.")
        except Exception as e:
            self._txt_log.warning(f"Could not calculate image sharpness: {e}")
