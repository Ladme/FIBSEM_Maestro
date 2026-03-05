# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.action import Action
from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.imaging.error import ImagingError
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)
from fibsem_maestro.store.frame.frame_store import FrameStore
from fibsem_maestro.store.props.props_store import PropsStore


class Imaging(Action):
    """
    Handles image acquisition for the electron microscope.
    """

    def __init__(
        self,
        microscope: Microscope,
        settings: ImagingSettings,
        props_store: PropsStore,
        frame_store: FrameStore,
        txt_log: TextLogger,
    ):
        """
        Initialize the Imaging instance.

        Args:
            microscope (Microscope): The microscope instance used for imaging.
            settings (ImagingSettings): Settings for image acquisition.
            props_store (PropsStore): Handler for storing microscope properties.
            frame_store (FrameStore): Handler for storing acquired frames.
            txt_log (TextLogger): A textual logger.
        """
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._frame_store = frame_store
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
        self._frame_store.raise_if_exists(ImagingError)

        # grab the frame and save it
        self._microscope.beam.grab_frame(self._frame_store)

        # update the saved microscope properties for the next frame
        self.save_properties(self._props_store.next)

    def set_properties(self) -> None:
        """
        Configure the electron microscope with settings from the properties file.
        """
        # select the beam used for imaging
        self._microscope.set_beam(self._settings.beam_type)

        # read properties
        self._txt_log.debug("Loading microscope properties for imaging.")
        props = self._props_store.read(str(self._settings.properties_file))

        # set properties to the microscope
        self._microscope.set_properties(props, beam=self._settings.beam_type)

    def save_properties(self, store: PropsStore | None = None) -> None:
        """
        Save selected properties from the microscope to a file.

        Args:
            store (PropsStore | None): Handler specifying the slice
                for which microscope properties should be saved.
                If `None`, the properties are saved for the current slice.
        """
        store = store or self._props_store
        self._txt_log.debug("Saving microscope properties for imaging.")

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
        store.write(str(self._settings.properties_file), props)
