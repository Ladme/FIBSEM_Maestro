# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget

from fibsem_maestro.gui.common import _model_to_dict
from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel
from fibsem_maestro.gui.form_builder.widgets.wrapper import WidgetWrapper


class ObjectWidget(QWidget, WidgetWrapper):
    def __init__(self, cls: type | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        WidgetWrapper.__init__(self)

        self._cls = cls
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setColumnStretch(1, 1)
        self._fields: dict[str, WidgetWrapper] = {}
        self._row_count = 0

    def add_field(
        self, name: str, label: str, widget: WidgetWrapper, description: str = ""
    ) -> None:
        widget._parent = self
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

    def get_value(self) -> Any:
        data = {name: w.get_value() for name, w in self._fields.items()}
        if self._cls is not None:
            return self._cls(**data)
        return data

    def set_value(self, value: Any) -> None:
        data = value if isinstance(value, dict) else _model_to_dict(value)
        if not isinstance(data, dict):
            return
        for name, w in self._fields.items():
            if name in data:
                w.set_value(data[name])

    def set_read_only(self, read_only: bool) -> None:
        for w in self._fields.values():
            w.set_read_only(read_only)
