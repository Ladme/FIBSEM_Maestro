# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import QRectF, Qt
from PyQt6.QtGui import QBrush, QPainterPath, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem

from fibsem_maestro.core.direction import Direction
from fibsem_maestro.criterion.criterion import (
    MIN_TILE_PX,
    tile_origins,
    tile_size_in_pixels,
    tile_step_in_pixels,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._constants import (
    ARROW_COLOR,
    ARROW_PEN,
    MARGIN_PEN,
    MAX_TILES,
    SHIFT_PEN,
    TILE_PEN,
)
from fibsem_maestro.settings.form_utils import AreaOverlay

if TYPE_CHECKING:
    from collections.abc import Sequence

    from fibsem_maestro.gui.form_builder.widgets.area_select._rectangle import (
        ResizableRect,
    )
    from fibsem_maestro.logging.text.text_logger import TextLogger


@dataclass(frozen=True)
class OverlayData:
    """
    Runtime values feeding the active area overlay.

    Attributes:
        margin_nm: Margin size in nanometers, used by `SHOW_MARGIN`.
        direction: Arrow direction, used by `SHOW_DIRECTION`.
        tile_size_nm: Tile size in nanometers, used by `SHOW_TILES`.
        tile_relative_overlap: Relative overlap of tiles, used by `SHOW_TILES`.
        shift_distance_nm: Area shift distance in nanometers, used by `SHOW_AREA_SHIFT`.
    """

    margin_nm: float | None = None
    direction: Direction | None = None
    tile_size_nm: float | None = None
    tile_relative_overlap: float | None = None
    shift_distance_nm: float | None = None


class AreaDecoration(ABC):
    """
    A non-interactive visual embellishment drawn on a `ResizableRect`.
    """

    @abstractmethod
    def attach(self, rect: ResizableRect) -> None:
        """Create the items as children of `rect` and lay them out."""

    @abstractmethod
    def update(self, rect: ResizableRect) -> None:
        """Re-lay-out the items after the rectangle's geometry changed."""

    @abstractmethod
    def detach(self) -> None:
        """Remove every item this decoration created from the scene."""


class MarginDecoration(AreaDecoration):
    """
    A soft halo extending the area outward by a fixed margin.

    The margin is supplied in scene units (image pixels), so it expands the
    rectangle uniformly on all sides. It is drawn behind the parent's fill in a
    fainter colour so the crisp area border stays legible on top.

    Args:
        margin_px: Margin width in scene units (image pixels).
    """

    def __init__(self, margin_px: float) -> None:
        self._margin_px = margin_px
        self._item: QGraphicsRectItem | None = None

    def attach(self, rect: ResizableRect) -> None:
        item = QGraphicsRectItem(rect)
        item.setPen(MARGIN_PEN)
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # draws behind the parent
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemStacksBehindParent, True)
        self._item = item
        self.update(rect)

    def update(self, rect: ResizableRect) -> None:
        if self._item is not None:
            m = self._margin_px
            self._item.setRect(rect.rect().adjusted(-m, -m, m, m))

    def detach(self) -> None:
        if self._item is not None and (scene := self._item.scene()) is not None:
            scene.removeItem(self._item)
        self._item = None


