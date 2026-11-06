# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The multiple action selector follows its catalog and never drops a link silently."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gui_testkit.forms import FakeCatalog, editor_at, messages
from gui_testkit.sample_settings import LINKED_NAME, KitchenSink

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.ui.forms.editors.action_multi_select import (
    ActionMultiSelectWidget,
)
from fibsem_maestro.ui.forms.issues import FieldValidationError

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.forms.builder import Form

UNAVAILABLE = "'{}' is not an available action."


def _unrelated_types() -> tuple[str, str]:
    """Registry keys of two action types neither of which is a subclass of the other."""
    for a in ACTION_REGISTRY:
        for b in ACTION_REGISTRY:
            type_a, type_b = ACTION_REGISTRY.get(a), ACTION_REGISTRY.get(b)
            if not issubclass(type_a, type_b) and not issubclass(type_b, type_a):
                return a, b
    raise AssertionError("the registry has no two unrelated action types")


@pytest.fixture
def kinds() -> tuple[str, str]:
    return _unrelated_types()


@pytest.fixture
def selector_of(
    qtbot: QtBot, catalog: FakeCatalog, kinds: tuple[str, str]
) -> Callable[..., ActionMultiSelectWidget]:
    """Build a selector over `catalog` offering the actions of the first kind."""

    def build(default: list[str] | None = None) -> ActionMultiSelectWidget:
        selector = ActionMultiSelectWidget(
            catalog.port(),
            type_filter=[ACTION_REGISTRY.get(kinds[0])],
            default=default,
        )
        qtbot.addWidget(selector)
        return selector

    return build


@pytest.fixture
def first_kind(
    add_action: Callable[..., Action], kinds: tuple[str, str]
) -> Callable[[str], Action]:
    return lambda name: add_action(kinds[0], name)


class ChangeCounter:
    """Counts an editor's change notifications."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


def rows(selector: ActionMultiSelectWidget) -> list[str]:
    """The texts of the selector's rows, in order."""
    return [item.text() for i in range(selector.count()) if (item := selector.item(i))]


def selected(selector: ActionMultiSelectWidget) -> list[str]:
    """The texts of the selected rows, in order."""
    return [
        item.text()
        for i in range(selector.count())
        if (item := selector.item(i)) and item.isSelected()
    ]


def deselect(selector: ActionMultiSelectWidget, text: str) -> None:
    """Deselect the row showing `text`, as the user would."""
    for i in range(selector.count()):
        if (item := selector.item(i)) and item.text() == text:
            item.setSelected(False)
            return
    raise AssertionError(f"no row {text!r}")


def unavailable_messages(selector: ActionMultiSelectWidget) -> list[str]:
    with pytest.raises(FieldValidationError) as info:
        selector.get_value()
    return [message for _, message in info.value.problems]


def test_selector_offers_only_actions_of_allowed_types_in_workflow_order(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    add_action: Callable[..., Action],
    kinds: tuple[str, str],
) -> None:
    first = add_action(kinds[0], "first")
    other = add_action(kinds[1], "other kind")
    last = add_action(kinds[0], "last")
    catalog.replace([first, other, last])

    selector = selector_of(default=["last", "first"])

    assert rows(selector) == ["first", "last"]
    assert selector.get_value() == ["first", "last"]


def test_user_selection_is_the_value(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("a"), first_kind("b")])
    selector = selector_of(default=["a", "b"])
    changes = ChangeCounter()
    selector.on_change(changes)

    deselect(selector, "a")

    assert selector.get_value() == ["b"]
    assert changes.count == 1


