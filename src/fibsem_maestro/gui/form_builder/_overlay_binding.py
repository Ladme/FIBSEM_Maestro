from dataclasses import dataclass

from fibsem_maestro.gui.form_builder._build_scope import BuildScope
from fibsem_maestro.gui.form_builder.widgets.area_select.widget import AreaSelectWidget
from fibsem_maestro.gui.form_builder.widgets.base import BaseWidget
from fibsem_maestro.settings.form_utils import OverlaySpec


@dataclass
class OverlayBinding:
    """
    An area selector's overlays, awaiting or holding a live subscription.

    Attributes:
        area: The area selector the decorations are drawn on.
        area_path: Dotted path of the declaring field, or None if unaddressable.
        field_name: The declaring field's name, for log messages.
        specs: The overlays declared on that field.
        scope: Scope of the declaring object; source paths resolve from here.
        siblings: The declaring object's widgets by field name. Held live so
            sibling lookup works in subtrees that have no address.
        wired: True once source subscriptions have been made.
        active: False once the area widget is gone; pushes become no-ops.
    """

    area: AreaSelectWidget
    area_path: str | None
    field_name: str
    specs: tuple[OverlaySpec, ...]
    scope: BuildScope
    siblings: dict[str, BaseWidget]
    wired: bool = False
    active: bool = True

    def deactivate(self, *_: object) -> None:
        """Stop this binding from touching its area widget."""
        self.active = False
