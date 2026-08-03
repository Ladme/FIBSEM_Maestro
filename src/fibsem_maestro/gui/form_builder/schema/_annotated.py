# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import typing
from dataclasses import dataclass
from typing import Any, get_args, get_origin

from fibsem_maestro.settings.form_utils import FieldUnit, FormHint


@dataclass(frozen=True)
class Annotated:
    """
    The parts of an `Annotated[...]` hint after unpacking.

    Attributes:
        bare: The underlying type with the annotations removed.
        hint: The first `FormHint` among the extras, if any.
        unit: The first `FieldUnit` among the extras, if any.
        extras: All annotation extras (constraint carriers included).
    """

    bare: Any
    hint: FormHint | None
    unit: FieldUnit | None
    extras: tuple


def split_annotated(hint: Any) -> Annotated:
    """
    Unpack `Annotated[X, ...]` into its bare type and recognised extras.

    Non-annotated hints pass through as `Annotated(hint, None, None, ())`.
    """
    if get_origin(hint) is not typing.Annotated:
        return Annotated(hint, None, None, ())

    args = get_args(hint)
    extras = args[1:]
    form_hint = next((a for a in extras if isinstance(a, FormHint)), None)
    field_unit = next((a for a in extras if isinstance(a, FieldUnit)), None)
    return Annotated(args[0], form_hint, field_unit, extras)
