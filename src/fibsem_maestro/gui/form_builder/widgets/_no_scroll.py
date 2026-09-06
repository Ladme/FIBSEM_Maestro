# Released under MIT License.
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


class NoScrollComboBox(QComboBox):
    """A QComboBox that ignores mouse wheel events."""

    def wheelEvent(self, e: QWheelEvent) -> None:
        """Ignore the wheel event so it propagates to the parent widget."""
        e.ignore()
