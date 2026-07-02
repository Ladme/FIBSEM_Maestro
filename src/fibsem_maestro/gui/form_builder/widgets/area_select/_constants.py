# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor, QPen

HANDLE_RADIUS = 5
HANDLE_COLOR = QColor(255, 255, 255)
HANDLE_BORDER = QColor(0, 100, 220)
RECT_FILL = QBrush(QColor(0, 120, 255, 60))
RECT_PEN_NORMAL = QPen(QColor(0, 120, 255), 2, Qt.PenStyle.SolidLine)
RECT_PEN_SELECTED = QPen(QColor(255, 60, 60), 2, Qt.PenStyle.DashLine)
MIN_RECT_PX = 8
# minimum drag, in *viewport* pixels, before a rect is created
MIN_DRAW_PX = 8
