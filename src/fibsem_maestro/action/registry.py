# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.registry import Registry

ACTION_REGISTRY = Registry[type[Action]]("action")
