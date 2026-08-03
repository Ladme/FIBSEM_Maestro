# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.action.action import Action


class WorkflowError(Exception):
    pass


class ActionError(Exception):
    def __init__(self, action: Action, message: str) -> None:
        super().__init__(message)
        self.action = action
        self.message = message
