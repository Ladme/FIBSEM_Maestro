# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from fibsem_maestro.action.action import Action


@pytest.fixture
def text_log() -> MemoryTextLogger:
    return MemoryTextLogger(lambda: 0)


@pytest.fixture
def image_log() -> MemoryImageLogger:
    return MemoryImageLogger(lambda: 0)


@pytest.fixture
def mock_microscope(text_log: MemoryTextLogger) -> Microscope:
    return Microscope(
        MicroscopeSettings(control="mock", ip_address="localhost"), text_log
    )


@pytest.fixture
def simulated_microscope(text_log: MemoryTextLogger) -> Microscope:
    return Microscope(
        MicroscopeSettings(control="simulated", ip_address="localhost"), text_log
    )


@pytest.fixture
def workflow(tmp_path: Path) -> Workflow:
    ctx = FileActionContext(tmp_path / "workflow", "workflow")
    microscope = Microscope(
        MicroscopeSettings(control="simulated", ip_address="localhost"),
        ContextualTextLogger(fallback=ctx.text_logger).derive("microscope"),
    )
    return Workflow(microscope, Actions(), Propagations(), ctx)


@pytest.fixture
def add_action(workflow: Workflow, tmp_path: Path) -> Callable[..., Action]:
    def add(type_key: str, name: str, **settings: object) -> Action:
        action_cls = ACTION_REGISTRY.get(type_key)
        action = action_cls(
            name=name,
            microscope=workflow.microscope,
            settings=action_cls.settings_cls()(**settings),
            ctx=FileActionContext(
                action_dir=tmp_path / name.replace(" ", "_"),
                name=name.replace(" ", "_"),
                slice=workflow.ctx.slice,
            ),
            actions=workflow.actions,
        )
        action.ctx.state_store.write("state.yaml", action.state)
        action.ctx.settings_store.write("settings.yaml", action.settings)
        workflow.actions.append(action)
        return action

    return add
