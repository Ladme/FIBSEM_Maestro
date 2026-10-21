# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Painted indicators of an action list item: the next-to-run arrow and the prepared check mark."""

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget


class CheckWidget(QWidget):
    """
    Draws a checkmark when on.

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._on = False

    @property
    def is_on(self) -> bool:
        """Whether the checkmark is drawn."""
        return self._on

    def set_on(self, on: bool) -> None:
        """
        Show or hide the checkmark.

        Args:
            on: True to draw it.
        """
        if on != self._on:
            self._on = on
            self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        """Paint the checkmark if on."""
        _ = a0
        if not self._on:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#4caf50"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(1, 6, 4, 10)
        painter.drawLine(4, 10, 11, 1)
        painter.end()


class ArrowWidget(QWidget):
    """
    Draws a right-pointing arrow when on.

    Args:
        parent: Parent widget.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._on = False

    @property
    def is_on(self) -> bool:
        """Whether the arrow is drawn."""
        return self._on

    def set_on(self, on: bool) -> None:
        """
        Show or hide the arrow.

        Args:
            on: True to draw it.
        """
        if on != self._on:
            self._on = on
            self.update()

    def paintEvent(self, a0: QPaintEvent | None) -> None:
        """Paint the arrow if on."""
        _ = a0
        if not self._on:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#5a9fd4"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)
        painter.drawLine(1, 6, 10, 6)
        painter.drawLine(6, 2, 10, 6)
        painter.drawLine(6, 10, 10, 6)
        painter.end()
