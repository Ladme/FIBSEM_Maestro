# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import Any

from nicegui import ui

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.gui.area_selector import AreaLimits, AreaSelector, AreaType
from fibsem_maestro.gui.properties_selector import PropertiesSelector
from fibsem_maestro.gui.settings_form.settings_form import SettingsForm
from fibsem_maestro.imaging.imaging import Imaging
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
        action: Imaging,
        microscope: Microscope,
    ):
        self.action = action
        self.microscope = microscope
        self.widgets = {}
        self.properties_selector = None

        area_limits = AreaLimits()
        area_limits.add_limit(AreaType.SCANNING, 1)
        scanning_area = self.action._settings.scanning_area

        self._area_selector = AreaSelector(
            self.microscope,
            area_limits,
            {AreaType.SCANNING: [scanning_area]} if scanning_area is not None else {},
        )

    def build(self):
        with ui.card().classes("w-full"):
            ui.label("Imaging Settings").classes("text-lg font-bold mb-4")

            with ui.column().classes("w-full gap-4"):
                # properties file path
                self.widgets["properties_file"] = (
                    ui.input(
                        label="Properties file",
                        value=str(self.action._settings.properties_file),
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
                        value=str(self.action._settings.images_directory),
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
                        value=self.action._settings.beam_type.value,
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
                        value=self.action._settings.bit_depth or None,
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

                # properties selector
                self.properties_selector = PropertiesSelector(
                    self.microscope, self.action._settings.properties_to_collect
                )

                # area selector
                self._area_selector.build()

    def get_settings(self) -> ImagingSettings:
        """Return the current settings."""
        self._get_areas()

        return self.action._settings

    def _get_areas(self) -> None:
        areas = self._area_selector.get_areas()
        scanning_areas = areas.get(AreaType.SCANNING, [])
        print(scanning_areas)

        if len(scanning_areas) > 1:
            raise ValueError(
                f"Expected at most one scanning area, got {len(scanning_areas)}"
            )

        self.action._settings.scanning_area = (
            scanning_areas[0] if scanning_areas else None
        )

    def _build_resolution_mode(self):
        """Build resolution mode radio with conditional extended fields."""
        current_mode = self.action._settings.resolution_mode
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
            current_mode = self.action._settings.resolution_mode
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
            self.action._settings.resolution_mode = StandardResolution()
        else:
            self.action._settings.resolution_mode = ExtendedResolution()  # pyright: ignore[reportCallIssue]
            if (pixel_size := self.widgets["pixel_size"].value) is not None:
                self.action._settings.resolution_mode.pixel_size = pixel_size

    def _update_field(self, field_name: str, value: Any):
        """Update a single field on the instance."""
        setattr(self.action._settings, field_name, value)

    def get_action(self) -> Action:
        self._get_areas()
        return self.action
