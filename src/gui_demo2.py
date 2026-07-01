# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
import random
from pathlib import Path

from nicegui import ui

from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.drift_correction.template_matching import (
    TemplateMatchingDriftCorrection,
)
from fibsem_maestro.gui.action_sequence import ActionButton
from fibsem_maestro.gui.main_view import MainView
from fibsem_maestro.gui.settings_form.imaging_form import ImagingForm
from fibsem_maestro.gui.settings_form.template_matching_form import TemplateMatchingForm
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.file import FileImageLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.microscope.simulated.microscope_control import (
    SimulatedMicroscopeControl,
)
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.frame.file import FileFrameStore
from fibsem_maestro.store.image.file import FileImageStore
from fibsem_maestro.store.props.file import FilePropsStore


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

    imaging_settings = ImagingSettings.from_file(
        Path("../fibsem_playground/imaging_simulated.yaml")
    )

    template_matching_settings = TemplateMatchingSettings.from_file(
        Path("../fibsem_playground/drift_corr_simulated.yaml")
    )

    slice = SliceContext(Path("logs"), 1)
    txt_log = FileTextLogger(slice, "microscope", logging.DEBUG)
    img_log = FileImageLogger(slice)
    props_store = FilePropsStore(slice)
    frame_store = FileFrameStore(slice, imaging_settings.images_directory)
    image_store = FileImageStore(slice, Image8Bit, Path("templates"))

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log)

    ui.label("FIBSEM Maestro").classes("text-2xl font-bold mb-6")

    imaging = Imaging(
        "imaging",
        microscope,
        imaging_settings,
        props_store,
        frame_store,
        txt_log.derive("imaging"),
    )

    # create form
    imaging_form = ImagingForm(
        imaging,
        microscope,
    )

    template_matching = TemplateMatchingDriftCorrection(
        "template matching drift correction",
        microscope,
        template_matching_settings,
        [imaging],
        props_store,
        image_store,
        txt_log.derive("template_matching"),
        img_log,
    )

    template_matching_form = TemplateMatchingForm(
        template_matching,
        microscope,
    )

    microscope._control.try_set_stage_position(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    microscope.beam.resolution = Resolution(1024, 768)
    microscope.beam.horizontal_field_width = 2000

    def run(slices: int):
        random.seed(1234567)
        template_matching.create_templates()
        for _ in range(slices):
            # microscope._control.try_move_stage_position(
            #    StagePosition(
            #        x=random.randrange(-1000, 1001), y=random.randrange(-1000, 1001)
            #    )
            # )
            control = microscope._control
            if isinstance(control, SimulatedMicroscopeControl):
                control._sample.apply_drift(  # pyright: ignore[reportAttributeAccessIssue]
                    drift_x=random.randrange(-40, 41),
                    drift_y=random.randrange(-40, 41),
                    # drift_x=-10,
                    # drift_y=-10,
                )
                print(control._sample.drift)  # pyright: ignore[reportAttributeAccessIssue]
            template_matching.correct_drift()
            imaging.grab_frame()
            slice.increment()

    MainView(
        [
            ActionButton("Template matching", template_matching_form),
            ActionButton("Imaging", imaging_form),
        ],
        run,
    )

    # async def save():
    #    settings = form.get_values()
    #    ui.notify(f"Saved: {settings}", type="positive")

    # ui.button("Save properties", on_click=save).classes("mt-6")


ui.run()
