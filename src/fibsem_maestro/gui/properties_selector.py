# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import cast

from nicegui import ui

from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.property_names import PropertyNames


class PropertiesSelector:
    def __init__(self, microscope: Microscope):
        property_names = microscope.get_property_names()

        with ui.card().classes("w-full"):
            ui.label("Properties to save").classes("text-lg font-bold")

            with ui.column().classes("w-full gap-4"):
                self.microscope = (
                    ui.select(
                        property_names.microscope,
                        with_input=True,
                        multiple=True,
                        label="microscope",
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                )

                self.electron_beam = (
                    ui.select(
                        property_names.electron_beam,
                        with_input=True,
                        multiple=True,
                        label="electron beam",
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                )

                self.ion_beam = (
                    ui.select(
                        property_names.ion_beam,
                        with_input=True,
                        multiple=True,
                        label="ion beam",
                    )
                    .classes("min-w-[16rem] max-w-[48rem] flex-grow")
                    .props("use-chips")
                )

    @property
    def props(self) -> PropertyNames:
        return PropertyNames(
            microscope=cast("list[str]", self.microscope.value),
            electron_beam=cast("list[str]", self.electron_beam.value),
            ion_beam=cast("list[str]", self.ion_beam.value),
        )
