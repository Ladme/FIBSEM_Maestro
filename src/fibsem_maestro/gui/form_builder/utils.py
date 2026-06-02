# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import dataclasses
import types
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Annotated, Any, Literal, Union, get_args, get_origin, get_type_hints

from pydantic import BaseModel
from pydantic_core import PydanticUndefined

from fibsem_maestro.settings.form_utils import FieldUnit, FormHint


class TypeKind(Enum):
    BOOL = "bool"
    INT = "int"
    FLOAT = "float"
    STR = "str"  # str or Path
    ENUM = "enum"  # subclass of enum.Enum -> QComboBox
    LITERAL = "literal"  # Literal["a", "b", ...]  -> QComboBox
    DATACLASS = "dataclass"  # nested dataclass/BaseModel  -> ObjectWidget / GroupBox
    DISCRIMINATED_UNION = (
        "discriminated_union"  # X | Y where both have a Literal discriminator field
    )
    LIST = "list"
    UNKNOWN = "unknown"  # anything else  -> TextArea fallback


@dataclass
class RawField:
    name: str
    type_hint: Any  # raw, with Annotated intact
    default: Any  # normalised to dataclasses.MISSING if absent
    default_factory: Any  # normalised to dataclasses.MISSING if absent
    description: str
    metadata: tuple  # annotated_types constraints etc.


@dataclass
class FieldInfo:
    name: str
    label: str
    kind: TypeKind
    inner_type: type | None  # unwrapped type (e.g. int for Optional[int])
    default: Any  # dataclasses.MISSING if no default
    description: str
    optional: bool  # True when the field can be None
    hint: FormHint | None  # from Annotated[], if present
    unit: FieldUnit | None  # from Annotated[], if present
    # pydantic / annotated_types numeric constraints (None = no constraint)
    minimum: float | None
    maximum: float | None
    # for LITERAL kind: the allowed values
    literal_choices: list | None
    # for DISCRIMINATED_UNION kind: list of (discriminator_value, inner_type) pairs
    union_variants: list[tuple[str, type]] | None


def _is_dataclass_type(t: Any) -> bool:
    """True for dataclass classes and Pydantic BaseModel subclasses."""
    return dataclasses.is_dataclass(t) and isinstance(t, type)


def _is_pydantic_model(cls: type) -> bool:
    return isinstance(cls, type) and issubclass(cls, BaseModel)


def _get_raw_fields(cls: type) -> list[RawField]:
    if _is_pydantic_model(cls):
        return _raw_fields_from_pydantic(cls)
    if dataclasses.is_dataclass(cls):
        return _raw_fields_from_dataclass(cls)
    raise TypeError(f"{cls} is not a dataclass or Pydantic model")


def _raw_fields_from_dataclass(cls: type) -> list[RawField]:
    hints = get_type_hints(cls, include_extras=True)
    result = []
    for f in dataclasses.fields(cls):
        result.append(
            RawField(
                name=f.name,
                type_hint=hints.get(f.name, f.type),
                default=f.default,
                default_factory=f.default_factory,
                description="",
                metadata=(),
            )
        )
    return result


def _raw_fields_from_pydantic(cls: type) -> list[RawField]:
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
    return result


def _unwrap_optional(hint: Any) -> tuple[bool, Any]:
    """
    Detect X | None and return (True, X).
    Returns (False, hint) if not optional.
    """
    origin = get_origin(hint)

    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(hint) if a is not type(None)]
        # if there is at least one None in the union
        if len(get_args(hint)) - len(args) >= 1:
            if len(args) == 1:
                return True, args[0]
            # multiple non-None args - could be a discriminated union wrapped in Optional
            # classify_type handles the union
            return True, hint
    return False, hint


def _get_discriminator_key(variant_types: list[type]) -> str | None:
    for rf in _get_raw_fields(variant_types[0]):
        bare_hint, _, _, _ = _extract_annotated_extras(rf.type_hint)
        if get_origin(bare_hint) is Literal and all(
            any(
                get_origin(_extract_annotated_extras(rf2.type_hint)[0]) is Literal
                and rf2.name == rf.name
                for rf2 in _get_raw_fields(v)
            )
            for v in variant_types[1:]
        ):
            return rf.name
    return None


def _extract_constraints(annotated_args: tuple) -> tuple[float | None, float | None]:
    """
    Pull gt/ge/lt/le constraints out of Annotated[] metadata.
    """
    minimum = maximum = None
    for arg in annotated_args:
        # annotated_types uses .gt / .ge / .lt / .le attributes
        if hasattr(arg, "gt") and arg.gt is not None:
            minimum = arg.gt + 1 if isinstance(arg.gt, int) else arg.gt
        if hasattr(arg, "ge") and arg.ge is not None:
            minimum = arg.ge
        if hasattr(arg, "lt") and arg.lt is not None:
            maximum = arg.lt - 1 if isinstance(arg.lt, int) else arg.lt
        if hasattr(arg, "le") and arg.le is not None:
            maximum = arg.le
        # pydantic FieldInfo stores them under metadata list
        if hasattr(arg, "metadata"):
            lo, hi = _extract_constraints(tuple(arg.metadata))
            if lo is not None:
                minimum = lo
            if hi is not None:
                maximum = hi
    return minimum, maximum


