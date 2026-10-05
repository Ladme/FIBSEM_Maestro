# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from dataclasses import dataclass
from typing import TypeAlias

from fibsem_maestro.properties.global_properties import GlobalProperties


@dataclass(frozen=True)
class Produced:
    """
    The action ran and produced new properties for the next slice.

    Attributes:
        props: The properties written to the action's next-slice store. These
            are also the only source for propagation to dependent actions.
    """

    props: GlobalProperties


@dataclass(frozen=True)
class CarriedOver:
    """
    The action produced nothing new for the next slice.

    Its current properties were copied to the next slice unchanged, and
    nothing is propagated to dependents.

    Attributes:
        reason: Human-readable reason, for logging.
    """

    reason: str


StepOutcome: TypeAlias = Produced | CarriedOver
