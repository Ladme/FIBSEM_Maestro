# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TypeVar, cast

from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class OptionalWidget(QWidget, BaseWidget[T | None]):
    """
    Checkbox that gates an inner widget: unchecked -> value is None.

    Args:
        inner: The widget edited when the checkbox is checked.
        inline: If True, lay the checkbox and inner widget out horizontally instead of vertically.
        enabled_by_default: If True, start checked with the inner widget shown.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        inner: BaseWidget[T],
        inline: bool = False,
        enabled_by_default: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)

        self._inner = cast("QWidget", inner)

        layout = QHBoxLayout(self) if inline else QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._checkbox = QCheckBox()
        layout.addWidget(self._checkbox)
        layout.addWidget(self._inner)
        layout.addStretch()

        self._checkbox.stateChanged.connect(self._on_toggled)
        self._checkbox.setChecked(enabled_by_default)
        self._inner.setVisible(enabled_by_default)

    def _on_toggled(self, _: int = 0) -> None:
        """Show or hide the inner widget to match the checkbox, then notify."""
        self._inner.setVisible(self._checkbox.isChecked())
        self._emit()

    def get_value(self) -> T | None:
        """
        Return the inner value, or None when unchecked.

        Returns:
            The inner widget's value if the checkbox is checked, else None.
        """

        if not self._checkbox.isChecked():
            return None
        return cast("BaseWidget[T]", self._inner).get_value()

    def set_value(self, value: T | None) -> None:
        """
        Set the value, checking the box only for a non-None value.

        A None value unchecks the box and hides the inner widget; otherwise
        the box is checked, the inner widget is shown, and the value is
        applied to it.

        Args:
            value: The value to apply, or None to disable the field.
        """

        if value is None:
            self._checkbox.setChecked(False)
            self._inner.setVisible(False)
        else:
            self._checkbox.setChecked(True)
            self._inner.setVisible(True)
            cast("BaseWidget[T]", self._inner).set_value(value)

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable the checkbox and the inner widget.

        Args:
            read_only: If True, prevent toggling and edits.
        """
        self._checkbox.setEnabled(not read_only)
        cast("BaseWidget[T]", self._inner).set_read_only(read_only)

    def highlight_target(self) -> QWidget:
        """Highlight the gated inner editor, not the checkbox row."""
        return self._inner
