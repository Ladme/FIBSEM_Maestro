# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint, WidgetType
from fibsem_maestro.settings.property_names import PropertyNames


class MillingSettings(BaseSettings):
    milling_area: Annotated[
        list[RelativeArea], FormHint(widget=WidgetType.AREA_SELECT, max_areas=1)
    ] = Field(
        default_factory=list,
        description="Area in which milling will be performed, defined in relative units.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ION,
        description="Beam used for milling.",
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Run the action every N-th slice. If not specified, the action will never run.",
    )
    pattern_file: Path | str = Field(
        default="",
        description="Configuration file containing definition of the pattern to use for milling.",
    )
    milling_depth: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0, description="Depth of the milling."
    )
    slice_distance: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="Thickness of each slice, i.e., distance to shift the pattern by after each milling step.",
    )
    milling_direction: Annotated[
        Direction,
        FormHint(
            widget=WidgetType.DROPDOWN, choices=lambda: [Direction.DOWN, Direction.UP]
        ),
    ] = Field(
        default=Direction.DOWN, description="Direction in which the slicing progresses."
    )
    properties_to_collect: PropertyNames = Field(
        default_factory=PropertyNames,
        description="Properties of the microscope and the beam relevant for milling.",
    )
    external_props: GlobalProperties = Field(
        default=GlobalProperties(),
        description="External properties of the microscope to use for milling. These properties will overwrite any current microscope properties.",
    )

    @field_validator("milling_direction")
    @classmethod
    def _validate_milling_direction(cls, v: Direction) -> Direction:
        if v not in (Direction.UP, Direction.DOWN):
            raise ValueError(f"milling_direction must be UP or DOWN, got {v!r}")
        return v
