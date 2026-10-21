# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Problems reported on form fields, and their attribution to field editors."""

from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self

from pydantic import ValidationError

from fibsem_maestro.ui.forms.editor import FieldEditor
from fibsem_maestro.ui.schema.validation import detail_message


class Severity(Enum):
    """How serious a field issue is."""

    ERROR = "error"
    """The value is invalid and was not written to the settings."""

    WARNING = "warning"
    """The value is valid but likely to cause a problem."""


@dataclass(frozen=True)
class FieldIssue:
    """
    A problem with a field's value, shown below the field.

    Attributes:
        severity: How serious the problem is.
        message: Short description shown to the user.
    """

    severity: Severity
    message: str


VALIDATION_ISSUE = "validation"
"""Source key of the issues set by the committer when an edited value fails validation."""


class FieldValidationError(ValueError):
    """
    A value could not be built from the form, with each problem attributed to a field widget.

    Args:
        problems: `(widget, message)` pairs. A None widget means the problem
            concerns the enclosing field as a whole: whoever catches the error
            attributes it to the field widget it was reading (see `attributed_to`).
    """

    def __init__(self, problems: Sequence[tuple[FieldEditor[Any] | None, str]]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(message for _, message in self.problems))

    @classmethod
    def from_validation_error(
        cls,
        error: ValidationError,
        field_widget: Callable[[str], FieldEditor[Any] | None],
    ) -> Self:
        """
        Attribute each error of a failed model construction to the field it concerns.

        Args:
            error: The error raised while constructing the model.
            field_widget: Looks up the widget of a model field by name; returns
                None for a name the form does not show.

        Returns:
            The error, with every problem on a field shown in the form attributed
            to that field's widget and the rest (model-level errors, fields not
            in the form) left to the enclosing field.
        """
        problems: list[tuple[FieldEditor[Any] | None, str]] = []
        for detail in error.errors():
            loc = detail["loc"]
            widget = field_widget(loc[0]) if loc and isinstance(loc[0], str) else None
            problems.append((widget, detail_message(detail)))
        return cls(problems)

    @classmethod
    def of_whole_field(cls, messages: Iterable[str]) -> Self:
        """
        Report problems concerning the enclosing field as a whole.

        Args:
            messages: The problem descriptions.

        Returns:
            The error, with no problem attributed to a particular widget.
        """
        return cls([(None, message) for message in messages])

    def attributed_to(
        self, widget: FieldEditor[Any]
    ) -> list[tuple[FieldEditor[Any], str]]:
        """
        Return the problems, with those concerning the field as a whole given to `widget`.

        Args:
            widget: The field widget the catcher was reading.

        Returns:
            Every problem paired with a widget.
        """
        return [(w if w is not None else widget, m) for w, m in self.problems]
