from __future__ import annotations

import sys
from enum import Enum
from typing import Annotated, Any

from annotated_types import Ge, Le
from pydantic import BaseModel, Field, PrivateAttr
from PyQt6.QtCore import QObject, pyqtSignal
from PyQt6.QtWidgets import QApplication, QMainWindow, QScrollArea

from fibsem_maestro.gui.new_form_builder.builder import FormBuilder
from fibsem_maestro.gui.new_form_builder.schema.schema import get_field_infos
from fibsem_maestro.settings.autofocus_settings import AutofocusSettings
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.imaging_settings import ExtendedResolution, ImagingSettings


# --------------------------------------------------------------------------- #
# Minimal reactive root (stand-in for your BaseSettings)                       #
# --------------------------------------------------------------------------- #
class ReactiveModel(BaseModel):
    """Fires registered hooks whenever one of its own fields is assigned."""

    _hooks: list = PrivateAttr(default_factory=list)

    def on_change(self, hook) -> None:
        self._hooks.append(hook)

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if name in type(self).model_fields:
            for hook in self._hooks:
                hook(self)


# --------------------------------------------------------------------------- #
# Sample settings exercising the main dispatch branches                        #
# --------------------------------------------------------------------------- #
class Mode(Enum):
    IMAGING = "imaging"
    MILLING = "milling"


class Detector(BaseModel):
    """A plain (non-reactive) nested model, on purpose."""

    name: str = "ETD"
    contrast: int = 50


class Settings(BaseSettings):
    beam_on: bool = False
    magnification: Annotated[int, Ge(100), Le(1_000_000)] = 1000
    dwell_time_us: float = 1.0
    label: str = "sample_01"
    mode: Mode = Mode.IMAGING
    focus_offset: int | None = None
    detector: Detector = Field(default_factory=Detector)
    tags: list[str] = Field(default_factory=lambda: ["roi", "auto"])


# --------------------------------------------------------------------------- #
# Stand-in WorkflowManager                                                     #
# --------------------------------------------------------------------------- #
class _Control:
    manufacturer_prop_names: list[str] = []


class _Microscope:
    control = _Control()


class _Workflow:
    microscope = _Microscope()
    actions: list = []


class FakeManager(QObject):
    actions_changed = pyqtSignal()
    action_changed = pyqtSignal(object)

    def __init__(self) -> None:
        super().__init__()
        self.workflow = _Workflow()


# --------------------------------------------------------------------------- #
# Main                                                                         #
# --------------------------------------------------------------------------- #
def main() -> None:
    app = QApplication(sys.argv)

    settings = AutofocusSettings()
    settings.on_change(lambda s: print("CHANGED ->", s.model_dump()))

    form = FormBuilder().build_form(settings, FakeManager())

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(form)

    window = QMainWindow()
    window.setCentralWidget(scroll)
    window.setWindowTitle("Form builder demo")
    window.resize(460, 640)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
