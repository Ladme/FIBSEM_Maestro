# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class WidgetType(Enum):
    DROPDOWN = "dropdown"
    CHIPS = "chips"
    YAML_EDITOR = "yaml_editor"
    FILE_PATH = "file_path"
    DIRECTORY_PATH = "directory_path"
    RANGE_PAIR = "range_pair"


@dataclass
class FormHint:
    widget: WidgetType
    choices: Callable[[], list] | None = None
    file_filter: str | None = None


@dataclass
class FieldUnit:
    suffix: str
