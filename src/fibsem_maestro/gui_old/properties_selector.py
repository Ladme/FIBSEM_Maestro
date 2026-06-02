# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from nicegui import ui

from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames


class PropertiesSelector:
    def __init__(self, microscope: Microscope, properties: PropertyNames):
        """
        Initialize PropertiesSelector.

        Args:
            microscope: The Microscope instance to get available properties from.
            properties: PropertyNames object to be modified by the user's selections.
        """
        self._properties = properties
        property_names = microscope.prop_names

        with ui.column().classes("w-full"):
            ui.label("Properties to save").classes("font-bold")

            with ui.column().classes("w-full gap-4"):
                self.microscope = (
                    ui.select(
                        property_names.microscope,
                        with_input=True,
                        multiple=True,
                        label="microscope",
                        value=properties.microscope,
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                    .on_value_change(lambda e: self._update_microscope(e.value))
                )

                self.electron_beam = (
                    ui.select(
                        property_names.electron_beam,
                        with_input=True,
                        multiple=True,
                        label="electron beam",
                        value=properties.electron_beam,
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                    .on_value_change(lambda e: self._update_electron_beam(e.value))
                )

                self.ion_beam = (
                    ui.select(
                        property_names.ion_beam,
                        with_input=True,
                        multiple=True,
                        label="ion beam",
                        value=properties.ion_beam,
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                    .on_value_change(lambda e: self._update_ion_beam(e.value))
                )

    def _update_microscope(self, value: list[str]) -> None:
        """
        Update microscope properties.

        Args:
            value: List of selected microscope properties.
        """
        self._properties.microscope = value

    def _update_electron_beam(self, value: list[str]) -> None:
        """
        Update electron beam properties.

        Args:
            value: List of selected electron beam properties.
        """
        self._properties.electron_beam = value

    def _update_ion_beam(self, value: list[str]) -> None:
        """
        Update ion beam properties.

        Args:
            value: List of selected ion beam properties.
        """
        self._properties.ion_beam = value
