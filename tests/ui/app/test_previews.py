# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""`PreviewService`: area-selector images acquired on the task thread."""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.ui.app.previews import PreviewService
from fibsem_maestro.ui.ports import PreviewRequest

if TYPE_CHECKING:
    from gui_testkit.app import Services
    from pytestqt.qtbot import QtBot

    from fibsem_maestro.microscope.abstract_control.beam_control import BeamControl

TIMEOUT_MS = 10_000


@pytest.fixture
def previews(services: Services) -> PreviewService:
    return PreviewService(services.session, services.tasks)


@pytest.fixture
def beam(services: Services) -> BeamControl:
    return services.session.microscope.electron_beam


def area(x: float, y: float, width: float, height: float) -> RelativeArea:
    return RelativeArea(origin=RelativePoint(x=x, y=y), width=width, height=height)


def grab(
    qtbot: QtBot,
    previews: PreviewService,
    *,
    offset_x_nm: float = 0.0,
    previous_offset_nm: float | None = None,
    crop: RelativeArea | None = None,
) -> Image:
    request = PreviewRequest(BeamType.ELECTRON, offset_x_nm, previous_offset_nm, crop)
    handle = previews.grab(request)
    with qtbot.waitSignal(handle.succeeded, timeout=TIMEOUT_MS) as blocker:
        pass
    (image,) = blocker.args
    assert isinstance(image, Image)
    return image


def test_preview_reuses_last_frame_without_offset(
    qtbot: QtBot, previews: PreviewService, beam: BeamControl
) -> None:
    last = beam.grab_frame()
    assert np.array_equal(grab(qtbot, previews), last)


@pytest.mark.parametrize("request_kind", ["offset", "previous offset"])
def test_preview_grabs_fresh_frame_with_offset(
    qtbot: QtBot, previews: PreviewService, beam: BeamControl, request_kind: str
) -> None:
    last = beam.grab_frame()
    shift = beam.beam_shift

    if request_kind == "offset":
        image = grab(qtbot, previews, offset_x_nm=100.0)
    else:
        image = grab(qtbot, previews, previous_offset_nm=100.0)

    assert not np.array_equal(image, last)
    assert beam.beam_shift == shift  # the temporary shift is undone


def test_preview_grabs_full_frame_when_microscope_scans_reduced_area(
    qtbot: QtBot, previews: PreviewService, beam: BeamControl
) -> None:
    last = beam.grab_frame()
    reduced = area(0.25, 0.25, 0.5, 0.5)
    beam.scanning_area = reduced

    image = grab(qtbot, previews)

    assert not np.array_equal(image, last)
    assert image.shape == last.shape
    assert beam.scanning_area == reduced  # restored


def test_preview_crops_to_requested_area(
    qtbot: QtBot, previews: PreviewService, beam: BeamControl
) -> None:
    full = beam.grab_frame()
    crop = area(0.0, 0.0, 0.5, 0.25)

    image = grab(qtbot, previews, crop=crop)

    assert np.array_equal(image, full.crop(crop))
    assert image.shape == (full.shape[0] // 4, full.shape[1] // 2)
