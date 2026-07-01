# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPainter, QPaintEvent, QPen
from PyQt6.QtWidgets import QWidget


class IndicatorMode(Enum):
    NONE = "none"
    CHECK = "check"
    ARROW = "arrow"


class IndicatorWidget(QWidget):
    """Draws a checkmark, arrow, or nothing depending on state."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._mode = IndicatorMode.NONE

    def set_mode(self, mode: IndicatorMode) -> None:
        self._mode = mode
        self.update()

    def paintEvent(self, a0: QPaintEvent) -> None:
        _ = a0
        if self._mode == IndicatorMode.NONE:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        pen = QPen(QColor("#4caf50"))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
        painter.setPen(pen)

        if self._mode == IndicatorMode.CHECK:
            painter.drawLine(1, 6, 4, 10)
            painter.drawLine(4, 10, 11, 1)
        elif self._mode == IndicatorMode.ARROW:
            painter.drawLine(1, 6, 10, 6)
            painter.drawLine(6, 2, 10, 6)
            painter.drawLine(6, 10, 10, 6)

        painter.end()
