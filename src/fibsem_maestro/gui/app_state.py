# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from enum import Enum


class AppState(Enum):
    EDITING = "editing"
    RUNNING = "running"
    STOPPING = "stopping"
    PAUSED = "paused"
    RELOADED = "reloaded"
    INTERRUPTED = "interrupted"
    FINISHED = "finished"

    def __str__(self) -> str:
        return self.value
