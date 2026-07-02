# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum
from typing import TypeVar

from PyQt6.QtWidgets import QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class EnumWidget(NoScrollComboBox, BaseWidget[T | None]):
    def __init__(
        self,
        choices: list[T],
        default: T | None = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self._values: list[T | None] = []

        if optional:
            self.addItem("(none)", userData=None)
            self._values.append(None)

        for choice in choices:
            # store the real Python value as userData alongside the display string
            self.addItem(
                choice.value if isinstance(choice, Enum) else str(choice),
                userData=choice,
            )
            self._values.append(choice)

        if default is not None and default in self._values:
            self.setCurrentIndex(self._values.index(default))

        self.setFixedWidth(200)
        self.currentIndexChanged.connect(lambda _: self._emit())

    def get_value(self) -> T | None:
        return self.currentData()

    def set_value(self, value: T | None) -> None:
        if value in self._values:
            self.setCurrentIndex(self._values.index(value))

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
