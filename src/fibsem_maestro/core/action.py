# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod


class Action(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the action.
        """
