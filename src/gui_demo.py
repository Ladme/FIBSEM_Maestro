# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import logging
from pathlib import Path

from fibsem_maestro.logging.context import LogContext, SliceContext
from fibsem_maestro.logging.image.slice_aware import SliceAwareImageLogger
from fibsem_maestro.logging.text.central import CentralTextLogger
from nicegui import ui

from fibsem_maestro.gui.properties_selector import PropertiesSelector
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings

microscope_settings = MicroscopeSettings.from_file(
    Path("../fibsem_playground/simulator.yaml")
)

slice = SliceContext(0)
log_context = LogContext(Path("logs"), slice, logging.DEBUG)
txt_log = CentralTextLogger("microscope", log_context)
img_log = SliceAwareImageLogger(log_context)

# initialize the microscope
microscope = Microscope(microscope_settings, txt_log, img_log)

selected_properties = PropertiesSelector(microscope)


def show_selection():
    print("Microscope:", selected_properties.props.microscope)
    print("Electron beam:", selected_properties.props.electron_beam)
    print("Ion beam:", selected_properties.props.ion_beam)


ui.button("Show selected properties", on_click=show_selection)

ui.run()
