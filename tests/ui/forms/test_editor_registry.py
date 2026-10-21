# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""Which editor edits which field: registration, duplicates and the text-area fallback."""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

import pytest
from gui_testkit.forms import editor_at, field_at
from gui_testkit.sample_settings import KitchenSink, RequiredLink
from pydantic import Field
from PyQt6.QtWidgets import QLineEdit

from fibsem_maestro.core.registry import RegistryError
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FormHint, WidgetType
from fibsem_maestro.ui.forms.builder import FormBuilder
from fibsem_maestro.ui.forms.editor import FieldEditor
from fibsem_maestro.ui.forms.editors.text_area import TextAreaWidget
from fibsem_maestro.ui.forms.registry import (
    EditorRegistry,
    connect_leaf,
    default_registry,
    optional_wrap,
)
from fibsem_maestro.ui.schema.field_type import IntType

if TYPE_CHECKING:
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.ui.forms.context import FormContext
    from fibsem_maestro.ui.forms.registry import EditorRequest


class Note(BaseSettings):
    """A hinted text field, an optional one, and a plain number."""

    text: Annotated[str, FormHint(widget=WidgetType.STRING)] = Field(default="hello")
    maybe: Annotated[str | None, FormHint(widget=WidgetType.STRING)] = Field(
        default=None
    )
    number: int = Field(default=1)


class ShoutingEditor(QLineEdit, FieldEditor[str]):
    """A third-party editor: shows text in capitals, stores it in lower case."""

    def __init__(self, default: str) -> None:
        super().__init__()
        FieldEditor.__init__(self)
        self.set_value(default)
        self.textEdited.connect(lambda _: self._emit())

    def get_value(self) -> str:
        return self.text().lower()

    def set_value(self, value: str) -> None:
        self.setText(value.upper())

    def set_read_only(self, read_only: bool) -> None:
        self.setReadOnly(read_only)


def _shouting(request: EditorRequest) -> FieldEditor[Any]:
    return optional_wrap(ShoutingEditor(request.value or ""), request, inline=True)


def test_registered_hint_editor_edits_and_commits_its_fields(
    qtbot: QtBot, form_context: FormContext
) -> None:
    registry = EditorRegistry()
    registry.register_hint(WidgetType.STRING, _shouting)
    settings = Note()
    form = FormBuilder(registry).build_live(settings, form_context)
    qtbot.addWidget(form.widget)
    editor = editor_at(form.widget, "text")
    assert isinstance(editor, ShoutingEditor)
    assert editor.text() == "HELLO"

    qtbot.keyClicks(editor, "!")

    assert settings.text == "hello!"


def test_registered_editor_is_wrapped_for_an_optional_field(
    qtbot: QtBot, form_context: FormContext
) -> None:
    registry = EditorRegistry()
    registry.register_hint(WidgetType.STRING, _shouting)
    form = FormBuilder(registry).build_detached(Note, form_context)
    qtbot.addWidget(form.widget)

    assert isinstance(editor_at(form.widget, "maybe"), ShoutingEditor)
    assert field_at(form.widget, "maybe").get_value() is None


def test_registered_type_editor_replaces_the_fallback(
    qtbot: QtBot, form_context: FormContext
) -> None:
    registry = EditorRegistry()
    registry.register_type(
        IntType, lambda request: connect_leaf(TextAreaWidget(int, 7), request)
    )
    form = FormBuilder(registry).build_detached(Note, form_context)
    qtbot.addWidget(form.widget)

    assert form.value().number == 7


def test_field_without_registered_editor_falls_back_to_yaml_text(
    qtbot: QtBot, form_context: FormContext
) -> None:
    form = FormBuilder(EditorRegistry()).build_detached(Note, form_context)
    qtbot.addWidget(form.widget)

    assert isinstance(editor_at(form.widget, "text"), TextAreaWidget)
    assert isinstance(editor_at(form.widget, "number"), TextAreaWidget)
    assert form.value() == Note()


def test_default_registry_edits_unknown_types_as_yaml_text(
    qtbot: QtBot, form_builder: FormBuilder, sink_context: FormContext
) -> None:
    form = form_builder.build_detached(KitchenSink, sink_context)
    qtbot.addWidget(form.widget)
    mapping = editor_at(form.widget, "mapping")
    assert isinstance(mapping, TextAreaWidget)

    mapping.setPlainText("x: 5\ny: 6")

    assert form.value().mapping == {"x": 5, "y": 6}


@pytest.mark.parametrize(
    "register",
    [
        pytest.param(
            lambda r: r.register_hint(WidgetType.DROPDOWN, _shouting), id="hint"
        ),
        pytest.param(lambda r: r.register_type(IntType, _shouting), id="type"),
    ],
)
def test_registering_an_editor_twice_is_refused(register: Any) -> None:
    with pytest.raises(RegistryError):
        register(default_registry())


@pytest.mark.usefixtures("qtbot")
def test_action_selector_without_action_catalog_names_the_field(
    form_builder: FormBuilder, form_context: FormContext
) -> None:
    with pytest.raises(ValueError, match="'target'"):
        form_builder.build_detached(RequiredLink, form_context)
