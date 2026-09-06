# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from typing import TypeVar

import yaml
from pydantic import TypeAdapter
from PyQt6.QtWidgets import QPlainTextEdit, QWidget

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget

T = TypeVar("T")


class TextAreaWidget(QPlainTextEdit, BaseWidget[T]):
    """
    Fallback editor for values with no dedicated widget.

    The value is edited as YAML text and validated back into `target_type`
    on read, so `get_value` returns a fully-typed object (a dataclass, a
    pydantic model, or anything pydantic can validate) rather than raw text.

    Args:
        target_type: The type to load the YAML into (e.g. a dataclass or model).
        default: An initial value, rendered to YAML for editing.
        parent: The parent widget, if any.
    """

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
        """
        Parse the YAML text and validate it into `target_type`.

        Returns:
            The validated value of type `T`.

        Raises:
            yaml.YAMLError: If the text is not valid YAML.
            pydantic.ValidationError: If the parsed data does not conform to `target_type`.
        """

        data = yaml.safe_load(self.toPlainText())
        return self._adapter.validate_python(data)

    def set_value(self, value: T) -> None:
        """
        Render a value to YAML and display it for editing.

        Args:
            value: The value to serialize; None clears the field.
        """

        if value is None:
            self.setPlainText("")
            return

        data = self._adapter.dump_python(value, mode="json")
        self.setPlainText(yaml.safe_dump(data, sort_keys=False).rstrip())

    def set_read_only(self, read_only: bool) -> None:
        """
        Enable or disable editing of the text.

        Args:
            read_only: If True, make the field read-only.
        """
        self.setReadOnly(read_only)
