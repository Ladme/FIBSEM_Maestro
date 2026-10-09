# Released under GPL-3.0 License.
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

    @property
    def is_running(self) -> bool:
        """True while the workflow thread executes actions, including while a pause is pending."""
        return self in (AppState.RUNNING, AppState.STOPPING)
