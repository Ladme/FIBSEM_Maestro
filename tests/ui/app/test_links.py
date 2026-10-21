# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`links.py`: action names and the settings fields linking to other actions."""

from __future__ import annotations

from typing import Annotated

import pytest
from pydantic import BaseModel

from fibsem_maestro.adjust.adjust_props import AdjustProps
from fibsem_maestro.settings.form_utils import FormHint, WidgetType
from fibsem_maestro.ui.app.links import (
    ActionLink,
    iter_links,
    retarget_links,
    validate_action_name,
)


class Nested(BaseModel):
    link: Annotated[str, FormHint(widget=WidgetType.ACTION_SELECTOR)] = "old"


class Links(BaseModel):
    """Synthetic settings with two links, an unrelated field and a nested link."""

    model_config = {"validate_assignment": True}

    first: Annotated[
        str,
        FormHint(widget=WidgetType.ACTION_SELECTOR, action_type_filter=[AdjustProps]),
    ] = "old"
    plain: str = "old"
    second: Annotated[str | None, FormHint(widget=WidgetType.ACTION_SELECTOR)] = None
    nested: Nested = Nested()


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("", "Name cannot be empty."),
        ("my action", "Name 'my action' is already in use."),
        ("My_Action", "Name 'My_Action' is already in use."),
        ("workflow", "Name 'workflow' is reserved."),
        ("WorkFlow", "Name 'workflow' is reserved."),
        ("my action 2", None),
    ],
)
def test_validate_action_name(name: str, message: str | None) -> None:
    assert validate_action_name(name, {"MY ACTION"}) == message


def test_iter_links_lists_top_level_action_selectors() -> None:
    assert list(iter_links(Links())) == [
        ActionLink("first", (AdjustProps,), optional=False),
        ActionLink("second", (), optional=True),
    ]


def test_retarget_links_changes_only_links_holding_old_name() -> None:
    links = Links(second="old")
    assert retarget_links(links, "old", "new") == ["first", "second"]
    assert (links.first, links.second, links.plain) == ("new", "new", "old")
    # only top-level fields are links
    assert links.nested.link == "old"

    assert retarget_links(links, "old", "newer") == []
