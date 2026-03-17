# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

import tempfile
from collections import Counter, defaultdict
from enum import Enum
from typing import TYPE_CHECKING, Self

import numpy as np
from nicegui import events, ui
from PIL import Image as PILImage
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.area import PixelArea, RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import PixelPoint

if TYPE_CHECKING:
    from collections.abc import Callable

    from fibsem_maestro.core.resolution import Resolution
    from fibsem_maestro.microscope.microscope import Microscope


class AreaType(Enum):
    SCANNING = "scanning_area"
    TEMPLATE = "template_area"
    FIDUCIAL = "fiducial"
    MILLING = "milling"


class SelectedArea(PixelArea):
    type: AreaType
    active: bool

    @property
    def color(self) -> str:
        if self.active:
            match self.type:
                case AreaType.SCANNING:
                    return "#00E5FF"
                case AreaType.TEMPLATE:
                    return "#FFD600"
                case AreaType.FIDUCIAL:
                    return "#FF40FF"
                case AreaType.MILLING:
                    return "#76FF03"

        match self.type:
            case AreaType.SCANNING:
                return "#0d10d4"
            case AreaType.TEMPLATE:
                return "#d15700"
            case AreaType.FIDUCIAL:
                return "#7B1FA2"
            case AreaType.MILLING:
                return "#167802"

    @property
    def label(self) -> str:
        match self.type:
            case AreaType.SCANNING:
                return "scanning area"
            case AreaType.TEMPLATE:
                return "template area"
            case AreaType.FIDUCIAL:
                return "fiducial"
            case AreaType.MILLING:
                return "milling area"

    def render(self) -> str:
        return (
            f'<rect x="{self.origin.x}" y="{self.origin.y}" width="{self.width}" height="{self.height}" '
            f'fill="{self.color}" fill-opacity="0.1" stroke="{self.color}" stroke-width="5" />'
            f'<text x="{self.origin.x + self.width // 2}" y="{self.origin.y + 20}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{self.color}" font-size="12">'
            f"{self.label}</text>"
        )

    @classmethod
    def from_relative(
        cls, relative_area: RelativeArea, type: AreaType, resolution: Resolution
    ) -> Self:
        pixel_area = relative_area.to_pixels(resolution)
        return cls(
            origin=pixel_area.origin,
            width=pixel_area.width,
            height=pixel_area.height,
            type=type,
            active=False,
        )


class AreaLimits:
    def __init__(self):
        self._area_limits: dict[AreaType, int] = {}

    def add_limit(self, area_type: AreaType, max_areas: int) -> None:
        self._area_limits[area_type] = max_areas

    def get_limit(self, area_type: AreaType) -> int:
        return self._area_limits.get(area_type) or 0

    def get_remaining(self, area_type: AreaType, current: int) -> int:
        return self.get_limit(area_type) - current

    def get_available(self, areas: list[SelectedArea]) -> list[AreaType]:
        counts = Counter([area.type for area in areas])

        return [
            area_type
            for area_type in self._area_limits
            if self.get_remaining(area_type, counts[area_type]) > 0
        ]


