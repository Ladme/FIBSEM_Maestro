# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import TYPE_CHECKING

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QPainterPath, QTransform
from PyQt6.QtWidgets import QGraphicsItem, QGraphicsPathItem, QGraphicsRectItem

from fibsem_maestro.core.direction import Direction
from fibsem_maestro.gui.form_builder.widgets.area_select._constants import (
    ARROW_COLOR,
    ARROW_PEN,
    MARGIN_FILL,
    MARGIN_PEN,
)
from fibsem_maestro.settings.form_utils import AreaOverlay

if TYPE_CHECKING:
    from fibsem_maestro.gui.form_builder.widgets.area_select._rectangle import (
        ResizableRect,
    )


@dataclass(frozen=True)
class OverlayData:
    """
    Runtime values feeding the active area overlay.

    Attributes:
        margin_nm: Margin size in nanometers, used by `SHOW_MARGIN`.
        direction: Arrow direction, used by `SHOW_DIRECTION`.
    """

    margin_nm: float | None = None
    direction: Direction | None = None


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
        item.setBrush(MARGIN_FILL)
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


def build_decoration(
    overlay: AreaOverlay | None,
    data: OverlayData,
    pixel_size_nm: float | None,
) -> AreaDecoration | None:
    """
    Build the decoration for an overlay kind from runtime data and image scale.

    Returns None when the overlay is unset or its required data/scale is missing.

    Args:
        overlay: The overlay kind from the form hint, or None.
        data: Runtime overlay values supplied to the widget.
        pixel_size_nm: Image pixel size in nanometers, or None if no image loaded.

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
