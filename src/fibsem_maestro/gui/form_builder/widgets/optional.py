# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any, cast

from PyQt6.QtWidgets import QCheckBox, QHBoxLayout, QVBoxLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class OptionalWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        inner: WidgetWrapper,
        inline: bool = False,
        enabled_by_default: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self._inner = cast("QWidget", inner)

        if inline:
            layout = QHBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self._checkbox = QCheckBox()
            layout.addWidget(self._checkbox)
            layout.addWidget(self._inner)
            layout.addStretch()
            self._checkbox.stateChanged.connect(
                lambda: self._inner.setVisible(self._checkbox.isChecked())
            )
            self._inner.setVisible(enabled_by_default)
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            self._checkbox = QCheckBox()
            layout.addWidget(self._checkbox)
            layout.addWidget(self._inner)
            layout.addStretch()
            self._checkbox.stateChanged.connect(
                lambda: self._inner.setVisible(self._checkbox.isChecked())
            )
            self._inner.setVisible(enabled_by_default)

        self._checkbox.setChecked(enabled_by_default)

    def get_value(self) -> Any:
        if not self._checkbox.isChecked():
            return None
        return cast("WidgetWrapper", self._inner).get_value()

    def set_value(self, value: Any) -> None:
        if value is None:
            self._checkbox.setChecked(False)
            self._inner.setVisible(False)
        else:
            self._checkbox.setChecked(True)
            self._inner.setVisible(True)
            inner = cast("WidgetWrapper", self._inner)
            inner.set_value(value)

    def set_read_only(self, read_only: bool) -> None:
        self._checkbox.setEnabled(not read_only)
        cast("WidgetWrapper", self._inner).set_read_only(read_only)
