# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QHBoxLayout, QWidget

from fibsem_maestro.gui.new_form_builder.widgets._no_scroll import NoScrollDoubleSpinBox
from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget


class FloatTupleWidget(QWidget, BaseWidget[tuple[float, ...]]):
    """
    A vertical stack of float spinboxes for editing a tuple of floats.

    Args:
        length: Number of elements in the tuple.
        default: Default values for each element, or None for all zeros.
        minimum: Minimum value for all spinboxes.
        maximum: Maximum value for all spinboxes.
        parent: Parent widget.
    """

    def __init__(
        self,
        length: int,
        default: tuple[float, ...] | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        defaults = default if default is not None else (0,) * length
        self._spinboxes: list[NoScrollDoubleSpinBox] = []

        for value in defaults:
            spinbox = NoScrollDoubleSpinBox()
            spinbox.setMinimum(minimum if minimum is not None else -1e12)
            spinbox.setMaximum(maximum if maximum is not None else 1e12)
            spinbox.setValue(value)
            spinbox.valueChanged.connect(lambda _: self._emit())
            layout.addWidget(spinbox)
            self._spinboxes.append(spinbox)

    def get_value(self) -> tuple[float, ...]:
        return tuple(s.value() for s in self._spinboxes)

    def set_value(self, value: tuple[float, ...]) -> None:
        for spinbox, v in zip(self._spinboxes, value):
            spinbox.setValue(v)

    def set_read_only(self, read_only: bool) -> None:
        for spinbox in self._spinboxes:
            spinbox.setReadOnly(read_only)
