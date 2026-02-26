# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod

from fibsem_maestro.settings.base_settings import BaseSettings


class SettingsForm(ABC):
    @abstractmethod
    def build(self) -> None:
        """
        Build the UI for the form.
        """

    @abstractmethod
    def get_settings(self) -> BaseSettings:
        """
        Get settings from the form.
        """
