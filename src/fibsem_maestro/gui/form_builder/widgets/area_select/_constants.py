# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QBrush, QColor

from fibsem_maestro.gui.form_builder.widgets.area_select._cosmetic_pen import (
    _cosmetic_pen,
)

HANDLE_RADIUS = 5
HANDLE_COLOR = QColor(255, 255, 255)
HANDLE_BORDER = QColor(0, 100, 220)
RECT_FILL = QBrush(QColor(0, 120, 255, 60))
RECT_PEN_NORMAL = _cosmetic_pen(QColor(0, 120, 255), 2)
RECT_PEN_SELECTED = _cosmetic_pen(QColor(255, 60, 60), 2)
MIN_RECT_PX = 8
# minimum drag, in *viewport* pixels, before a rect is created
MIN_DRAW_PX = 8
GRAB_FACTOR = 2

MARGIN_COLOR = QColor(140, 200, 255)
MARGIN_PEN = _cosmetic_pen(MARGIN_COLOR, 5, Qt.PenStyle.DotLine)

ARROW_COLOR = QColor(0, 30, 190, 120)
ARROW_PEN = _cosmetic_pen(ARROW_COLOR, 1)

MAX_TILES = 4096
TILE_COLOR = QColor(255, 0, 0)
TILE_PEN = _cosmetic_pen(TILE_COLOR, 3)

LINE_COLOR = QColor(140, 200, 255)
LINE_PEN = _cosmetic_pen(LINE_COLOR, 3, Qt.PenStyle.DotLine)
MAX_LINES = 1000
