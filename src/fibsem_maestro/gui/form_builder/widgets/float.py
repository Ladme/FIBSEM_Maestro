# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QDoubleSpinBox, QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class FloatWidget(QWidget, WidgetWrapper):
    """Floating-point spinner for JSON 'float' fields."""

    def __init__(
        self,
        default: float = 0.0,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spin = QDoubleSpinBox()
        self._spin.setDecimals(6)
        self._spin.setMinimum(minimum if minimum is not None else -1e12)
        self._spin.setMaximum(maximum if maximum is not None else 1e12)
        self._spin.setSingleStep(1.0)
        self._spin.setValue(float(default))
        layout.addWidget(self._spin)

        if suffix:
            layout.addWidget(QLabel(suffix))

    def get_value(self) -> float:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(float(value))
