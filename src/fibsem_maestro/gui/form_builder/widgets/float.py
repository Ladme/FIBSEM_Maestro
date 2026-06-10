# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollDoubleSpinBox
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

        self._spin = NoScrollDoubleSpinBox()
        self._spin.setDecimals(6)
        self._spin.setMinimum(minimum if minimum is not None else -1e12)
        self._spin.setMaximum(maximum if maximum is not None else 1e12)
        self._spin.setSingleStep(1.0)
        self._spin.setValue(float(default))
        self._spin.setFixedWidth(200)
        layout.addWidget(self._spin)
        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def get_value(self) -> float:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(float(value))

    def set_read_only(self, read_only: bool) -> None:
        self._spin.setReadOnly(read_only)
