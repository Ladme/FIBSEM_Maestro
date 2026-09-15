# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from dataclasses import dataclass, field

from fibsem_maestro.gui.form_builder._build_scope import BuildScope
from fibsem_maestro.gui.form_builder.widgets.union import DiscriminatedUnionWidget


@dataclass
class FollowerBinding:
    """
    A nested union whose variant is chosen by a field elsewhere in the form.

    Attributes:
        union: The inner union widget, built with its selector hidden.
        source_path: Dotted path to the driving field, relative to `scope`,
            resolved outward toward the form root.
        fallback: Discriminator value selected when the source holds a value
            matching no variant, or when the source cannot be resolved.
        field_name: Name of the union arm, used in warnings.
        scope: The scope of the union field.
        wired: True once the source subscription has been made.
    """

    union: DiscriminatedUnionWidget
    source_path: str
    fallback: str
    field_name: str
    scope: BuildScope
    wired: bool = False
    _active: bool = field(default=True, init=False, repr=False)

    @property
    def active(self) -> bool:
        """False once the union widget's C++ object has been destroyed."""
        return self._active

    def deactivate(self) -> None:
        """Stop pushing to a union whose underlying widget is gone."""
        self._active = False
