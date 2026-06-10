# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TYPE_CHECKING

import yaml

from fibsem_maestro.action.action import Action, ActionConfig
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.error import MillingError
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from fibsem_maestro.core.area import NMArea


@ACTION_REGISTRY.register("milling")
class Milling(Action[MillingSettings, None]):
    """
    Performs focused ion beam milling one slice at a time.

    Executes a rectangular milling pattern at a configurable depth and
    direction, advancing the milling area by the configured slice distance
    after each step.

    Args:
        name: Human-readable identifier for this milling instance.
        microscope: Interface to the electron microscope.
        settings: Milling configuration.
        props_store: Store for reading and writing microscope properties.
        text_store: Store for reading and writing text data.
        txt_log: Logger for diagnostic and status messages.
    """

    def __init__(
        self,
        config: ActionConfig[MillingSettings],
    ):
        self._name = config.name
        self._microscope = config.microscope
        self._settings = config.settings
        self._props_store = config.props_store
        self._txt_store = config.txt_store
        self._txt_log = config.txt_log

        self._current_milling_area: None | NMArea = None

    @classmethod
    def settings_cls(cls) -> type[MillingSettings]:
        return MillingSettings

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def props_file(self) -> str:
        return str(self._settings.properties_file)

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

    @property
    def beam_type(self) -> BeamType | None:
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
    def settings(self) -> MillingSettings:
        return self._settings

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    def execute(self, slice_number: int, links: None = None) -> None:
        """
        Perform one milling step for the current slice if conditions are met.

        Args:
            slice_number: The current slice index.
        """
        _ = links

        if len(self._settings.milling_area) != 1:
            raise MillingError(
                f"Expected exactly one milling area, got {len(self._settings.milling_area)}."
            )

        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping {self.name} for slice {slice_number}.")
            # even if milling is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
            return

        # set the properties of the microscope
        self.read_and_set_properties()

        # set the current milling area for the first slice
        if self._current_milling_area is None:
            self._current_milling_area = self._settings.milling_area[0].to_nanometers(
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

        # store the milling area for the next slice
        # this is needed only for restoring the milling in case the workflow is interrupted
        if (area := self._current_milling_area) is not None:
            self._txt_store.next.write(
                str(self._settings.state_file),
                data=yaml.dump({"milling_area": area.model_dump()}),
            )

        self.collect_and_write_properties(self._props_store.next)
