# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from dataclasses import dataclass
from enum import Enum
from typing import Any


class FieldType:
    """
    Base of the sealed set of field-type descriptors.
    """


@dataclass(frozen=True)
class BoolType(FieldType):
    """A boolean field."""


@dataclass(frozen=True)
class IntType(FieldType):
    """An integer field."""


@dataclass(frozen=True)
class FloatType(FieldType):
    """A float field."""


@dataclass(frozen=True)
class StrType(FieldType):
    """A string or filesystem-path field."""


@dataclass(frozen=True)
class EnumType(FieldType):
    """
    An `enum.Enum``field.

    Attributes:
        enum_type: The concrete `Enum` subclass; its members are the choices.
    """

    enum_type: type[Enum]


@dataclass(frozen=True)
class LiteralType(FieldType):
    """
    A `Literal[...]` field.

    Attributes:
        choices: The allowed values, non-empty by construction.
    """

    choices: tuple[Any, ...]


@dataclass(frozen=True)
class DataclassType(FieldType):
    """
    A nested dataclass or Pydantic model field.

    Attributes:
        model: The nested model class to recurse into.
    """

    model: type


@dataclass(frozen=True)
class UnionVariant:
    """
    One arm of a discriminated union.

    Attributes:
        discriminator_value: The tag value that selects this variant.
        variant_type: The model class for this variant.
    """

    discriminator_value: str
    variant_type: type


@dataclass(frozen=True)
class DiscriminatedUnionType(FieldType):
    """
    A tagged union of models sharing a `Literal` discriminator field.

    Attributes:
        discriminator_key: The name of the shared discriminator field.
        variants: The union arms, non-empty by construction.
    """

    discriminator_key: str
    variants: tuple[UnionVariant, ...]


@dataclass(frozen=True)
class ListType(FieldType):
    """
    A homogeneous `list[...]` field.

    Attributes:
        item: The descriptor for the element type.
    """

    item: FieldType


@dataclass(frozen=True)
class FloatTupleType(FieldType):
    """
    A fixed-length tuple of floats, e.g. `tuple[float, float]`.

    Attributes:
        length: The number of float elements.
    """

    length: int


@dataclass(frozen=True)
class UnknownType(FieldType):
    """
    Anything without a dedicated widget.

    Attributes:
        hint: The original (unwrapped) type hint, kept for diagnostics.
    """

    hint: Any


SCALAR_TYPES: tuple[type[FieldType], ...] = (
    BoolType,
    IntType,
    FloatType,
    StrType,
    EnumType,
    LiteralType,
)


def is_scalar(field_type: FieldType) -> bool:
    """Return True if ``field_type`` is a scalar (leaf) descriptor."""
    return isinstance(field_type, SCALAR_TYPES)
