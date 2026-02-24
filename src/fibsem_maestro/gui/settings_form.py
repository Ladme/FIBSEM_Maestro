# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from nicegui import ui

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.gui.properties_selector import PropertiesSelector
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)


class ImagingSettingsForm:
    """Simple form for ImagingSettings."""

    def __init__(
        self,
        instance: ImagingSettings,
        microscope: Microscope,
    ):
        self.instance = instance
        self.microscope = microscope
        self.widgets = {}
        self.properties_selector = None
        self.build()

    def build(self):
        """Build the form UI."""
        with ui.card().classes("w-full"):
            ui.label("Imaging Settings").classes("text-lg font-bold mb-4")

            with ui.column().classes("w-full gap-4"):
                # properties file path
                self.widgets["properties_file"] = ui.input(
                    label="Properties File",
                    value=str(self.instance.properties_file),
                ).classes("w-full")

                # images directory path
                self.widgets["images_directory"] = ui.input(
                    label="Images Directory",
                    value=str(self.instance.images_directory),
                ).classes("w-full")

                # beam type
                self.widgets["beam_type"] = ui.select(
                    {e.value: e.value for e in BeamType},
                    label="Beam Type",
                    value=self.instance.beam_type.value,
                ).classes("w-full")

                # bit depth
                self.widgets["bit_depth"] = ui.number(
                    label="Bit Depth",
                    value=self.instance.bit_depth or 0,
                    step=1,
                ).classes("w-full")

                # resolution mode
                self._build_resolution_mode()

                # properties selector
                self.properties_selector = PropertiesSelector(self.microscope)

    def _build_resolution_mode(self):
        """Build resolution mode radio with conditional extended fields."""
        current_mode = self.instance.resolution_mode
        is_extended = isinstance(current_mode, ExtendedResolution)

        ui.label("Resolution Mode").classes("font-semibold mt-4")

        self.widgets["resolution_radio"] = ui.radio(
            {
                "standard": "Standard",
                "extended": "Extended",
            },
            value="extended" if is_extended else "standard",
        ).classes("gap-2")

        # container for extended fields
        self.widgets["extended_container"] = ui.column().classes(
            "w-full gap-3 pl-4 mt-2"
        )

        # draw extended fields initially if needed
        self._update_resolution_fields()

        # update on radio change
        self.widgets["resolution_radio"].on_value_change(self._update_resolution_fields)

    def _update_resolution_fields(self):
        """Update displayed fields based on resolution mode selection."""
        container = self.widgets["extended_container"]
        container.clear()

        if self.widgets["resolution_radio"].value == "extended":
            current_mode = self.instance.resolution_mode
            pixel_size = 0.0
            if isinstance(current_mode, ExtendedResolution):
                pixel_size = current_mode.pixel_size

            with container:
                self.widgets["pixel_size"] = ui.number(
                    label="Pixel Size (nm)",
                    value=pixel_size,
                    step=0.1,
                ).classes("w-full")

    def get_values(self) -> ImagingSettings:
        """Extract form values and return ImagingSettings instance."""
        # get basic fields
        properties_file = Path(self.widgets["properties_file"].value)
        images_directory = Path(self.widgets["images_directory"].value)
        beam_type = BeamType(self.widgets["beam_type"].value)
        bit_depth = int(self.widgets["bit_depth"].value) or None

        # get properties from selector
        assert self.properties_selector is not None
        properties = self.properties_selector.props

        # get resolution mode
        if self.widgets["resolution_radio"].value == "standard":
            resolution_mode = StandardResolution()
        else:
            pixel_size = self.widgets["pixel_size"].value
            resolution_mode = ExtendedResolution(pixel_size=pixel_size)

        return ImagingSettings(
            properties_file=properties_file,
            images_directory=images_directory,
            properties_to_collect=properties,
            resolution_mode=resolution_mode,
            beam_type=beam_type,
            bit_depth=bit_depth,
        )
