# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from enum import Enum


class AppState(Enum):
    EDITING = "editing"
    RUNNING = "running"
    STOPPING = "stopping"
    PAUSED = "paused"
    INTERRUPTED = "interrupted"

    def __str__(self) -> str:
        return self.value
