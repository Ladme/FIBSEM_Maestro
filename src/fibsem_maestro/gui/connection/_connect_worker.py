# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import logging
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.logging.text.file import FileTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class ConnectWorker(QThread):
    """
    Attempts to construct a Microscope instance in a background thread.

    Args:
        settings: The MicroscopeSettings to connect with.
    """

    # emits Microscope instance
    succeeded = pyqtSignal(object)
    # emits error message
    failed = pyqtSignal(str)

    def __init__(self, settings: MicroscopeSettings) -> None:
        super().__init__()
        self._settings = settings

    def run(self) -> None:
        slice = SliceContext(Path("logs"), 0)
        txt_log = FileTextLogger(slice, "microscope", logging.DEBUG)

        try:
            microscope = Microscope(self._settings, txt_log)
            self.succeeded.emit(microscope)
        except Exception as e:
            self.failed.emit(str(e))
