# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable

from nicegui import events

from fibsem_maestro.core.area import PixelArea
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.gui.area_selector.selected_area import SelectedArea


class ViewportController:
    """
    Manages zoom and pan state for a 2D image viewport.

    Args:
        resolution: The full resolution of the source image.
        max_display_dimensions: Maximum (width, height) of the display area.
        on_change: Called with the new viewport whenever zoom or pan changes.
    """

    def __init__(
        self,
        resolution: Resolution,
        max_display_dimensions: tuple[int, int],
        on_change: Callable[[PixelArea], None],
    ):
        self._resolution = resolution
        self._max_display_width, self._max_display_height = max_display_dimensions
        self._on_change = on_change

        self._zoom_level: float = 1.0
        self._cursor_x: int = 0
        self._cursor_y: int = 0

        self._viewport = PixelArea(
            origin=PixelPoint(x=0, y=0),
            width=resolution.width,
            height=resolution.height,
        )

    def screen_to_image(
        self,
        x: float,
        y: float,
    ) -> tuple[int, int]:
        rel_x = x / self._resolution.width
        rel_y = y / self._resolution.height
        return (
            int(round(self._viewport.origin.x + rel_x * self._viewport.width)),
            int(round(self._viewport.origin.y + rel_y * self._viewport.height)),
        )

    def image_to_screen(self, x: int, y: int) -> tuple[float, float]:
        rel_x = (x - self._viewport.origin.x) / self._viewport.width
        rel_y = (y - self._viewport.origin.y) / self._viewport.height
        return (
            rel_x * self._resolution.width,
            rel_y * self._resolution.height,
        )

    def render_area(self, area: SelectedArea) -> str:
        x, y = self.image_to_screen(area.origin.x, area.origin.y)

        return (
            f'<rect x="{x}" y="{y}" width="{area.width}" height="{area.height}" '
            f'fill="{area.color}" fill-opacity="0.1" stroke="{area.color}" stroke-width="5" />'
            f'<text x="{x + area.width // 2}" y="{y + 20}" text-anchor="middle" '
            f'dominant-baseline="middle" fill="{area.color}" font-size="12">'
            f"{area.label}</text>"
        )

    @property
    def viewport(self) -> PixelArea:
        return self._viewport

    def set_zoom(self, zoom_level: float) -> None:
        img_w, img_h = self._resolution.width, self._resolution.height

        self._zoom_level = max(1.0, zoom_level)
        new_width = max(int(img_w / self._zoom_level), 1)
        new_height = max(int(img_h / self._zoom_level), 1)

        self._viewport = PixelArea(
            origin=PixelPoint(
                x=max(0, min(img_w - new_width, self._cursor_x - new_width // 2)),
                y=max(0, min(img_h - new_height, self._cursor_y - new_height // 2)),
            ),
            width=new_width,
            height=new_height,
        )
        self._on_change(self._viewport)

    def pan(self, dx: int, dy: int) -> None:
        img_w, img_h = self._resolution.width, self._resolution.height

        self._viewport = PixelArea(
            origin=PixelPoint(
                x=max(
                    0, min(img_w - self._viewport.width, self._viewport.origin.x + dx)
                ),
                y=max(
                    0, min(img_h - self._viewport.height, self._viewport.origin.y + dy)
                ),
            ),
            width=self._viewport.width,
            height=self._viewport.height,
        )
        self._on_change(self._viewport)

    def handle_key(self, e: events.KeyEventArguments) -> bool:
        """Returns True if the event was consumed."""
        if not e.action.keydown:
            return False

        pan_step_x = int(self._viewport.width * 0.1)
        pan_step_y = int(self._viewport.height * 0.1)

        match str(e.key):
            case "+" | "=":
                self.set_zoom(self._zoom_level * 1.2)
            case "-":
                self.set_zoom(self._zoom_level / 1.2)
            case "ArrowLeft":
                self.pan(-pan_step_x, 0)
            case "ArrowRight":
                self.pan(pan_step_x, 0)
            case "ArrowUp":
                self.pan(0, -pan_step_y)
            case "ArrowDown":
                self.pan(0, pan_step_y)
            case _:
                return False

        return True

    def handle_mouse(self, e: events.MouseEventArguments) -> None:
        """Track cursor position for zoom centering."""
        if e.type == "mousemove":
            self._cursor_x, self._cursor_y = self.screen_to_image(e.image_x, e.image_y)
