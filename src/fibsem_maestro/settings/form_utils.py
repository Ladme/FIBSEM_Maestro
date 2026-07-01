# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum

from fibsem_maestro.action.action import Action


class WidgetType(Enum):
    DROPDOWN = "dropdown"
    MULTI_SELECT = "multi_select"
    PROPERTY_SELECTOR = "property_selector"
    MULTI_PROPERTY_SELECTOR = "multi_property_selector"
    AREA_SELECT = "area_select"
    RANGE_PAIR = "range_pair"
    DETAIL_BAND = "detail_band"
    STRING = "string"
    ACTION_SELECTOR = "action_selector"


@dataclass
class FormHint:
    widget: WidgetType
    choices: Callable[[], list[str]] | None = None
    file_filter: str | None = None
    max_areas: int | None = None
    action_type_filter: list[type[Action]] = field(default_factory=list)


@dataclass
class FieldUnit:
    suffix: str
