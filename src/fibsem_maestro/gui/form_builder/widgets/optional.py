# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import TypeVar, cast

from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class OptionalWidget(QWidget, BaseWidget[T | None]):
    """
    Checkbox that gates an inner widget: unchecked -> value is None.
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
        self._inner.setVisible(self._checkbox.isChecked())
        self._emit()

    def get_value(self) -> T | None:
        if not self._checkbox.isChecked():
            return None
        return cast("BaseWidget[T]", self._inner).get_value()

    def set_value(self, value: T | None) -> None:
        if value is None:
            self._checkbox.setChecked(False)
            self._inner.setVisible(False)
        else:
            self._checkbox.setChecked(True)
            self._inner.setVisible(True)
            cast("BaseWidget[T]", self._inner).set_value(value)

    def set_read_only(self, read_only: bool) -> None:
        self._checkbox.setEnabled(not read_only)
        cast("BaseWidget[T]", self._inner).set_read_only(read_only)
