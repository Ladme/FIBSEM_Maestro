# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path
from typing import Any

from nicegui import ui

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.drift_correction.template_matching import (
    TemplateMatchingDriftCorrection,
)
from fibsem_maestro.gui.area_selector import AreaLimits, AreaSelector, AreaType
from fibsem_maestro.gui.properties_selector import PropertiesSelector
from fibsem_maestro.gui.settings_form.settings_form import SettingsForm
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings


class TemplateMatchingForm(SettingsForm):
    """Simple form for TemplateMatchingDriftCorrection with real-time instance updates."""

    def __init__(
        self,
        action: TemplateMatchingDriftCorrection,
        microscope: Microscope,
    ):
        self.action = action
        self.microscope = microscope
        self.widgets = {}
        self.properties_selector = None

        area_limits = AreaLimits()
        area_limits.add_limit(AreaType.TEMPLATE, 100)
        self._area_selector = AreaSelector(self.microscope, area_limits)

    def build(self):
        with ui.card().classes("w-full"):
            ui.label("Template Matching Settings").classes("text-lg font-bold mb-4")

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

                # templates directory path
                self.widgets["templates_directory"] = (
                    ui.input(
                        label="Templates directory",
                        value=str(self.action._settings.templates_directory),
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field(
                            "templates_directory", Path(v.value)
                        )
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

                # minimum confidence
                self.widgets["min_confidence"] = (
                    ui.number(
                        label="Minimum confidence",
                        value=self.action._settings.min_confidence,
                        min=0.0,
                        max=1.0,
                        step=0.01,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field("min_confidence", float(v.value))
                    )
                )

                # rescan interval
                self.widgets["rescan"] = (
                    ui.number(
                        label="Rescan interval",
                        value=self.action._settings.rescan,
                        step=1,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field("rescan", int(v.value))
                    )
                )

                # blur (Gaussian sigma)
                self.widgets["blur"] = (
                    ui.number(
                        label="Blur",
                        value=self.action._settings.blur,
                        step=1,
                    )
                    .classes("w-full")
                    .on_value_change(lambda v: self._update_field("blur", int(v.value)))
                )

                # correction margin
                self.widgets["correction_margin"] = (
                    ui.number(
                        label="Correction margin [nm]",
                        value=self.action._settings.correction_margin,
                        step=1000,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field(
                            "correction_margin", float(v.value)
                        )
                    )
                )

                # stop acquisition at failure
                self.widgets["stop_acquisition_at_failure"] = (
                    ui.checkbox(
                        text="Stop acquisition at failure",
                        value=self.action._settings.stop_acquisition_at_failure,
                    )
                    .classes("w-full")
                    .on_value_change(
                        lambda v: self._update_field(
                            "stop_acquisition_at_failure", v.value
                        )
                    )
                )

                # properties selector
                self.properties_selector = PropertiesSelector(
                    self.microscope, self.action._settings.properties_to_collect
                )

                # area selector
                self._area_selector.build()

    def get_settings(self) -> TemplateMatchingSettings:
        """Return the current instance."""
        # TODO: make this dynamic
        areas = self._area_selector.get_areas()
        template_areas = areas.get(AreaType.TEMPLATE, [])
        self.action._settings.areas = template_areas

        return self.action._settings

    def _update_field(self, field_name: str, value: Any):
        """Update a single field on the instance."""
        setattr(self.action._settings, field_name, value)

    def get_action(self) -> Action:
        # TODO: make this dynamic
        areas = self._area_selector.get_areas()
        template_areas = areas.get(AreaType.TEMPLATE, [])
        self.action._settings.areas = template_areas

        return self.action
