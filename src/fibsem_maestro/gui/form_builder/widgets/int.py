# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollSpinBox
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

        self._spin = NoScrollSpinBox()
        # use large sentinels for 'no limit'
        self._spin.setMinimum(int(minimum) if minimum is not None else -2_147_483_648)
        self._spin.setMaximum(int(maximum) if maximum is not None else 2_147_483_647)
        self._spin.setValue(int(default))
        self._spin.setFixedWidth(200)
        self._spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        layout.addWidget(self._spin)
        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def get_value(self) -> int:
        return self._spin.value()

    def set_value(self, value: Any) -> None:
        self._spin.setValue(int(value))

    def set_read_only(self, read_only: bool) -> None:
        self._spin.setReadOnly(read_only)
