# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The action list: item view data, add, selection, inline rename, context menu, locks, indicators."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit.app import prepare, wait_for_state
from gui_testkit.driving import (
    RUNNABLE_ACTION,
    add_prepared,
    add_through_dialog,
    answering,
    children,
    choose_from_context_menu,
    interrupt_run,
    item_of,
    open_app,
    panel_of,
    press,
    rename_inline,
    task_running,
)
from gui_testkit.workflows import simulated_workflow
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QAbstractItemView, QDialogButtonBox

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.ui.app.action_status import ActionIndicator
from fibsem_maestro.ui.app.files import WorkflowFiles
from fibsem_maestro.ui.app.run_state import AppState
from fibsem_maestro.ui.app.session import WorkflowSession
from fibsem_maestro.ui.views.action_list.add_dialog import AddActionDialog
from fibsem_maestro.ui.views.action_list.item import action_item_view

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    import pytest
    from gui_testkit.dialogs import DirectoryChoices, MessageBoxes
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.user_config import UserConfig
    from fibsem_maestro.ui.composition import Composition
    from fibsem_maestro.workflow.workflow import Workflow

ANY_TYPE = sorted(ACTION_REGISTRY)[0]
"""Any action type: the list treats every type alike."""


def names(app: Composition) -> list[str]:
    return [a.name for a in app.session.actions]


def test_action_item_view_shows_the_badge_only_with_dependents(
    add_action: Callable[..., Action],
) -> None:
    action = add_action(ANY_TYPE, "first")

    alone = action_item_view(action, ActionIndicator(True, False, 7), [])
    parent = action_item_view(action, ActionIndicator(False, True, 0), ["a", "b"])

    assert alone.name == "first"
    assert alone.badge_text is None
    assert "7" in alone.name_tooltip
    assert (alone.prepared, alone.next_to_run) == (True, False)
    assert parent.badge_text == "→2"
    assert "a" in parent.badge_tooltip and "b" in parent.badge_tooltip
    assert (parent.prepared, parent.next_to_run) == (False, True)


def test_action_list_add_dialog_adds_and_selects_the_new_action(
    app: Composition,
) -> None:
    add_through_dialog(app, ANY_TYPE, "first")
    second = add_through_dialog(app, ANY_TYPE, "second")

    assert names(app) == ["first", "second"]
    assert app.window.action_list.current_action is second
    assert app.window.panel_host.currentWidget() is panel_of(app, second)


def test_action_list_add_dialog_refuses_a_taken_name(app: Composition) -> None:
    app.commands.add_action(ANY_TYPE, "taken")

    def try_taken(dialog: AddActionDialog) -> None:
        dialog.name_edit.setText("Taken")
        (box,) = children(dialog, QDialogButtonBox)
        ok = box.button(QDialogButtonBox.StandardButton.Ok)
        assert ok is not None and not ok.isEnabled()
        press(dialog, QDialogButtonBox.StandardButton.Cancel)

    with answering(AddActionDialog, try_taken) as shown:
        app.window.action_list.add_button.click()

    # cancelled: nothing added
    assert shown
    assert names(app) == ["taken"]


