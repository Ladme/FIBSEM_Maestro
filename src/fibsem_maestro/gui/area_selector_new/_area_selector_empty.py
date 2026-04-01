# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Awaitable, Callable

from nicegui import ui

from fibsem_maestro.gui.area_selector_new.area_limits import AreaLimits
from fibsem_maestro.microscope.microscope import Microscope


class AreaSelectorEmpty:
    """Empty placeholder that loads an image when clicked."""

    def __init__(
        self,
        microscope: Microscope,
        area_limits: AreaLimits,
        on_load: Callable[[], Awaitable[None]],
        placeholder_size: tuple[int, int],
    ):
        """
        Initialize empty area selector.

        Args:
            microscope: The Microscope instance to retrieve images from.
            area_limits: Area limits configuration.
            on_load: Async callback when user clicks to load image.
        """
        self._microscope = microscope
        self._area_limits = area_limits
        self._on_load = on_load
        self._placeholder_size = placeholder_size

    def build(self) -> None:
        """Build the UI component with clickable placeholder."""
        ui.add_head_html("""
<style>
  .no-select {
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
  }
</style>
""")

        with (
            ui.card().classes("area-selector-empty"),
            ui.element("div")
            .classes("cursor-pointer no-select")
            .on("click", self._on_load),
        ):
            ui.label("Area selector").classes("font-bold")
            ui.html(
                f'<svg width="{self._placeholder_size[0]}" height="{self._placeholder_size[1]}" style="border: 2px dashed #ccc; background-color: #f5f5f5; display: block;">'
                f'<text x="{self._placeholder_size[0] // 2}" y="{self._placeholder_size[1] // 2}" text-anchor="middle" dominant-baseline="middle" fill="#999" font-size="24">'
                f"Click to load image"
                f"</text></svg>"
            )
