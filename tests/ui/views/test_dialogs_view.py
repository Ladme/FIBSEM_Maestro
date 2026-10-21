# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The microscope settings dialog, the action-error dialog and the workflow-error dialog."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit import TIMEOUT_MS
from gui_testkit.app import wait_for_state
from gui_testkit.driving import (
    FAILURE_MESSAGE,
    add_prepared,
    answering,
    button,
    children,
    editable,
    first_spin_box,
    interrupt_run,
    logged_messages,
    task_running,
)
from PyQt6.QtWidgets import QLabel, QPushButton

from fibsem_maestro.ui.app.edit_policy import permissions_for
from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.views.dialogs.action_error import ActionErrorDialog
from fibsem_maestro.ui.views.dialogs.microscope_settings import (
    MicroscopeSettingsDialog,
)
from fibsem_maestro.workflow.error_choice import ErrorChoice

if TYPE_CHECKING:
    import pytest
    from gui_testkit.dialogs import ExitCalls, MessageBoxes
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import Composition

CHOICES = ("Retry action", "Skip action", "Skip action and pause")


def microscope_dialog(
    qtbot: QtBot, app: Composition, state: AppState, danger_mode: bool
) -> MicroscopeSettingsDialog:
    dialog = MicroscopeSettingsDialog(
        app.session,
        app.commands,
        permissions_for(state, danger_mode, task_busy=False),
        app.form_builder,
        app.form_contexts.for_microscope_settings(),
    )
    qtbot.addWidget(dialog)
    return dialog


def test_microscope_settings_dialog_is_editable_per_state_and_danger_mode(
    qtbot: QtBot, app: Composition
) -> None:
    cases = [
        (AppState.EDITING, False, False),
        (AppState.PAUSED, False, False),
        (AppState.RELOADED, False, False),
        (AppState.INTERRUPTED, False, False),
        (AppState.FINISHED, False, False),
        (AppState.RUNNING, False, True),
        (AppState.STOPPING, False, True),
        (AppState.RUNNING, True, False),
    ]
    for state, danger_mode, read_only in cases:
        dialog = microscope_dialog(qtbot, app, state, danger_mode)

        assert dialog.read_only is read_only, (state, danger_mode)
        assert editable(first_spin_box(dialog)) is not read_only, (state, danger_mode)
        dialog.done(0)


def test_microscope_settings_dialog_apply_saves_the_profile_when_editable(
    qtbot: QtBot, app: Composition, user_config: UserConfig
) -> None:
    dialog = microscope_dialog(qtbot, app, AppState.EDITING, False)
    first_spin_box(dialog).stepBy(1)
    edited = app.session.microscope.settings.model_copy()

    button(dialog, "Apply").click()

    assert dialog.result() == MicroscopeSettingsDialog.DialogCode.Accepted
    assert user_config.load_microscope_profile() == edited


def test_microscope_settings_dialog_apply_keeps_the_profile_when_read_only(
    qtbot: QtBot, app: Composition, user_config: UserConfig
) -> None:
    dialog = microscope_dialog(qtbot, app, AppState.RUNNING, False)

    button(dialog, "Apply").click()

    assert dialog.result() == MicroscopeSettingsDialog.DialogCode.Accepted
    assert user_config.load_microscope_profile() is None


def test_microscope_settings_dialog_opened_while_running_is_read_only(
    qtbot: QtBot, app: Composition
) -> None:
    add_prepared(qtbot, app, "first")
    app.window.top_bar.run_button.click()
    read_only: list[bool] = []

    def look(dialog: MicroscopeSettingsDialog) -> None:
        read_only.append(dialog.read_only)
        button(dialog, "Apply").click()

    with answering(MicroscopeSettingsDialog, look):
        app.window.top_bar.microscope_button.click()

    assert read_only == [True]
    app.window.top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)


def test_action_error_dialog_offers_the_choices_for_a_failed_action(
    qtbot: QtBot,
) -> None:
    dialog = ActionErrorDialog("beam lost", "imaging")
    qtbot.addWidget(dialog)

    assert dialog.windowTitle() == "Action failed"
    texts = [b.text() for b in children(dialog, QPushButton)]
    assert texts == list(CHOICES)
    assert any("beam lost" in label.text() for label in children(dialog, QLabel))

    with qtbot.waitSignal(dialog.choice_made) as chosen:
        button(dialog, "Skip action").click()
    assert chosen.args == [ErrorChoice.SKIP]


