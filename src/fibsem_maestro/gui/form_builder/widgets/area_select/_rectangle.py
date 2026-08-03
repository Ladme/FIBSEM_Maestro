# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import QBrush, QCursor, QPainter, QPainterPath, QPen
from PyQt6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsRectItem,
    QGraphicsSceneMouseEvent,
    QStyle,
    QStyleOptionGraphicsItem,
    QWidget,
)

from fibsem_maestro.gui.form_builder.widgets.area_select._constants import (
    GRAB_FACTOR,
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
from fibsem_maestro.gui.form_builder.widgets.area_select.overlay import AreaDecoration


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

        self._read_only = False
        self._decoration: AreaDecoration | None = None

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
            ellipse.setFlag(
                QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True
            )
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
        if self._decoration is not None:
            self._decoration.update(self)

    def apply_decoration(self, decoration: AreaDecoration | None) -> None:
        """
        Replace this rectangle's decoration.

        Args:
            decoration: The decoration to attach, or None to remove the current one.
        """
        if self._decoration is not None:
            self._decoration.detach()

        self._decoration = decoration
        if decoration is not None:
            decoration.attach(self)

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
            scale = self._view_scale()
            tol = (
                (HANDLE_RADIUS * GRAB_FACTOR) / scale
                if scale
                else HANDLE_RADIUS * GRAB_FACTOR
            )
            if (dx * dx + dy * dy) ** 0.5 <= tol:
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

        styled = QStyleOptionGraphicsItem(option)
        styled.state &= ~QStyle.StateFlag.State_Selected
        super().paint(painter, styled, widget)

    def mousePressEvent(self, event: QGraphicsSceneMouseEvent) -> None:
        """Begin a handle-resize or body-move gesture."""
        if self._read_only:
            event.ignore()
            return

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

        if not self.isSelected() and self.scene() is not None:
            self.scene().clearSelection()

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

    def _view_scale(self) -> float:
        """
        Return the active view's scene-to-viewport scale factor.

        Returns:
            Pixels per scene unit for the first attached view, or 1.0 if none.
        """
        scene = self.scene()
        views = scene.views() if scene is not None else []
        return views[0].transform().m11() if views else 1.0

    def set_handles_visible(self, visible: bool) -> None:
        """
        Show or hide all resize handles.

        Args:
            visible: True to show the handles, False to hide them.
        """
        for ellipse in self._handles.values():
            ellipse.setVisible(visible)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable interactive editing of this rectangle.

        Args:
            read_only: True to block moving and resizing and hide the handles.
        """
        self._read_only = read_only
        self.setFlag(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable, not read_only)
        self.set_handles_visible(not read_only)

    def restore_handles(self) -> None:
        """
        Restore handle visibility to match the current edit state.
        """
        self.set_handles_visible(not self._read_only)

    def boundingRect(self) -> QRectF:
        """
        Return the item's bounds, padded for handles and unioned with any children.

        Returns:
            A rectangle covering the geometry, the handle grab area, and every
            child item, so the scene invalidates the full painted region when this
            item moves or resizes.
        """
        margin = self._grab_margin()
        return (
            self.rect().adjusted(-margin, -margin, margin, margin)
            | self.childrenBoundingRect()
        )

    def shape(self) -> QPainterPath:
        """
        Return the clickable shape, including the handle grab area.

        Returns:
            A path covering the rectangle plus a margin wide enough to contain
            the handles, which are drawn at a fixed screen size and therefore
            extend beyond the rectangle's border.
        """
        path = QPainterPath()
        path.addRect(self.boundingRect())
        return path

    def _grab_margin(self) -> float:
        """
        Return the handle grab radius in local coordinates.

        The handles ignore view transformations, so their screen size is
        constant and the equivalent size in scene units grows as the view is
        zoomed out.

        Returns:
            The grab radius, in the item's local coordinate space.
        """
        scale = self._view_scale()
        return (
            (HANDLE_RADIUS * GRAB_FACTOR) / scale
            if scale
            else HANDLE_RADIUS * GRAB_FACTOR
        )
