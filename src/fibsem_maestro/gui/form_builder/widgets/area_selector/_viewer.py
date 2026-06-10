# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import QPainter
from PyQt6.QtWidgets import QGraphicsEllipseItem, QGraphicsScene, QGraphicsView

from fibsem_maestro.gui.form_builder.widgets.area_selector._constants import MIN_RECT_PX
from fibsem_maestro.gui.form_builder.widgets.area_selector._rectangle import (
    ResizableRect,
)


class _AreaViewer(QGraphicsView):
    """
    Interactive image viewer: zoom (scroll), pan (right-click drag),
    draw new rects (left-click drag on empty area), delete selected (Del).

    Args:
        scene: The QGraphicsScene to use.
        status_callback: Called with a status string on interactions.
        max_areas: Maximum number of SelectionRect items. None = unlimited.
    """

    def __init__(
        self,
        scene: QGraphicsScene,
        status_callback,
        max_areas: int | None = None,
    ) -> None:
        super().__init__(scene)
        self._status_cb = status_callback
        self._max_areas = max_areas
        self._zoom: float = 1.0
        self._panning = False
        self._pan_start = QPointF()
        self._drawing = False
        self._draw_origin = QPointF()
        self._current_rect: ResizableRect | None = None
        self._image_loaded = False

        self._status_timer = QTimer(self)
        self._status_timer.setSingleShot(True)
        self._status_timer.timeout.connect(self._clear_status_message)
        self._status_message: str | None = None

        self.setRenderHints(
            QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)

    def _status(self, text: str) -> None:
        self._status_cb(text)

    def _status_message_timed(self, text: str, ms: int = 3000) -> None:
        """Show a message that will not be overwritten by mouse moves for `ms` milliseconds."""
        self._status_message = text
        self._status(text)
        self._status_timer.start(ms)

    def _clear_status_message(self) -> None:
        self._status_message = None

    def _rect_count(self) -> int:
        return sum(1 for i in self.scene().items() if isinstance(i, ResizableRect))

    def wheelEvent(self, event) -> None:
        factor = 1.25 if event.angleDelta().y() > 0 else 1 / 1.25
        self._zoom *= factor
        self.scale(factor, factor)
        if self._status_message is None:
            self._status(f"Zoom: {self._zoom:.1%}")

    def reset_zoom(self) -> None:
        self.resetTransform()
        self._zoom = 1.0
        self.fitInView(self.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mousePressEvent(self, event) -> None:
        if self._read_only:
            return

        if event.button() == Qt.MouseButton.RightButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return

        # if clicking on an existing rect or its handles, let the item handle it
        item = self.itemAt(event.pos())
        if isinstance(item, (ResizableRect, QGraphicsEllipseItem)):
            super().mousePressEvent(event)
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if not self._image_loaded:
                self._status_message_timed("Load an image first.")
                return

            if self._max_areas is not None and self._rect_count() >= self._max_areas:
                self._status_message_timed(
                    f"Maximum of {self._max_areas} area(s) reached."
                )
                return

            for it in self.scene().selectedItems():
                it.setSelected(False)

            self._drawing = True
            self._draw_origin = self.mapToScene(event.pos())
            self._current_rect = ResizableRect(
                QRectF(self._draw_origin, self._draw_origin)
            )
            self.scene().addItem(self._current_rect)
            event.accept()
            return

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return

        if self._drawing and self._current_rect is not None:
            pos = self.mapToScene(event.pos())
            rect = QRectF(self._draw_origin, pos).normalized()
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

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton and self._panning:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return

        if event.button() == Qt.MouseButton.LeftButton and self._drawing:
            self._drawing = False
            if self._current_rect is not None:
                r = self._current_rect.rect()
                if r.width() < MIN_RECT_PX and r.height() < MIN_RECT_PX:
                    self.scene().removeItem(self._current_rect)
                else:
                    self._status_message_timed(
                        f"Area created: x={r.x():.0f} y={r.y():.0f} "
                        f"w={r.width():.0f} h={r.height():.0f}",
                    )
            self._current_rect = None
            event.accept()
            return

        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Delete:
            for item in self.scene().selectedItems():
                if isinstance(item, ResizableRect):
                    self.scene().removeItem(item)
            event.accept()
            return
        super().keyPressEvent(event)

    def set_image_loaded(self) -> None:
        self._image_loaded = True

    def set_read_only(self, read_only: bool) -> None:
        self._read_only = read_only
