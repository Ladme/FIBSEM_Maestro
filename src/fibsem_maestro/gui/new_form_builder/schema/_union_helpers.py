# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from functools import cache
from typing import Literal, get_args, get_origin, get_type_hints

from fibsem_maestro.gui.new_form_builder.schema._annotated import split_annotated
from fibsem_maestro.gui.new_form_builder.schema._extraction import get_raw_fields
from fibsem_maestro.gui.new_form_builder.schema.field_type import (
    DiscriminatedUnionType,
    UnionVariant,
)


@cache
def _discriminator_key_cached(variant_types: tuple[type, ...]) -> str | None:
    """Cached core of `_get_discriminator_key` (keyed on a hashable tuple)."""
    # look for a Literal field on the first variant...
    for rf in get_raw_fields(variant_types[0]):
        if get_origin(split_annotated(rf.type_hint).bare) is not Literal:
            continue
        # ...that also appears as a Literal field, by the same name, on every other variant
        # that field is the discriminator
        if all(
            any(
                get_origin(split_annotated(rf2.type_hint).bare) is Literal
                and rf2.name == rf.name
                for rf2 in get_raw_fields(v)
            )
            for v in variant_types[1:]
        ):
            return rf.name
    return None


def get_discriminator_key(variant_types: list[type]) -> str | None:
    """
    Find the shared `Literal` field that discriminates a union.

    A tagged union is recognised by a field that is a `Literal` in every
    variant and carries the same name across all of them.

    Args:
        variant_types: The candidate variant classes.

    Returns:
        The discriminator field name, or `None` if none is shared.
    """
    return _discriminator_key_cached(tuple(variant_types))


def discriminator_value(variant: type, key: str) -> str:
    """Read a variant's concrete tag value from its `Literal` annotation."""
    literal = get_type_hints(variant, include_extras=False).get(key)
    # the Literal's first argument is this variant's tag value
    return get_args(literal)[0]


def make_union(variants: tuple[type, ...], key: str) -> DiscriminatedUnionType:
    """Build a `DiscriminatedUnionType` from variants and a known key."""
    return DiscriminatedUnionType(
        discriminator_key=key,
        variants=tuple(
            UnionVariant(discriminator_value(vt, key), vt) for vt in variants
        ),
    )
