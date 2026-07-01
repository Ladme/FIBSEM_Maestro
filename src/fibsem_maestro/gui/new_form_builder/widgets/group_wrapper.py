# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TypeVar

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import QGroupBox, QLabel, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.new_form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.new_form_builder.widgets.union import DiscriminatedUnionWidget

T = TypeVar("T")


class ClickableLabel(QLabel):
    """A QLabel that exposes a clicked signal."""

    clicked = pyqtSignal()

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        self.clicked.emit()
        super().mousePressEvent(ev)


class GroupWrapper(QGroupBox, BaseWidget[T]):
    """Plain (non-checkable) QGroupBox wrapping an ObjectWidget for required nested objects."""

    def __init__(
        self,
        inner: ObjectWidget[T] | DiscriminatedUnionWidget,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self._inner = inner
        self._collapsed = False

        # small toggle button in the title bar area
        self._toggle = ClickableLabel("⯆", self)
        self._toggle.setFixedSize(20, 20)
        self._toggle.setStyleSheet(
            "color: #8a8a8a; font-size: 12px; border: none; background: transparent;"
        )
        self._toggle.setCursor(Qt.CursorShape.PointingHandCursor)
        self._toggle.clicked.connect(self._on_click)

        layout = QVBoxLayout(self)
        layout.addWidget(inner)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def resizeEvent(self, a0: QResizeEvent) -> None:
        """Keep the toggle button pinned to the top-left of the group box."""
        self._toggle.move(-2, 5)
        super().resizeEvent(a0)

    def _on_click(self) -> None:
        self._collapsed = not self._collapsed
        self._toggle.setText("⯈" if self._collapsed else "⯆")
        self._inner.setVisible(not self._collapsed)

    def get_value(self) -> T:
        return self._inner.get_value()

    def set_value(self, value: T) -> None:
        self._inner.set_value(value)

    def set_read_only(self, read_only: bool) -> None:
        self._inner.set_read_only(read_only)
