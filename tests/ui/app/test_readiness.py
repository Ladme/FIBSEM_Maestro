# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`Readiness`, `assess_readiness` and `readiness_tooltip`: why Run is disabled."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gui_testkit.app import wait_for_task

from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.ui.app.audit import AuditIssue
from fibsem_maestro.ui.app.readiness import (
    ReadinessReport,
    assess_readiness,
    readiness_tooltip,
)
from fibsem_maestro.workflow.workflow import Workflow

if TYPE_CHECKING:
    from collections.abc import Callable, Collection, Sequence

    from gui_testkit.app import Services
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.session import WorkflowSession

KEY = "adjust_props"


def assess(
    actions: Sequence[Action],
    *,
    workflow_slice: int = 0,
    preparation_issues: Sequence[str] = (),
    completion_reasons: Sequence[str] = (),
    audit: Sequence[AuditIssue] = (),
    forms_with_errors: Collection[Action] = (),
    paused: bool = False,
) -> tuple[str, ...]:
    return assess_readiness(
        actions,
        workflow_slice,
        preparation_issues,
        completion_reasons,
        audit,
        forms_with_errors,
        paused,
    ).reasons


@pytest.fixture
def prepared(add_action: Callable[..., Action]) -> Action:
    return add_action(KEY, "prepared", prepare=True)


def test_assess_readiness_ready(prepared: Action) -> None:
    assert assess([prepared]) == ()
    assert ReadinessReport(()).ready


def test_assess_readiness_no_actions() -> None:
    assert assess([]) == ("The workflow has no actions.",)


def test_assess_readiness_all_slices_acquired(prepared: Action) -> None:
    assert assess([prepared], workflow_slice=Workflow.MAX_SLICE) == ()
    assert assess([prepared], workflow_slice=Workflow.MAX_SLICE + 1) == (
        f"All {Workflow.MAX_SLICE} slices have been acquired.",
    )


def test_assess_readiness_unprepared_names_action_slice(
    add_action: Callable[..., Action],
) -> None:
    action = add_action(KEY, "raw")
    action.ctx.set_slice(7)
    assert assess([action]) == ("'raw' is not prepared for slice 7.",)


def test_assess_readiness_lists_workflow_reasons(prepared: Action) -> None:
    reasons = ("'a': first", "'b': second")
    assert assess([prepared], preparation_issues=reasons) == reasons
    assert assess([prepared], completion_reasons=reasons) == reasons


def test_assess_readiness_paused_ignores_completion(prepared: Action) -> None:
    assert assess([prepared], completion_reasons=("'m': used up",), paused=True) == ()
    assert assess([prepared], preparation_issues=("'d': issue",), paused=True) == (
        "'d': issue",
    )


def test_assess_readiness_lists_audit_issues(prepared: Action) -> None:
    issue = AuditIssue(prepared, "pattern type", "A value is required.")
    assert assess([prepared], audit=[issue]) == (
        "'prepared': pattern type: A value is required.",
    )


def test_assess_readiness_form_error_only_without_audit_issue(
    prepared: Action, add_action: Callable[..., Action]
) -> None:
    other = add_action(KEY, "other", prepare=True)
    issue = AuditIssue(prepared, "x", "y")
    assert assess(
        [prepared, other], audit=[issue], forms_with_errors={prepared, other}
    ) == (
        "'prepared': x: y",
        "'other': the settings form shows an invalid value.",
    )


def test_assess_readiness_order(add_action: Callable[..., Action]) -> None:
    raw = add_action(KEY, "raw")
    ready = add_action(KEY, "ready", prepare=True)
    assert assess(
        [raw, ready],
        workflow_slice=Workflow.MAX_SLICE + 1,
        preparation_issues=["'raw': issue"],
        completion_reasons=["'ready': done"],
        audit=[AuditIssue(raw, "where", "what")],
        forms_with_errors={ready},
    ) == (
        f"All {Workflow.MAX_SLICE} slices have been acquired.",
        "'raw' is not prepared for slice 0.",
        "'raw': issue",
        "'ready': done",
        "'raw': where: what",
        "'ready': the settings form shows an invalid value.",
    )


