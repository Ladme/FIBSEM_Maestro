# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
from pathlib import Path

from nicegui import ui

from fibsem_maestro.gui.action_sequence import ActionButton
from fibsem_maestro.gui.main_view import MainView
from fibsem_maestro.gui.settings_form.imaging_form import ImagingForm
from fibsem_maestro.gui.settings_form.template_matching_form import TemplateMatchingForm
from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings


@ui.page("/")
def main():
    ui.add_head_html("""
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600&display=swap" rel="stylesheet">
<style>
    body {
        font-family: 'Inter', sans-serif;
    }
</style>
""")

    microscope_settings = MicroscopeSettings.from_file(
        Path("../fibsem_playground/simulator.yaml")
    )

    slice = SliceContext(0)
    log_context = LogContext(Path("logs"), slice, logging.DEBUG)
    txt_log = CentralTextLogger("microscope", log_context)
    img_log = SliceAwareImageLogger(log_context)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log, img_log)

    ui.label("FIBSEM Maestro").classes("text-2xl font-bold mb-6")

    # create form
    form = ImagingForm(
        ImagingSettings(),  # pyright: ignore[reportCallIssue]
        microscope,
    )

    template_matching_form = TemplateMatchingForm(
        TemplateMatchingSettings(),  # pyright: ignore[reportCallIssue]
        microscope,
    )

    MainView(
        [
            ActionButton("Drift correction", template_matching_form),
            ActionButton("Imaging", form),
        ]
    )

    # async def save():
    #    settings = form.get_values()
    #    ui.notify(f"Saved: {settings}", type="positive")

    # ui.button("Save properties", on_click=save).classes("mt-6")


ui.run()
