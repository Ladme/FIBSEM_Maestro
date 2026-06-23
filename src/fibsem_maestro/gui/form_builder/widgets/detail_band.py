# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.gui.form_builder.widgets.range_pair import RangePairWidget


class DetailBandWidget(RangePairWidget):
    """RangePairWidget that reads and writes DetailBand instances."""

    def get_value(self) -> DetailBand:  # type: ignore
        low, high = super().get_value()
        return DetailBand(low=low, high=high)

    def set_value(self, value: Any) -> None:
        if hasattr(value, "low") and hasattr(value, "high"):
            super().set_value((value.low, value.high))
        elif isinstance(value, dict) and "low" in value and "high" in value:
            super().set_value((value["low"], value["high"]))
        else:
            super().set_value(value)
