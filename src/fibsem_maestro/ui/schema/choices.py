# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
The values a choice editor offers for a field.

Shared by the field editors and the settings audit, so that "which values can
this editor show" has a single definition.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.pattern_type import PatternType
from fibsem_maestro.settings.form_utils import WidgetType
from fibsem_maestro.ui.schema.field_info import FieldInfo
from fibsem_maestro.ui.schema.field_type import EnumType, LiteralType

CHOICE_WIDGETS: frozenset[WidgetType] = frozenset(
    {
        WidgetType.DROPDOWN,
        WidgetType.PROPERTY_SELECTOR,
        WidgetType.PATTERN_TYPE_SELECTOR,
        WidgetType.ACTION_SELECTOR,
        WidgetType.MULTI_SELECT,
        WidgetType.MULTI_PROPERTY_SELECTOR,
    }
)
"""Hinted widgets whose values come from `choices_for`."""


@dataclass(frozen=True)
class ChoiceContext:
    """
    What choice lists depend on beyond the field itself.

    Attributes:
        actions: The workflow's actions, or None outside a workflow.
        manufacturer_property_names: Extra property names offered by the microscope.
        pattern_types: Milling pattern types offered by the microscope.
    """

    actions: Sequence[Action] | None = None
    manufacturer_property_names: tuple[str, ...] = ()
    pattern_types: tuple[PatternType, ...] = field(default_factory=tuple)


def has_choices(fi: FieldInfo) -> bool:
    """
    Whether `choices_for` applies to the field.

    Args:
        fi: The field.

    Returns:
        True for the hinted choice widgets and for Enum and Literal fields.
    """
    if fi.hint is not None:
        return fi.hint.widget in CHOICE_WIDGETS
    return isinstance(fi.type, EnumType | LiteralType)


def choices_for(fi: FieldInfo, ctx: ChoiceContext) -> list[Any]:
    """
    The values an editor of `fi` offers, without "(none)".

    Args:
        fi: The field.
        ctx: The workflow and microscope context.

    Returns:
        The choices, in the order the editor lists them.

    Raises:
        ValueError: If the field is not a choice field (see `has_choices`).
    """
    hint = fi.hint
    if hint is not None:
        listed = hint.choices() if hint.choices else []
        match hint.widget:
            case WidgetType.DROPDOWN | WidgetType.MULTI_SELECT:
                return list(listed)
            case WidgetType.PROPERTY_SELECTOR | WidgetType.MULTI_PROPERTY_SELECTOR:
                return list(listed) + list(ctx.manufacturer_property_names)
            case WidgetType.PATTERN_TYPE_SELECTOR:
                return list(ctx.pattern_types)
            case WidgetType.ACTION_SELECTOR:
                allowed = tuple(hint.action_type_filter)
                return [
                    action.name
                    for action in ctx.actions or ()
                    if isinstance(action, allowed)
                ]
            case _:
                raise ValueError(f"field {fi.name!r} is not a choice field")

    match fi.type:
        case EnumType(enum_type=enum_cls):
            return list(enum_cls)
        case LiteralType(choices=choices):
            return list(choices)
        case _:
            raise ValueError(f"field {fi.name!r} is not a choice field")
