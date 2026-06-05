# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QSpinBox, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class IntWidget(QWidget, WidgetWrapper):
    def __init__(
        self,
        default: int = 0,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spin = QSpinBox()
        # use large sentinels for 'no limit'
        self._spin.setMinimum(int(minimum) if minimum is not None else -2_147_483_648)
        self._spin.setMaximum(int(maximum) if maximum is not None else 2_147_483_647)
        self._spin.setValue(int(default))
        layout.addWidget(self._spin)

        if suffix:
            layout.addWidget(QLabel(suffix))

    def get_value(self) -> int:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(int(value))
