# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
from pathlib import Path

from nicegui import ui

from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.gui.area_selector_new.area_limits import AreaLimits
from fibsem_maestro.gui.area_selector_new.area_selector import AreaSelector
from fibsem_maestro.gui.area_selector_new.area_type import AreaType
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


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

    ui.run_javascript("""
// disable right-click
window.addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

// disable middle-click (wheel button)
window.addEventListener('mousedown', function(e) {
    if (e.button === 1) {
        e.preventDefault();
    }
});

// disable arrow key scrolling
window.addEventListener("keydown", function(e) {
    const keys = ["ArrowUp", "ArrowDown", "ArrowLeft", "ArrowRight"];
    if (keys.includes(e.key)) e.preventDefault();
});
""")

    microscope_settings = MicroscopeSettings.from_file(
        Path("../fibsem_playground/simulator.yaml")
    )

    slice = SliceContext(Path("logs"), 1)
    txt_log = FileTextLogger(slice, "microscope", logging.INFO)

    # initialize the microscope
    microscope = Microscope(microscope_settings, txt_log)
    microscope.beam.resolution = Resolution(1000, 1000)
    microscope.beam.horizontal_field_width = 2000
    microscope.set_stage_position_with_verification(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=30)
    )

    areas = AreaLimits()
    areas.add_limit(AreaType.SCANNING, 1)
    areas.add_limit(AreaType.TEMPLATE, 5)
    selector = AreaSelector(microscope, areas)
    selector.build()


ui.run()
