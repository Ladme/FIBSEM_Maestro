# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.settings.base_settings import BaseSettings


class ActionState(BaseSettings):
    """
    Dataclass representing the persistent internal state of an action.

    In other words, this should contain everything needed
    to resume a workflow after interruption or crash.
    """

    pass
