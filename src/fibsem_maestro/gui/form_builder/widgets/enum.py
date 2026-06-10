# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from enum import Enum
from typing import Any

from PyQt6.QtWidgets import QWidget

from fibsem_maestro.gui.form_builder.widgets._no_scroll import NoScrollComboBox
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class EnumWidget(NoScrollComboBox, WidgetWrapper):
    def __init__(
        self,
        choices: list[Any],
        default: Any = None,
        optional: bool = False,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        if optional:
            self.addItem("(none)", userData=None)
        for choice in choices:
            # store the real Python value as userData alongside the display string
            self.addItem(
                choice.value if isinstance(choice, Enum) else str(choice),
                userData=choice,
            )
        if default is not None:
            idx = self.findData(default)
            if idx >= 0:
                self.setCurrentIndex(idx)
        self.setFixedWidth(200)

    def get_value(self) -> Any:
        return self.currentData()

    def set_value(self, value: Any) -> None:
        idx = self.findData(value)
        if idx >= 0:
            self.setCurrentIndex(idx)

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
