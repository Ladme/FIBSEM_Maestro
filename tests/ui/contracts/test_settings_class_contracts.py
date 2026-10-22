# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""
Properties of the settings classes the GUI shows outside the action panels.

Each form is built as its view builds it, with the context the application
gives it: the props in the properties dialog, the microscope settings in the
microscope dialog and on the connection page, and the propagated property
names in the rule editor. The values come from the simulated microscope or
from the catalogs, never from field names written here.
"""

from __future__ import annotations

import copy
from typing import TYPE_CHECKING, Any

import pytest
from gui_testkit.forms import editable_controls, warnings_of

from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.properties.microscope_properties import MicroscopeProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.ui.app.user_config import CONNECTION_FIELDS
from fibsem_maestro.ui.forms.context import FormContext
from fibsem_maestro.ui.schema.choices import choices_for
from fibsem_maestro.ui.schema.schema import get_field_infos

if TYPE_CHECKING:
    from collections.abc import Callable

    from gui_testkit.app import Services
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.logging.text.memory import MemoryTextLogger
    from fibsem_maestro.ui.composition import FormContexts
    from fibsem_maestro.ui.forms.builder import DetachedForm, Form, FormBuilder


def _collected_properties(services: Services) -> GlobalProperties:
    """Every standard property the simulated microscope reports."""
    return services.session.microscope.collect_properties(
        PropertyNames(
            microscope=list(MicroscopeProperties.model_fields),
            electron_beam=list(BeamProperties.model_fields),
            ion_beam=list(BeamProperties.model_fields),
        )
    )


@pytest.fixture(params=["collected", "empty"])
def properties(request: pytest.FixtureRequest, services: Services) -> GlobalProperties:
    """Props as Prepare stores them, and props with nothing collected."""
    if request.param == "empty":
        return GlobalProperties()
    return _collected_properties(services)


@pytest.fixture
def properties_form(
    qtbot: QtBot,
    services: Services,
    form_builder: FormBuilder,
    form_contexts: FormContexts,
    recorded: Callable[[FormContext], FormContext],
    properties: GlobalProperties,
) -> Form:
    """The properties dialog's form, for an action of any type."""
    action = services.session.add_action(next(iter(ACTION_REGISTRY)), "action")
    form = form_builder.build_live(
        properties, recorded(form_contexts.for_properties(action))
    )
    qtbot.addWidget(form.widget)
    return form


def test_collected_properties_fill_every_group(services: Services) -> None:
    props = _collected_properties(services)

    assert None not in (props.microscope, props.electron_beam, props.ion_beam)


def test_properties_form_builds_without_warnings_or_errors(
    properties_form: Form, log: MemoryTextLogger
) -> None:
    assert warnings_of(log) == []
    assert not properties_form.has_errors()


def test_properties_form_round_trip_preserves_the_properties(
    properties_form: Form, properties: GlobalProperties
) -> None:
    before = copy.deepcopy(properties)
    assert properties_form.widget.get_value() == before

    properties_form.set_value(properties_form.widget.get_value())

    assert properties == before


def test_read_only_properties_form_leaves_nothing_editable(
    properties_form: Form,
) -> None:
    properties_form.set_read_only(True)

    assert editable_controls(properties_form.widget) == []


@pytest.fixture
def microscope_form(
    qtbot: QtBot,
    services: Services,
    form_builder: FormBuilder,
    form_contexts: FormContexts,
    recorded: Callable[[FormContext], FormContext],
) -> Form:
    """The microscope dialog's form: the live settings without the connection fields."""
    settings = services.session.microscope.settings
    fields = [
        fi.name
        for fi in get_field_infos(MicroscopeSettings)
        if fi.name not in CONNECTION_FIELDS
    ]
    form = form_builder.build_live(
        settings, recorded(form_contexts.for_microscope_settings()), fields=fields
    )
    qtbot.addWidget(form.widget)
    return form


def test_connection_fields_are_microscope_settings_fields() -> None:
    names = [fi.name for fi in get_field_infos(MicroscopeSettings)]

    assert set(CONNECTION_FIELDS) < set(names)


def test_microscope_form_shows_the_settings_without_warnings(
    microscope_form: Form, services: Services, log: MemoryTextLogger
) -> None:
    settings = services.session.microscope.settings
    before = copy.deepcopy(settings)

    # what the dialog does when it opens
    microscope_form.set_value(settings.model_dump())

    assert settings == before
    assert warnings_of(log) == []
    assert not microscope_form.has_errors()


def test_read_only_microscope_form_leaves_nothing_editable(
    microscope_form: Form,
) -> None:
    microscope_form.set_read_only(True)

    assert editable_controls(microscope_form.widget) == []


def test_connection_form_round_trips_the_connection_fields(
    qtbot: QtBot, services: Services, form_builder: FormBuilder
) -> None:
    settings = services.session.microscope.settings
    form: DetachedForm = form_builder.build_detached(
        MicroscopeSettings, FormContext(), fields=CONNECTION_FIELDS
    )
    qtbot.addWidget(form.widget)

    form.set_value(settings)

    value = form.value()
    assert {name: getattr(value, name) for name in CONNECTION_FIELDS} == {
        name: getattr(settings, name) for name in CONNECTION_FIELDS
    }


def _every_offered_name(ctx: FormContext) -> dict[str, Any]:
    """Every property name the rule editor offers, per field."""
    return {
        fi.name: choices_for(fi, ctx.choice_context())
        for fi in get_field_infos(PropertyNames)
    }


@pytest.mark.parametrize("selection", ["all", "none"])
def test_rule_properties_form_round_trips_its_selection(
    qtbot: QtBot,
    form_builder: FormBuilder,
    form_contexts: FormContexts,
    recorded: Callable[[FormContext], FormContext],
    log: MemoryTextLogger,
    selection: str,
) -> None:
    ctx = recorded(form_contexts.for_rules())
    names = (
        PropertyNames(**_every_offered_name(ctx))
        if selection == "all"
        else (PropertyNames())
    )
    form = form_builder.build_detached(PropertyNames, ctx)
    qtbot.addWidget(form.widget)

    # what the rule editor does with a rule's properties
    form.set_value(names.model_dump())

    assert form.value() == names
    assert warnings_of(log) == []
