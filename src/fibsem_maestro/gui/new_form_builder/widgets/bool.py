# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtWidgets import QCheckBox, QWidget

from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget


class BoolWidget(QCheckBox, BaseWidget[bool]):
    def __init__(self, default: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        BaseWidget.__init__(self)
        self.setChecked(bool(default))
        self.toggled.connect(lambda _: self._emit())

    def get_value(self) -> bool:
        return self.isChecked()

    def set_value(self, value: bool) -> None:
        self.setChecked(bool(value))

    def set_read_only(self, read_only: bool) -> None:
        self.setEnabled(not read_only)
