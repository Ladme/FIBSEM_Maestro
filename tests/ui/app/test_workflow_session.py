# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`WorkflowSession`: the structure invariants I1–I11 and their persistence."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gui_testkit.situations import link_pairs
from gui_testkit.windows_lock import windows_like_delete

from fibsem_maestro.action_context.file import FileActionContext
from fibsem_maestro.notifications.null_notifier import NullNotifier
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.ui.app.errors import (
    ActionRenameError,
    InvalidActionNameError,
    WorkflowImportError,
    WorkflowResetError,
)
from fibsem_maestro.ui.app.files import WorkflowFiles
from fibsem_maestro.ui.app.session import WorkflowSession
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.propagations import Propagations
from fibsem_maestro.workflow.workflow import Workflow, WorkflowState

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.workflow.propagations import PropagationRule

KEY = "adjust_props"
"""A plain action type; these tests depend on no action's specific behaviour."""


def stored_state(session: WorkflowSession) -> WorkflowState:
    """The workflow `state.yaml` of the session's current slice, as read from disk."""
    return session.workflow.ctx.state_store.read("state.yaml", WorkflowState)


def complete_rule(
    session: WorkflowSession, parent: Action, *dependents: str
) -> PropagationRule:
    rule = session.add_rule(parent)
    session.set_rule_dependents(rule, dependents)
    session.set_rule_properties(rule, PropertyNames(electron_beam=["working_distance"]))
    return rule


def record(session: WorkflowSession) -> list[str]:
    """The names of the session's signals, in emission order."""
    emitted: list[str] = []
    for name in (
        "structure_changed",
        "action_removed",
        "action_renamed",
        "action_settings_changed",
        "action_props_changed",
        "rules_changed",
        "workflow_replaced",
        "workflow_reset",
    ):
        getattr(session, name).connect(lambda *_, n=name: emitted.append(n))
    return emitted


@pytest.fixture
def windows_session(
    qtbot: QtBot, workflow: Workflow, workflow_dir: Path
) -> WorkflowSession:
    """A session whose deletions fail like on Windows while a file is open."""
    _ = qtbot
    return WorkflowSession(workflow, workflow_dir, WorkflowFiles(windows_like_delete))


@pytest.fixture
def source_dir(tmp_path: Path, workflow: Workflow, qtbot: QtBot) -> Path:
    """Another workflow directory, with actions "first" and "second one" and a rule."""
    _ = qtbot
    directory = tmp_path / "source"
    source = WorkflowSession(
        Workflow(
            workflow.microscope,
            Actions(),
            Propagations(),
            FileActionContext(directory / "workflow", "workflow"),
        ),
        directory,
        WorkflowFiles(),
    )
    complete_rule(source, source.add_action(KEY, "first"), "second one")
    source.add_action(KEY, "second one")
    return directory


def test_session_construction_writes_state_and_microscope_settings(
    session: WorkflowSession,
) -> None:
    view = session.workflow.ctx.current_view.path()
    assert (view / "state.yaml").is_file()
    assert (view / "microscope_settings.yaml").is_file()


def test_session_add_action_persists_in_own_directory_at_workflow_slice(
    session: WorkflowSession,
) -> None:
    actions_list = session.workflow.actions
    session.workflow.ctx.set_slice(4)

    action = session.add_action(KEY, "my action")

    assert action.ctx.path_to_dir == session.workflow_dir / "my_action"
    assert action.ctx.slice == 4
    assert action.ctx.state_store.exists("state.yaml")
    assert action.ctx.settings_store.exists("settings.yaml")
    assert stored_state(session).action_names == ["my action"]
    # I9: the list every action resolves links through is extended, never replaced
    assert session.workflow.actions is actions_list


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "Name cannot be empty."),
        ("Taken_Name", "Name 'Taken_Name' is already in use."),
        ("WorkFlow", "Name 'workflow' is reserved."),
    ],
)
def test_session_add_action_rejects_invalid_name(
    session: WorkflowSession, add_action: Callable[..., Action], name: str, message: str
) -> None:
    add_action(KEY, "taken name")
    with pytest.raises(InvalidActionNameError) as info:
        session.add_action(KEY, name)
    assert str(info.value) == message
    assert len(session.actions) == 1


