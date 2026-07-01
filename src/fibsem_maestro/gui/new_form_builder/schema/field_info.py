# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

from fibsem_maestro.gui.new_form_builder.schema.constraints import NumericBounds
from fibsem_maestro.gui.new_form_builder.schema.default import Default
from fibsem_maestro.gui.new_form_builder.schema.field_type import FieldType
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint


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
