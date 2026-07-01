# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class RawField:
    """
    A single field as read directly from a model, before interpretation.

    Attributes:
        name: The field's attribute name.
        type_hint: The raw annotation, with `Annotated[]` still intact.
        default: The default value, or `dataclasses.MISSING` if none.
        default_factory: The default factory, or `dataclasses.MISSING` if none.
        description: A description, or `""` if none.
        metadata: Extra constraint carriers (e.g. `annotated_types` bounds).
    """

    name: str
    type_hint: Any
    default: Any
    default_factory: Any
    description: str
    metadata: tuple