class DirectionDecoration(AreaDecoration):
    """
    A coloured arrow through the centre of the area.

    Directions are in image space, where `Direction.UP` points toward the top of
    the image (decreasing y).

    Args:
        direction: The direction the arrow points.
    """

    _ANGLES = {
        Direction.RIGHT: 0.0,
        Direction.DOWN: 90.0,
        Direction.LEFT: 180.0,
        Direction.UP: 270.0,
    }

    def __init__(self, direction: Direction) -> None:
        self._direction = direction
        self._item: QGraphicsPathItem | None = None

    def attach(self, rect: ResizableRect) -> None:
        item = QGraphicsPathItem(rect)
        item.setPen(ARROW_PEN)
        item.setBrush(QBrush(ARROW_COLOR))
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # above the fill, below the handles
        item.setZValue(0.5)
        self._item = item
        self.update(rect)

    def update(self, rect: ResizableRect) -> None:
        if self._item is None:
            return

        r = rect.rect()
        path = self._arrow_path(0.25 * min(r.width(), r.height()))
        transform = QTransform()
        transform.translate(r.center().x(), r.center().y())
        transform.rotate(self._ANGLES[self._direction])

        self._item.setPath(transform.map(path))

    def detach(self) -> None:
        if self._item is not None and (scene := self._item.scene()) is not None:
            scene.removeItem(self._item)
        self._item = None

    @staticmethod
    def _arrow_path(length: float) -> QPainterPath:
        """
        Build a filled arrow of the given length pointing along +x, centred at the origin.

        Args:
            length: Total arrow length in scene units.

        Returns:
            A closed path describing the arrow outline.
        """
        half = length / 2.0
        shaft = max(2.0, length * 0.12)
        head_len = length * 0.4
        head_half = shaft * 2.8
        tip, neck = half, half - head_len

        path = QPainterPath()
        path.moveTo(-half, -shaft)
        path.lineTo(neck, -shaft)
        path.lineTo(neck, -head_half)
        path.lineTo(tip, 0.0)
        path.lineTo(neck, head_half)
        path.lineTo(neck, shaft)
        path.lineTo(-half, shaft)
        path.closeSubpath()
        return path


class TileDecoration(AreaDecoration):
    """
    A grid of tiles over the area.

    Args:
        tile_px: Tile side length in pixels, already quantised.
        step_px: Distance between tile origins in pixels.
        txt_log: Logger for warning messages.
    """

    def __init__(
        self,
        tile_px: int,
        step_px: int,
        txt_log: TextLogger | None,
    ) -> None:
        self._tile_px = tile_px
        self._step_px = step_px
        self._txt_log = txt_log
        self._warned = False
        self._item: QGraphicsPathItem | None = None

    def attach(self, rect: ResizableRect) -> None:
        item = QGraphicsPathItem(rect)
        item.setPen(TILE_PEN)
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # above the fill, below the handles
        item.setZValue(0.5)
        self._item = item
        self.update(rect)

    def update(self, rect: ResizableRect) -> None:
        if self._item is not None:
            self._item.setPath(self._grid_path(rect.rect()))

    def detach(self) -> None:
        if self._item is not None and (scene := self._item.scene()) is not None:
            scene.removeItem(self._item)
        self._item = None

    def _grid_path(self, r: QRectF) -> QPainterPath:
        """
        Build the tile grid for an area rectangle.

        Args:
            r: The area rectangle, in the parent item's local coordinates.

        Returns:
            A path of tile outlines, or an empty path if a tile does not fit or
            the grid would exceed `MAX_TILES`.
        """
        xs = tile_origins(int(r.width()), self._tile_px, self._step_px)
        ys = tile_origins(int(r.height()), self._tile_px, self._step_px)

        path = QPainterPath()
        if (count := len(xs) * len(ys)) > MAX_TILES:
            # update() runs on every mouse-move of a resize, so warn once
            if not self._warned:
                self._warned = True
                self._txt_log.warning(
                    f"The selected area yields {count} tiles, more than the "
                    f"{MAX_TILES} that can be displayed; the tiling overlay is "
                    "hidden. Increase the tile size or shrink the area."
                ) if self._txt_log is not None else None
            return path

        for y in ys:
            for x in xs:
                path.addRect(r.x() + x, r.y() + y, self._tile_px, self._tile_px)
        return path


