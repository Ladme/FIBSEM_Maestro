# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Put the application layer into situations that are hard to reach otherwise."""

from __future__ import annotations

import threading
from contextlib import contextmanager
from typing import TYPE_CHECKING

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.ui.app.links import iter_links
from fibsem_maestro.ui.app.microscope_tasks import MicroscopeTask
from gui_testkit import TIMEOUT_MS

if TYPE_CHECKING:
    from collections.abc import Iterator

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.microscope_tasks import MicroscopeTasks
    from fibsem_maestro.ui.ports import TaskHandle


@contextmanager
def busy_tasks(qtbot: QtBot, tasks: MicroscopeTasks) -> Iterator[TaskHandle]:
    """
    Keep the microscope task runner busy with a blocking task for the duration of the block.

    Args:
        qtbot: The Qt test helper.
        tasks: The task runner.

    Yields:
        The blocking task's handle; the task ends (successfully) when the block exits,
        and the runner is idle again afterwards.
    """
    release = threading.Event()
    handle = tasks.submit(
        MicroscopeTask(
            run=lambda: release.wait(TIMEOUT_MS / 1000), description="Blocking"
        )
    )
    assert tasks.busy, "the blocking task was refused"
    try:
        yield handle
    finally:
        release.set()
        qtbot.waitUntil(lambda: not tasks.busy, timeout=TIMEOUT_MS)


def store_unappliable_props(action: Action) -> None:
    """
    Store props for the action's current slice that the microscope refuses to apply.

    Executing the action then fails (an action error, as a real microscope fault
    would) until it is prepared again. Skipping it still works, because skipping
    only copies the props to the next slice.

    Args:
        action: The action; its props for its current slice are replaced.
    """
    action.write_properties(
        GlobalProperties(electron_beam=BeamProperties(no_such_setting=1.0))
    )


def link_pairs() -> list[tuple[str, str, str]]:
    """
    Every way one registered action can link to another, found through the schema.

    Returns:
        `(linking type key, link field name, linked type key)` for every
        action-selector field and every registered type it accepts.
    """
    pairs: list[tuple[str, str, str]] = []
    for key in ACTION_REGISTRY:
        settings = ACTION_REGISTRY.get(key).settings_cls()()
        for link in iter_links(settings):
            pairs.extend(
                (key, link.field_name, target)
                for target in ACTION_REGISTRY
                if issubclass(ACTION_REGISTRY.get(target), link.allowed_types)
            )
    return pairs
