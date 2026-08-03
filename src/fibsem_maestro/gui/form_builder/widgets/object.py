# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Any, TypeVar, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QWidget

from fibsem_maestro.gui.common import _model_to_dict
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel

T = TypeVar("T")


class ObjectWidget(QWidget, BaseWidget[T]):
    """
    A form widget that edits an object's fields in a labelled grid.

    Args:
        cls: The dataclass or model type to construct from the field values.
        parent: The parent widget, if any.
    """

    def __init__(self, cls: type[T], parent: QWidget | None = None):
        super().__init__(parent)
        BaseWidget.__init__(self)

        # required to highlight selected box
        self.setProperty("dataclass_form", True)

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
        """
        Add a labelled field row to the form.

        Args:
            name: The field key used when reading and writing values.
            label: The text shown in the field's label.
            widget: The editor widget for the field's value.
            description: Optional tooltip text for the label.
        """

        label_widget = FieldLabel(label, widget.highlight_target())
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
        """
        Return the field editor widgets in insertion order.

        Returns:
            A list of the field widgets.
        """

        return list(self._fields.values())

    def values_dict(self) -> dict[str, Any]:
        """
        Return the current field values keyed by field name.

        Returns:
            A mapping from field name to that field's current value.
        """

        return {name: w.get_value() for name, w in self._fields.items()}

    def get_value(self) -> T:
        """
        Construct an instance of the underlying class from the current field values.

        Returns:
            A new instance of the underlying class built from the field values.
        """

        return self._cls(**self.values_dict())

    def set_value(self, value: T) -> None:
        """
        Populate the fields from an object or dict.

        Accepts a dict or a model/dataclass instance; the latter is
        converted to a dict first. Fields absent from the data are left
        unchanged.

        Args:
            value: The object or dict to read field values from.
        """

        data: dict | None = value if isinstance(value, dict) else _model_to_dict(value)
        if not isinstance(data, dict):
            return

        for name, w in self._fields.items():
            if name in data:
                w.set_value(data[name])

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of all field widgets.

        Args:
            read_only: If True, make every field read-only.
        """
        for w in self._fields.values():
            w.set_read_only(read_only)
