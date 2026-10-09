# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Callable, Iterable, Sequence
from dataclasses import dataclass
from enum import Enum
from typing import Any, Self

from pydantic import ValidationError
from pydantic_core import ErrorDetails

from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget


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
"""Source key of the issues set by the write-back when an edited value fails validation."""


class FieldValidationError(ValueError):
    """
    A value could not be built from the form, with each problem attributed to a field widget.

    Args:
        problems: `(widget, message)` pairs. A None widget means the problem
            concerns the enclosing field as a whole: whoever catches the error
            attributes it to the field widget it was reading (see `attributed_to`).
    """

    def __init__(self, problems: Sequence[tuple[BaseWidget[Any] | None, str]]) -> None:
        self.problems = list(problems)
        super().__init__("; ".join(message for _, message in self.problems))

    @classmethod
    def from_validation_error(
        cls,
        error: ValidationError,
        field_widget: Callable[[str], BaseWidget[Any] | None],
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
        problems: list[tuple[BaseWidget[Any] | None, str]] = []
        for detail in error.errors():
            loc = detail["loc"]
            widget = field_widget(loc[0]) if loc and isinstance(loc[0], str) else None
            problems.append((widget, _detail_message(detail)))
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
        self, widget: BaseWidget[Any]
    ) -> list[tuple[BaseWidget[Any], str]]:
        """
        Return the problems, with those concerning the field as a whole given to `widget`.

        Args:
            widget: The field widget the catcher was reading.

        Returns:
            Every problem paired with a widget.
        """
        return [(w if w is not None else widget, m) for w, m in self.problems]


def validation_messages(error: ValidationError) -> list[str]:
    """
    Return a short message for every error in a pydantic validation error.

    Args:
        error: The validation error.

    Returns:
        One message per error, in order.
    """
    return [_detail_message(detail) for detail in error.errors()]


def _detail_message(detail: ErrorDetails) -> str:
    """
    Phrase one pydantic error for the user.

    A type error on None means nothing was selected or entered in a required
    field (e.g. an empty dropdown), which pydantic phrases as a type mismatch.

    Args:
        detail: One entry of `ValidationError.errors()`.

    Returns:
        The message, without pydantic's error-type prefix.
    """
    if detail["type"].endswith("_type") and detail.get("input") is None:
        return "A value is required."

    return short_message(detail["msg"])


def short_message(message: str) -> str:
    """
    Strip pydantic's error-type prefix from a validator's message.

    Args:
        message: A pydantic error message, e.g. `"Value error, range is reversed"`.

    Returns:
        The message without a `"Value error, "` or `"Assertion failed, "` prefix.
    """
    for prefix in ("Value error, ", "Assertion failed, "):
        if message.startswith(prefix):
            return message.removeprefix(prefix)

    return message
