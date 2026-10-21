# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Validating a field assignment as a settings form does, and phrasing pydantic errors for the user.

Shared by the forms (which validate every edit before writing it) and the
settings audit (which predicts what a fresh form would reject), so both judge
values and word problems identically.
"""

import copy
from typing import Any

from pydantic import ValidationError
from pydantic_core import ErrorDetails

REQUIRED_MESSAGE = "A value is required."
"""The message for None in a field that requires a value."""


def validate_assignment(owner: object, name: str, value: Any) -> Any:
    """
    Validate a new value for a field as its owner would on assignment.

    The owner is a pydantic model, a pydantic dataclass, or a plain dataclass.
    Pydantic owners do not validate assignments, so without this the
    constraints and validators of their fields would never run. Validation
    runs on a shallow copy, so the owner and its change hooks are untouched.
    A plain dataclass has no validation to run.

    Args:
        owner: The object owning the field.
        name: The field name.
        value: The candidate value.

    Returns:
        The validated value, possibly coerced (e.g. a list rebuilt); `value`
        unchanged for a plain dataclass.

    Raises:
        pydantic.ValidationError: If the value is invalid for the field.
    """
    validator = getattr(type(owner), "__pydantic_validator__", None)
    if validator is None:
        return value

    probe = copy.copy(owner)
    validator.validate_assignment(probe, name, value)
    return getattr(probe, name)


def validation_messages(error: ValidationError) -> list[str]:
    """
    Return a short message for every error in a pydantic validation error.

    Args:
        error: The validation error.

    Returns:
        One message per error, in order.
    """
    return [detail_message(detail) for detail in error.errors()]


def detail_message(detail: ErrorDetails) -> str:
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
        return REQUIRED_MESSAGE

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
