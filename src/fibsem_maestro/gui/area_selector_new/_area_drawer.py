# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from nicegui import events, ui

from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.gui.area_selector_new._viewport_controller import ViewportController
from fibsem_maestro.gui.area_selector_new.area_state import AreaState
from fibsem_maestro.gui.area_selector_new.area_type import AreaType
from fibsem_maestro.gui.area_selector_new.selected_area import SelectedArea


class AreaDrawer:
    def __init__(
        self,
        image_resolution: Resolution,
        viewport_controller: ViewportController,
    ):
        self._viewport_controller = viewport_controller
        self._drawn_area_type: AreaType | None = None

        self._max_width = image_resolution.width
        self._max_height = image_resolution.height

        self._start: tuple[int, int] | None = None

        self._preview_layer = None
        self._final_layer = None

    def build_layers(self, image_widget: ui.interactive_image) -> None:
        self._preview_layer = image_widget.add_layer()
        self._final_layer = image_widget.add_layer()

    def is_active(self) -> bool:
        return self._drawn_area_type is not None

    def get_drawn_area_type(self) -> AreaType | None:
        return self._drawn_area_type

    def update(self, area_type: AreaType | None) -> None:
        self._drawn_area_type = area_type

    def handle_mouse(self, e: events.MouseEventArguments) -> None:
        mx, my = self._viewport_controller.screen_to_image(e.image_x, e.image_y)

        assert self._preview_layer is not None

        if e.type == "mousedown":
            self._start = (mx, my)
            self._preview_layer.content = ""

        elif e.type == "mousemove" and self._start:
            if (area := self._get_area_preview(e)) is None:
                return

            self._preview_layer.content = self._viewport_controller.render_area(area)

        elif e.type == "mouseup" and self._start:
            # self._finalize_area(e)
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
        if self._drawn_area_type is None:
            return None

        assert self._start is not None
        x1, y1 = self._start
        x2, y2 = self._viewport_controller.screen_to_image(e.image_x, e.image_y)
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

            w = min(w, self._max_width - x)
            h = min(h, self._max_height - y)

            size = min(w, h)
            w = h = size

        return SelectedArea(
            origin=PixelPoint(x=x, y=y),
            width=w,
            height=h,
            type=self._drawn_area_type,
            state=AreaState.ACTIVE,
            padding=(0, 0),
        )
