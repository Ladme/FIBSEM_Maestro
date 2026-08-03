# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Default:
    """
    A resolved default value.

    Absence of a default is represented by `None` at the use site (`default: Default | None`).

    Attributes:
        value: The default value (may itself be `None`).
    """

    value: Any
