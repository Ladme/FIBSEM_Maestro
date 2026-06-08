# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

from fibsem_maestro.action.action import Action


@dataclass(frozen=True)
class ActionDescriptor:
    name: str
    action_cls: type[Action]
