# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Invalid values in live forms: shown and attributed, never written, and reported as validity."""

from __future__ import annotations

from typing import TYPE_CHECKING

from gui_testkit.forms import editor_at, field_at, messages, optional_checkbox
from gui_testkit.sample_settings import (
    CircleShape,
    KitchenSink,
    Optionals,
    PagedArea,
    PlainLayout,
    SquareShape,
)
from PyQt6.QtWidgets import QPlainTextEdit

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.pattern_type import PatternType
from fibsem_maestro.ui.forms.editors.union import DiscriminatedUnionWidget
from fibsem_maestro.ui.forms.issues import Severity

if TYPE_CHECKING:
    from collections.abc import Callable

    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.forms.builder import Form
    from fibsem_maestro.ui.forms.editor import FieldEditor

GREATER_THAN_ZERO = "Input should be greater than 0"


def _union(form: Form, path: str) -> DiscriminatedUnionWidget:
    union = editor_at(form.widget, path)
    assert isinstance(union, DiscriminatedUnionWidget)
    return union


def _errors(editor: FieldEditor[object]) -> list[str]:
    return [i.message for i in editor.issues() if i.severity is Severity.ERROR]


def test_invalid_value_is_shown_but_not_written(
    live_form: Callable[..., Form],
) -> None:
    settings = Optionals()
    commits: list[str] = []
    form = live_form(settings, on_commit=commits.append)
    limit = field_at(form.widget, "limit")

    # ticking shows 0.0, which the field's `gt=0` rejects
    optional_checkbox(limit).click()

    assert settings.limit is None
    assert commits == []
    assert _errors(limit) == [GREATER_THAN_ZERO]
    assert form.has_errors()


def test_invalid_edit_keeps_the_last_valid_value(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink(limit=2.0)
    form = live_form(settings)

    editor_at(form.widget, "limit").set_value(0.0)

    assert settings.limit == 2.0
    assert editor_at(form.widget, "limit").get_value() == 0.0

    editor_at(form.widget, "limit").set_value(3.0)

    assert settings.limit == 3.0
    assert field_at(form.widget, "limit").issues() == []


def test_choice_the_editor_cannot_show_reads_a_value_is_required(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink(pattern=PatternType("no longer offered"))

    form = live_form(settings)

    assert _errors(field_at(form.widget, "pattern")) == ["A value is required."]
    assert settings.pattern == "no longer offered"
    assert form.has_errors()


def test_nested_error_is_shown_on_its_field_and_noted_on_the_enclosing_one(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink()
    form = live_form(settings)

    editor_at(form.widget, "shape.radius").set_value(0.0)

    assert _errors(field_at(form.widget, "shape.radius")) == [GREATER_THAN_ZERO]
    assert _errors(field_at(form.widget, "shape")) == ["Contains an invalid value."]
    assert settings.shape == CircleShape()

    editor_at(form.widget, "shape.radius").set_value(4.0)

    assert field_at(form.widget, "shape.radius").issues() == []
    assert field_at(form.widget, "shape").issues() == []
    assert settings.shape == CircleShape(radius=4.0)


def test_model_level_error_is_shown_on_the_enclosing_field(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink(shape=SquareShape(side=2.0))
    form = live_form(settings)

    editor_at(form.widget, "shape.margin").set_value(3.0)

    assert _errors(field_at(form.widget, "shape")) == [
        "The margin must be smaller than the side."
    ]
    assert field_at(form.widget, "shape.margin").issues() == []
    assert settings.shape == SquareShape(side=2.0)


def test_switching_variant_clears_the_errors_of_the_page_left(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink()
    form = live_form(settings)
    editor_at(form.widget, "shape.radius").set_value(0.0)
    radius = field_at(form.widget, "shape.radius")
    assert form.has_errors()

    _union(form, "shape").select("point")

    assert not form.has_errors()
    assert radius.issues() == []
    assert settings.shape.kind == "point"


def test_validity_changed_is_emitted_only_when_errors_appear_or_vanish(
    qtbot: QtBot, live_form: Callable[..., Form]
) -> None:
    form = live_form(KitchenSink())

    with qtbot.waitSignal(form.validity_changed, timeout=1000) as appeared:
        editor_at(form.widget, "shape.radius").set_value(0.0)
    with qtbot.assertNotEmitted(form.validity_changed):
        editor_at(form.widget, "width").set_value(0.0)
        editor_at(form.widget, "shape.radius").set_value(1.0)
    with qtbot.waitSignal(form.validity_changed, timeout=1000) as vanished:
        editor_at(form.widget, "width").set_value(1.0)

    assert appeared.args == [True]
    assert vanished.args == [False]


def test_area_minimum_is_a_form_error(
    qtbot: QtBot, live_form: Callable[..., Form]
) -> None:
    settings = KitchenSink()
    form = live_form(settings)
    area = editor_at(form.widget, "area")

    with qtbot.waitSignal(form.validity_changed, timeout=1000) as appeared:
        area.set_value([])

    assert appeared.args == [True]
    assert form.has_errors()
    assert _errors(area) == ["At least 1 area(s) required."]

    with qtbot.waitSignal(form.validity_changed, timeout=1000) as vanished:
        area.set_value([RelativeArea.full()])

    assert vanished.args == [False]


def test_has_errors_counts_errors_on_unselected_union_pages(
    live_form: Callable[..., Form],
) -> None:
    settings = PagedArea()
    form = live_form(settings)
    editor_at(form.widget, "layout.frame").set_value([])

    _union(form, "layout").select("plain")

    assert settings.layout == PlainLayout()
    assert form.has_errors()


def test_invalid_yaml_is_reported_on_the_text_field(
    live_form: Callable[..., Form],
) -> None:
    settings = KitchenSink()
    form = live_form(settings)
    mapping = editor_at(form.widget, "mapping")
    # the YAML fallback editor is a plain text edit
    assert isinstance(mapping, QPlainTextEdit)

    mapping.setPlainText("a: [1")

    assert [m.startswith("Invalid YAML: ") for m in messages(mapping)] == [True]
    assert settings.mapping == {"a": 1}
