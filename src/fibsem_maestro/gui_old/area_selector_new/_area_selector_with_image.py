# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import base64
import io
from collections.abc import Callable

from nicegui import events, ui
from PIL import Image as PILImage
from scipy import ndimage  # type: ignore

from fibsem_maestro.core.area import PixelArea, RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.gui.area_selector_new._area_drawer import AreaDrawer
from fibsem_maestro.gui.area_selector_new._viewport_controller import ViewportController
from fibsem_maestro.gui.area_selector_new.area_limits import AreaLimits
from fibsem_maestro.gui.area_selector_new.area_type import AreaType


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

        self._viewport = PixelArea(
            origin=PixelPoint(x=0, y=0),
            width=image.resolution.width,
            height=image.resolution.height,
        )

        self._viewport_controller = ViewportController(
            resolution=image.resolution,
            max_display_dimensions=max_display_dimensions,
            on_change=self._on_viewport_changed,
        )

        self._area_drawer = AreaDrawer(
            self._image_original.resolution, self._viewport_controller
        )

        self._image_widget: ui.interactive_image | None = None
        self._image_base64 = self._get_image_base64()

        self._areas = []

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
        with ui.card().style("overflow: hidden;"):
            ui.label("Area selector").classes("font-bold")

            ui.button(icon="close", on_click=self._on_close).style(
                "position: absolute; top: 40px; right: 10px; z-index: 10; "
                "width: 30px !important; height: 30px !important; min-width: 30px !important; "
                "padding: 0 !important; background-color: black !important; color: white !important; "
                "border: none !important;"
            )

            self._image_widget = ui.interactive_image(
                self._image_base64,
                on_mouse=self._mouse_handler,
                events=["mousedown", "mousemove", "mouseup"],
                cross=self._area_drawer.is_active(),
                sanitize=False,
            ).classes(
                f"no-select {'crosshair-cursor' if self._area_drawer.is_active() else ''}"
            )

            ui.toggle(
                {
                    x: x.value.replace("_", " ").title()
                    for x in self._area_limits.get_available(self._areas)
                },
                value=self._area_drawer.get_drawn_area_type(),
                clearable=True,
                on_change=lambda e: self._set_area_type(e.value),
            )

            self._area_drawer.build_layers(self._image_widget)

        ui.keyboard(on_key=self._on_key_pressed)

    def get_areas(self) -> dict[AreaType, list[RelativeArea]]:
        """
        Retrieve all finalized areas in relative units.

        Returns:
            Dictionary mapping AreaType to list of RelativeArea objects.
        """
        raise NotImplementedError()

    def _on_viewport_changed(self, viewport: PixelArea) -> None:
        self._viewport = viewport
        assert self._image_widget is not None
        self._image_widget.source = self._get_image_base64()
        self._image_widget.update()

    def _get_display_image(self) -> Image:
        """Return cropped viewport scaled to display size."""
        img = self._image_original
        crop = img.crop(self._viewport.to_relative(img.resolution))

        scale_w = self._max_display_width / self._viewport.width
        scale_h = self._max_display_height / self._viewport.height
        scale = min(scale_w, scale_h)

        scaled = ndimage.zoom(crop, scale, order=1)
        return Image(scaled, pixel_size=img.pixel_size / scale)

    def _get_image_base64(self) -> str:
        display_image = self._get_display_image()

        img_8bit = display_image.to_8bit()
        pil_img = PILImage.fromarray(img_8bit, mode="L")

        buffer = io.BytesIO()
        pil_img.save(buffer, format="PNG")
        base64_str = base64.b64encode(buffer.getvalue()).decode()

        return f"data:image/png;base64,{base64_str}"

    def _on_key_pressed(self, e: events.KeyEventArguments) -> None:
        if not self._viewport_controller.handle_key(e):
            pass

    def _mouse_handler(self, e: events.MouseEventArguments) -> None:
        self._viewport_controller.handle_mouse(e)

        self._area_drawer.handle_mouse(e)

    def _set_area_type(self, area_type: AreaType | None):
        self._area_drawer.update(area_type)

        if self._image_widget is not None:
            self._image_widget.props(
                add="cross" if self._area_drawer.is_active() else None,
                remove=None if self._area_drawer.is_active() else "cross",
            )
            self._image_widget.classes(
                add="crosshair-cursor" if self._area_drawer.is_active() else None,
                remove=None if self._area_drawer.is_active() else "crosshair-cursor",
            )