def test_readiness_tooltip_lists_reasons() -> None:
    assert readiness_tooltip([], "Cannot start:") == ""
    assert readiness_tooltip(["a", "b"], "Cannot start:") == "Cannot start:\n• a\n• b"


def test_readiness_tooltip_truncates_after_limit() -> None:
    reasons = [f"r{i}" for i in range(15)]
    lines = readiness_tooltip(reasons, "Cannot resume:", limit=12).split("\n")
    assert lines == [
        "Cannot resume:",
        *(f"• r{i}" for i in range(12)),
        "• … and 3 more",
    ]
    assert "more" not in readiness_tooltip(reasons[:12], "h", limit=12)


def test_readiness_computed_at_start(services: Services) -> None:
    assert services.readiness.report.reasons == ("The workflow has no actions.",)


def test_readiness_follows_structure_and_props(
    qtbot: QtBot, services: Services, session: WorkflowSession
) -> None:
    readiness = services.readiness
    with qtbot.waitSignal(readiness.changed):
        action = session.add_action(KEY, "action")
    assert readiness.report.reasons == ("'action' is not prepared for slice 0.",)

    action.prepare()
    with qtbot.waitSignal(readiness.changed):
        session.props_changed(action)
    assert readiness.report.ready

    with qtbot.waitSignal(readiness.changed):
        session.reset()
    assert not readiness.report.ready


def test_readiness_follows_form_validity(
    qtbot: QtBot, services: Services, prepared: Action
) -> None:
    readiness = services.readiness
    with qtbot.waitSignal(readiness.changed):
        services.validity.set_has_errors(prepared, True)
    assert not readiness.report.ready
    with qtbot.waitSignal(readiness.changed):
        services.validity.forget(prepared)
    assert readiness.report.ready


def test_readiness_follows_rules(
    qtbot: QtBot,
    services: Services,
    session: WorkflowSession,
    add_action: Callable[..., Action],
) -> None:
    parent = add_action(KEY, "parent", prepare=True)
    add_action(KEY, "child", prepare=True)
    rule = session.add_rule(parent)
    session.set_rule_dependents(rule, ["child"])
    assert services.readiness.report.ready

    # a property the parent does not collect makes the rule fail at run time
    with qtbot.waitSignal(services.readiness.changed):
        session.set_rule_properties(rule, PropertyNames(microscope=["stage_position"]))
    assert not services.readiness.report.ready


def test_readiness_emits_only_on_change(
    qtbot: QtBot, services: Services, session: WorkflowSession, prepared: Action
) -> None:
    with qtbot.assertNotEmitted(services.readiness.changed):
        session.commit_settings(prepared)


def test_readiness_recomputes_after_failed_prepare(
    qtbot: QtBot,
    services: Services,
    add_action: Callable[..., Action],
) -> None:
    """A Prepare can write the props and then fail, without any session signal."""
    action = add_action(KEY, "action")

    def prepare_then_fail() -> None:
        action.prepare()
        raise RuntimeError("template creation failed")

    handle = services.commands.run_microscope_task(
        action, "Preparing", prepare_then_fail
    )
    failed: list[object] = []
    handle.failed.connect(failed.append)
    wait_for_task(qtbot, services.tasks, handle)

    assert len(failed) == 1
    assert services.readiness.report.ready


def test_form_validity_emits_only_on_change(
    qtbot: QtBot, services: Services, prepared: Action
) -> None:
    validity = services.validity
    with qtbot.waitSignal(validity.changed):
        validity.set_has_errors(prepared, True)
    with qtbot.assertNotEmitted(validity.changed):
        validity.set_has_errors(prepared, True)
    assert validity.owners_with_errors() == {prepared}
    with qtbot.waitSignal(validity.changed):
        validity.forget(prepared)
    assert validity.owners_with_errors() == frozenset()
