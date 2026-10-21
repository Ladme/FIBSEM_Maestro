# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Everything the forms need to know about one field of a settings class."""

from dataclasses import dataclass

from fibsem_maestro.settings.form_utils import FieldUnit, FormHint
from fibsem_maestro.ui.schema.constraints import NumericBounds
from fibsem_maestro.ui.schema.default import Default
from fibsem_maestro.ui.schema.field_type import FieldType


@dataclass(frozen=True)
class FieldInfo:
    """
    A fully interpreted field, ready for the form builder.

    Attributes:
        name: The field's attribute name.
        label: A display label derived from `name`.
        description: A description, or `""` if none.
        optional: True when the field accepts `None`.
        default: The default, or `None` if the field has none.
        hint: A `FormHint` from `Annotated[]`, if present.
        unit: A `FieldUnit` from `Annotated[]`, if present.
        bounds: Numeric constraints, or `None` if unconstrained.
        type: The kind-specific descriptor.
    """

    name: str
    label: str
    description: str
    optional: bool
    default: Default | None
    hint: FormHint | None
    unit: FieldUnit | None
    bounds: NumericBounds | None
    type: FieldType
