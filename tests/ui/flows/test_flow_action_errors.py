# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""An action failing during a run, answered in the error dialog; recovery after editing."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    button,
    editable,
    first_spin_box,
    interrupt_run,
    logged_messages,
    panel_of,
    prepare_with_tool,
)

from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.top_bar import WAITING_FOR_CHOICE_TOOLTIP

if TYPE_CHECKING:
    import pytest
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.composition import Composition
    from fibsem_maestro.ui.views.dialogs.action_error import ActionErrorDialog


def error_dialog(app: Composition) -> ActionErrorDialog:
    dialog = app.window.error_dialog
    assert dialog is not None
    return dialog


def pause(qtbot: QtBot, app: Composition) -> None:
    app.window.top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)


def test_flow_action_error_interrupts_and_retry_continues(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = [True]
    _, second = interrupt_run(qtbot, app, monkeypatch, lambda _: failing[0])
    failed_at = second.ctx.slice
    assert app.run.state is AppState.INTERRUPTED
    assert not app.window.top_bar.run_button.isEnabled()
    assert app.window.top_bar.run_button.toolTip() == WAITING_FOR_CHOICE_TOOLTIP

    # retrying while the cause persists fails again and asks again
    first_dialog = error_dialog(app)
    button(first_dialog, "Retry action").click()
    qtbot.waitUntil(
        lambda: app.window.error_dialog not in (None, first_dialog), timeout=TIMEOUT_MS
    )
    assert app.run.state is AppState.INTERRUPTED

    failing[0] = False
    button(error_dialog(app), "Retry action").click()

    assert app.window.error_dialog is None
    qtbot.waitUntil(lambda: second.ctx.slice > failed_at + 1, timeout=TIMEOUT_MS)
    pause(qtbot, app)
    messages = logged_messages(app.session.workflow_dir, "second", failed_at)
    assert messages.count("Retrying action 'second'.") == 2
    assert f"Completed 'second' for slice {failed_at}." in messages


def test_flow_action_error_skip_leaves_the_action_out_for_the_slice(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = [True]
    _, second = interrupt_run(qtbot, app, monkeypatch, lambda _: failing[0])
    failed_at = second.ctx.slice
    failing[0] = False

    button(error_dialog(app), "Skip action").click()

    assert app.run.state is AppState.RUNNING
    qtbot.waitUntil(lambda: second.ctx.slice > failed_at + 1, timeout=TIMEOUT_MS)
    pause(qtbot, app)
    messages = logged_messages(app.session.workflow_dir, "second", failed_at)
    assert (
        f"Skipping 'second' for slice {failed_at}: failed and skipped by the user."
        in messages
    )
    assert f"Completed 'second' for slice {failed_at}." not in messages


def test_flow_action_error_skip_and_pause_then_resume(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    failing = [True]
    _, second = interrupt_run(qtbot, app, monkeypatch, lambda _: failing[0])
    failed_at = second.ctx.slice

    button(error_dialog(app), "Skip action and pause").click()

    wait_for_state(qtbot, app.run, AppState.PAUSED)
    assert app.window.error_dialog is None
    assert second.ctx.slice == failed_at + 1
    assert app.window.action_list.add_button.isEnabled()

    failing[0] = False
    app.window.top_bar.run_button.click()
    assert app.run.state is AppState.RUNNING
    qtbot.waitUntil(lambda: second.ctx.slice > failed_at + 1, timeout=TIMEOUT_MS)
    pause(qtbot, app)


def test_flow_action_error_recovers_after_editing_settings_while_interrupted(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    # it fails while its settings are the defaults, as a misconfigured action would
    _, second = interrupt_run(
        qtbot,
        app,
        monkeypatch,
        lambda action: action.settings == type(action.settings)(),
    )
    failed_at = second.ctx.slice

    app.window.action_list.select(second)
    panel = panel_of(app, second)
    field = first_spin_box(panel.form.widget)
    # V24: settings, rules and tools stay available; the structure is locked
    assert editable(field)
    assert panel.propagations.add_button.isEnabled()
    assert panel.header.button("prepare").isEnabled()
    assert not app.window.action_list.add_button.isEnabled()

    prepare_with_tool(qtbot, app, second)
    field.stepBy(1)
    button(error_dialog(app), "Retry action").click()

    qtbot.waitUntil(lambda: second.ctx.slice > failed_at + 1, timeout=TIMEOUT_MS)
    pause(qtbot, app)
    assert f"Completed 'second' for slice {failed_at}." in logged_messages(
        app.session.workflow_dir, "second", failed_at
    )
