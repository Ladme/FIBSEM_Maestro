# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import Annotated

from pydantic import Field

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.base_settings import BaseSettings
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.lens_alignment import LensAlignment
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.source_tilt import SourceTilt
from fibsem_maestro.core.stigmator import Stigmator


class BeamProperties(BaseSettings):
    model_config = {"extra": "allow"}

    stigmator: Stigmator | None = Field(
        default=None,
        description="Stigmator settings for beam correction.",
    )

    stigmator_x: float | None = Field(
        default=None,
        description="Stigmator in the x-dimension.",
    )

    stigmator_y: float | None = Field(
        default=None,
        description="Stigmator in the y-dimension.",
    )

    lens_alignment: LensAlignment | None = Field(
        default=None,
        description="Alignment of lens in the microscope (in nanometers).",
    )

    lens_alignment_x: float | None = Field(
        default=None,
        description="Alignment of lens in the microscope along the x-dimension (in nanometers).",
    )

    lens_alignment_y: float | None = Field(
        default=None,
        description="Alignment of lens in the microscope along the y-dimension (in nanometers).",
    )

    beam_shift: BeamShift | None = Field(
        default=None,
        description="Beam shift settings (in nanometers).",
    )

    detector_contrast: float | None = Field(
        default=None,
        description="Contrast level of the detector.",
    )

    detector_brightness: float | None = Field(
        default=None,
        description="Brightness level of the detector.",
    )

    source_tilt: SourceTilt | None = Field(
        default=None,
        description="Tilt settings for the electron source (in degrees).",
    )

    line_integration: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description="Number of line integrations per scan.",
    )

    dwell_time: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Dwell time per pixel in seconds.",
    )

    bit_depth: Annotated[int, Field(gt=0)] | None = Field(
        default=None,
        description="Bit depth of the detector output.",
    )

    resolution: Resolution | None = Field(
        default=None,
        description="Resolution of the scan in pixels.",
    )

    horizontal_field_width: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Horizontal field of view in nanometers.",
    )

    vertical_field_width: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Vertical field of view in nanometers.",
    )

    pixel_size: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
        description="Physical size of a pixel in nanometers.",
    )

    scanning_area: RelativeArea | None = Field(
        default=None,
        description="Area to be scanned.",
    )

    working_distance: Annotated[float, Field(gt=0)] | None = Field(
        default=None,
    )

    def get_property_names(self) -> list[str]:
        """
        Return a list of all property names that are not None.

        Returns:
            list[str]: List of property names.
        """
        return [
            name for name in type(self).model_fields if getattr(self, name) is not None
        ]
