# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TYPE_CHECKING

from fibsem_maestro.core.action import Action
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.milling import MillingSettings
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from fibsem_maestro.core.area import NMArea


class Milling(Action):
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
        txt_log: Logger for diagnostic and status messages.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: MillingSettings,
        props_store: PropsStore,
        txt_log: TextLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._txt_log = txt_log

        self._current_milling_area: None | NMArea = None

    @property
    def name(self) -> str:
        return self._name

    def mill(self, slice_number: int) -> None:
        """
        Perform one milling step for the current slice if conditions are met.

        Args:
            slice_number: The current slice index.
        """
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping milling for slice {slice_number}.")
            return

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
