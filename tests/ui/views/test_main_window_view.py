# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The main window: its parts, selection routing, the error dialogs and closing."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    add_prepared,
    button,
    interrupt_run,
    task_running,
)
from PyQt6.QtWidgets import QMessageBox

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.ui.app import commands as commands_module
from fibsem_maestro.ui.app.run_state import AppState

if TYPE_CHECKING:
    from pathlib import Path

    import pytest
    from gui_testkit.dialogs import DirectoryChoices, ExitCalls, MessageBoxes
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.composition import Composition

ANY_TYPE = sorted(ACTION_REGISTRY)[0]


def test_main_window_shows_its_parts(app: Composition) -> None:
    window = app.window
    for part in (
        window.top_bar,
        window.action_list,
        window.panel_host,
        window.log_panel,
    ):
        assert part.isVisible()
    assert not window.danger_banner.isVisible()
    assert window.error_dialog is None
    assert window.workflow_error_dialog is None


def test_main_window_shows_a_non_modal_dialog_for_a_failed_action(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    interrupt_run(qtbot, app, monkeypatch)
    dialog = app.window.error_dialog
    assert dialog is not None

    assert dialog.isVisible()
    assert not dialog.isModal()
    # the rest of the window stays usable while the user decides
    assert app.window.top_bar.microscope_button.isEnabled()

    button(dialog, "Skip action and pause").click()

    assert app.window.error_dialog is None
    wait_for_state(qtbot, app.run, AppState.PAUSED)


def test_main_window_closes_the_action_error_dialog_on_new_workflow(
    qtbot: QtBot,
    tmp_path: Path,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    directory_choice: DirectoryChoices,
) -> None:
    interrupt_run(qtbot, app, monkeypatch)
    new_dir = tmp_path / "new"
    new_dir.mkdir()
    directory_choice.path = str(new_dir)

    app.window.top_bar.new_button.click()

    assert app.window.error_dialog is None
    assert app.run.state is AppState.EDITING


def test_main_window_close_while_idle_exits_without_asking(
    app: Composition, exits: ExitCalls, boxes: MessageBoxes
) -> None:
    app.window.close()

    assert exits.codes == [0]
    assert boxes.calls == []


def test_main_window_close_while_a_task_runs_asks_first(
    qtbot: QtBot, app: Composition, exits: ExitCalls, boxes: MessageBoxes
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")

    with task_running(qtbot, app, action):
        boxes.answer = QMessageBox.StandardButton.Cancel
        app.window.close()
        assert exits.codes == []
        assert app.window.isVisible()
        assert boxes.titles() == ["Quit FIBSEM Maestro"]
        assert boxes.texts()[0].startswith("A microscope task is still running.")

        boxes.answer = QMessageBox.StandardButton.Yes
        app.window.close()
        assert exits.codes == [0]


def test_main_window_close_while_running_names_the_workflow(
    qtbot: QtBot, app: Composition, exits: ExitCalls, boxes: MessageBoxes
) -> None:
    add_prepared(qtbot, app, "first")
    app.window.top_bar.run_button.click()
    boxes.answer = QMessageBox.StandardButton.Cancel

    app.window.close()

    assert exits.codes == []
    assert boxes.texts()[0].startswith("The workflow is still running.")


def test_main_window_close_flushes_the_logs_before_the_hard_exit(
    app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    events: list[str] = []
    monkeypatch.setattr(
        commands_module, "close_all_log_files", lambda: events.append("logs closed")
    )
    monkeypatch.setattr(os, "_exit", lambda code: events.append(f"exit {code}"))

    app.window.close()

    assert events == ["logs closed", "exit 0"]


def test_main_window_terminates_after_a_workflow_error_without_asking(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    exits: ExitCalls,
    boxes: MessageBoxes,
) -> None:
    action = add_prepared(qtbot, app, "first")

    def fail(_: object) -> None:
        raise RuntimeError("disk gone")

    monkeypatch.setattr(type(action), "initialize_first_slice", fail)
    app.window.top_bar.run_button.click()
    qtbot.waitUntil(
        lambda: app.window.workflow_error_dialog is not None, timeout=TIMEOUT_MS
    )
    dialog = app.window.workflow_error_dialog
    assert dialog is not None

    button(dialog, "Terminate workflow").click()

    assert exits.codes == [0]
    # the run was abandoned before the window closed
    assert app.window.workflow_error_dialog is None
    assert not app.run.state.is_running
    assert boxes.calls == []
