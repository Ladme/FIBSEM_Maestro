# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from dataclasses import dataclass
from typing import Annotated

from fibsem_maestro.settings.form_utils import FieldUnit


@dataclass(frozen=True)
class Drift:
    """
    Represents a measured image drift along the x and y dimensions.

    Attributes:
        x: Drift along the x-axis in nanometers. None if undetermined.
        y: Drift along the y-axis in nanometers. None if undetermined.
        confidence: Confidence of the drift estimate in the range [0, 1].
            None if the estimator does not provide a confidence value.
    """

    x: Annotated[float | None, FieldUnit(suffix="nm")]
    y: Annotated[float | None, FieldUnit(suffix="nm")]
    confidence: float | None = None

    def is_valid(self) -> bool:
        """Check if the drift is fully defined in all dimensions."""
        return self.x is not None and self.y is not None
