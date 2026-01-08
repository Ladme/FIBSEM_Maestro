# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

from fibsem_maestro.autofunctions.sweep_step import SweepStep


@dataclass(frozen=True)
class AutofocusResult:
    resolution: float
    sweep: SweepStep
