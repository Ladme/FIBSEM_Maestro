# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Links between actions and action names.

A link is a top-level settings field edited with an action selector
(`WidgetType.ACTION_SELECTOR`); it holds the name of another action.
"""

from collections.abc import Iterator
from dataclasses import dataclass

from fibsem_maestro.action.action import Action
from fibsem_maestro.settings.form_utils import WidgetType
from fibsem_maestro.ui.schema.schema import get_field_infos


@dataclass(frozen=True)
class ActionLink:
    """
    One link field of a settings object.

    Attributes:
        field_name: Name of the settings field holding the linked action's name.
        allowed_types: Action classes the link may name.
        optional: True if the field may hold None (no link).
    """

    field_name: str
    allowed_types: tuple[type[Action], ...]
    optional: bool


def iter_links(settings: object) -> Iterator[ActionLink]:
    """
    Yield the link fields of a settings object, in declaration order.

    Only top-level fields are links; nested objects are not searched.

    Args:
        settings: A settings object (pydantic model or dataclass).

    Yields:
        One `ActionLink` per action-selector field.
    """
    for fi in get_field_infos(type(settings)):
        if fi.hint is None or fi.hint.widget is not WidgetType.ACTION_SELECTOR:
            continue
        yield ActionLink(
            field_name=fi.name,
            allowed_types=tuple(fi.hint.action_type_filter),
            optional=fi.optional,
        )


def retarget_links(settings: object, old_name: str, new_name: str) -> list[str]:
    """
    Point every link holding `old_name` at `new_name`.

    The fields are assigned on `settings` itself, so its change hooks fire.

    Args:
        settings: A settings object (pydantic model or dataclass).
        old_name: The renamed action's previous name.
        new_name: Its new name.

    Returns:
        The names of the fields that were changed, in declaration order.
    """
    changed: list[str] = []
    for link in iter_links(settings):
        if getattr(settings, link.field_name) == old_name:
            setattr(settings, link.field_name, new_name)
            changed.append(link.field_name)
    return changed


def validate_action_name(name: str, existing_names: set[str]) -> str | None:
    """
    Validate a candidate action name against existing names.

    Names are compared ignoring case, with spaces and underscores treated as
    equal, because such names map to the same action directory on a
    case-insensitive filesystem (Windows). The reserved name "workflow" (the
    workflow's own directory) is compared the same way.

    Args:
        name: The candidate name to validate.
        existing_names: Names already in use (excluding the name being edited, if any).

    Returns:
        An error message if invalid, or None if valid.
    """
    if not name:
        return "Name cannot be empty."
    key = _directory_key(name)
    if any(key == _directory_key(existing) for existing in existing_names):
        return f"Name '{name}' is already in use."
    if key == "workflow":
        return "Name 'workflow' is reserved."
    return None


def _directory_key(name: str) -> str:
    """The form of an action name under which two names share a directory."""
    return name.lower().replace(" ", "_")
