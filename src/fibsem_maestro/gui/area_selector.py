# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import tempfile

import numpy as np
from nicegui import events, ui
from PIL import Image as PILImage

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint


class AreaSelector:
    """Interactive area selector for image regions."""

    def __init__(self, image: Image, max_areas: int | None = None):
        """
        Initialize AreaSelector.

        Args:
            image: An instance of image to work with.
            max_areas: Maximum number of areas to select. None for unlimited.
        """
        self._image = image
        self._max_areas = max_areas
        self._areas: list[RelativeArea] = []
        self._start: tuple[int, int] | None = None

        # get image dimensions from the numpy array
        self._width = image.shape[1]
        self._height = image.shape[0]

        # convert to PIL and save temporarily for display
        self._image_path = self._save_temp_image(image)

        self._image_widget = None
        self._final_layer = None
        self._preview_layer = None
        self._mouse_layer = None

    def _save_temp_image(self, image: Image) -> str:
        """Save image to temporary file for UI display."""
        img_8bit = image.to_8bit()
        img_array = np.uint8(img_8bit)

        pil_img = PILImage.fromarray(
            img_array, mode="L" if len(image.shape) == 2 else "RGB"
        )

        with tempfile.NamedTemporaryFile(delete=False, suffix=".png") as temp_file:
            pil_img.save(temp_file.name)
            return temp_file.name

    def build(self):
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

        self._image_widget = (
            ui.interactive_image(
                self._image_path,
                on_mouse=self._mouse_handler,
                events=["mousedown", "mousemove", "mouseup"],
                cross=True,
                sanitize=False,
            )
            .classes("no-select crosshair-cursor")
            .style("width: 1200px; height: auto;")
        )

        self._final_layer = self._image_widget.add_layer()
        self._preview_layer = self._image_widget.add_layer()
        self._mouse_layer = self._image_widget.add_layer()

    def _mouse_handler(self, e: events.MouseEventArguments):
        """Handle mouse events."""
        mx, my = e.image_x, e.image_y

        # update mouse coordinates display
        assert self._mouse_layer is not None
        assert self._preview_layer is not None
        if 0 <= mx <= self._width and 0 <= my <= self._height:
            self._mouse_layer.content = self._render_mouse_text(mx, my)
        else:
            self._mouse_layer.content = ""

        if e.type == "mousedown":
            self._start = (mx, my)
            self._preview_layer.content = ""

        elif e.type == "mousemove" and self._start:
            self._preview_layer.content = self._render_preview_rect(e)

        elif e.type == "mouseup" and self._start:
            self._finalize_area(e)
            self._preview_layer.content = ""
            self._start = None

    def _render_mouse_text(self, x: int, y: int) -> str:
        """Render mouse position text."""
        return (
            f'<text x="{x + 40}" y="{y + 60}" fill="black" font-size="40">'
            f"{int(x)},{int(y)}</text>"
        )

    def _render_preview_rect(self, e: events.MouseEventArguments) -> str:
        """Render preview rectangle while dragging."""
        assert self._start is not None
        x1, y1 = self._start
        x2, y2 = e.image_x, e.image_y
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

        perc_w = w / self._width * 100
        perc_h = h / self._height * 100
        perc_area = (w * h) / (self._width * self._height) * 100

        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="blue" fill-opacity="0.05" stroke="blue" stroke-width="8" />'
            f'<text x="{x + 40}" y="{y + 60}" fill="blue" font-size="40">'
            f"{int(x)},{int(y)}</text>"
            f'<text x="{x + w / 2}" y="{y + 50}" fill="blue" font-size="40" text-anchor="middle">'
            f"{int(w)} ({perc_w:.1f}%)</text>"
            f'<text x="{x + 20}" y="{y + h / 2}" fill="blue" font-size="40" text-anchor="start" dominant-baseline="middle">'
            f"{int(h)} ({perc_h:.1f}%)</text>"
            f'<text x="{x + w / 2}" y="{y + h / 2}" fill="blue" font-size="40" text-anchor="middle" dominant-baseline="middle">'
            f"{perc_area:.1f}%</text>"
        )

    def _render_final_rect(self, x: int, y: int, w: int, h: int) -> str:
        """Render finalized rectangle."""
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" '
            f'fill="green" fill-opacity="0.05" stroke="green" stroke-width="8" />'
        )

    def _finalize_area(self, e: events.MouseEventArguments):
        """Finalize the selected area."""
        if self._max_areas is not None and len(self._areas) >= self._max_areas:
            return

        assert self._final_layer is not None
        assert self._start is not None
        x1, y1 = self._start
        x2, y2 = e.image_x, e.image_y
        x = min(x1, x2)
        y = min(y1, y2)
        w = abs(x2 - x1)
        h = abs(y2 - y1)

        if w > 0 and h > 0:
            self._final_layer.content += self._render_final_rect(x, y, w, h)

            area = RelativeArea(
                origin=RelativePoint(x=x / self._width, y=y / self._height),
                width=w / self._width,
                height=h / self._height,
            )
            self._areas.append(area)

    def get_areas(self) -> list[RelativeArea]:
        """Return list of selected areas in relative coordinates."""
        return self._areas
