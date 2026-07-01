# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from PyQt6.QtCore import QObject, pyqtSignal

from fibsem_maestro.action.action import Action


class ActionTestWorker(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(Exception)

    def __init__(self, action: Action) -> None:
        super().__init__()
        self._action = action

    def run(self) -> None:
        try:
            self._action.test()
        except Exception as e:
            self.error.emit(e)
        finally:
            self.finished.emit()
