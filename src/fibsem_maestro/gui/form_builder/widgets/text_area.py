# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import json
from typing import Any

from PyQt6.QtWidgets import QPlainTextEdit, QWidget

from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class TextAreaWidget(QPlainTextEdit, WidgetWrapper):
    def __init__(self, default: Any = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFixedHeight(80)
        if default is not None:
            self.setPlainText(json.dumps(default, indent=2, default=str))

    def get_value(self) -> Any:
        text = self.toPlainText().strip()
        if not text:
            return None
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return text

    def set_value(self, value: Any) -> None:
        self.setPlainText(
            json.dumps(value, indent=2, default=str) if value is not None else ""
        )
