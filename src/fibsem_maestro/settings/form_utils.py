# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

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
    PATTERN_TYPE_SELECTOR = "pattern_type_selector"


class AreaOverlay(Enum):
    """Optional, display-only decoration drawn over every acquisition area."""

    SHOW_MARGIN = "show_margin"
    SHOW_DIRECTION = "show_direction"
    SHOW_TILES = "show_tiles"
    SHOW_AREA_SHIFT = "show_area_shift"

    @property
    def data_fields(self) -> frozenset[str]:
        """Names of the `OverlayData` attributes this overlay reads from."""
        return {
            AreaOverlay.SHOW_MARGIN: frozenset({"margin_nm"}),
            AreaOverlay.SHOW_DIRECTION: frozenset({"direction"}),
            AreaOverlay.SHOW_TILES: frozenset(
                {"tile_size_nm", "tile_relative_overlap"}
            ),
            AreaOverlay.SHOW_AREA_SHIFT: frozenset({"shift_distance_nm", "direction"}),
        }[self]


@dataclass(frozen=True)
class OverlaySpec:
    """
    One decoration to draw over an area selector, and where its values come from.

    Attributes:
        kind: Which decoration to draw.
        sources: `(OverlayData attribute, dotted field path)` pairs. Paths are
            resolved against the settings object declaring the hint, then
            outward toward the form root; the innermost match wins. An
            unresolved or None-valued source leaves that attribute None, which
            suppresses this decoration without affecting the others on the
            same field.
        requires: `(dotted path, required type)` pairs that must all hold in the
            live settings for this decoration to be drawn.

    """

    kind: AreaOverlay
    sources: tuple[tuple[str, str], ...] = ()
    requires: tuple[tuple[str, type], ...] = ()

    def __post_init__(self) -> None:
        names = [name for name, _ in self.sources]
        if unknown := set(names) - self.kind.data_fields:
            raise ValueError(
                f"{self.kind.name} does not read {sorted(unknown)}; "
                f"it reads {sorted(self.kind.data_fields)}"
            )
        if len(names) != len(set(names)):
            raise ValueError(f"{self.kind.name} has duplicate overlay sources")

    @classmethod
    def of(
        cls,
        kind: AreaOverlay,
        requires: Mapping[str, type] | None = None,
        **paths: str,
    ) -> OverlaySpec:
        """
        Build a spec from keyword sources.

        Args:
            kind: Which decoration to draw.
            requires: Dotted path to required type, e.g.
                `{"tiling_mode": MultiTileMode}`.
            **paths: `OverlayData` attribute name to dotted field path.

        Returns:
            The spec.
        """
        return cls(kind, tuple(paths.items()), tuple((requires or {}).items()))


@dataclass
class FormHint:
    widget: WidgetType
    choices: Callable[[], list[str]] | None = None
    file_filter: str | None = None
    max_areas: int | None = None
    action_type_filter: list[type[Action]] = field(default_factory=list)
    overlays: tuple[OverlaySpec, ...] = ()
    # field name feeding the beam source
    beam_source: str | None = None


@dataclass
class FieldUnit:
    suffix: str
