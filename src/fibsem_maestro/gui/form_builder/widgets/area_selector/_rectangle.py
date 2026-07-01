# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPen
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsItem, QGraphicsRectItem

from fibsem_maestro.gui.form_builder.widgets.area_selector._constants import (
    HANDLE_BORDER,
    HANDLE_COLOR,
    HANDLE_RADIUS,
    RECT_FILL,
    RECT_PEN_NORMAL,
    RECT_PEN_SELECTED,
)
from fibsem_maestro.gui.form_builder.widgets.area_selector._handle import (
    HANDLE_CURSORS,
    Handle,
    apply_handle_drag,
)


class ResizableRect(QGraphicsRectItem):
    """
    A rectangle with 8 resize handles and a movable body.

    Dragging the body moves the rectangle.
    Dragging a handle resizes from that anchor point.
    """

    def __init__(self, rect: QRectF, parent: QGraphicsRectItem | None = None) -> None:
        super().__init__(rect, parent)
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

        # create one ellipse item per handle, parented to this rect
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
        r = self.rect()
        for h, ellipse in self._handles.items():
            pos = h.position(r)
            ellipse.setPos(pos)

    def set_rect(self, rect: QRectF) -> None:
        self.setRect(rect)
        self._update_handle_positions()

    def _handle_at(self, pos: QPointF) -> Handle | None:
        """Return which handle (if any) is under the given item-local position."""
        for h in self._handles:
            hp = h.position(self.rect())
            dx = pos.x() - hp.x()
            dy = pos.y() - hp.y()
            if (dx * dx + dy * dy) ** 0.5 <= HANDLE_RADIUS * 2:
                return h
        return None

    def paint(self, painter, option, widget=None) -> None:
        self.setPen(RECT_PEN_SELECTED if self.isSelected() else RECT_PEN_NORMAL)
        super().paint(painter, option, widget)

    def mousePressEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            super().mousePressEvent(event)
            return

        pos = event.pos()
        handle = self._handle_at(pos)

        if handle is not None:
            self._drag_handle = handle
            self._drag_start_scene = event.scenePos()
            self._drag_start_rect = QRectF(self.rect())
        else:
            self._body_drag_start = event.scenePos()
            self._body_drag_origin = self.pos()

        self.setSelected(True)
        event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self._drag_handle is not None and self._drag_start_scene is not None:
            delta = event.scenePos() - self._drag_start_scene
            assert self._drag_start_rect is not None
            new_rect = apply_handle_drag(
                self._drag_start_rect, self._drag_handle, delta
            )
            self.set_rect(new_rect)
            event.accept()
            return

        if self._body_drag_start is not None and self._body_drag_origin is not None:
            delta = event.scenePos() - self._body_drag_start
            self.setPos(self._body_drag_origin + delta)
            event.accept()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self._drag_handle = None
        self._drag_start_scene = None
        self._drag_start_rect = None
        self._body_drag_start = None
        self._body_drag_origin = None
        super().mouseReleaseEvent(event)

    def scene_rect(self) -> QRectF:
        """Return the rect in scene coordinates, accounting for any body drag offset."""
        return self.mapToScene(self.rect()).boundingRect()
