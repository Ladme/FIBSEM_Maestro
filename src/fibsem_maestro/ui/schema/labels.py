# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Display labels derived from Python names; shared by the schema, the forms and the views."""

import re


def field_name_to_label(name: str) -> str:
    """'stage_position' -> 'stage position'"""
    return name.replace("_", " ")


def class_name_to_label(name: str) -> str:
    """'StandardResolution' -> 'standard resolution'"""
    spaced = re.sub(r"(?<=[a-z])(?=[A-Z])", " ", name)
    return spaced.lower()