class AreaSelector:
    """Parent selector that manages switching between empty and image-based states."""

    def __init__(
        self,
        microscope: Microscope,
        area_limits: AreaLimits,
        initial_areas: dict[AreaType, list[RelativeArea]],
    ):
        """
        Initialize the area selector.

        Args:
            microscope: The Microscope instance to retrieve images from.
        """
        self._microscope = microscope
        self._container = None
        self._empty_selector: _AreaSelectorEmpty | None = None
        self._image_selector: _AreaSelectorWithImage | None = None
        self._active_container = None

        self._area_limits = area_limits
        self._init_areas = initial_areas

    async def _on_image_loaded(self) -> None:
        """Handle image loading and transition to image selector."""
        assert self._empty_selector is not None
        self._image_selector = await self._empty_selector.load_image()
        self._active_container = self._image_selector

        # clear and rebuild container
        assert self._container is not None
        self._container.clear()

        with self._container:
            self._image_selector.build()

    def _on_image_selector_closed(self) -> None:
        """Handle closing the image selector to go back to empty."""
        assert self._container is not None
        self._container.clear()

        with self._container:
            self._empty_selector = _AreaSelectorEmpty(
                self._microscope,
                self._area_limits,
                self._init_areas,
                self._on_image_selector_closed,
            )
            self._empty_selector._on_placeholder_clicked = self._on_image_loaded
            self._empty_selector.build()

        self._image_selector = None
        self._active_container = self._empty_selector

    def build(self) -> None:
        """Build the UI component."""
        self._container = ui.card().classes("!border-0 !shadow-none")

        with self._container:
            if isinstance(self._active_container, _AreaSelectorWithImage):
                self._active_container.build()
            else:
                self._empty_selector = _AreaSelectorEmpty(
                    self._microscope,
                    self._area_limits,
                    self._init_areas,
                    self._on_image_selector_closed,
                )
                self._active_container = self._empty_selector
                self._empty_selector._on_placeholder_clicked = self._on_image_loaded
                self._empty_selector.build()

    def get_areas(self) -> dict[AreaType, list[RelativeArea]]:
        """
        Retrieve all finalized areas.

        Returns:
            List of SelectedArea objects that have been created.
        """
        if self._image_selector is None:
            return {}
        return self._image_selector.get_areas()


class _AreaSelectorEmpty:
    """Area selector placeholder that loads an image on click."""

    def __init__(
        self,
        microscope: Microscope,
        area_limits: AreaLimits,
        initial_areas: dict[AreaType, list[RelativeArea]],
        on_close: Callable[[], None],
    ):
        """
        Initialize empty area selector for image loading.

        Args:
            microscope: The Microscope instance to retrieve images from.
        """
        self._microscope = microscope
        self._width: int = 1024
        self._height: int = 884

        self._area_limits = area_limits
        self._init_areas = initial_areas
        self._on_close = on_close

    async def load_image(self) -> _AreaSelectorWithImage:
        """
        Load image from microscope and create the image-based selector.

        Returns:
            AreaSelectorWithImage instance ready to use.

        Raises:
            Exception: If image loading fails.
        """
        image = self._microscope.beam.get_image()
        return _AreaSelectorWithImage(
            image, self._area_limits, self._init_areas, self._on_close
        )

    async def _on_placeholder_clicked(self) -> None:
        """Handle click on the empty placeholder."""
        await self.load_image()

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
            (
                ui.element("div")
                .classes("cursor-pointer no-select")
                .on("click", self._on_placeholder_clicked)
            ),
        ):
            ui.label("Area selector").classes("font-bold")
            ui.html(
                f'<svg width="{self._width}" height="{self._height}" style="border: 2px dashed #ccc; background-color: #f5f5f5; display: block;">'
                f'<text x="{self._width // 2}" y="{self._height // 2}" text-anchor="middle" dominant-baseline="middle" fill="#999" font-size="24">'
                f"Click to load image"
                f"</text></svg>"
            )


