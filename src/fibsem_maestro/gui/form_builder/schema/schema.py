# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import types
from enum import Enum
from pathlib import Path
from types import NoneType
from typing import Any, Literal, Union, get_args, get_origin

from fibsem_maestro.gui.common import field_name_to_label
from fibsem_maestro.gui.form_builder.schema._annotated import split_annotated
from fibsem_maestro.gui.form_builder.schema._extraction import (
    get_raw_fields,
    unwrap_optional,
)
from fibsem_maestro.gui.form_builder.schema._predicates import (
    is_float_tuple,
    is_model,
)
from fibsem_maestro.gui.form_builder.schema._resolve import (
    pydantic_discriminator,
    resolve_default,
    resolve_description,
)
from fibsem_maestro.gui.form_builder.schema._union_helpers import (
    get_discriminator_key,
    make_union,
)
from fibsem_maestro.gui.form_builder.schema.constraints import extract_bounds
from fibsem_maestro.gui.form_builder.schema.field_info import FieldInfo
from fibsem_maestro.gui.form_builder.schema.field_type import (
    BoolType,
    DataclassType,
    EnumType,
    FieldType,
    FloatTupleType,
    FloatType,
    IntType,
    ListType,
    LiteralType,
    StrType,
    UnknownType,
)


def classify_type(t: Any) -> FieldType:
    """
    Classify an already-unwrapped, non-`Optional` hint into a descriptor.

    The caller must have stripped `Annotated[]` and `Optional[]` first.
    Numeric bounds and the Pydantic single-variant discriminator are resolved
    by `get_field_infos`, not here, since both require field metadata.

    Args:
        t: A bare type hint.

    Returns:
        The matching `FieldType` descriptor; `UnknownType` as a fallback.
    """
    # bool before int, since bool is a subclass of int
    if t is bool:
        return BoolType()
    if t is int:
        return IntType()
    if t is float:
        return FloatType()
    if is_float_tuple(t):
        return FloatTupleType(length=len(get_args(t)))

    # filesystem paths are edited as strings
    if t in (str, Path, Path | str):
        return StrType()

    if get_origin(t) is Literal:
        return LiteralType(choices=get_args(t))

    if isinstance(t, type) and issubclass(t, Enum):
        return EnumType(enum_type=t)

    if is_model(t):
        return DataclassType(model=t)

    origin = get_origin(t)

    # union (X | Y | ...): a tagged union only if every arm is a model and they
    # share a Literal discriminator field
    if origin is Union or origin is types.UnionType:
        variants = tuple(a for a in get_args(t) if a is not NoneType)
        if variants and all(is_model(a) for a in variants):
            key = get_discriminator_key(list(variants))
            if key is not None:
                return make_union(variants, key)

    if origin is list:
        args = get_args(t)
        # argless list has no editable element type -> text-area fallback
        if args:
            return ListType(item=classify_type(args[0]))
        return UnknownType(hint=t)

    return UnknownType(hint=t)


def get_field_infos(cls: type) -> list[FieldInfo]:
    """
    Return a `FieldInfo` for every field of a dataclass or Pydantic model.

    Args:
        cls: A dataclass class or Pydantic ``BaseModel`` subclass.

    Returns:
        One ``FieldInfo`` per field, in declaration order.
    """
    result: list[FieldInfo] = []

    for rf in get_raw_fields(cls):
        outer = split_annotated(rf.type_hint)

        # unwrap optional, then strip a possibly-annotated inner type
        optional, unwrapped = unwrap_optional(outer.bare)
        inner = split_annotated(unwrapped)

        # outer annotations take precedence; inner ones fill any gaps
        form_hint = outer.hint or inner.hint
        field_unit = outer.unit or inner.unit
        all_extras = outer.extras + inner.extras + rf.metadata

        result.append(
            FieldInfo(
                name=rf.name,
                label=field_name_to_label(rf.name),
                description=resolve_description(rf, all_extras),
                optional=optional,
                default=resolve_default(rf),
                hint=form_hint,
                unit=field_unit,
                bounds=extract_bounds(all_extras),
                type=_classify_field(inner.bare, all_extras),
            )
        )

    return result


def _classify_field(inner_hint: Any, extras: tuple) -> FieldType:
    """
    Classify the field type, applying the Pydantic single-variant promotion.

    A model field carrying ``Field(discriminator=...)`` is a one-armed
    discriminated union even though only one variant is visible on the hint.
    """
    field_type = classify_type(inner_hint)
    if isinstance(field_type, DataclassType):
        discriminator = pydantic_discriminator(extras)
        if discriminator is not None:
            model = (field_type.model,)
            key = get_discriminator_key([field_type.model]) or discriminator
            return make_union(model, key)
    return field_type
