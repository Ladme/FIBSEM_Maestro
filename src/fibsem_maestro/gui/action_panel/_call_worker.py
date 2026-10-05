from collections.abc import Callable

from PyQt6.QtCore import QObject, pyqtSignal


class CallWorker(QObject):
    """
    Runs a callable on a worker thread and reports the outcome.

    Signals:
        error: Emitted with the exception if the callable raised.
        finished: Emitted after the callable returned or raised.

    Args:
        fn: The callable to run.
    """

    error = pyqtSignal(Exception)
    finished = pyqtSignal()

    def __init__(self, fn: Callable[[], None]) -> None:
        super().__init__()
        self._fn = fn

    def run(self) -> None:
        """Call the callable, reporting any exception through `error`."""
        try:
            self._fn()
        except Exception as e:
            self.error.emit(e)
        finally:
            self.finished.emit()
