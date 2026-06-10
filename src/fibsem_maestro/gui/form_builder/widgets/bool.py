# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

from PyQt6.QtWidgets import QCheckBox, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class BoolWidget(QCheckBox, WidgetWrapper):
    def __init__(self, default: bool = False, parent: QWidget | None = None):
        super().__init__(parent)
        self.setChecked(bool(default))

    def get_value(self) -> bool:
        return self.isChecked()

    def set_value(self, value: Any) -> None:
        self.setChecked(bool(value))

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