def test_session_rename_rejects_invalid_name(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    action = add_action(KEY, "a")
    add_action(KEY, "b")
    for name in ("B", "workflow", ""):
        with pytest.raises(InvalidActionNameError):
            session.rename_action(action, name)
    assert action.name == "a"
    assert stored_state(session).action_names == ["a", "b"]


def test_session_rename_to_same_name_emits_nothing(
    qtbot: QtBot, session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    action = add_action(KEY, "same")
    with qtbot.assertNotEmitted(session.structure_changed):
        session.rename_action(action, "same")


def test_session_rename_moves_directory_and_persists(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    action = add_action(KEY, "old")
    emitted = record(session)

    session.rename_action(action, "new name")

    assert action.ctx.path_to_dir == session.workflow_dir / "new_name"
    assert (session.workflow_dir / "new_name").is_dir()
    assert not (session.workflow_dir / "old").exists()
    assert stored_state(session).action_names == ["new name"]
    assert emitted == ["action_renamed", "rules_changed", "structure_changed"]


def test_session_rename_follows_rules_in_place(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    child = add_action(KEY, "child")
    outgoing = complete_rule(session, parent, "child")
    incoming = complete_rule(session, child, "parent")

    session.rename_action(parent, "renamed")

    # I10: the same rule objects, edited
    assert session.rules_of(parent) == [outgoing]
    assert session.rules_of(parent)[0] is outgoing
    assert incoming.dependent_names == ["renamed"]
    assert [r.parent_name for r in stored_state(session).propagations] == [
        "renamed",
        "child",
    ]


@pytest.mark.parametrize(("linker_key", "field", "target_key"), link_pairs())
def test_session_rename_retargets_and_persists_links(
    session: WorkflowSession,
    add_action: Callable[..., Action],
    linker_key: str,
    field: str,
    target_key: str,
) -> None:
    target = add_action(target_key, "target")
    linker = add_action(linker_key, "linker")
    setattr(linker.settings, field, "target")
    changed: list[Action] = []
    session.action_settings_changed.connect(changed.append)

    session.rename_action(target, "renamed target")

    assert getattr(linker.settings, field) == "renamed target"
    stored = linker.ctx.settings_store.read("settings.yaml", type(linker.settings))
    assert getattr(stored, field) == "renamed target"
    assert changed == [linker]


def test_session_rename_onto_existing_directory_changes_nothing(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    action = add_action(KEY, "old")
    add_action(KEY, "other")
    rule = complete_rule(session, action, "other")
    (session.workflow_dir / "taken").mkdir()

    with pytest.raises(ActionRenameError) as info:
        session.rename_action(action, "taken")

    assert isinstance(info.value.__cause__, OSError)
    assert str(info.value) == str(info.value.__cause__)
    assert action.name == "old"
    assert (session.workflow_dir / "old").is_dir()
    assert rule.parent_name == "old"
    assert stored_state(session).action_names == ["old", "other"]


def test_session_remove_deletes_directory_and_parent_rules(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    child = add_action(KEY, "child")
    complete_rule(session, parent, "child")
    emitted = record(session)

    assert session.remove_action(parent) is None

    assert session.actions == (child,)
    assert session.workflow.propagations.rules == []
    assert not (session.workflow_dir / "parent").exists()
    assert stored_state(session).action_names == ["child"]
    assert emitted == ["action_removed", "rules_changed", "structure_changed"]


def test_session_remove_keeps_rule_left_without_dependents(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    rule = complete_rule(session, parent, "child")
    child = add_action(KEY, "child")

    session.remove_action(child)

    assert session.rules_of(parent) == [rule]
    assert rule.dependent_names == []
    assert stored_state(session).propagations[0].dependent_names == []


def test_session_remove_keeps_links_to_removed_action(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    linker_key, field, target_key = link_pairs()[0]
    target = add_action(target_key, "target")
    linker = add_action(linker_key, "linker")
    setattr(linker.settings, field, "target")

    session.remove_action(target)

    # a broken link is shown and blocks Run; it is never cleared silently
    assert getattr(linker.settings, field) == "target"


def test_session_remove_reports_directory_error_and_still_removes(
    windows_session: WorkflowSession,
) -> None:
    action = windows_session.add_action(KEY, "held")
    held = windows_session.workflow_dir / "held" / "held.txt"

    with held.open("w"):
        error = windows_session.remove_action(action)

    assert isinstance(error, PermissionError)
    assert windows_session.actions == ()
    assert stored_state(windows_session).action_names == []


def test_session_empty_rule_survives_structure_changes(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    rule = session.add_rule(parent)

    session.remove_action(add_action(KEY, "temporary"))
    session.move_actions(0, 1, 0)

    assert session.rules_of(parent)[0] is rule


def test_session_remove_rule_by_identity(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    first = session.add_rule(parent)
    second = session.add_rule(parent)
    assert first == second  # equal by value

    session.remove_rule(second)

    assert session.rules_of(parent)[0] is first


def test_session_rejects_rule_of_another_workflow(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    rule = session.add_rule(add_action(KEY, "parent"))
    session.remove_rule(rule)
    with pytest.raises(ValueError, match="not a rule of this workflow"):
        session.set_rule_dependents(rule, ["x"])


@pytest.mark.parametrize(
    "via", ["commit_settings", "props_changed", "write_properties"]
)
def test_session_persists_settings_before_emitting(
    session: WorkflowSession, add_action: Callable[..., Action], via: str
) -> None:
    action = add_action(KEY, "action", prepare=True)
    props = action.read_properties()
    action.ctx.set_slice(3)  # a slice without settings.yaml yet
    action.write_properties(props)
    seen: list[bool] = []

    def check(changed: Action) -> None:
        seen.append(changed.ctx.settings_store.exists("settings.yaml"))

    session.action_settings_changed.connect(check)
    session.action_props_changed.connect(check)
    if via == "write_properties":
        session.write_properties(action, props)
    else:
        getattr(session, via)(action)

    assert seen == [True]


def test_session_rules_persist_before_rules_changed(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    seen: list[int] = []
    session.rules_changed.connect(
        lambda: seen.append(len(stored_state(session).propagations))
    )

    rule = session.add_rule(parent)
    session.remove_rule(rule)

    assert seen == [1, 0]


def test_session_commit_microscope_settings_writes_file(
    session: WorkflowSession,
) -> None:
    path = session.workflow.ctx.current_view.path() / "microscope_settings.yaml"
    path.unlink()
    session.commit_microscope_settings()
    assert path.is_file()


def test_session_move_reorders_shared_list(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    a, b, c, d = (add_action(KEY, name) for name in "abcd")
    actions_list = session.workflow.actions

    session.move_actions(0, 2, 2)

    assert session.actions == (c, d, a, b)
    assert session.workflow.actions is actions_list
    assert stored_state(session).action_names == ["c", "d", "a", "b"]


def test_session_move_clamps_slices_and_persists_clamped_actions(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    first = add_action(KEY, "first")
    second = add_action(KEY, "second")
    first.ctx.set_slice(5)
    second.ctx.set_slice(4)

    # the lagging action dragged to the top may not lag behind the one below it
    session.move_actions(1, 1, 0)

    assert session.actions == (second, first)
    assert second.ctx.slice == 5
    assert second.ctx.state_store.exists("state.yaml")
    assert second.ctx.settings_store.exists("settings.yaml")


@pytest.mark.parametrize(
    ("start", "count", "destination"), [(0, 1, 2), (1, 2, 0), (0, 0, 0)]
)
def test_session_move_out_of_range_raises(
    session: WorkflowSession,
    add_action: Callable[..., Action],
    start: int,
    count: int,
    destination: int,
) -> None:
    actions = (add_action(KEY, "a"), add_action(KEY, "b"))
    with pytest.raises(IndexError):
        session.move_actions(start, count, destination)
    assert session.actions == actions


def test_session_duplicate_copies_settings_and_outgoing_rules(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    original = add_action(KEY, "original")
    add_action(KEY, "child")
    rule = complete_rule(session, original, "child")

    copy = session.duplicate_action(original)

    assert copy.name == "original 2"
    assert copy.settings == original.settings
    assert copy.settings is not original.settings
    assert (
        copy.settings.properties_to_collect
        is not original.settings.properties_to_collect
    )
    (copied_rule,) = session.rules_of(copy)
    assert copied_rule.dependent_names == ["child"]
    assert copied_rule is not rule
    assert copy.ctx.settings_store.exists("settings.yaml")
    assert stored_state(session).action_names == ["original", "child", "original 2"]


def test_session_duplicate_name_avoids_directory_collision(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    original = add_action(KEY, "imaging")
    add_action(KEY, "imaging_2")

    copy = session.duplicate_action(original)

    # "imaging 2" would share the directory of "imaging_2"
    assert copy.name == "imaging 3"
    assert copy.ctx.path_to_dir == session.workflow_dir / "imaging_3"


def test_session_new_workflow_keeps_microscope_and_notifier(
    session: WorkflowSession, tmp_path: Path
) -> None:
    session.workflow.notifier = notifier = NullNotifier()  # not the shared default
    old = session.workflow
    emitted = record(session)

    session.new_workflow(tmp_path / "fresh")

    assert session.workflow is not old
    assert session.workflow_dir == tmp_path / "fresh"
    assert session.workflow.notifier is notifier
    assert session.workflow.microscope is old.microscope
    assert session.actions == ()
    view = session.workflow.ctx.current_view.path()
    assert view.is_relative_to(tmp_path / "fresh")
    assert (view / "state.yaml").is_file()
    assert (view / "microscope_settings.yaml").is_file()
    assert emitted == ["workflow_replaced", "structure_changed", "rules_changed"]


def test_session_new_workflow_failure_changes_nothing(
    qtbot: QtBot, session: WorkflowSession, tmp_path: Path
) -> None:
    old, old_dir = session.workflow, session.workflow_dir
    target = tmp_path / "new"
    target.mkdir()
    (target / "workflow").write_text("a file where the workflow directory must go")

    with qtbot.assertNotEmitted(session.workflow_replaced), pytest.raises(OSError):
        session.new_workflow(target)

    assert session.workflow is old
    assert session.workflow_dir == old_dir


def test_session_import_replaces_actions_and_rules(
    session: WorkflowSession, add_action: Callable[..., Action], source_dir: Path
) -> None:
    old = add_action(KEY, "old")
    removed: list[Action] = []
    session.action_removed.connect(removed.append)
    emitted = record(session)

    session.import_workflow(source_dir)

    first, second = session.actions
    assert (first.name, second.name) == ("first", "second one")
    assert removed == [old]
    assert not (session.workflow_dir / "old").exists()
    assert second.ctx.path_to_dir == session.workflow_dir / "second_one"
    assert second.ctx.settings_store.exists("settings.yaml")
    assert session.rules_of(first)[0].dependent_names == ["second one"]
    assert stored_state(session).action_names == ["first", "second one"]
    assert emitted[-2:] == ["structure_changed", "rules_changed"]


def test_session_import_failure_changes_nothing(
    session: WorkflowSession, add_action: Callable[..., Action], tmp_path: Path
) -> None:
    old = add_action(KEY, "old")
    (tmp_path / "not a workflow").mkdir()

    with pytest.raises(WorkflowImportError) as info:
        session.import_workflow(tmp_path / "not a workflow")

    assert str(info.value) == str(info.value.__cause__)
    assert session.actions == (old,)
    assert (session.workflow_dir / "old").is_dir()


def test_session_import_with_open_log_files_succeeds_on_windows(
    windows_session: WorkflowSession, source_dir: Path
) -> None:
    old = windows_session.add_action(KEY, "old")
    old.ctx.text_logger.info("opens the action's run.log")

    windows_session.import_workflow(source_dir)

    assert not (windows_session.workflow_dir / "old").exists()
    assert [a.name for a in windows_session.actions] == ["first", "second one"]


def test_session_reset_returns_everything_to_slice_zero(
    qtbot: QtBot, session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    action = add_action(KEY, "action", prepare=True)
    session.workflow.run(last_slice=2)
    assert (session.workflow_dir / "action" / "slice_0002").is_dir()

    with qtbot.waitSignal(session.workflow_reset):
        session.reset()

    assert (session.slice, action.ctx.slice) == (0, 0)
    assert not (session.workflow_dir / "action" / "slice_0002").exists()
    assert not action.has_stored_properties()
    assert action.ctx.settings_store.exists("settings.yaml")
    assert action.ctx.state_store.exists("state.yaml")
    assert stored_state(session).action_names == ["action"]


def test_session_reset_failure_is_wrapped(windows_session: WorkflowSession) -> None:
    windows_session.add_action(KEY, "action")
    held = windows_session.workflow_dir / "action" / "slice_0000" / "held.txt"

    with held.open("w"), pytest.raises(WorkflowResetError) as info:
        windows_session.reset()

    assert isinstance(info.value.__cause__, PermissionError)
    assert str(info.value) == str(info.value.__cause__)


def test_session_dependents_of_are_unique_in_first_seen_order(
    session: WorkflowSession, add_action: Callable[..., Action]
) -> None:
    parent = add_action(KEY, "parent")
    complete_rule(session, parent, "b", "a")
    complete_rule(session, parent, "a", "c")
    assert session.dependents_of(parent) == ["b", "a", "c"]