def _extract_annotated_extras(
    hint: Any,
) -> tuple[Any, FormHint | None, FieldUnit | None, tuple]:
    """
    If hint is Annotated[X, ...], unpack X and scan the extra args for
    FormHint, FieldUnit, and constraint metadata.
    Returns (bare_type, hint_or_none, unit_or_none, all_annotated_args).
    """
    if get_origin(hint) is not Annotated:
        return hint, None, None, ()

    args = get_args(hint)
    bare_type = args[0]
    extras = args[1:]

    form_hint = next((a for a in extras if isinstance(a, FormHint)), None)
    field_unit = next((a for a in extras if isinstance(a, FieldUnit)), None)

    return bare_type, form_hint, field_unit, extras


def field_name_to_label(name: str) -> str:
    """'stage_position' -> 'stage position'"""
    return name.replace("_", " ")


def class_name_to_label(name: str) -> str:
    """'StandardResolution' -> 'standard resolution'"""
    import re

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return spaced.lower()


def classify_type(t: Any) -> TypeKind:
    """
    Categorise a (already-unwrapped, non-Optional) type hint into a TypeKind.
    The caller should have already stripped Annotated[] and Optional[].
    """
    # bool must be checked before int since bool is a subclass of int
    if t is bool:
        return TypeKind.BOOL
    if t is int:
        return TypeKind.INT
    if t is float:
        return TypeKind.FLOAT

    if t in (str, Path):
        return TypeKind.STR

    if get_origin(t) is Literal:
        return TypeKind.LITERAL

    if isinstance(t, type) and issubclass(t, Enum):
        return TypeKind.ENUM

    if _is_dataclass_type(t) or _is_pydantic_model(t):
        return TypeKind.DATACLASS

    origin = get_origin(t)

    # union (X | Y | ...)
    if origin is Union or origin is types.UnionType:
        args = [a for a in get_args(t) if a is not type(None)]
        # all variants must be dataclasses with a shared Literal discriminator field
        if (
            all(_is_dataclass_type(a) or _is_pydantic_model(a) for a in args)
            and _get_discriminator_key(args) is not None
        ):
            return TypeKind.DISCRIMINATED_UNION

    if origin is list:
        return TypeKind.LIST

    return TypeKind.UNKNOWN


def get_field_infos(cls: type) -> list[FieldInfo]:
    """
    Return a FieldInfo for every field of a dataclass or Pydantic BaseModel.
    """
    result = []

    for rf in _get_raw_fields(cls):
        # unpack annotated
        bare_hint, form_hint, field_unit, annotated_extras = _extract_annotated_extras(
            rf.type_hint
        )

        # unwrap optional values
        optional, inner_hint = _unwrap_optional(bare_hint)

        # unpack annotated again, in case inner is also annotated
        inner_hint, inner_form_hint, inner_unit, inner_extras = (
            _extract_annotated_extras(inner_hint)
        )
        form_hint = form_hint or inner_form_hint
        field_unit = field_unit or inner_unit

        # combine metadata from Annotated + pydantic field metadata
        all_extras = annotated_extras + inner_extras + rf.metadata

        # get description
        description = rf.description
        if not description:
            for extra in all_extras:
                if hasattr(extra, "description") and extra.description:
                    description = extra.description
                    break

        # get default value
        default = rf.default
        if (
            default is dataclasses.MISSING
            and rf.default_factory is not dataclasses.MISSING
        ):
            try:
                default = rf.default_factory()
            except Exception:
                default = dataclasses.MISSING

        # get numerical constraints
        minimum, maximum = _extract_constraints(all_extras)

        # classify the inner type
        kind = classify_type(inner_hint)

        # get literal choices
        literal_choices = (
            list(get_args(inner_hint)) if kind is TypeKind.LITERAL else None
        )

        # resolve discriminated union variants - handles both single- and multi-variant cases
        pydantic_discriminator = next(
            (
                extra.discriminator
                for extra in all_extras
                if hasattr(extra, "discriminator") and extra.discriminator
            ),
            None,
        )

        if pydantic_discriminator and kind == TypeKind.DATACLASS:
            # single-variant discriminated union declared via Field(discriminator=...)
            kind = TypeKind.DISCRIMINATED_UNION
            variant_types = [inner_hint]
        elif kind is TypeKind.DISCRIMINATED_UNION:
            # multi-variant union: X | Y | ...
            variant_types = [a for a in get_args(inner_hint) if a is not type(None)]
        else:
            variant_types = []

        if variant_types:
            disc_key = (
                _get_discriminator_key(variant_types) or pydantic_discriminator or ""
            )
            union_variants = []
            for vt in variant_types:
                vt_hints = get_type_hints(vt, include_extras=False)
                disc_literal = vt_hints.get(disc_key)
                disc_value = get_args(disc_literal)[0]
                union_variants.append((disc_value, vt))
        else:
            union_variants = None

        result.append(
            FieldInfo(
                name=rf.name,
                label=field_name_to_label(rf.name),
                kind=kind,
                inner_type=inner_hint,
                default=default,
                description=description,
                optional=optional,
                hint=form_hint,
                unit=field_unit,
                minimum=minimum,
                maximum=maximum,
                literal_choices=literal_choices,
                union_variants=union_variants,
            )
        )

    return result
