# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QPen


def _cosmetic_pen(
    color: QColor, width: float, style: Qt.PenStyle = Qt.PenStyle.SolidLine
) -> QPen:
    """
    Create a pen whose width is in viewport pixels.

    Args:
        color: Line colour.
        width: Line width in viewport pixels.
        style: Line style.

    Returns:
        The cosmetic pen.
    """
    pen = QPen(color, width, style)
    pen.setCosmetic(True)
    return pen
