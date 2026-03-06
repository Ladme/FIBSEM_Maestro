# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod

from fibsem_maestro.store.props.props_store import PropsStore


class Action(ABC):
    @abstractmethod
    def save_properties(self, store: PropsStore | None = None) -> None:
        """
        Collect and save the properties of the microscope.
        """
