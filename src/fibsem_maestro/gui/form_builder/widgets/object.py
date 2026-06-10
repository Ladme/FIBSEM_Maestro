# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget

from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class ObjectWidget(QWidget, WidgetWrapper):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setColumnStretch(1, 1)
        self._fields: dict[str, WidgetWrapper] = {}
        self._row_count = 0

    def add_field(
        self, name: str, label: str, widget: WidgetWrapper, description: str = ""
    ) -> None:
        label_widget = FieldLabel(label, cast("QWidget", widget))
        label_widget.setWordWrap(True)
        label_widget.setAlignment(
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        )
        if description:
            label_widget.setToolTip(description)
        self._layout.addWidget(label_widget, self._row_count, 0)
        self._layout.addWidget(cast("QWidget", widget), self._row_count, 1)
        self._row_count += 1
        self._fields[name] = widget

    def get_value(self) -> dict:
        return {name: w.get_value() for name, w in self._fields.items()}

    def set_value(self, value: dict) -> None:
        if not isinstance(value, dict):
            return
        for name, w in self._fields.items():
            if name in value:
                w.set_value(value[name])

    def set_read_only(self, read_only: bool) -> None:
        for w in self._fields.values():
            w.set_read_only(read_only)
