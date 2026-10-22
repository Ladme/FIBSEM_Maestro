# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Small layout helpers shared by the views."""

from PyQt6.QtWidgets import QWidget

SEPARATOR_COLOR = "#444444"
"""Colour of the thin separator lines."""


def horizontal_separator() -> QWidget:
    """
    A 1 px high separator line spanning its layout's width.

    Returns:
        The line widget.
    """
    line = QWidget()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {SEPARATOR_COLOR};")
    return line


def vertical_separator(height: int = 20) -> QWidget:
    """
    A 1 px wide separator line of a fixed height.

    Args:
        height: Height of the line, in px.

    Returns:
        The line widget.
    """
    line = QWidget()
    line.setFixedWidth(1)
    line.setFixedHeight(height)
    line.setStyleSheet(f"background: {SEPARATOR_COLOR};")
    return line
