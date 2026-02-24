# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
from pathlib import Path

from nicegui import ui

from fibsem_maestro.gui.settings_form import ImagingSettingsForm
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


@ui.page("/")
def main():
    microscope_settings = MicroscopeSettings.from_file(
        Path("../fibsem_playground/simulator.yaml")
    )

    slice = SliceContext(0)
    log_context = LogContext(Path("logs"), slice, logging.DEBUG)
    txt_log = CentralTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    ui.label("Imaging Settings Form").classes("text-2xl font-bold mb-6")

    # Create form
    form = ImagingSettingsForm(
        ImagingSettings.from_file(Path("../fibsem_playground/imaging_simulated.yaml")),
        microscope,
    )

    async def save():
        settings = form.get_values()
        ui.notify(f"Saved: {settings}", type="positive")

    ui.button("Save", on_click=save).classes("mt-6")


ui.run()
