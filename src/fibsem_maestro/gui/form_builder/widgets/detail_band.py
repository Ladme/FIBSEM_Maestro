# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QVBoxLayout, QWidget

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget


class DetailBandWidget(QWidget, BaseWidget[DetailBand]):
    """A range-pair editor that reads and writes DetailBand instances."""

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
        low, high = self._range.get_value()
        return DetailBand(low=low, high=high)

    def set_value(self, value: DetailBand) -> None:
        self._range.set_value((value.low, value.high))

    def set_read_only(self, read_only: bool) -> None:
        self._range.set_read_only(read_only)