def test_selector_follows_added_actions_keeping_its_selection_silently(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    kept = first_kind("kept")
    catalog.replace([kept])
    selector = selector_of(default=["kept"])
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([first_kind("new"), kept])

    assert rows(selector) == ["new", "kept"]
    assert selector.get_value() == ["kept"]
    assert changes.count == 0


def test_reordering_selected_actions_is_not_a_change(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    a, b = first_kind("a"), first_kind("b")
    catalog.replace([a, b])
    selector = selector_of(default=["a", "b"])
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([b, a])

    assert selector.get_value() == ["b", "a"]
    assert changes.count == 0


def test_removed_selected_action_is_kept_marked_and_notifies_once(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    removed, stays = first_kind("removed"), first_kind("stays")
    catalog.replace([removed, stays])
    selector = selector_of(default=["removed", "stays"])
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([stays])

    assert rows(selector) == ["stays", "removed (not available)"]
    assert selected(selector) == ["stays", "removed (not available)"]
    assert unavailable_messages(selector) == [UNAVAILABLE.format("removed")]
    assert changes.count == 1


def test_deselecting_an_unavailable_name_drops_it(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("stays")])
    selector = selector_of(default=["stays", "gone"])

    deselect(selector, "gone (not available)")

    assert selector.get_value() == ["stays"]


def test_unavailable_names_are_reported_in_their_order(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
) -> None:
    catalog.replace([])

    selector = selector_of(default=["b", "a", "b"])

    assert rows(selector) == ["b (not available)", "a (not available)"]
    assert unavailable_messages(selector) == [
        UNAVAILABLE.format("b"),
        UNAVAILABLE.format("a"),
    ]


def test_readded_action_makes_the_link_valid_again(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    action = first_kind("back")
    catalog.replace([])
    selector = selector_of(default=["back"])
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([action])

    assert rows(selector) == ["back"]
    assert selector.get_value() == ["back"]
    assert changes.count == 1


def test_renamed_action_is_shown_under_its_new_name(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    action = first_kind("before")
    catalog.replace([action])
    selector = selector_of(default=["before"])
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.rename(action, "after")

    assert rows(selector) == ["after"]
    assert selector.get_value() == ["after"]
    assert changes.count == 0


def test_replaced_action_of_the_same_name_is_a_change(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    session: WorkflowSession,
    first_kind: Callable[[str], Action],
) -> None:
    """After an import a different action carries the name: the link is written again."""
    original = first_kind("same")
    catalog.replace([original])
    selector = selector_of(default=["same"])
    changes = ChangeCounter()
    selector.on_change(changes)
    session.remove_action(original)

    catalog.replace([first_kind("same")])

    assert selector.get_value() == ["same"]
    assert changes.count == 1


def test_set_value_selects_exactly_the_names(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("a"), first_kind("b")])
    selector = selector_of(default=["a"])
    changes = ChangeCounter()
    selector.on_change(changes)

    selector.set_value(["b"])
    selector.set_value(["b"])

    assert selector.get_value() == ["b"]
    assert changes.count == 1


def test_detached_selector_ignores_the_catalog(
    selector_of: Callable[..., ActionMultiSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("kept")])
    selector = selector_of(default=["kept"])

    selector.detach()
    catalog.replace([])

    assert rows(selector) == ["kept"]
    selector.detach()


def test_detach_after_destruction_is_harmless(
    qtbot: QtBot, selector_of: Callable[..., ActionMultiSelectWidget]
) -> None:
    selector = selector_of()
    with qtbot.waitSignal(selector.destroyed, timeout=1000):
        selector.deleteLater()

    selector.detach()
    selector.detach()


def test_form_marks_a_stored_name_that_is_not_offered(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink(linked_many=[LINKED_NAME, "missing"])

    form = live_form(settings)

    assert form.has_errors()
    assert messages(editor_at(form.widget, "linked_many")) == [
        UNAVAILABLE.format("missing")
    ]
    assert settings.linked_many == [LINKED_NAME, "missing"]


def test_form_link_to_a_removed_action_is_marked_and_kept_until_deselected(
    qtbot: QtBot, live_form: Callable[..., Form], catalog: FakeCatalog
) -> None:
    settings = KitchenSink(linked_many=[LINKED_NAME])
    commits: list[str] = []
    form = live_form(settings, on_commit=commits.append)
    assert not form.has_errors()

    with qtbot.waitSignal(form.validity_changed, timeout=1000) as appeared:
        catalog.replace([])

    assert appeared.args == [True]
    selector = editor_at(form.widget, "linked_many")
    assert messages(selector) == [UNAVAILABLE.format(LINKED_NAME)]
    assert settings.linked_many == [LINKED_NAME]
    assert commits == []

    assert isinstance(selector, ActionMultiSelectWidget)
    deselect(selector, f"{LINKED_NAME} (not available)")

    assert not form.has_errors()
    assert settings.linked_many == []
    assert commits == ["linked_many"]


def test_disposed_form_ignores_catalog_changes(
    live_form: Callable[..., Form],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    settings = KitchenSink(linked_many=[LINKED_NAME])
    commits: list[str] = []
    form = live_form(settings, on_commit=commits.append)
    selector = editor_at(form.widget, "linked_many")
    assert isinstance(selector, ActionMultiSelectWidget)

    form.dispose()
    catalog.replace([first_kind("new")])

    assert rows(selector) == [LINKED_NAME]
    assert settings.linked_many == [LINKED_NAME]
    assert commits == []
