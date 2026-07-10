# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TypeVar

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent, QResizeEvent
from PyQt6.QtWidgets import QGroupBox, QLabel, QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.form_builder.widgets.union import DiscriminatedUnionWidget

T = TypeVar("T")


class ClickableLabel(QLabel):
    """
    A QLabel that exposes a clicked signal.

    Emits ``clicked`` on each mouse press.
    """

    clicked = pyqtSignal()

    def mousePressEvent(self, ev: QMouseEvent) -> None:
        """
        Emit `clicked` and forward the event to the base class.

        Args:
            ev: The mouse press event.
        """

        self.clicked.emit()
        super().mousePressEvent(ev)


class GroupWrapper(QGroupBox, BaseWidget[T]):
    """
    Plain (non-checkable) QGroupBox wrapping an ObjectWidget for required nested objects.

    Args:
        inner: The nested object or discriminated-union widget to wrap.
        parent: The parent widget, if any.
    """

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
        """Toggle the collapsed state, updating the arrow and inner visibility."""

        self._collapsed = not self._collapsed
        self._toggle.setText("⯈" if self._collapsed else "⯆")
        self._inner.setVisible(not self._collapsed)

    def get_value(self) -> T:
        """
        Return the inner widget's value.

        Returns:
            The value held by the wrapped widget.
        """

        return self._inner.get_value()

    def set_value(self, value: T) -> None:
        """
        Set the inner widget's value.

        Args:
            value: The value to pass to the wrapped widget.
        """

        self._inner.set_value(value)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of the inner widget.

        Args:
            read_only: If True, make the wrapped widget read-only.
        """
        self._inner.set_read_only(read_only)
