# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TYPE_CHECKING

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from fibsem_maestro.core.area import NMArea


class Milling(Action):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: MillingSettings,
        props_store: PropsStore,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._txt_log = txt_log
        self._img_log = img_log

        self._current_milling_area: None | NMArea = None

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

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    def mill(self, slice_number: int) -> None:
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping milling for slice {slice_number}.")
            # even if milling is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
            return

        # set the properties of the microscope
        self.read_and_set_properties()

        # set the current milling area for the first slice
        if self._current_milling_area is None:
            self._current_milling_area = self._settings.milling_area.to_nanometers(
                self._microscope.beam.resolution, self._microscope.beam.pixel_size
            )
            self._txt_log.debug(
                f"First frame: setting milling area to: {self._current_milling_area}."
            )

        # perform the milling step
        self._txt_log.info("Starting milling.")
        self._microscope.beam.rectangle_milling(
            self._current_milling_area,
            self._settings.milling_depth,
            self._settings.milling_direction,
            self._settings.pattern_file,
        )
        self._txt_log.info("Milling step completed.")

        # update the current milling area for the next slice
        self._current_milling_area = self._current_milling_area.shifted_in_direction(
            self._settings.milling_direction, self._settings.slice_distance
        )
        self._txt_log.debug(
            f"Updating milling area for the next slice: {self._current_milling_area}."
        )

        self.collect_and_write_properties(self._props_store.next)
