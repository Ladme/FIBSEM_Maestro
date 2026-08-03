# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QVBoxLayout, QWidget

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget


class DetailBandWidget(QWidget, BaseWidget[DetailBand]):
    """
    A range-pair editor that reads and writes DetailBand instances.

    Wraps a RangePairWidget and maps its low/high pair to and from a
    DetailBand value.

    Args:
        default: The initial band; if None, the range starts empty.
        minimum: The lowest value the range allows, if any.
        maximum: The highest value the range allows, if any.
        suffix: A unit suffix to display after each value, if any.
        parent: The parent widget, if any.
    """

    def __init__(
        self,
        default: DetailBand | None = None,
        minimum: float | None = None,
        maximum: float | None = None,
        suffix: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)
        pair = (default.low, default.high) if default is not None else None
        self._range = RangePairWidget(pair, minimum, maximum, suffix)
        self._range.on_change(self._emit)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._range)

    def get_value(self) -> DetailBand:
        """
        Return the current band as a DetailBand.

        Returns:
            A DetailBand with the current low and high values.
        """

        low, high = self._range.get_value()
        return DetailBand(low=low, high=high)

    def set_value(self, value: DetailBand) -> None:
        """
        Set the low and high values from a DetailBand.

        Args:
            value: The band whose low and high values to apply.
        """

        self._range.set_value((value.low, value.high))

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable user interaction with the widget.

        Args:
            read_only: If True, prevent edits to the range.
        """
        self._range.set_read_only(read_only)
