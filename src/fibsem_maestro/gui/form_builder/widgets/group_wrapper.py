# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import TypeVar, cast

from PyQt6.QtWidgets import QSizePolicy, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.collapsible_box import CollapsibleGroupBox

T = TypeVar("T")


class GroupWrapper(CollapsibleGroupBox, BaseWidget[T]):
    """
    Plain (non-checkable) QGroupBox wrapping an ObjectWidget for required nested objects.

    Args:
        inner: The nested object or discriminated-union widget to wrap.
        parent: The parent widget, if any.
    """

    def __init__(self, inner, parent=None):
        super().__init__("", parent)
        BaseWidget.__init__(self)
        self._inner = inner

        layout = QVBoxLayout(self)
        layout.addWidget(inner)
        layout.addStretch()
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)

    def _collapse_body(self) -> QWidget:
        return cast("QWidget", self._inner)

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
