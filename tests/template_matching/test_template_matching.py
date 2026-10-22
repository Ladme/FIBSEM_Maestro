# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import numpy as np
import pytest
from scipy import ndimage

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.settings.drift_correction_settings import (
    TemplateMatchingDriftCorrection,
)
from fibsem_maestro.settings.template_matching_settings import (
    ReducedAreaMode,
    StandardMode,
    SubpixelMode,
    TemplateMatchingSettings,
)
from fibsem_maestro.store.image.memory import MemoryImageStore
from fibsem_maestro.template_matching.area_provider import AreaProvider
from fibsem_maestro.template_matching.error import TemplateMatchingError
from fibsem_maestro.template_matching.template_matching import TemplateMatching

if TYPE_CHECKING:
    from collections.abc import Callable

    from fibsem_maestro.action.action import Action
    from fibsem_maestro.workflow.workflow import Workflow

PIXEL_SIZE_NM = 10.0
AREA = RelativeArea(origin=RelativePoint(0.4, 0.4), width=0.2, height=0.2)


def _texture() -> np.ndarray[Any, Any]:
    rng = np.random.default_rng(0)
    base = ndimage.gaussian_filter(rng.random((600, 600)), 3)
    return (base - base.min()) / (base.max() - base.min()) * 255


TEXTURE = _texture()


def _scene(dx: float = 0.0, dy: float = 0.0) -> Image8Bit:
    """The texture with its content moved by (dx, dy) px; +x right, +y down."""
    shifted = ndimage.shift(TEXTURE, (dy, dx), order=3, mode="nearest")
    return Image8Bit(np.clip(shifted, 0, 255).astype(np.uint8), PIXEL_SIZE_NM)


class ScriptedAreaProvider(AreaProvider):
    """Serves pre-made frames in order, cropped as the full-frame provider does."""

    def __init__(
        self,
        settings: TemplateMatchingSettings,
        txt_log: MemoryTextLogger,
        frames: list[Image8Bit],
    ) -> None:
        super().__init__(None, settings, txt_log)  # ty: ignore[invalid-argument-type]
        self._frames = list(frames)

    @property
    def last_full_frame(self) -> None:
        return None

    def acquire_template_regions(self) -> list[Image8Bit]:
        frame = self._frames.pop(0)
        return [frame.crop(area) for area in self._settings.areas]

    def acquire_search_regions(self) -> list[Image8Bit]:
        frame = self._frames.pop(0)
        return [
            frame.crop_with_padding(area, self._settings.correction_margin)
            for area in self._settings.areas
        ]


def _matcher(
    settings: TemplateMatchingSettings, frames: list[Image8Bit]
) -> TemplateMatching:
    log = MemoryTextLogger(lambda: 0)
    return TemplateMatching(
        ScriptedAreaProvider(settings, log, frames),
        settings,
        MemoryImageStore(lambda: 0, Image8Bit),
        log,
        MemoryImageLogger(lambda: 0),
    )


def _measured_shift_px(
    mode: StandardMode | SubpixelMode, dx: float, dy: float
) -> tuple[float, float]:
    settings = TemplateMatchingSettings(
        areas=[AREA], correction_margin=200.0, matching_mode=mode
    )
    matcher = _matcher(settings, [_scene(), _scene(dx, dy)])
    matcher.create_templates()
    drift = matcher.calculate_drift()
    assert drift.x is not None and drift.y is not None
    return drift.x / PIXEL_SIZE_NM, drift.y / PIXEL_SIZE_NM


@pytest.mark.parametrize("factor", [1.0, 2.0, 4.0])
def test_subpixel_match_without_drift_reports_no_drift(factor: float) -> None:
    dx, dy = _measured_shift_px(SubpixelMode(upsampling_factor=factor), 0.0, 0.0)
    assert dx == pytest.approx(0.0, abs=0.1)
    assert dy == pytest.approx(0.0, abs=0.1)


@pytest.mark.parametrize("factor", [1.0, 4.0])
def test_subpixel_match_recovers_fractional_shift(factor: float) -> None:
    dx, dy = _measured_shift_px(SubpixelMode(upsampling_factor=factor), 2.3, -1.6)
    assert dx == pytest.approx(2.3, abs=0.15)
    assert dy == pytest.approx(-1.6, abs=0.15)


def test_standard_match_recovers_integer_shift() -> None:
    # guards the sign convention that the sub-pixel fix must keep
    assert _measured_shift_px(StandardMode(), 3.0, -2.0) == (3.0, -2.0)


@pytest.mark.parametrize(
    "area",
    [
        RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.2, height=0.2),
        RelativeArea(origin=RelativePoint(0.85, 0.85), width=0.15, height=0.15),
    ],
    ids=["top-left corner", "bottom-right corner"],
)
def test_reduced_area_drift_correction_near_frame_edge_measures_no_drift(
    workflow: Workflow, add_action: Callable[..., Action], area: RelativeArea
) -> None:
    add_action(
        "drift_correction",
        "dc",
        drift_calculation_mode=TemplateMatchingDriftCorrection(
            areas=[area],
            correction_margin=60.0,
            frame_grabbing_mode=ReducedAreaMode(),
        ),
    )
    for action in workflow.actions:
        action.prepare()

    workflow.run(last_slice=2)

    # the simulated sample does not drift, so no correction may be applied
    beam = workflow.microscope.electron_beam
    one_pixel = beam.pixel_size
    assert abs(beam.beam_shift.x) < one_pixel
    assert abs(beam.beam_shift.y) < one_pixel


def test_template_scans_that_drifted_apart_are_rejected() -> None:
    settings = TemplateMatchingSettings(
        areas=[AREA], template_scans=2, maximal_drift=1.0
    )
    matcher = _matcher(settings, [_scene(), _scene(8.0, 0.0)])
    with pytest.raises(TemplateMatchingError, match="drift"):
        matcher.create_templates()


def test_identical_template_scans_are_accepted() -> None:
    settings = TemplateMatchingSettings(
        areas=[AREA], template_scans=2, maximal_drift=1.0
    )
    matcher = _matcher(settings, [_scene(), _scene()])
    matcher.create_templates()
    assert matcher.templates_exist()


def test_template_scan_drift_limit_is_in_nanometers() -> None:
    # 3 px at 10 nm/px is 30 nm: above a 20 nm limit, below a 50 nm one
    too_strict = TemplateMatchingSettings(
        areas=[AREA], template_scans=2, maximal_drift=20.0
    )
    with pytest.raises(TemplateMatchingError, match="drift"):
        _matcher(too_strict, [_scene(), _scene(3.0, 0.0)]).create_templates()

    lenient = TemplateMatchingSettings(
        areas=[AREA], template_scans=2, maximal_drift=50.0
    )
    _matcher(lenient, [_scene(), _scene(3.0, 0.0)]).create_templates()
