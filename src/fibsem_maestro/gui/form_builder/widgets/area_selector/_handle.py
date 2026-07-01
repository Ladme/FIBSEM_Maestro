# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum

from PyQt6.QtCore import QPointF, QRectF, Qt

from fibsem_maestro.gui.form_builder.widgets.area_selector._constants import MIN_RECT_PX


class Handle(Enum):
    TOP_LEFT = "top_left"
    TOP = "top"
    TOP_RIGHT = "top_right"
    RIGHT = "right"
    BOTTOM_RIGHT = "bottom_right"
    BOTTOM = "bottom"
    BOTTOM_LEFT = "bottom_left"
    LEFT = "left"

    def position(self, rect: QRectF) -> QPointF:
        """Return the scene position of a handle of a given rectangle."""
        cx = rect.center().x()
        cy = rect.center().y()
        match self:
            case Handle.TOP_LEFT:
                return rect.topLeft()
            case Handle.TOP:
                return QPointF(cx, rect.top())
            case Handle.TOP_RIGHT:
                return rect.topRight()
            case Handle.RIGHT:
                return QPointF(rect.right(), cy)
            case Handle.BOTTOM_RIGHT:
                return rect.bottomRight()
            case Handle.BOTTOM:
                return QPointF(cx, rect.bottom())
            case Handle.BOTTOM_LEFT:
                return rect.bottomLeft()
            case Handle.LEFT:
                return QPointF(rect.left(), cy)


HANDLE_CURSORS: dict[Handle, Qt.CursorShape] = {
    Handle.TOP_LEFT: Qt.CursorShape.SizeFDiagCursor,
    Handle.TOP_RIGHT: Qt.CursorShape.SizeBDiagCursor,
    Handle.BOTTOM_LEFT: Qt.CursorShape.SizeBDiagCursor,
    Handle.BOTTOM_RIGHT: Qt.CursorShape.SizeFDiagCursor,
    Handle.TOP: Qt.CursorShape.SizeVerCursor,
    Handle.BOTTOM: Qt.CursorShape.SizeVerCursor,
    Handle.LEFT: Qt.CursorShape.SizeHorCursor,
    Handle.RIGHT: Qt.CursorShape.SizeHorCursor,
}


def apply_handle_drag(rect: QRectF, handle: Handle, delta: QPointF) -> QRectF:
    """Return a new QRectF after moving `handle` by `delta`."""
    left, top, right, bottom = rect.left(), rect.top(), rect.right(), rect.bottom()
    dx, dy = delta.x(), delta.y()

    match handle:
        case Handle.TOP_LEFT:
            left += dx
            top += dy
        case Handle.TOP:
            top += dy
        case Handle.TOP_RIGHT:
            right += dx
            top += dy
        case Handle.RIGHT:
            right += dx
        case Handle.BOTTOM_RIGHT:
            right += dx
            bottom += dy
        case Handle.BOTTOM:
            bottom += dy
        case Handle.BOTTOM_LEFT:
            left += dx
            bottom += dy
        case Handle.LEFT:
            left += dx

    # enforce minimum size
    if right - left < MIN_RECT_PX:
        if handle in (Handle.LEFT, Handle.TOP_LEFT, Handle.BOTTOM_LEFT):
            left = right - MIN_RECT_PX
        else:
            right = left + MIN_RECT_PX
    if bottom - top < MIN_RECT_PX:
        if handle in (Handle.TOP, Handle.TOP_LEFT, Handle.TOP_RIGHT):
            top = bottom - MIN_RECT_PX
        else:
            bottom = top + MIN_RECT_PX

    return QRectF(QPointF(left, top), QPointF(right, bottom))
