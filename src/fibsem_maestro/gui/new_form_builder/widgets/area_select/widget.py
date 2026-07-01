# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QLabel, QWidget

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget
from fibsem_maestro.microscope.microscope import Microscope


class AreaSelectWidget(QLabel, BaseWidget[list[RelativeArea]]):
    def __init__(
        self,
        microscope: Microscope,
        max_areas: int | None = None,
        default: list[RelativeArea] = [],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__("(area select)", parent)
        BaseWidget.__init__(self)
        self._value = default
        _ = microscope, max_areas

    def get_value(self) -> list[RelativeArea]:
        return self._value

    def set_value(self, value: list[RelativeArea]) -> None:
        self._value = value
        self._emit()

    def set_read_only(self, read_only: bool) -> None:
        pass
