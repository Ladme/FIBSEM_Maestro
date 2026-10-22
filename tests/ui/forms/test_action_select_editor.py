# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The action selector follows its action catalog: types, additions, removals and renames."""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from gui_testkit.forms import FakeCatalog, combo_texts, editor_at, messages
from gui_testkit.sample_settings import LINKED_NAME, KitchenSink, RequiredLink

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.ui.forms.editors.action_select import ActionSelectWidget

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.forms.builder import Form


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
) -> Callable[..., ActionSelectWidget]:
    """Build a selector over `catalog` offering the actions of the first kind."""

    def build(default: str | None = None, optional: bool = False) -> ActionSelectWidget:
        selector = ActionSelectWidget(
            catalog.port(),
            type_filter=[ACTION_REGISTRY.get(kinds[0])],
            default=default,
            optional=optional,
        )
        qtbot.addWidget(selector)
        return selector

    return build


class ChangeCounter:
    """Counts an editor's change notifications."""

    def __init__(self) -> None:
        self.count = 0

    def __call__(self) -> None:
        self.count += 1


@pytest.fixture
def first_kind(
    add_action: Callable[..., Action], kinds: tuple[str, str]
) -> Callable[[str], Action]:
    return lambda name: add_action(kinds[0], name)


def test_selector_offers_only_actions_of_allowed_types_in_order(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    add_action: Callable[..., Action],
    kinds: tuple[str, str],
) -> None:
    first = add_action(kinds[0], "first")
    other = add_action(kinds[1], "other kind")
    last = add_action(kinds[0], "last")
    catalog.replace([first, other, last])

    selector = selector_of(default="last")

    assert combo_texts(selector) == ["first", "last"]
    assert selector.get_value() == "last"


def test_optional_selector_offers_none_first(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("only")])

    selector = selector_of(optional=True)

    assert combo_texts(selector) == ["(none)", "only"]
    assert selector.get_value() is None


def test_unknown_name_selects_nothing(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("only")])

    selector = selector_of(default="missing")

    assert selector.currentIndex() == -1
    assert selector.get_value() is None


def test_selector_follows_added_actions_keeping_its_selection_silently(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    kept = first_kind("kept")
    catalog.replace([kept])
    selector = selector_of(default="kept")
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([first_kind("new"), kept])

    assert combo_texts(selector) == ["new", "kept"]
    assert selector.get_value() == "kept"
    assert changes.count == 0


def test_removing_the_selected_action_notifies_once(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    removed, stays = first_kind("removed"), first_kind("stays")
    catalog.replace([removed, stays])
    selector = selector_of(default="removed")
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.replace([stays])

    assert combo_texts(selector) == ["stays"]
    assert selector.get_value() is None
    assert changes.count == 1


def test_renamed_action_is_shown_under_its_new_name(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    action = first_kind("before")
    catalog.replace([action])
    selector = selector_of(default="before")
    changes = ChangeCounter()
    selector.on_change(changes)

    catalog.rename(action, "after")

    assert combo_texts(selector) == ["after"]
    assert selector.get_value() == "after"
    assert changes.count == 0


def test_replaced_action_of_the_same_name_is_a_change(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    session: WorkflowSession,
    first_kind: Callable[[str], Action],
) -> None:
    """After an import a different action carries the name: the link is written again."""
    original = first_kind("same")
    catalog.replace([original])
    selector = selector_of(default="same")
    changes = ChangeCounter()
    selector.on_change(changes)
    session.remove_action(original)

    catalog.replace([first_kind("same")])

    assert selector.get_value() == "same"
    assert changes.count == 1


def test_detached_selector_ignores_the_catalog(
    selector_of: Callable[..., ActionSelectWidget],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    catalog.replace([first_kind("kept")])
    selector = selector_of(default="kept")

    selector.detach()
    catalog.replace([])

    assert combo_texts(selector) == ["kept"]
    selector.detach()


def test_detach_after_destruction_is_harmless(
    qtbot: QtBot, selector_of: Callable[..., ActionSelectWidget]
) -> None:
    selector = selector_of()
    with qtbot.waitSignal(selector.destroyed, timeout=1000):
        selector.deleteLater()

    selector.detach()
    selector.detach()


def test_form_link_to_a_removed_action_is_marked_and_kept(
    qtbot: QtBot, live_form: Callable[..., Form], catalog: FakeCatalog
) -> None:
    settings = RequiredLink(target=LINKED_NAME)
    form = live_form(settings)
    assert not form.has_errors()

    with qtbot.waitSignal(form.validity_changed, timeout=1000) as appeared:
        catalog.replace([])

    assert appeared.args == [True]
    assert messages(editor_at(form.widget, "target")) == ["A value is required."]
    assert settings.target == LINKED_NAME


def test_disposed_form_ignores_catalog_changes(
    live_form: Callable[..., Form],
    catalog: FakeCatalog,
    first_kind: Callable[[str], Action],
) -> None:
    settings = KitchenSink(linked=LINKED_NAME)
    commits: list[str] = []
    form = live_form(settings, on_commit=commits.append)
    selector = editor_at(form.widget, "linked")
    assert isinstance(selector, ActionSelectWidget)

    form.dispose()
    catalog.replace([first_kind("new")])

    assert combo_texts(selector) == ["(none)", LINKED_NAME]
    assert settings.linked == LINKED_NAME
    assert commits == []
