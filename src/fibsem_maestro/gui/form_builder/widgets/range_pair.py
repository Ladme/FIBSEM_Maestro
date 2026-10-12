# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from PyQt6.QtCore import QSignalBlocker
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollDoubleSpinBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


class RangePairWidget(QWidget, BaseWidget[tuple[float, float]]):
    """
    Two float spinners keeping low <= high at all times.

    Raising the low value above the high one carries the high value along with
    it, so a range can be edited low value first. The high value cannot be
    lowered below the low one. Supports optional outer bounds and a unit suffix.

    Args:
        default: The initial (low, high) pair; defaults to (0.0, 0.0).
        minimum: The lowest value either spinner allows; defaults to -1e12.
        maximum: The highest value either spinner allows; defaults to 1e12.
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
        upper_bound = maximum if maximum is not None else 1e12

        self._low = NoScrollDoubleSpinBox()
        self._low.setDecimals(6)
        self._low.setFixedWidth(200)
        self._low.setMinimum(minimum if minimum is not None else -1e12)
        self._low.setMaximum(upper_bound)
        self._low.setValue(low)

        self._high = NoScrollDoubleSpinBox()
        self._high.setDecimals(6)
        self._high.setFixedWidth(200)
        # the low value is the high spinner's floor; raising it pushes the high value up
        self._high.setMinimum(self._low.value())
        self._high.setMaximum(upper_bound)
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
        Make the new low value the high spinner's floor, then notify.

        If the low value now exceeds the high one, the high value is raised to
        match, so the pair stays valid and the edit is reported once.

        Args:
            value: The new low value.
        """
        with QSignalBlocker(self._high):
            self._high.setMinimum(value)
        self._emit()

    def _on_high_changed(self, value: float) -> None:
        """
        Notify of the new high value.

        Args:
            value: The new high value; never below the low value, which is the
                spinner's minimum.
        """
        _ = value
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
        # apply both values atomically, so the change is reported once
        with QSignalBlocker(self._low), QSignalBlocker(self._high):
            self._low.setValue(low)
            self._high.setMinimum(self._low.value())
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
