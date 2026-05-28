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
from fibsem_maestro.settings.property_names import PropertyNames


class MillingSettings(BaseSettings):
    properties_file: Path = Field(
        default=Path("milling_props.yaml"),
        description="Path to a file storing properties of the microscope used for milling.",
    )
    state_file: Path = Field(
        default=Path("milling_state.yaml"),
        description="Path to a file where the state of the milling process is stored.",
    )
    beam_type: BeamType = Field(
        default=BeamType.ION,
        description="Beam used for milling.",
    )
    milling_area: RelativeArea = Field(
        description="Area in which milling will be performed, defined in relative units."
    )
    execution_frequency: Annotated[int, Field(gt=0)] | None = Field(
        default=1,
        description="Milling runs every N-th slice. If None, milling will never run.",
    )
    milling_depth: float = Field(description="Depth of the milling [in nm].")
    slice_distance: float = Field(
        description="Thickness of each slice, i.e., distance to shift the pattern by after each milling step [in nm]."
    )
    pattern_file: Path | str = Field(
        description="Configuration file containing definition of the pattern to use for milling."
    )
    milling_direction: Direction = Field(
        description="Direction in which the slicing progresses. Either `up` or `down`."
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
