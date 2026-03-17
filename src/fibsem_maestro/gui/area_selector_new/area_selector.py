# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from enum import Enum

from nicegui import ui

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.gui.area_selector._area_selector_empty import AreaSelectorEmpty
from fibsem_maestro.gui.area_selector._area_selector_with_image import (
    AreaSelectorWithImage,
)
from fibsem_maestro.gui.area_selector.area_limits import AreaLimits
from fibsem_maestro.gui.area_selector.area_type import AreaType
from fibsem_maestro.microscope.microscope import Microscope


class SelectorState(Enum):
    """Current state of the area selector."""

    EMPTY = "empty"
    WITH_IMAGE = "with_image"


class AreaSelector:
    """Manages switching between empty and image-based area selection."""

    def __init__(
        self,
        microscope: Microscope,
        area_limits: AreaLimits,
        max_display_dimensions: tuple[int, int] = (768, 663),
    ):
        self._microscope = microscope
        self._area_limits = area_limits
        self._max_display_dimensions = max_display_dimensions
        self._state = SelectorState.EMPTY

        self._container = None
        self._image_selector: AreaSelectorWithImage | None = None

    async def _load_image(self) -> None:
        """Transition to image-based selector."""
        image = self._microscope.beam.get_image()
        self._image_selector = AreaSelectorWithImage(
            image,
            self._area_limits,
            on_close=self._return_to_empty,
            max_display_dimensions=self._max_display_dimensions,
        )
        self._state = SelectorState.WITH_IMAGE
        self._rebuild_ui()

    def _return_to_empty(self) -> None:
        """Transition back to empty selector."""
        self._image_selector = None
        self._state = SelectorState.EMPTY
        self._rebuild_ui()

    def _rebuild_ui(self) -> None:
        """Clear and rebuild the UI based on current state."""
        assert self._container is not None
        self._container.clear()

        with self._container:
            if self._state == SelectorState.EMPTY:
                AreaSelectorEmpty(
                    self._microscope,
                    self._area_limits,
                    on_load=self._load_image,
                    placeholder_size=self._max_display_dimensions,
                ).build()
            else:
                assert self._image_selector is not None
                self._image_selector.build()

    def build(self) -> None:
        """Build the UI component."""
        self._container = ui.card().classes("!border-0 !shadow-none")
        self._rebuild_ui()

    def get_areas(self) -> dict[AreaType, list[RelativeArea]]:
        """Retrieve all finalized areas, or empty dict if no image loaded."""
        return self._image_selector.get_areas() if self._image_selector else {}
