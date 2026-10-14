# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoScrollSpinBox(QSpinBox):
    """A QSpinBox that ignores mouse wheel events."""

    def wheelEvent(self, e: QWheelEvent) -> None:
        """Ignore the wheel event so it propagates to the parent widget."""
        e.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    """A QDoubleSpinBox that ignores mouse wheel events."""

    def wheelEvent(self, e: QWheelEvent) -> None:
        """Ignore the wheel event so it propagates to the parent widget."""
        e.ignore()

    def textFromValue(self, v: float) -> str:
        """
        Format a value in the widget's locale, without trailing zeros beyond the first decimal.

        Args:
            v: The value to display.

        Returns:
            The value with at least one and at most `decimals()` decimals
            (none if `decimals()` is 0).
        """
        locale = self.locale()
        text = locale.toString(v, "f", self.decimals())
        if not self.isGroupSeparatorShown():
            text = text.replace(locale.groupSeparator(), "")

        point = locale.decimalPoint()
        if point in text:
            text = text.rstrip("0")
            if text.endswith(point):
                text += "0"

        # a negative value that rounds to zero would otherwise keep its sign
        value, ok = locale.toDouble(text)
        if ok and value == 0.0:
            text = text.lstrip("-")
        return text


class NoScrollComboBox(QComboBox):
    """A QComboBox that ignores mouse wheel events."""

    def wheelEvent(self, e: QWheelEvent) -> None:
        """Ignore the wheel event so it propagates to the parent widget."""
        e.ignore()
