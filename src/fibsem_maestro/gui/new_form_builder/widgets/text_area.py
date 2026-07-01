# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import TypeVar

import yaml
from pydantic import TypeAdapter
from PyQt6.QtWidgets import QPlainTextEdit, QWidget

from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class TextAreaWidget(QPlainTextEdit, BaseWidget[T]):
    def __init__(
        self,
        target_type: type[T],
        default: T | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        BaseWidget.__init__(self)
        self._adapter: TypeAdapter[T] = TypeAdapter(target_type)

        self.setFixedHeight(96)

        if default is not None:
            self.set_value(default)

        self.textChanged.connect(self._emit)

    def get_value(self) -> T:
        data = yaml.safe_load(self.toPlainText())
        return self._adapter.validate_python(data)

    def set_value(self, value: T) -> None:
        if value is None:
            self.setPlainText("")
            return

        data = self._adapter.dump_python(value, mode="json")
        self.setPlainText(yaml.safe_dump(data, sort_keys=False).rstrip())

    def set_read_only(self, read_only: bool) -> None:
        self.setReadOnly(read_only)
