import json
import logging
import sys
from enum import Enum
from pathlib import Path
from typing import Annotated, Literal

import qdarkstyle
from autoscript_sdb_microscope_client.sdb_microscope_client import SdbMicroscopeClient
from pydantic import BaseModel, Field
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.autofocus.autofocus import Autofocus
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.core.stage_position import StagePosition
from fibsem_maestro.gui.connection.screen import ConnectionScreen
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.form_builder.utils import get_field_infos
from fibsem_maestro.gui.window.window import MainWindow
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.autoscript_control.manufacturer_props import (
    AutoscriptManufacturerPropertiesRegistry,
)
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.adjust_props_settings import AdjustPropsSettings
from fibsem_maestro.settings.autofocus_settings import AutofocusSettings
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionSettings
from fibsem_maestro.settings.form_utils import FieldUnit
from fibsem_maestro.settings.imaging_settings import ImagingSettings
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow


def main() -> None:
    app = QApplication(sys.argv)

    app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt6"))

    screen = ConnectionScreen()
    if screen.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    workflow = screen.workflow
    assert workflow is not None

    workflow.microscope.control.try_set_stage_position(
        StagePosition(x=0.0, y=0.0, z=5_000_000.0, rotation=0, tilt=0)
    )
    workflow.microscope.beam.resolution = Resolution(2048, 1536)
    workflow.microscope.beam.horizontal_field_width = 2000

    window = MainWindow(workflow, screen.workflow_dir or Path())

    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
