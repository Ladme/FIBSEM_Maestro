# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Annotated

from pydantic import Field, field_validator

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction


class MillingSettings(BaseSettings):
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

    @field_validator("milling_direction")
    @classmethod
    def _validate_milling_direction(cls, v: Direction) -> Direction:
        if v not in (Direction.UP, Direction.DOWN):
            raise ValueError(f"milling_direction must be UP or DOWN, got {v!r}")
        return v
