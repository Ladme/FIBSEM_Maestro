# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from PyQt6.QtGui import QWheelEvent
from PyQt6.QtWidgets import QComboBox, QDoubleSpinBox, QSpinBox


class NoScrollSpinBox(QSpinBox):
    def wheelEvent(self, e: QWheelEvent) -> None:
        e.ignore()


class NoScrollDoubleSpinBox(QDoubleSpinBox):
    def wheelEvent(self, e: QWheelEvent) -> None:
        e.ignore()


class NoScrollComboBox(QComboBox):
    def wheelEvent(self, e: QWheelEvent) -> None:
        e.ignore()
