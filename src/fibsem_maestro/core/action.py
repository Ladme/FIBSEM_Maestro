# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod

from fibsem_maestro.settings.base_settings import BaseSettings


class Action(ABC):
    @property
    @abstractmethod
    def settings(self) -> BaseSettings:
        pass
