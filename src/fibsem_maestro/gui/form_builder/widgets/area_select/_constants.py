# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen

HANDLE_RADIUS = 5
HANDLE_COLOR = QColor(255, 255, 255)
HANDLE_BORDER = QColor(0, 100, 220)
RECT_FILL = QBrush(QColor(0, 120, 255, 60))
RECT_PEN_NORMAL = QPen(QColor(0, 120, 255), 2, Qt.PenStyle.SolidLine)
RECT_PEN_SELECTED = QPen(QColor(255, 60, 60), 2, Qt.PenStyle.SolidLine)
MIN_RECT_PX = 8
# minimum drag, in *viewport* pixels, before a rect is created
MIN_DRAW_PX = 8
GRAB_FACTOR = 2

MARGIN_FILL = QBrush(QColor(145, 145, 145, 60))
MARGIN_PEN = QPen(QColor(30, 30, 35, 200), 1, Qt.PenStyle.DashLine)
ARROW_COLOR = QColor(0, 30, 190, 120)
ARROW_PEN = QPen(QColor(0, 30, 190, 120), 0)
