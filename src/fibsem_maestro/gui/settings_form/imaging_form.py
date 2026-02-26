# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import Any

from nicegui import ui

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.gui.area_selector import AreaSelector
from fibsem_maestro.gui.properties_selector import PropertiesSelector
from fibsem_maestro.gui.settings_form.settings_form import SettingsForm
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import (
    ExtendedResolution,
    ImagingSettings,
    StandardResolution,
)


class ImagingForm(SettingsForm):
    """Simple form for ImagingSettings with real-time instance updates."""

    def __init__(
        self,
        instance: ImagingSettings,
        microscope: Microscope,
    ):
        self.instance = instance
        self.microscope = microscope
        self.widgets = {}
        self.properties_selector = None
        self._area_selector = AreaSelector(
            self.microscope.beam.get_image(), max_areas=1
        )

    def build(self):
        with ui.card().classes("w-full"):
            ui.label("Imaging Settings").classes("text-lg font-bold mb-4")

            with ui.column().classes("w-full gap-4"):
                # properties file path
                self.widgets["properties_file"] = (
                    ui.input(
                        label="Properties file",
                        value=str(self.instance.properties_file),
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field("properties_file", Path(v.value))
                    )
                )

                # images directory path
                self.widgets["images_directory"] = (
                    ui.input(
                        label="Images directory",
                        value=str(self.instance.images_directory),
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field("images_directory", Path(v.value))
                    )
                )

                # beam type
                self.widgets["beam_type"] = (
                    ui.select(
                        {e.value: e.value for e in BeamType},
                        label="Beam type",
                        value=self.instance.beam_type.value,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field("beam_type", BeamType(v.value))
                    )
                )

                # bit depth
                self.widgets["bit_depth"] = (
                    ui.number(
                        label="Bit depth",
                        value=self.instance.bit_depth or None,
                        step=1,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field(
                            "bit_depth", int(v.value) if v else None
                        )
                    )
                )

                # resolution mode
                self._build_resolution_mode()

                # area selector
                self._area_selector.build()

                # properties selector
                self.properties_selector = PropertiesSelector(self.microscope)

    def get_settings(self) -> ImagingSettings:
        """Return the current instance (now updated in real-time)."""
        # ensure properties are current from selector
        if self.properties_selector is not None:
            self.instance.properties_to_collect = self.properties_selector.props
        return self.instance

    def _build_resolution_mode(self):
        """Build resolution mode radio with conditional extended fields."""
        current_mode = self.instance.resolution_mode
        is_extended = isinstance(current_mode, ExtendedResolution)

        ui.label("Resolution mode").classes("font-semibold mt-4")

        self.widgets["resolution_radio"] = (
            ui.radio(
                {
                    "standard": "Standard",
                    "extended": "Extended",
                },
                value="extended" if is_extended else "standard",
            )
            .classes("gap-2")
            .on_value_change(self._update_resolution_fields)
        )

        # container for extended fields
        self.widgets["extended_container"] = ui.column().classes(
            "w-full gap-3 pl-4 mt-2"
        )

        # draw extended fields initially if needed
        self._update_resolution_fields()

    def _update_resolution_fields(self):
        """Update displayed fields based on resolution mode selection."""
        container = self.widgets["extended_container"]
        container.clear()

        if self.widgets["resolution_radio"].value == "extended":
            current_mode = self.instance.resolution_mode
            pixel_size = ExtendedResolution().pixel_size  # pyright: ignore[reportCallIssue]
            if isinstance(current_mode, ExtendedResolution):
                pixel_size = current_mode.pixel_size

            with container:
                self.widgets["pixel_size"] = (
                    ui.number(
                        label="Pixel size [nm]",
                        value=pixel_size,
                        step=1,
                    )
                    .classes("w-full")
                    .on_value_change(self._update_resolution_mode)
                )

        # Update resolution mode on the instance
        self._update_resolution_mode()

    def _update_resolution_mode(self):
        """Update resolution mode on the instance."""
        if self.widgets["resolution_radio"].value == "standard":
            self.instance.resolution_mode = StandardResolution()
        else:
            self.instance.resolution_mode = ExtendedResolution()  # pyright: ignore[reportCallIssue]
            if (pixel_size := self.widgets["pixel_size"].value) is not None:
                self.instance.resolution_mode.pixel_size = pixel_size

    def _update_field(self, field_name: str, value: Any):
        """Update a single field on the instance."""
        setattr(self.instance, field_name, value)
