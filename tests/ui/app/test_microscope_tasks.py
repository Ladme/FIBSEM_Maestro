# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`MicroscopeTasks`: the single serial door to the microscope."""

from __future__ import annotations

import threading
from typing import TYPE_CHECKING

import pytest
from gui_testkit.app import wait_for_task
from gui_testkit.situations import busy_tasks

from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.ui.app.errors import NotAllowedError
from fibsem_maestro.ui.app.microscope_tasks import MicroscopeTask, MicroscopeTasks

if TYPE_CHECKING:
    from gui_testkit.app import Services
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.ports import TaskHandle

TIMEOUT_MS = 10_000


@pytest.fixture
def tasks(services: Services) -> MicroscopeTasks:
    return services.tasks


@pytest.fixture
def log() -> MemoryTextLogger:
    return MemoryTextLogger(lambda: 0)


def lines(log: MemoryTextLogger) -> list[tuple[str, str]]:
    return [(record.level, record.message) for record in log.records[0]]


def outcome(qtbot: QtBot, handle: TaskHandle) -> list[tuple[str, object]]:
    """Every signal the handle emits until it is released (`succeeded`/`failed`, payload)."""
    emitted: list[tuple[str, object]] = []
    handle.succeeded.connect(lambda result: emitted.append(("succeeded", result)))
    handle.failed.connect(lambda error: emitted.append(("failed", error)))
    with qtbot.waitSignal(handle.destroyed, timeout=TIMEOUT_MS):
        pass
    return emitted


def test_tasks_run_off_the_gui_thread(qtbot: QtBot, tasks: MicroscopeTasks) -> None:
    handle = tasks.submit(MicroscopeTask(run=threading.get_ident, description="x"))
    ((signal, ident),) = outcome(qtbot, handle)
    assert signal == "succeeded"
    assert ident != threading.get_ident()


def test_tasks_failure_is_reported_once(qtbot: QtBot, tasks: MicroscopeTasks) -> None:
    def fail() -> None:
        raise ValueError("no beam")

    ((signal, error),) = outcome(qtbot, tasks.submit(MicroscopeTask(fail, "x")))
    assert signal == "failed"
    assert isinstance(error, ValueError)
    assert not tasks.busy


def test_tasks_refuse_second_task_while_busy(
    qtbot: QtBot, tasks: MicroscopeTasks
) -> None:
    ran: list[bool] = []
    with busy_tasks(qtbot, tasks):
        refused = tasks.submit(MicroscopeTask(lambda: ran.append(True), "second"))
        ((signal, error),) = outcome(qtbot, refused)
        assert tasks.busy
    assert (signal, type(error)) == ("failed", NotAllowedError)
    assert ran == []


def test_tasks_refuse_while_locked(qtbot: QtBot, tasks: MicroscopeTasks) -> None:
    tasks.set_locked(True)
    ran: list[bool] = []

    handle = tasks.submit(MicroscopeTask(lambda: ran.append(True), "x"))

    assert not tasks.busy
    ((signal, error),) = outcome(qtbot, handle)
    assert (signal, type(error)) == ("failed", NotAllowedError)
    assert ran == []


def test_tasks_refusal_arrives_after_caller_connected(
    qtbot: QtBot, tasks: MicroscopeTasks
) -> None:
    received: list[object] = []
    handle = tasks.refuse(NotAllowedError("no"))
    # connected after the call returned, as every caller does
    handle.failed.connect(received.append)
    assert received == []
    qtbot.waitUntil(lambda: len(received) == 1, timeout=TIMEOUT_MS)


def test_tasks_busy_until_handle_slots_returned(
    qtbot: QtBot, tasks: MicroscopeTasks
) -> None:
    busy_in_slot: list[bool] = []
    changes: list[bool] = []
    tasks.busy_changed.connect(changes.append)

    handle = tasks.submit(MicroscopeTask(lambda: 42, "x"))
    assert tasks.busy
    handle.succeeded.connect(lambda _: busy_in_slot.append(tasks.busy))
    wait_for_task(qtbot, tasks, handle)

    assert busy_in_slot == [True]
    assert changes == [True, False]


def test_tasks_raising_slot_still_clears_busy(
    qtbot: QtBot, tasks: MicroscopeTasks
) -> None:
    def explode(_: object) -> None:
        raise RuntimeError("slot failed")

    with qtbot.captureExceptions() as exceptions:
        handle = tasks.submit(MicroscopeTask(lambda: 1, "x"))
        handle.succeeded.connect(explode)
        wait_for_task(qtbot, tasks, handle)

    assert len(exceptions) == 1
    assert not tasks.busy


def test_tasks_then_runs_before_succeeded(qtbot: QtBot, tasks: MicroscopeTasks) -> None:
    order: list[str] = []
    handle = tasks.submit(
        MicroscopeTask(
            run=lambda: "result",
            description="x",
            then=lambda result: order.append(f"then {result}, busy {tasks.busy}"),
        )
    )
    handle.succeeded.connect(lambda result: order.append(f"succeeded {result}"))
    wait_for_task(qtbot, tasks, handle)
    assert order == ["then result, busy True", "succeeded result"]


def test_tasks_raising_then_fails_the_task(
    qtbot: QtBot, tasks: MicroscopeTasks, log: MemoryTextLogger
) -> None:
    def then(_: object) -> None:
        raise OSError("disk full")

    handle = tasks.submit(MicroscopeTask(lambda: 1, "Preparing 'a'", log, then))

    ((signal, error),) = outcome(qtbot, handle)
    assert (signal, str(error)) == ("failed", "disk full")
    assert not tasks.busy
    assert lines(log) == [
        ("info", "Preparing 'a'..."),
        ("info", "Preparing 'a' completed."),
        ("error", "Preparing 'a' failed: disk full"),
    ]


def test_tasks_log_lines(
    qtbot: QtBot, tasks: MicroscopeTasks, log: MemoryTextLogger
) -> None:
    def fail() -> None:
        raise ValueError("no beam")

    wait_for_task(
        qtbot, tasks, tasks.submit(MicroscopeTask(lambda: 1, "Testing 'a'", log))
    )
    wait_for_task(
        qtbot, tasks, tasks.submit(MicroscopeTask(fail, "Preparing 'b'", log))
    )
    with busy_tasks(qtbot, tasks):
        tasks.submit(MicroscopeTask(lambda: 1, "Refused", log))

    assert lines(log) == [
        ("info", "Testing 'a'..."),
        ("info", "Testing 'a' completed."),
        ("info", "Preparing 'b'..."),
        ("error", "Preparing 'b' failed: no beam"),
    ]
