# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any, TypeVar, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget

from fibsem_maestro.gui.common import _model_to_dict
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel

T = TypeVar("T")


class ObjectWidget(QWidget, BaseWidget[T]):
    def __init__(self, cls: type[T], parent: QWidget | None = None):
        super().__init__(parent)
        BaseWidget.__init__(self)

        self._cls = cls
        self._layout = QGridLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(4)
        self._layout.setColumnStretch(1, 1)
        self._fields: dict[str, BaseWidget[Any]] = {}
        self._row_count = 0

    def add_field(
        self, name: str, label: str, widget: BaseWidget[Any], description: str = ""
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

    def child_widgets(self) -> list[BaseWidget[Any]]:
        return list(self._fields.values())

    def values_dict(self) -> dict[str, Any]:
        return {name: w.get_value() for name, w in self._fields.items()}

    def get_value(self) -> T:
        return self._cls(**self.values_dict())

    def set_value(self, value: T) -> None:
        data: dict | None = value if isinstance(value, dict) else _model_to_dict(value)
        if not isinstance(data, dict):
            return

        for name, w in self._fields.items():
            if name in data:
                w.set_value(data[name])

    def set_read_only(self, read_only: bool) -> None:
        for w in self._fields.values():
            w.set_read_only(read_only)
