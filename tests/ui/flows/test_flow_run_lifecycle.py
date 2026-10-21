# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
On the composed main window: add, prepare, run, pause, edit while paused, resume.

A run that ends by itself is in `test_flow_milling_end.py`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    RUNNABLE_ACTION,
    add_through_dialog,
    editable,
    first_spin_box,
    item_of,
    logged_messages,
    panel_of,
    prepare_with_tool,
)

from fibsem_maestro.ui.app.run_state import AppState

if TYPE_CHECKING:
    from pathlib import Path

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.composition import Composition


def stored_settings(app: Composition, action: Action, slice_index: int) -> str:
    """The action's `settings.yaml` for a slice."""
    path: Path = (
        app.session.workflow_dir
        / action.name_with_underscores
        / f"slice_{slice_index:04d}"
        / "settings.yaml"
    )
    return path.read_text()


def test_flow_run_lifecycle_from_adding_to_resuming_after_an_edit(
    qtbot: QtBot, app: Composition
) -> None:
    top_bar = app.window.top_bar
    states: list[AppState] = []
    app.run.state_changed.connect(states.append)

    # F2: add; Run waits for the preparation
    first = add_through_dialog(app, RUNNABLE_ACTION, "first")
    second = add_through_dialog(app, RUNNABLE_ACTION, "second")
    assert app.window.action_list.current_action is second
    assert not top_bar.run_button.isEnabled()
    assert "'first' is not prepared for slice 0." in top_bar.run_button.toolTip()

    # F4: prepare both with their tools
    prepare_with_tool(qtbot, app, first)
    prepare_with_tool(qtbot, app, second)
    assert item_of(app, first).check_mark.is_on
    assert top_bar.run_button.isEnabled()

    # F5: run, then pause after the current action
    top_bar.run_button.click()
    assert app.run.state is AppState.RUNNING
    assert not app.window.action_list.add_button.isEnabled()
    qtbot.waitUntil(lambda: app.session.slice >= 2, timeout=TIMEOUT_MS)
    top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)
    assert states == [AppState.RUNNING, AppState.STOPPING, AppState.PAUSED]
    assert top_bar.slice_label.text() == str(app.session.slice)
    paused_at = app.session.slice
    next_action = app.session.workflow.next_pending_action() or first
    assert item_of(app, next_action).arrow.is_on

    # F3 while paused: an edit is committed and written for the action's slice
    app.window.action_list.select(first)
    field = first_spin_box(panel_of(app, first).form.widget)
    assert editable(field)
    before = stored_settings(app, first, first.ctx.slice)
    field.stepBy(1)
    edited = stored_settings(app, first, first.ctx.slice)
    assert edited != before

    # resume: the run goes on with the edited settings
    top_bar.run_button.click()
    assert app.run.state is AppState.RUNNING
    qtbot.waitUntil(lambda: app.session.slice >= paused_at + 2, timeout=TIMEOUT_MS)
    top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)

    assert stored_settings(app, first, first.ctx.slice) == edited
    # the run went on for the slice after the pause; whether 'first' ran or was
    # skipped depends on which field the edit changed, which the test does not know
    messages = logged_messages(app.session.workflow_dir, "first", paused_at + 1)
    assert any(f"'first' for slice {paused_at + 1}" in m for m in messages)
