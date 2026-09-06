# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollDoubleSpinBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class RangePairWidget(QWidget, BaseWidget[tuple[float, float]]):
    """
    Two float spinners enforcing low <= high at all times.

    Each spin box constrains the other's bound so the low value can never
    exceed the high value. Supports optional outer bounds and a unit suffix.

    Args:
        default: The initial (low, high) pair; defaults to (0.0, 0.0).
        minimum: The lowest value the low spinner allows; defaults to -1e12.
        maximum: The highest value the high spinner allows; defaults to 1e12.
        suffix: A unit label to display after the spinners, if any.
        parent: The parent widget, if any.
    """

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
        """
        Raise the high spinner's minimum to the new low value, then notify.

        Args:
            value: The new low value.
        """

        self._high.setMinimum(value)
        self._emit()

    def _on_high_changed(self, value: float) -> None:
        """
        Lower the low spinner's maximum to the new high value, then notify.

        Args:
            value: The new high value.
        """

        self._low.setMaximum(value)
        self._emit()

    def get_value(self) -> tuple[float, float]:
        """
        Return the current values as a tuple.

        Returns:
            The (low, high) values.
        """

        return (self._low.value(), self._high.value())

    def set_value(self, value: tuple[float, float]) -> None:
        """
        Set both bounds atomically.

        Args:
            value: The (low, high) values to apply.
        """

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
        """
        Enable or disable editing of both spinners.

        Args:
            read_only: If True, make both spinners read-only.
        """
        for spinbox in (self._low, self._high):
            spinbox.setReadOnly(read_only)
