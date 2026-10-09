# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF
#
from dataclasses import dataclass
from functools import partial
from html import escape
from typing import Any, TypeVar, cast

from pydantic import ValidationError
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QGridLayout, QLabel, QWidget

from fibsem_maestro.gui.common import _model_to_dict
from fibsem_maestro.gui.form_builder.issues import (
    FieldIssue,
    FieldValidationError,
    Severity,
)
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.form_builder.widgets.field_label import FieldLabel

T = TypeVar("T")

_ISSUE_COLORS = {Severity.ERROR: "#e05252", Severity.WARNING: "#e0a030"}
"""Text colour of a field's label and message, by the most severe issue."""


@dataclass(frozen=True)
class _FieldRow:
    """
    The widgets showing one field's issues.

    Attributes:
        label: The field's label, coloured while the field has issues.
        message: The line below the editor describing the issues; hidden while
            there are none.
    """

    label: FieldLabel
    message: QLabel


def _issue_html(issue: FieldIssue) -> str:
    """
    Render one issue as a line of rich text in its severity's colour.

    Args:
        issue: The issue to render.

    Returns:
        HTML-escaped message text, with line breaks kept.
    """
    text = escape(issue.message).replace("\n", "<br>")
    color = _ISSUE_COLORS[issue.severity]
    return f'<span style="color: {color}; font-size: 11px;">{text}</span>'


class ObjectWidget(QWidget, BaseWidget[T]):
    """
    A form widget that edits an object's fields in a labelled grid.

    Every field occupies two grid rows: the label and editor, and below the
    editor a message line that is shown only while the field reports issues
    (see `BaseWidget.set_issue`). A field with issues also has its label
    coloured by the most severe one.

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
        self._rows: dict[str, _FieldRow] = {}
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

        message = QLabel()
        message.setWordWrap(True)
        message.setTextFormat(Qt.TextFormat.RichText)
        message.hide()

        self._layout.addWidget(label_widget, self._row_count, 0)
        self._layout.addWidget(cast("QWidget", widget), self._row_count, 1)
        # a row holding only a hidden widget takes no space
        self._layout.addWidget(message, self._row_count + 1, 1)
        self._row_count += 2

        self._fields[name] = widget
        self._rows[name] = _FieldRow(label_widget, message)
        widget.on_issues_changed(partial(self._show_issues, name))

    def _show_issues(self, name: str) -> None:
        """
        Redraw one field's label colour and message line from its current issues.

        Args:
            name: The field key given to `add_field`.
        """
        issues = self._fields[name].issues()
        row = self._rows[name]

        if not issues:
            row.label.setStyleSheet("")
            row.message.clear()
            row.message.hide()
            return

        # errors first, each line in its own severity's colour
        ordered = sorted(issues, key=lambda issue: issue.severity is not Severity.ERROR)
        row.message.setText("<br>".join(_issue_html(issue) for issue in ordered))
        row.label.setStyleSheet(f"color: {_ISSUE_COLORS[ordered[0].severity]};")
        row.message.show()

    def has_errors(self) -> bool:
        """
        Check whether any field of this object reports an error.

        Fields of nested objects are not included; they belong to their own
        `ObjectWidget`.

        Returns:
            True if a field's issues include one of severity `ERROR`.
        """
        return any(
            issue.severity is Severity.ERROR
            for widget in self._fields.values()
            for issue in widget.issues()
        )

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

        Every field is read, so the problems of all invalid fields are reported
        together.

        Returns:
            A mapping from field name to that field's current value.

        Raises:
            FieldValidationError: If any field's value cannot be built. Problems
                concerning a field as a whole are attributed to that field's
                widget.
        """
        values: dict[str, Any] = {}
        problems: list[tuple[BaseWidget[Any], str]] = []
        first_error: FieldValidationError | None = None

        for name, w in self._fields.items():
            try:
                values[name] = w.get_value()
            except FieldValidationError as e:
                problems.extend(e.attributed_to(w))
                first_error = first_error or e

        if first_error is not None:
            raise FieldValidationError(problems) from first_error
        return values

    def get_value(self) -> T:
        """
        Construct an instance of the underlying class from the current field values.

        Returns:
            A new instance of the underlying class built from the field values.

        Raises:
            FieldValidationError: If a field's value cannot be built, or the
                instance fails validation. Problems on a field are attributed
                to that field's widget; model-level problems are left to the
                field containing this object.
        """
        values = self.values_dict()
        try:
            return self._cls(**values)
        except ValidationError as e:
            raise FieldValidationError.from_validation_error(
                e, self.field_widget
            ) from e

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

    def field_widget(self, name: str) -> BaseWidget[Any] | None:
        """
        Return the editor widget for one field.

        Args:
            name: The field key given to `add_field`.

        Returns:
            The field's widget, or None if this form has no such field.
        """
        return self._fields.get(name)