class AreaShiftDecoration(AreaDecoration):
    """
    A dashed outline of where the area moves to after one shift.

    The offset is supplied in scene units (image pixels) and applied along
    `direction` in image space, where `Direction.UP` points toward the top of
    the image (decreasing y). The outline is unfilled so the underlying image
    stays visible, and is drawn behind the parent so the area border
    remains legible where the two overlap.

    Args:
        shift_px: Shift distance in scene units (image pixels).
        direction: The direction the area moves in.
    """

    _OFFSETS = {
        Direction.RIGHT: (1.0, 0.0),
        Direction.LEFT: (-1.0, 0.0),
        Direction.DOWN: (0.0, 1.0),
        Direction.UP: (0.0, -1.0),
    }

    def __init__(self, shift_px: float, direction: Direction) -> None:
        self._shift_px = shift_px
        self._direction = direction
        self._item: QGraphicsRectItem | None = None

    def attach(self, rect: ResizableRect) -> None:
        item = QGraphicsRectItem(rect)
        item.setPen(SHIFT_PEN)
        item.setBrush(QBrush(Qt.BrushStyle.NoBrush))
        item.setAcceptedMouseButtons(Qt.MouseButton.NoButton)
        # draws behind the parent
        item.setFlag(QGraphicsItem.GraphicsItemFlag.ItemStacksBehindParent, True)
        self._item = item
        self.update(rect)

    def update(self, rect: ResizableRect) -> None:
        if self._item is not None:
            dx, dy = self._OFFSETS[self._direction]
            self._item.setRect(
                rect.rect().translated(dx * self._shift_px, dy * self._shift_px)
            )

    def detach(self) -> None:
        if self._item is not None and (scene := self._item.scene()) is not None:
            scene.removeItem(self._item)
        self._item = None


def build_decoration(
    overlay: AreaOverlay | None,
    data: OverlayData,
    pixel_size_nm: float | None,
    txt_log: TextLogger | None,
) -> AreaDecoration | None:
    """
    Build the decoration for an overlay kind from runtime data and image scale.

    Returns None when the overlay is unset or its required data/scale is
    missing. A configuration that the criterion itself would reject (a tile
    below `MIN_TILE_PX`, or an overlap leaving no step) is logged rather than
    passed over silently.

    Args:
        overlay: The overlay kind from the form hint, or None.
        data: Runtime overlay values supplied to the widget.
        pixel_size_nm: Image pixel size in nanometers, or None if no image loaded.
        txt_log: Logger for unusable overlay configurations.

    Returns:
        A decoration instance, or None if nothing should be drawn.
    """
    match overlay:
        case None:
            return None

        case AreaOverlay.SHOW_MARGIN:
            if data.margin_nm is None or not pixel_size_nm:
                return None
            return MarginDecoration(margin_px=data.margin_nm / pixel_size_nm)

        case AreaOverlay.SHOW_DIRECTION:
            if data.direction is None:
                return None
            return DirectionDecoration(direction=data.direction)

        case AreaOverlay.SHOW_TILES:
            if (
                data.tile_size_nm is None
                or data.tile_relative_overlap is None
                or not pixel_size_nm
            ):
                return None

            tile_px = tile_size_in_pixels(data.tile_size_nm, pixel_size_nm)
            if tile_px < MIN_TILE_PX:
                txt_log.warning(
                    f"A {data.tile_size_nm:g} nm tile is smaller than "
                    f"{MIN_TILE_PX} pixels at this pixel size; the tiling "
                    "overlay is hidden and the criterion would fail."
                ) if txt_log is not None else None
                return None

            step_px = tile_step_in_pixels(tile_px, data.tile_relative_overlap)
            if step_px <= 0:
                txt_log.warning(
                    f"An overlap of {data.tile_relative_overlap:g} leaves no "
                    "step between tiles; the tiling overlay is hidden and the "
                    "criterion would fail."
                ) if txt_log is not None else None
                return None

            return TileDecoration(tile_px=tile_px, step_px=step_px, txt_log=txt_log)

        case AreaOverlay.SHOW_AREA_SHIFT:
            if (
                data.shift_distance_nm is None
                or data.direction is None
                or not pixel_size_nm
            ):
                return None
            return AreaShiftDecoration(
                shift_px=data.shift_distance_nm / pixel_size_nm,
                direction=data.direction,
            )


def build_decorations(
    overlays: Sequence[tuple[AreaOverlay, OverlayData]],
    pixel_size_nm: float | None,
    txt_log: TextLogger | None,
) -> list[AreaDecoration]:
    """
    Build every decoration whose data and image scale are available.

    Args:
        overlays: Overlay kinds paired with their own runtime values.
        pixel_size_nm: Image pixel size in nanometers, or None if no image loaded.
        txt_log: Logger for unusable overlay configurations.

    Returns:
        The buildable decorations, in declaration order. Overlays with missing
        data or missing scale are skipped.
    """
    return [
        decoration
        for kind, data in overlays
        if (decoration := build_decoration(kind, data, pixel_size_nm, txt_log))
        is not None
    ]
