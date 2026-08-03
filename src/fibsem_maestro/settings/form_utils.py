# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

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


class AreaOverlay(Enum):
    """Optional, display-only decoration drawn over every acquisition area."""

    SHOW_MARGIN = "show_margin"
    SHOW_DIRECTION = "show_direction"

    @property
    def data_field(self) -> str:
        """Name of the `OverlayData` attribute this overlay reads from."""
        return {
            AreaOverlay.SHOW_MARGIN: "margin_nm",
            AreaOverlay.SHOW_DIRECTION: "direction",
        }[self]


@dataclass
class FormHint:
    widget: WidgetType
    choices: Callable[[], list[str]] | None = None
    file_filter: str | None = None
    max_areas: int | None = None
    action_type_filter: list[type[Action]] = field(default_factory=list)
    area_overlay: AreaOverlay | None = None
    # sibling field name feeding the overlay
    overlay_source: str | None = None


@dataclass
class FieldUnit:
    suffix: str
