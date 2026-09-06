# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import dataclasses
import types
from functools import cache
from types import NoneType
from typing import Any, Union, get_args, get_origin, get_type_hints

from pydantic_core import PydanticUndefined

from fibsem_maestro.gui.form_builder.schema._predicates import is_pydantic_model
from fibsem_maestro.gui.form_builder.schema._raw_field import RawField


@cache
def get_raw_fields(cls: type) -> tuple[RawField, ...]:
    """
    Extract raw field metadata from a dataclass or Pydantic model.

    Cached so that introspection is performed only once per class.

    Args:
        cls: A dataclass class or Pydantic `BaseModel` subclass.

    Returns:
        One `RawField` per declared field.

    Raises:
        TypeError: If `cls` is neither a dataclass nor a Pydantic model.
    """
    if is_pydantic_model(cls):
        return _raw_fields_from_pydantic(cls)
    if dataclasses.is_dataclass(cls):
        return _raw_fields_from_dataclass(cls)
    raise TypeError(f"{cls} is not a dataclass or Pydantic model")


def _raw_fields_from_dataclass(cls: type) -> tuple[RawField, ...]:
    """
    Read raw fields from a standard-library dataclass.

    Hints are resolved with `include_extras=True` so `Annotated[]` survives.
    Dataclasses carry no description or metadata of their own.
    """
    hints = get_type_hints(cls, include_extras=True)
    return tuple(
        RawField(
            name=f.name,
            type_hint=hints.get(f.name, f.type),
            default=f.default,
            default_factory=f.default_factory,
            description="",
            metadata=(),
        )
        for f in dataclasses.fields(cls)
    )


def _raw_fields_from_pydantic(cls: type) -> tuple[RawField, ...]:
    """
    Read raw fields from a Pydantic `BaseModel`.

    Pydantic sentinels are translated to the dataclass conventions so the rest
    of the pipeline treats both sources identically.
    """
    hints = get_type_hints(cls, include_extras=True)
    result = []
    for name, fi in cls.model_fields.items():  # type: ignore
        # normalize pydantic's sentinel to dataclasses.MISSING
        default = dataclasses.MISSING if fi.default is PydanticUndefined else fi.default
        default_factory = (
            dataclasses.MISSING if fi.default_factory is None else fi.default_factory
        )
        result.append(
            RawField(
                name=name,
                type_hint=hints.get(name),
                default=default,
                default_factory=default_factory,
                description=fi.description or "",
                metadata=tuple(fi.metadata) if fi.metadata else (),
            )
        )
    return tuple(result)


def unwrap_optional(hint: Any) -> tuple[bool, Any]:
    """
    Detect `X | None` and return `(True, inner)`.

    Two shapes are handled:

    - `X | None` (one non-None arm): returns `(True, X)`.
    - `X | Y | None` (several non-None arms, e.g. an optional discriminated
      union): returns `(True, hint)` with `None` still present, leaving
      `classify_type` to interpret the remaining union.

    Returns `(False, hint)` when the hint is not optional.
    """
    origin = get_origin(hint)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(hint) if a is not NoneType]

        # at least one None present in the union?
        if len(get_args(hint)) - len(args) >= 1:
            if len(args) == 1:
                return True, args[0]
            # multiple non-None arms: hand the whole union to classify_type
            return True, hint
    return False, hint
