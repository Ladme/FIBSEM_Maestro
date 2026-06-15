# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import QThread, pyqtSignal

from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
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

    def __init__(
        self, settings: MicroscopeSettings, workflow_ctx: ActionContext
    ) -> None:
        super().__init__()
        self._settings = settings
        self._workflow_ctx = workflow_ctx

    def run(self) -> None:
        try:
            microscope = Microscope(
                self._settings,
                ContextualTextLogger(fallback=self._workflow_ctx.text_logger).derive(
                    "microscope"
                ),
            )
            self.succeeded.emit(microscope)
        except Exception as e:
            self.failed.emit(str(e))
