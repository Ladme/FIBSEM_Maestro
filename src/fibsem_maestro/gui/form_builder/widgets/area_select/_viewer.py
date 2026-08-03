# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QMouseEvent, QPainter, QWheelEvent
from PyQt6.QtWidgets import (
    QGraphicsItem,
    QGraphicsScene,
    QGraphicsView,
)

from fibsem_maestro.gui.form_builder.widgets.area_select._constants import (
    MIN_DRAW_PX,
)
from fibsem_maestro.gui.form_builder.widgets.area_select._rectangle import (
    ResizableRect,
)


class AreaViewer(QGraphicsView):
    """
    Interactive image viewer for drawing rectangular acquisition areas.

    Interactions: scroll to zoom, right-drag to pan, left-drag on empty canvas
    to draw a new area, Delete to remove selected areas. A completed draw or
    delete invokes `on_edit_finished` once; drawing new rects also wires that
    callback into them so their later moves and resizes notify too.

    Args:
        scene: The graphics scene to display.
        status_callback: Called with a status string on interactions.
        max_areas: Maximum number of areas, or None for unlimited.
        on_edit_finished: Called once whenever a user gesture commits a change.
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        status_callback: Callable[[str], None],
        max_areas: int | None = None,
        on_edit_finished: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(scene)
        self._status_cb = status_callback
        self._max_areas = max_areas
        self._on_edit_finished = on_edit_finished
        self._zoom: float = 1.0
        self._panning = False
        self._pan_start = QPointF()
        self._drawing = False
        self._draw_origin = QPointF()
        self._current_rect: ResizableRect | None = None
        self._image_loaded = False
        self._read_only = False

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status_message)
        self._status_message: str | None = None

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def _notify_edit_finished(self) -> None:
        """Invoke the edit-finished callback, if one was provided."""
        if self._on_edit_finished is not None:
            self._on_edit_finished()

    def _status(self, text: str) -> None:
        self._status_cb(text)

    def _status_message_timed(self, text: str, ms: int = 3000) -> None:
        """Show a status message protected from mouse-move overwrites.

        Args:
            text: The message to display.
            ms: How long, in milliseconds, to keep it pinned.
        """
        self._status_message = text
        self._status(text)
        self._status_timer.start(ms)

    def _clear_status_message(self) -> None:
        self._status_message = None

    def _rect_count(self) -> int:
        """Return the number of area rectangles currently in the scene."""
        return sum(1 for i in self.scene().items() if isinstance(i, ResizableRect))

    def wheelEvent(self, event: QWheelEvent) -> None:
        """Zoom the view around the cursor."""
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self._zoom *= factor
        self.scale(factor, factor)
        if self._status_message is None:
            self._status(f"Zoom: {self._zoom:.1%}")

    def reset_zoom(self) -> None:
        """Reset zoom to fit the whole scene in the view."""
        self.resetTransform()
        self._zoom = 1.0
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        """Start panning, forward to an item, or begin drawing a new rect."""
        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # clicking a rect, a handle, or one of its decoration items:
        # forward so the item can select; it refuses edits when read-only
        if _owning_rect(self.itemAt(event.pos())) is not None:
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            self.scene().clearSelection()
            if self._read_only:
                return

            if not self._image_loaded:
                self._status_message_timed("Load an image first.")
                return

            self._drawing = True
            self._draw_origin = self.mapToScene(event.pos())
            # the rectangle is created lazily in mouseMoveEvent, once the drag clears MIN_DRAW_PX
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        """Pan, grow the rect being drawn, or update the coordinate readout."""
        if self._panning:
            delta = event.position() - self._pan_start  # type: ignore
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return

        if self._drawing:
            pos = self.mapToScene(event.pos())
            rect = QRectF(self._draw_origin, pos).normalized()
            scale = self.transform().m11()  # scene units -> viewport px

            if self._current_rect is None:
                if (
                    rect.width() * scale >= MIN_DRAW_PX
                    or rect.height() * scale >= MIN_DRAW_PX
                ):
                    # make sure we haven't exceeded the max number of areas
                    if (
                        self._max_areas is not None
                        and self._rect_count() >= self._max_areas
                    ):
                        self._status_message_timed(
                            f"Maximum of {self._max_areas} area(s) reached."
                        )
                        return

                    self._current_rect = ResizableRect(
                        rect, on_edit_finished=self._on_edit_finished
                    )
                    self.scene().addItem(self._current_rect)
            else:
                self._current_rect.set_rect(rect)

            if self._status_message is None:
                self._status(f"Drawing: {rect.width():.0f} × {rect.height():.0f} px")

            event.accept()
            return

        if self._status_message is None:
            scene_pos = self.mapToScene(event.pos())
            self._status(
                f"({scene_pos.x():.0f}, {scene_pos.y():.0f})  Zoom: {self._zoom:.1%}"
            )
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        """Finish panning or committing a freshly drawn rectangle."""
        if event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            committed = self._current_rect is not None
            if committed:
                r = self._current_rect.rect()
                self._status_message_timed(
                    f"Area created: x={r.x():.0f} y={r.y():.0f} "
                    f"w={r.width():.0f} h={r.height():.0f}"
                )
            self._current_rect = None
            event.accept()
            if committed:
                self._notify_edit_finished()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        """Delete selected areas, notifying once if anything was removed."""
        if event.key() == Qt.Key.Key_Delete:
            removed = False
            for item in self.scene().selectedItems():
                if isinstance(item, ResizableRect):
                    self.scene().removeItem(item)
                    removed = True
            event.accept()
            if removed:
                self._notify_edit_finished()
            return
        super().keyPressEvent(event)

    def set_image_loaded(self) -> None:
        """Mark that an image is present, enabling area drawing."""
        self._image_loaded = True

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable all editing interactions.

        Args:
            read_only: True to block drawing, moving, resizing, and deleting.
        """
        self._read_only = read_only


def _owning_rect(item: QGraphicsItem | None) -> ResizableRect | None:
    """Return the ResizableRect owning `item` (itself or an ancestor), or None."""
    while item is not None:
        if isinstance(item, ResizableRect):
            return item
        item = item.parentItem()

    return None
