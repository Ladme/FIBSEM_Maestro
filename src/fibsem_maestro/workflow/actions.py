# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections import UserList

from fibsem_maestro.action.action import Action


class Actions(UserList[Action]):
    def named(self, name: str) -> Action:
        for action in self.data:
            if action.name == name:
                return action
        raise KeyError(f"Action with name '{name}' not found")