class _AreaSelectorWithImage:
    """Interactive area selector for image regions."""

    def __init__(
        self,
        image: Image,
        area_limits: AreaLimits,
        initial_areas: dict[AreaType, list[RelativeArea]],
        on_close: Callable[[], None],
    ):
        """
        Initialize AreaSelector with a loaded image.

        Args:
            image: The Image object to perform area selection on.
        """
        self._image = self._downscale_image_if_needed(image)

        self._areas: list[SelectedArea] = self._convert_initial_areas(initial_areas)
        self._start: tuple[int, int] | None = None
        self._selected_area_index: int | None = None
        self._current_pos: tuple[int, int] = (0, 0)
        self._edit_mode = False
        self._on_close = on_close

        self._resolution = self._image.resolution
        self._width = self._resolution.width
        self._height = self._resolution.height

        self._image_path = self._save_temp_image(self._image)
        self._area_limits = area_limits
        available_area_types = self._area_limits.get_available(self._areas)
        self._active_area_type: AreaType | None = (
            available_area_types[0] if len(available_area_types) > 0 else None
        )

        self._image_widget = None
        self._final_layer = None
        self._preview_layer = None
        self._mouse_layer = None

        self._area_type_row = None
        self._area_type_select = None

    def _downscale_image_if_needed(self, image: Image) -> Image:
        """
        Downscale image if its resolution exceeds 1024x884.

        Maintains aspect ratio.

        Args:
            image: The Image object to potentially downscale.

        Returns:
            Downscaled Image or original Image if no downscaling needed.
        """
        resolution = image.resolution
        max_width = 1024
        max_height = 884

        if resolution.width <= max_width and resolution.height <= max_height:
            return image

        scale_w = max_width / resolution.width
        scale_h = max_height / resolution.height
        scale = min(scale_w, scale_h)

        img_array = np.array(image)

        downscaled = ndimage.zoom(img_array, scale, order=1)
        return Image(downscaled, pixel_size=image.pixel_size * scale)

    def _convert_initial_areas(
        self, init_areas: dict[AreaType, list[RelativeArea]]
    ) -> list[SelectedArea]:
        res = self._image.resolution
        return [
            SelectedArea.from_relative(area, area_type, res)
            for area_type, areas in init_areas.items()
            for area in areas
        ]

    def _save_temp_image(self, image: Image) -> str:
        """
        Save image to temporary file for UI display.

        Args:
            image: The Image object to save.

        Returns:
            Path to the temporary image file.
        """
        img_8bit = image.to_8bit()
        img_array = np.uint8(img_8bit)

        pil_img = PILImage.fromarray(
            img_array, mode="L" if len(image.shape) == 2 else "RGB"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            pil_img.save(temp_file.name)
            return temp_file.name

    def _set_active_area_type(self, area_type: str) -> None:
        """
        Set the current area type.

        Args:
            area_type: The AreaType value selected.
        """
        self._active_area_type = AreaType(area_type)

    def _update_active_area_type(self) -> None:
        available = self._area_limits.get_available(self._areas)
        if self._active_area_type not in available:
            if len(available) == 0:
                self._active_area_type = None
            else:
                self._active_area_type = available[0]

    def build(self) -> None:
        """Build the UI component."""
        ui.add_head_html("""
<style>
  .no-select {
    user-select: none;
    -webkit-user-select: none;
    -moz-user-select: none;
    -ms-user-select: none;
  }
  .crosshair-cursor {
    cursor: crosshair;
  }
</style>
""")

        with ui.card():
            ui.label("Area selector").classes("font-bold")

            # close button
            with ui.element("div").style(
                "position: relative; display: inline-block; width: 100%;"
            ):
                ui.button(icon="close", on_click=self._on_close_clicked).style(
                    "position: absolute; top: 0; right: -10px; z-index: 10; "
                    "width: 30px !important; height: 30px !important; min-width: 30px !important; "
                    "padding: 0 !important; background-color: black !important; color: white !important; "
                    "border: none !important;"
                )

            # image viewer
            self._image_widget = ui.interactive_image(
                self._image_path,
                on_mouse=self._mouse_handler,
                events=["mousedown", "mousemove", "mouseup"],
                cross=True,
                sanitize=False,
            ).classes("no-select crosshair-cursor")

            self._area_type_row = (
                ui.row()
                .bind_visibility_from(
                    self, "_active_area_type", lambda active: active is not None
                )
                .classes("items-center gap-2")
            )

            # area type selector
            with self._area_type_row:
                ui.label("Area type:")
                self._area_type_select = ui.select(
                    {},
                    on_change=lambda e: self._set_active_area_type(e.value),
                )

            self._update_area_type_options()

            self._final_layer = self._image_widget.add_layer()
            self._preview_layer = self._image_widget.add_layer()
            self._mouse_layer = self._image_widget.add_layer()

            self._redraw_final_layer()

        ui.keyboard(on_key=self._on_key_pressed)

    def _update_area_type_options(self) -> None:
        """Update available area types in the select widget."""
        if self._area_type_row is None:
            return

        self._area_type_row.clear()

        available_types = self._area_limits.get_available(self._areas)
        # add the active area if in edit mode
        if self._active_area_type is not None and self._edit_mode:
            available_types.append(self._active_area_type)

        with self._area_type_row:
            ui.label("Area type:")
            self._area_type_select = ui.select(
                {
                    area_type.value: area_type.value.replace("_", " ").title()
                    for area_type in available_types
                },
                value=self._active_area_type.value
                if self._active_area_type and self._active_area_type in available_types
                else (available_types[0].value if available_types else None),
                on_change=lambda e: self._set_active_area_type(e.value),
            )

    def _mouse_handler(self, e: events.MouseEventArguments) -> None:
        """
        Handle mouse events.

        Args:
            e: Mouse event arguments containing position and type information.
        """
        mx, my = int(round(e.image_x)), int(round(e.image_y))
        self._current_pos = (mx, my)

        assert self._mouse_layer is not None
        assert self._preview_layer is not None

        if e.type == "mousedown":
            self._start = (mx, my)
            self._preview_layer.content = ""

        elif e.type == "mousemove" and self._start:
            if self._edit_mode:
                # redraw selected area
                if (area := self._get_edited_area_preview(e)) is None:
                    return
            else:
                # create new area
                if (area := self._get_area_preview(e)) is None:
                    return

            self._preview_layer.content = area.render()

        elif e.type == "mouseup" and self._start:
            if self._edit_mode:
                # finalize edited area
                self._finalize_edited_area(e)
            else:
                # create new area
                self._finalize_area(e)

            self._preview_layer.content = ""
            self._start = None

    def _get_area_preview(self, e: events.MouseEventArguments) -> SelectedArea | None:
        """
        Render preview rectangle while dragging.

        Args:
            e: Mouse event arguments.

        Returns:
            SelectedArea representing the preview rectangle.
        """
        if self._active_area_type is None:
            return None

        assert self._start is not None
        x1, y1 = self._start
        x2, y2 = int(round(e.image_x)), int(round(e.image_y))
        dx = x2 - x1
        dy = y2 - y1

        # force square if shift is held
        if e.shift:
            size = max(abs(dx), abs(dy))
            dx = size if dx >= 0 else -size
            dy = size if dy >= 0 else -size

        x = min(x1, x1 + dx)
        y = min(y1, y1 + dy)
        w = abs(dx)
        h = abs(dy)

        if e.shift:
            x = max(0, x)
            y = max(0, y)

            w = min(w, self._width - x)
            h = min(h, self._height - y)

            size = min(w, h)
            w = h = size

        return SelectedArea(
            origin=PixelPoint(x=x, y=y),
            width=w,
            height=h,
            type=self._active_area_type,
            active=True,
        )

    def _get_edited_area_preview(
        self, e: events.MouseEventArguments
    ) -> SelectedArea | None:
        """
        Render preview rectangle while redrawing an area in edit mode.

        Args:
            e: Mouse event arguments.

        Returns:
            SelectedArea representing the redrawn area.
        """
        assert self._start is not None
        assert self._selected_area_index is not None

        selected_area = self._areas[self._selected_area_index]

        x1, y1 = self._start
        x2, y2 = int(round(e.image_x)), int(round(e.image_y))
        dx = x2 - x1
        dy = y2 - y1

        # force square if shift is held
        if e.shift:
            size = max(abs(dx), abs(dy))
            dx = size if dx >= 0 else -size
            dy = size if dy >= 0 else -size

        x = min(x1, x1 + dx)
        y = min(y1, y1 + dy)
        w = abs(dx)
        h = abs(dy)

        if e.shift:
            x = max(0, x)
            y = max(0, y)

            w = min(w, self._width - x)
            h = min(h, self._height - y)

            size = min(w, h)
            w = h = size

        return SelectedArea(
            origin=PixelPoint(x=x, y=y),
            width=w,
            height=h,
            type=selected_area.type,
            active=True,
        )

    def _finalize_area(self, e: events.MouseEventArguments) -> None:
        """
        Finalize the selected area.

        Args:
            e: Mouse event arguments at area completion.
        """
        if (area := self._get_area_preview(e)) is None:
            return

        area.active = False
        self._areas.append(area)

        self._update_area_type_options()
        self._update_active_area_type()

        assert self._final_layer is not None
        if area.width > 0 and area.height > 0:
            self._final_layer.content += area.render()

    def _finalize_edited_area(self, e: events.MouseEventArguments) -> None:
        """
        Finalize the edited area and deselect.

        Args:
            e: Mouse event arguments at edit completion.
        """
        if (area := self._get_edited_area_preview(e)) is None:
            return

        assert self._selected_area_index is not None

        # replace the selected area with the new one
        area.active = False
        self._areas[self._selected_area_index] = area

        self._deselect_area()

        self._update_area_type_options()
        self._update_active_area_type()

    def get_areas(self) -> dict[AreaType, list[RelativeArea]]:
        """
        Retrieve all finalized areas in relative units separated by AreaType.
        """
        grouped: dict[AreaType, list[RelativeArea]] = defaultdict(list)

        for area in self._areas:
            grouped[area.type].append(area.to_relative(self._image.resolution))

        return grouped

    def _find_area_at_point(self, x: int, y: int) -> int | None:
        """
        Find the index of an area at the given point.

        If multiple areas overlap, returns the one latest in the list.

        Args:
            x: X coordinate in pixels.
            y: Y coordinate in pixels.

        Returns:
            Index of the area or None if no area found at point.
        """
        # iterate from end to start to get the latest one
        for i in range(len(self._areas) - 1, -1, -1):
            area = self._areas[i]
            if (
                area.origin.x <= x <= area.origin.x + area.width
                and area.origin.y <= y <= area.origin.y + area.height
            ):
                return i
        return None

    def _select_area(self, index: int) -> None:
        """
        Select an area and move it to the front of the list.

        Args:
            index: Index of the area to select.
        """
        if index < 0 or index >= len(self._areas):
            return

        # mark as active
        self._areas[index].active = True
        self._active_area_type = self._areas[index].type

        # move to the front of the list
        area = self._areas.pop(index)
        self._areas.insert(0, area)
        self._selected_area_index = 0
        self._edit_mode = True

        self._update_area_type_options()

        # re-render
        self._redraw_final_layer()

    def _deselect_area(self) -> None:
        """Deselect the currently selected area."""
        if self._selected_area_index is not None:
            self._areas[self._selected_area_index].active = False
            self._selected_area_index = None

        self._edit_mode = False

        self._update_area_type_options()
        self._update_active_area_type()

        # re-render
        self._redraw_final_layer()

    def _delete_selected_area(self) -> None:
        """Delete the currently selected area."""
        if self._selected_area_index is not None:
            self._areas.pop(self._selected_area_index)
            self._selected_area_index = None
            self._edit_mode = False

            self._update_area_type_options()
            self._update_active_area_type()

            # re-render
            self._redraw_final_layer()

    def _redraw_final_layer(self) -> None:
        """Redraw all areas in the final layer."""
        assert self._final_layer is not None
        self._final_layer.content = ""

        for area in self._areas:
            self._final_layer.content += area.render()

    def _on_key_pressed(self, e: events.KeyEventArguments) -> None:
        """
        Handle keyboard events.

        Args:
            e: Keyboard event arguments.
        """
        # only handle keydown events, ignore keyup and repeats
        if not e.action.keydown:
            return

        if e.key == "Delete":
            self._delete_selected_area()
        elif e.key == "e":
            # toggle edit mode for area at current cursor position
            if self._edit_mode:
                self._deselect_area()
            else:
                mx, my = self._current_pos
                area_index = self._find_area_at_point(mx, my)
                if area_index is not None:
                    self._select_area(area_index)

    def _on_close_clicked(self) -> None:
        """Handle close button click."""
        self._on_close()
