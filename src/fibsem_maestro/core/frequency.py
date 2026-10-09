# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from abc import ABC, abstractmethod
from typing import Annotated, Literal, TypeAlias

from pydantic import Field

from fibsem_maestro.settings.base_settings import BaseSettings


class _FrequencyBase(BaseSettings, ABC):
    """Behaviour shared by every frequency variant."""

    @abstractmethod
    def matches(self, slice_index: int) -> bool:
        """
        Check whether the action runs on a slice.

        Args:
            slice_index: The slice index; the first acquired slice is 1.

        Returns:
            `True` if the action runs on this slice.
        """

    @property
    @abstractmethod
    def runs_every_slice(self) -> bool:
        """`True` if the action runs on every slice."""


class Never(_FrequencyBase):
    """The action never runs."""

    type: Literal["never"] = Field(
        default="never", description="Do not run this action."
    )

    def matches(self, slice_index: int) -> bool:
        _ = slice_index
        return False

    @property
    def runs_every_slice(self) -> bool:
        return False

    def __str__(self) -> str:
        return "never"


class Every(_FrequencyBase):
    """The action runs every n-th slice, starting with the first."""

    type: Literal["every"] = Field(
        default="every",
        description="Run this action every n-th slice, starting with the first.",
    )
    n: Annotated[int, Field(gt=0)] = Field(
        default=1,
        description="Interval in slices; 1 runs the action on every slice.",
    )

    def matches(self, slice_index: int) -> bool:
        return (slice_index - 1) % self.n == 0

    @property
    def runs_every_slice(self) -> bool:
        return self.n == 1

    def __str__(self) -> str:
        return "every slice" if self.n == 1 else f"every {self.n} slices"


Frequency: TypeAlias = Annotated[Every | Never, Field(discriminator="type")]
"""How often an action runs, counted in slices from 1."""
