# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


def field_name_to_label(name: str) -> str:
    """'stage_position' -> 'stage position'"""
    return name.replace("_", " ")


def class_name_to_label(name: str) -> str:
    """'StandardResolution' -> 'standard resolution'"""
    import re

    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return spaced.lower()


def validate_action_name(name: str, existing_names: set[str]) -> str | None:
    """
    Validate a candidate action name against existing names.

    Args:
        name: The candidate name to validate.
        existing_names: Names already in use (excluding the name being edited, if any).

    Returns:
        An error message if invalid, or None if valid.
    """
    if not name:
        return "Name cannot be empty."
    if any(
        name.lower().replace(" ", "_") == existing.lower().replace(" ", "_")
        for existing in existing_names
    ):
        return f"Name '{name}' is already in use."
    if name == "workflow":
        return "Name 'workflow' is reserved."
    return None