def test_action_error_dialog_cannot_be_dismissed_without_a_choice(
    qtbot: QtBot,
) -> None:
    dialog = ActionErrorDialog("beam lost", "imaging")
    qtbot.addWidget(dialog)
    dialog.show()

    dialog.reject()
    dialog.close()

    assert dialog.isVisible()


def test_action_error_dialog_choices_follow_the_permission(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _ = interrupt_run(qtbot, app, monkeypatch)
    dialog = app.window.error_dialog
    assert dialog is not None
    assert all(button(dialog, text).isEnabled() for text in CHOICES)

    # V17: a choice would resume the run, so it waits for a running task
    with task_running(qtbot, app, first):
        assert not any(button(dialog, text).isEnabled() for text in CHOICES)

    assert all(button(dialog, text).isEnabled() for text in CHOICES)


def test_action_error_dialog_is_closed_by_reset(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    boxes: MessageBoxes,
) -> None:
    first, second = interrupt_run(qtbot, app, monkeypatch)

    app.window.top_bar.reset_button.click()

    assert boxes.titles() == ["Data will be lost!"]
    assert app.window.error_dialog is None
    assert app.run.state is AppState.EDITING
    assert (first.ctx.slice, second.ctx.slice) == (0, 0)


def fail_first_slice(monkeypatch: pytest.MonkeyPatch, action: Action) -> None:
    """Make the run fail as a whole (not as an action error) when it initialises the action."""

    def fail(_: Action) -> None:
        raise RuntimeError("disk gone")

    monkeypatch.setattr(type(action), "initialize_first_slice", fail)


def test_workflow_error_dialog_offers_only_terminate(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    fail_first_slice(monkeypatch, add_prepared(qtbot, app, "first"))

    app.window.top_bar.run_button.click()
    qtbot.waitUntil(
        lambda: app.window.workflow_error_dialog is not None, timeout=TIMEOUT_MS
    )

    dialog = app.window.workflow_error_dialog
    assert dialog is not None
    assert dialog.windowTitle() == "Workflow error"
    assert [b.text() for b in children(dialog, QPushButton)] == ["Terminate workflow"]
    assert app.run.state is AppState.INTERRUPTED
    assert app.window.error_dialog is None


def test_workflow_error_dialog_terminates_without_asking(
    qtbot: QtBot,
    app: Composition,
    monkeypatch: pytest.MonkeyPatch,
    exits: ExitCalls,
    boxes: MessageBoxes,
) -> None:
    fail_first_slice(monkeypatch, add_prepared(qtbot, app, "first"))
    app.window.top_bar.run_button.click()
    qtbot.waitUntil(
        lambda: app.window.workflow_error_dialog is not None, timeout=TIMEOUT_MS
    )
    dialog = app.window.workflow_error_dialog
    assert dialog is not None

    button(dialog, "Terminate workflow").click()

    assert exits.codes == [0]
    assert boxes.calls == []
    assert "Terminating workflow." in logged_messages(
        app.session.workflow_dir, "workflow", app.session.slice
    )


def test_workflow_error_dialog_terminates_on_escape(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch, exits: ExitCalls
) -> None:
    fail_first_slice(monkeypatch, add_prepared(qtbot, app, "first"))
    app.window.top_bar.run_button.click()
    qtbot.waitUntil(
        lambda: app.window.workflow_error_dialog is not None, timeout=TIMEOUT_MS
    )
    dialog = app.window.workflow_error_dialog
    assert dialog is not None

    dialog.reject()

    assert exits.codes == [0]


def test_action_error_dialog_names_the_failure(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    interrupt_run(qtbot, app, monkeypatch)
    dialog = app.window.error_dialog
    assert dialog is not None

    labels = [label.text() for label in children(dialog, QLabel)]
    assert "Action 'second' failed." in labels
    assert any(FAILURE_MESSAGE in text for text in labels)
