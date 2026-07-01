# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import dataclasses

from fibsem_maestro.gui.new_form_builder.schema._raw_field import RawField
from fibsem_maestro.gui.new_form_builder.schema.default import Default


def pydantic_discriminator(extras: tuple) -> str | None:
    """Return a `Field(discriminator=...)` name from metadata, if present."""
    return next(
        (e.discriminator for e in extras if getattr(e, "discriminator", None)),
        None,
    )


def resolve_description(rf: RawField, extras: tuple) -> str:
    """Prefer the model-provided description, else the first metadata carrier."""
    if rf.description:
        return rf.description
    for extra in extras:
        description = getattr(extra, "description", None)
        if description:
            return description
    return ""


def resolve_default(rf: RawField) -> Default | None:
    """Resolve a field's default. Returns ``None`` when the field has no default."""
    if rf.default is not dataclasses.MISSING:
        return Default(rf.default)
    if rf.default_factory is not dataclasses.MISSING:
        try:
            return Default(rf.default_factory())
        except Exception:
            # default factory failed; treat as no default
            return None
    return None
