# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum


class WidgetType(Enum):
    DROPDOWN = "dropdown"
    MULTI_SELECT = "multi_select"
    PROPERTY_SELECTOR = "property_selector"
    MULTI_PROPERTY_SELECTOR = "multi_property_selector"
    AREA_SELECT = "area_select"
    RANGE_PAIR = "range_pair"


@dataclass
class FormHint:
    widget: WidgetType
    choices: Callable[[], list[str]] | None = None
    file_filter: str | None = None
    max_areas: int | None = None


@dataclass
class FieldUnit:
    suffix: str
