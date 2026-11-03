# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from dataclasses import dataclass

# Pydantic evaluates this dataclass's annotations (it is a field of AutofocusState)
from fibsem_maestro.autofocus.sweep_step import SweepStep  # noqa: TC001


@dataclass(frozen=True)
class AutofocusResult:
    sharpness: float
    sweep: SweepStep