def test_action_list_remove_selects_the_successor_or_the_new_last_row(
    app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    first = app.commands.add_action(ANY_TYPE, "first")
    middle = app.commands.add_action(ANY_TYPE, "middle")
    last = app.commands.add_action(ANY_TYPE, "last")
    view = app.window.action_list
    view.select(middle)

    choose_from_context_menu(monkeypatch, view, 1, "Remove")

    assert names(app) == ["first", "last"]
    assert view.current_action is last

    choose_from_context_menu(monkeypatch, view, 1, "Remove")

    assert names(app) == ["first"]
    assert view.current_action is first
    assert app.window.panel_host.currentWidget() is panel_of(app, first)


def test_action_list_import_selects_nothing_when_the_row_is_gone(
    tmp_path: Path, app: Composition, directory_choice: DirectoryChoices
) -> None:
    app.commands.add_action(ANY_TYPE, "first")
    app.window.action_list.select(app.commands.add_action(ANY_TYPE, "second"))
    source = tmp_path / "source"
    source.mkdir()
    WorkflowSession(simulated_workflow(source), source, WorkflowFiles()).add_action(
        ANY_TYPE, "imported"
    )
    directory_choice.path = str(source)

    app.window.top_bar.import_button.click()

    assert names(app) == ["imported"]
    assert app.window.action_list.current_action is None
    assert app.window.panel_host.currentWidget() is app.window.panel_host.widget(0)


def test_action_list_rename_inline_renames_the_action(
    qtbot: QtBot, app: Composition
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")

    rename_inline(qtbot, item_of(app, action), "  renamed  ")

    assert action.name == "renamed"
    item = item_of(app, action)
    assert item.name_label.text() == "renamed"
    assert not item.name_edit.isVisible()


def test_action_list_rename_to_an_invalid_name_shows_an_error_and_reverts(
    qtbot: QtBot, app: Composition, boxes: MessageBoxes
) -> None:
    app.commands.add_action(ANY_TYPE, "other")
    action = app.commands.add_action(ANY_TYPE, "first")
    item = item_of(app, action)

    rename_inline(qtbot, item, "Other")

    assert boxes.titles() == ["Invalid name"]
    assert action.name == "first"
    assert item.name_label.text() == "first"
    # reverted before the box, so the focus loss that follows renames nothing
    assert item.name_edit.text() == "first"


def test_action_list_rename_to_the_same_name_does_nothing(
    qtbot: QtBot, app: Composition, boxes: MessageBoxes
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")

    with qtbot.assertNotEmitted(app.session.action_renamed):
        rename_inline(qtbot, item_of(app, action), "first ")

    assert boxes.calls == []


def test_action_list_rename_reports_a_directory_it_could_not_move(
    qtbot: QtBot, app: Composition, boxes: MessageBoxes
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")
    # a stray directory where the renamed action's directory would go
    (app.session.workflow_dir / "renamed").mkdir()
    (app.session.workflow_dir / "renamed" / "stray.txt").write_text("x")

    rename_inline(qtbot, item_of(app, action), "renamed")

    assert boxes.titles() == ["Could not rename action"]
    assert action.name == "first"
    assert item_of(app, action).name_label.text() == "first"


def test_action_list_duplicate_keeps_the_selection(
    app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")
    app.window.action_list.select(action)

    choose_from_context_menu(monkeypatch, app.window.action_list, 0, "Duplicate")

    assert names(app) == ["first", "first 2"]
    assert app.window.action_list.current_action is action


def test_action_list_remove_reports_a_directory_left_behind(
    qtbot: QtBot,
    request: pytest.FixtureRequest,
    workflow: Workflow,
    workflow_dir: Path,
    user_config: UserConfig,
    monkeypatch: pytest.MonkeyPatch,
    boxes: MessageBoxes,
) -> None:
    def refuse(path: Path) -> None:
        raise PermissionError(f"locked: {path.name}")

    app = open_app(
        qtbot, request, workflow, workflow_dir, user_config, WorkflowFiles(refuse)
    )
    app.commands.add_action(ANY_TYPE, "first")

    choose_from_context_menu(monkeypatch, app.window.action_list, 0, "Remove")

    assert app.session.actions == ()
    assert boxes.titles() == ["Could not remove action directory"]


def test_action_list_structure_is_locked_while_a_task_runs(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    action = app.commands.add_action(ANY_TYPE, "first")
    view = app.window.action_list

    with task_running(qtbot, app, action):
        assert not view.add_button.isEnabled()
        assert view.list_widget.dragDropMode() == (
            QAbstractItemView.DragDropMode.NoDragDrop
        )
        qtbot.mouseDClick(item_of(app, action).name_label, Qt.MouseButton.LeftButton)
        assert not item_of(app, action).name_edit.isVisible()
        entries = choose_from_context_menu(monkeypatch, view, 0, "Remove")
        assert entries == {"Remove": False, "Duplicate": False}
        assert names(app) == ["first"]

    assert view.add_button.isEnabled()
    assert (
        view.list_widget.dragDropMode() == QAbstractItemView.DragDropMode.InternalMove
    )


def test_action_list_structure_is_locked_while_interrupted(
    qtbot: QtBot, app: Composition, monkeypatch: pytest.MonkeyPatch
) -> None:
    first, _ = interrupt_run(qtbot, app, monkeypatch)
    view = app.window.action_list

    assert app.run.state is AppState.INTERRUPTED
    assert not view.add_button.isEnabled()
    qtbot.mouseDClick(item_of(app, first).name_label, Qt.MouseButton.LeftButton)
    assert not item_of(app, first).name_edit.isVisible()
    entries = choose_from_context_menu(monkeypatch, view, 0, None)
    assert entries == {"Remove": False, "Duplicate": False}


def test_action_list_indicators_follow_the_run(qtbot: QtBot, app: Composition) -> None:
    first = app.commands.add_action(RUNNABLE_ACTION, "first")
    assert not item_of(app, first).check_mark.is_on

    prepare(qtbot, app.commands, app.tasks, first)
    add_prepared(qtbot, app, "second")
    assert item_of(app, first).check_mark.is_on
    # no arrow while editing
    assert not any(item_of(app, a).arrow.is_on for a in app.session.actions)

    app.window.top_bar.run_button.click()
    app.window.top_bar.run_button.click()
    wait_for_state(qtbot, app.run, AppState.PAUSED)

    next_action = app.session.workflow.next_pending_action() or first
    arrows = [item_of(app, a).arrow.is_on for a in app.session.actions]
    assert arrows == [a is next_action for a in app.session.actions]
    assert str(next_action.ctx.slice) in item_of(app, next_action).name_label.toolTip()


def test_action_list_badge_follows_the_rules(app: Composition) -> None:
    parent = app.commands.add_action(ANY_TYPE, "parent")
    app.commands.add_action(ANY_TYPE, "child")
    badge = item_of(app, parent).badge
    assert badge.isHidden()

    rule = app.commands.add_rule(parent)
    app.commands.set_rule_dependents(rule, ["child"])
    assert not item_of(app, parent).badge.isHidden()
    assert item_of(app, parent).badge.text() == "→1"

    app.commands.remove_rule(rule)
    assert item_of(app, parent).badge.isHidden()
