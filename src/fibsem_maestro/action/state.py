# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pydantic import BaseModel


class ActionState(BaseModel):
    """
    Dataclass representing the persistent internal state of an action.

    In other words, this should contain everything needed
    to resume a workflow after interruption or crash.
    """

    pass
