# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPainter, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QStyleOptionGraphicsItem,
    QWidget,
)

from fibsem_maestro.gui.form_builder.widgets.area_select._constants import (
    HANDLE_BORDER,
    HANDLE_COLOR,
    HANDLE_RADIUS,
    RECT_FILL,
    RECT_PEN_NORMAL,
    RECT_PEN_SELECTED,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._handle import (
    HANDLE_CURSORS,
    Handle,
    apply_handle_drag,
)


class ResizableRect(QGraphicsRectItem):
    """
    A rectangle with eight resize handles and a movable body.

    Args:
        rect: Initial geometry, in scene coordinates.
        on_edit_finished: Called once when a move or resize gesture completes.
        parent: Parent graphics item.
    """

    def __init__(
        self,
        rect: QRectF,
        on_edit_finished: Callable[[], None] | None = None,
        parent: QGraphicsRectItem | None = None,
    ) -> None:
        super().__init__(rect, parent)
        self._on_edit_finished = on_edit_finished
        self.setPen(RECT_PEN_NORMAL)
        self.setBrush(RECT_FILL)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges)
        self.setAcceptHoverEvents(True)

        self._drag_handle: Handle | None = None
        self._drag_start_scene: QPointF | None = None
        self._drag_start_rect: QRectF | None = None
        self._body_drag_start: QPointF | None = None
        self._body_drag_origin: QPointF | None = None
        self._moved_during_drag = False

        # one ellipse item per handle, parented to this rect
        self._handles: dict[Handle, QGraphicsEllipseItem] = {}
        for h in Handle:
            ellipse = QGraphicsEllipseItem(
                -HANDLE_RADIUS,
                -HANDLE_RADIUS,
                HANDLE_RADIUS * 2,
                HANDLE_RADIUS * 2,
                self,
            )
            ellipse.setBrush(QBrush(HANDLE_COLOR))
            ellipse.setPen(QPen(HANDLE_BORDER, 1.5))
            ellipse.setZValue(1)
            ellipse.setCursor(QCursor(HANDLE_CURSORS[h]))
            self._handles[h] = ellipse

        self._update_handle_positions()

    def _update_handle_positions(self) -> None:
        """Reposition all handle ellipses to match the current rectangle."""
        r = self.rect()
        for h, ellipse in self._handles.items():
            ellipse.setPos(h.position(r))

    def set_rect(self, rect: QRectF) -> None:
        """
        Set the rectangle geometry and refresh handle positions.

        Args:
            rect: The new geometry, in the item's local coordinates.
        """
        self.setRect(rect)
        self._update_handle_positions()

    def _handle_at(self, pos: QPointF) -> Handle | None:
        """
        Return the handle under a local position, or None.

        Args:
            pos: A point in the item's local coordinate space.

        Returns:
            The handle within grab distance of `pos`, or None.
        """
        for h in self._handles:
            hp = h.position(self.rect())
            dx = pos.x() - hp.x()
            dy = pos.y() - hp.y()
            if (dx * dx + dy * dy) ** 0.5 <= HANDLE_RADIUS * 2:
                return h
        return None

    def paint(
        self,
        painter: QPainter,
        option: QStyleOptionGraphicsItem,
        widget: QWidget | None = None,
    ) -> None:
        """Paint the rectangle, styling its border by selection state."""
        self.setPen(RECT_PEN_SELECTED if self.isSelected() else RECT_PEN_NORMAL)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Begin a handle-resize or body-move gesture."""
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.pos()
        handle = self._handle_at(pos)
        self._moved_during_drag = False

        if handle is not None:
            self._drag_handle = handle
            self._drag_start_scene = event.scenePos()
            self._drag_start_rect = QRectF(self.rect())
        else:
            self._body_drag_start = event.scenePos()
            self._body_drag_origin = self.pos()

        self.setSelected(True)
        event.accept()

    def mouseMoveEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Apply an in-progress resize or move."""
        if self._drag_handle is not None and self._drag_start_scene is not None:
            delta = event.scenePos() - self._drag_start_scene  # type: ignore
            assert self._drag_start_rect is not None
            new_rect = apply_handle_drag(
                self._drag_start_rect, self._drag_handle, delta
            )
            self.set_rect(new_rect)
            self._moved_during_drag = True
            event.accept()
            return

        if self._body_drag_start is not None and self._body_drag_origin is not None:
            delta = event.scenePos() - self._body_drag_start  # type: ignore
            self.setPos(self._body_drag_origin + delta)
            self._moved_during_drag = True
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """End the gesture and notify once if the geometry actually changed."""
        moved = self._moved_during_drag and (
            self._drag_handle is not None or self._body_drag_start is not None
        )
        self._drag_handle = None
        self._drag_start_scene = None
        self._drag_start_rect = None
        self._body_drag_start = None
        self._body_drag_origin = None
        self._moved_during_drag = False
        super().mouseReleaseEvent(event)
        if moved and self._on_edit_finished is not None:
            self._on_edit_finished()

    def scene_rect(self) -> QRectF:
        """
        Return the rectangle in scene coordinates, including any move offset.

        Returns:
            The bounding rectangle of this item mapped into the scene.
        """
        return self.mapToScene(self.rect()).boundingRect()
