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
