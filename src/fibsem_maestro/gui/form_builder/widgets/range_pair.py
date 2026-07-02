# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollDoubleSpinBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class RangePairWidget(QWidget, BaseWidget[tuple[float, float]]):
    """Two float spinners enforcing low <= high at all times."""

    def __init__(
        self,
        default: tuple[float, float] | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        low, high = default if default is not None else (0.0, 0.0)

        self._low = NoScrollDoubleSpinBox()
        self._low.setDecimals(6)
        self._low.setFixedWidth(200)
        self._low.setMinimum(minimum if minimum is not None else -1e12)
        self._low.setMaximum(high)
        self._low.setValue(low)

        self._high = NoScrollDoubleSpinBox()
        self._high.setDecimals(6)
        self._high.setFixedWidth(200)
        self._high.setMinimum(low)
        self._high.setMaximum(maximum if maximum is not None else 1e12)
        self._high.setValue(high)

        self._low.valueChanged.connect(self._on_low_changed)
        self._high.valueChanged.connect(self._on_high_changed)

        layout.addWidget(self._low)
        layout.addWidget(QLabel("–"))
        layout.addWidget(self._high)

        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def _on_low_changed(self, value: float) -> None:
        self._high.setMinimum(value)
        self._emit()

    def _on_high_changed(self, value: float) -> None:
        self._low.setMaximum(value)
        self._emit()

    def get_value(self) -> tuple[float, float]:
        return (self._low.value(), self._high.value())

    def set_value(self, value: tuple[float, float]) -> None:
        low, high = value
        # apply both values atomically so the interlocking min/max handlers
        # don't fire and rewrite each other mid-update
        with QSignalBlocker(self._low), QSignalBlocker(self._high):
            self._low.setMaximum(high)
            self._high.setMinimum(low)
            self._low.setValue(low)
            self._high.setValue(high)
        self._emit()

    def set_read_only(self, read_only: bool) -> None:
        for spinbox in (self._low, self._high):
            spinbox.setReadOnly(read_only)
