# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass


@dataclass(frozen=True)
class SweepStep:
    """
    A single step in a parameter sweep.

    Attributes:
        repetition: Zero-based index of the sweep cycle this step belongs to.
        value: The beam attribute value to apply at this step.
        index: Global sequential index of this step across all cycles.
        line_index: Row index of this step in the acquired image, used by
            line autofocus to map sharpness results back to their position
            in the image for logging. `None` for modes that do not operate
            on individual image rows.
    """

    repetition: int
    value: float
    index: int
    line_index: int | None = None
