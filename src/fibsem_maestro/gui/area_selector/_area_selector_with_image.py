# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import base64
import io
from collections.abc import Callable

from nicegui import events, ui
from PIL import Image as PILImage
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.gui.area_selector.area_limits import AreaLimits
from fibsem_maestro.gui.area_selector.area_type import AreaType


class AreaSelectorWithImage:
    """Interactive area selector for image regions."""

    def __init__(
        self,
        image: Image,
        area_limits: AreaLimits,
        on_close: Callable[[], None],
        max_display_dimensions: tuple[int, int],
    ):
        """
        Initialize area selector with a loaded image.

        Args:
            image: The Image object to perform area selection on.
            area_limits: Area limits configuration.
            on_close: Callback when user closes the selector.
        """
        self._image_original = image
        self._area_limits = area_limits
        self._on_close = on_close

        # display constraints
        self._max_display_width = max_display_dimensions[0]
        self._max_display_height = max_display_dimensions[1]

        # zoom state
        self._initial_scale = self._compute_initial_scale()
        self._zoom_level: float = 1.0

        # viewport
        self._viewport_x = 0
        self._viewport_y = 0
        self._viewport_w = self._image_original.resolution.width
        self._viewport_h = self._image_original.resolution.height

        # display size
        self._display_width = int(
            self._image_original.resolution.width * self._initial_scale
        )
        self._display_height = int(
            self._image_original.resolution.height * self._initial_scale
        )

        # cursor
        self._cursor_x = 0
        self._cursor_y = 0

        self._image_base64 = self._get_image_base64()

        self._image_widget = None

    def build(self) -> None:
        """Build the UI component."""
        with ui.card().style("overflow: hidden;"):
            ui.label("Area selector").classes("font-bold")

            ui.button(icon="close", on_click=self._on_close).style(
                "position: absolute; top: 0; right: -10px; z-index: 10;"
            )

            self._image_widget = ui.interactive_image(
                self._image_base64,
                on_mouse=self._mouse_handler,
                events=["mousedown", "mousemove", "mouseup"],
                cross=True,
                sanitize=False,
            )

        ui.keyboard(on_key=self._on_key_pressed)

    def get_areas(self) -> dict[AreaType, list[RelativeArea]]:
        """
        Retrieve all finalized areas in relative units.

        Returns:
            Dictionary mapping AreaType to list of RelativeArea objects.
        """
        raise NotImplementedError()

    def _compute_initial_scale(self) -> float:
        """
        Compute the scale factor needed to fit original image in display area.

        Returns:
            Scale factor (1.0 if already fits, < 1.0 if downscaling needed).
        """
        resolution = self._image_original.resolution
        if (
            resolution.width <= self._max_display_width
            and resolution.height <= self._max_display_height
        ):
            return 1.0

        scale_w = self._max_display_width / resolution.width
        scale_h = self._max_display_height / resolution.height
        return min(scale_w, scale_h)

    def _get_display_image(self) -> Image:
        """Return cropped viewport scaled to display size."""

        img = self._image_original

        crop = img[
            self._viewport_y : self._viewport_y + self._viewport_h,
            self._viewport_x : self._viewport_x + self._viewport_w,
        ]

        scale_w = self._max_display_width / self._viewport_w
        scale_h = self._max_display_height / self._viewport_h
        scale = min(scale_w, scale_h)

        scaled = ndimage.zoom(crop, scale, order=1)

        return Image(scaled, pixel_size=img.pixel_size / scale)

    def _get_image_base64(self) -> str:
        display_image = self._get_display_image()

        img_8bit = display_image.to_8bit()
        pil_img = PILImage.fromarray(
            img_8bit, mode="L" if len(img_8bit.shape) == 2 else "RGB"
        )

        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{base64_str}"

    def _set_zoom(self, zoom_level: float) -> None:
        img_w = self._image_original.resolution.width
        img_h = self._image_original.resolution.height

        zoom_level = max(1.0, zoom_level)
        self._zoom_level = zoom_level

        new_w = int(img_w / zoom_level)
        new_h = int(img_h / zoom_level)

        cx = self._cursor_x
        cy = self._cursor_y

        self._viewport_w = new_w
        self._viewport_h = new_h

        self._viewport_x = max(0, min(img_w - new_w, cx - new_w // 2))
        self._viewport_y = max(0, min(img_h - new_h, cy - new_h // 2))

        base64_img = self._get_image_base64()

        assert self._image_widget is not None
        self._image_widget.source = base64_img
        self._image_widget.update()

    def _pan(self, dx: int, dy: int) -> None:
        img_w = self._image_original.resolution.width
        img_h = self._image_original.resolution.height

        self._viewport_x = max(0, min(img_w - self._viewport_w, self._viewport_x + dx))
        self._viewport_y = max(0, min(img_h - self._viewport_h, self._viewport_y + dy))

        assert self._image_widget is not None
        self._image_widget.source = self._get_image_base64()
        self._image_widget.update()

    def _on_key_pressed(self, e: events.KeyEventArguments) -> None:
        """
        Handle keyboard events.

        Args:
            e: Keyboard event arguments.
        """
        if not e.action.keydown:
            return

        pan_step_x = int(self._viewport_w * 0.1)
        pan_step_y = int(self._viewport_h * 0.1)

        if e.key == "+":
            self._set_zoom(self._zoom_level * 1.2)
        elif e.key == "-":
            self._set_zoom(max(self._zoom_level / 1.2, 1.0))
        elif e.key == "ArrowLeft":
            self._pan(-pan_step_x, 0)

        elif e.key == "ArrowRight":
            self._pan(pan_step_x, 0)

        elif e.key == "ArrowUp":
            self._pan(0, -pan_step_y)

        elif e.key == "ArrowDown":
            self._pan(0, pan_step_y)

    def _mouse_handler(self, e: events.MouseEventArguments) -> None:
        if e.type != "mousemove":
            return

        rel_x = e.image_x / self._display_width
        rel_y = e.image_y / self._display_height

        self._cursor_x = int(self._viewport_x + rel_x * self._viewport_w)
        self._cursor_y = int(self._viewport_y + rel_y * self._viewport_h)
