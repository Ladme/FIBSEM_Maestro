# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollSpinBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class IntWidget(QWidget, BaseWidget[int]):
    """
    A spin-box widget for editing an integer value.

    Args:
        default: The initial value.
        minimum: The lowest value allowed; defaults to -2_147_483_648 if None.
        maximum: The highest value allowed; defaults to 2_147_483_647 if None.
        suffix: A unit label to display after the spin box, if any.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        default: int = 0,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._spin = NoScrollSpinBox()
        # use large sentinels for 'no limit'
        self._spin.setMinimum(int(minimum) if minimum is not None else -2_147_483_648)
        self._spin.setMaximum(int(maximum) if maximum is not None else 2_147_483_647)
        self._spin.setFixedWidth(200)
        self._spin.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._spin.setValue(int(default))
        self._spin.valueChanged.connect(lambda _: self._emit())
        layout.addWidget(self._spin)
        if suffix:
            layout.addWidget(QLabel(suffix))
        layout.addStretch()

    def get_value(self) -> int:
        """
        Return the current value.

        Returns:
            The value held by the spin box.
        """

        return self._spin.value()

    def set_value(self, value: int) -> None:
        """
        Set the spin box's value.

        Args:
            value: The new value.
        """

        self._spin.setValue(int(value))

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of the value.

        Args:
            read_only: If True, make the spin box read-only.
        """
        self._spin.setReadOnly(read_only)
