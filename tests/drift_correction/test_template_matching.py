# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Sequence
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from fibsem_maestro.core.slice import SliceContext
from fibsem_maestro.drift_correction.result import TemplateMatchResult
from fibsem_maestro.drift_correction.template_matching import (
    TemplateMatchingDriftCorrection,
)
from numpy._typing import NDArray

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.point import PixelPoint, RelativePoint
from fibsem_maestro.drift_correction.error import DriftCorrectionError
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.image.overlay import Overlay
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.beam_properties import BeamProperties
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.memory import MemoryImageStore
from fibsem_maestro.store.props.memory import MemoryPropsStore


def _make_drift_correction(
    txt_log: MemoryTextLogger | None = None,
    img_log: MemoryImageLogger | None = None,
    settings: TemplateMatchingSettings | None = None,
    ctx: SliceContext | None = None,
    image_store: MemoryImageStore[Image8Bit] | None = None,
    props: GlobalProperties | None = None,
) -> TemplateMatchingDriftCorrection:
    txt_log = txt_log or MemoryTextLogger()
    microscope_settings = MicroscopeSettings(
        control="mock",
        ip_address="localhost",
        beam_shift_tolerance=1.0,
        stage_tolerance=100.0,
        stage_trials=3,
        holder_pretilt=0.0,
    )
    microscope = Microscope(microscope_settings, txt_log)
    ctx = ctx or SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = settings or TemplateMatchingSettings()
    props_store = MemoryPropsStore(ctx)
    if props is not None:
        props_store.write(str(settings.properties_file), props)

    return TemplateMatchingDriftCorrection(
        name="test drift correction",
        microscope=microscope,
        settings=settings,
        props_store=props_store,
        image_store=image_store or MemoryImageStore(ctx, Image8Bit, "templates"),
        txt_log=txt_log,
        img_log=img_log or MemoryImageLogger(),
    )


def test_constructor_stores_name():
    dc = _make_drift_correction()

    assert dc._name == "test drift correction"


def test_constructor_stores_settings():
    settings = TemplateMatchingSettings(min_confidence=0.5)
    dc = _make_drift_correction(settings=settings)

    assert dc._settings is settings


def test_name_returns_configured_name():
    dc = _make_drift_correction()

    assert dc.name == "test drift correction"


def test_name_with_underscores_replaces_spaces():
    dc = _make_drift_correction()

    assert dc.name_with_underscores == "test_drift_correction"


def test_props_file_returns_string_of_properties_file():
    dc = _make_drift_correction()

    assert dc.props_file == str(TemplateMatchingSettings().properties_file)


def test_beam_type_returns_configured_beam_type():
    dc = _make_drift_correction()

    assert dc.beam_type == BeamType.ELECTRON


def test_microscope_returns_configured_microscope():
    dc = _make_drift_correction()

    assert isinstance(dc.microscope, Microscope)


def test_txt_log_returns_configured_logger():
    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(txt_log=txt_log)

    assert dc.txt_log is txt_log


def test_log_heatmap_saves_image_with_correct_filename():
    img_log = MemoryImageLogger()
    dc = _make_drift_correction(img_log=img_log)
    heatmap = np.zeros((32, 32), dtype=np.float32)

    dc._log_heatmap(heatmap, index=2)

    assert len(img_log.saved_images) == 1
    assert img_log.saved_images[0]["filename"] == "test_drift_correction_heatmap_2.png"


def test_log_heatmap_saves_correct_heatmap_array():
    img_log = MemoryImageLogger()
    dc = _make_drift_correction(img_log=img_log)
    heatmap = np.ones((32, 32), dtype=np.float32) * 0.5

    dc._log_heatmap(heatmap, index=0)

    assert np.array_equal(img_log.saved_images[0]["img"], heatmap)


def test_log_heatmap_logs_warning_on_failure():
    class FailingImageLogger(MemoryImageLogger):
        def save_image(
            self,
            filename: str,
            img: NDArray[np.floating],
            overlays: Sequence[Overlay] | None = None,
            title: str | None = None,
        ) -> None:
            _ = filename, img, overlays, title
            raise RuntimeError("save failed")

    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(txt_log=txt_log, img_log=FailingImageLogger())
    heatmap = np.zeros((32, 32), dtype=np.float32)

    dc._log_heatmap(heatmap, index=0)

    assert any(r.level == "warning" for r in txt_log.records)
    assert any(
        "Could not log a template matching drift correction heatmap" in r.message
        for r in txt_log.records
    )


def test_log_heatmaps_saves_one_image_per_match():
    img_log = MemoryImageLogger()
    dc = _make_drift_correction(img_log=img_log)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=1, dy=1, confidence=0.8, heatmap=np.ones((32, 32), dtype=np.float32)
        ),
    ]

    dc._log_heatmaps(matches)

    assert len(img_log.saved_images) == 2


def test_log_heatmaps_uses_correct_index_in_filename():
    img_log = MemoryImageLogger()
    dc = _make_drift_correction(img_log=img_log)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=1, dy=1, confidence=0.8, heatmap=np.ones((32, 32), dtype=np.float32)
        ),
    ]

    dc._log_heatmaps(matches)

    filenames = [s["filename"] for s in img_log.saved_images]
    assert "test_drift_correction_heatmap_0.png" in filenames
    assert "test_drift_correction_heatmap_1.png" in filenames


def test_log_heatmaps_does_nothing_for_empty_matches():
    img_log = MemoryImageLogger()
    dc = _make_drift_correction(img_log=img_log)

    dc._log_heatmaps([])

    assert len(img_log.saved_images) == 0


def test_log_image_shifts_saves_image_with_correct_filename():
    img_log = MemoryImageLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)]
    )
    dc = _make_drift_correction(img_log=img_log, settings=settings)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        )
    ]

    dc._log_image_shifts(img, matches)

    assert len(img_log.saved_images) == 1
    assert img_log.saved_images[0]["filename"] == "test_drift_correction_log.png"


def test_log_image_shifts_adds_red_overlay_for_each_area():
    img_log = MemoryImageLogger()
    settings = TemplateMatchingSettings(
        areas=[
            RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5),
            RelativeArea(origin=RelativePoint(0.5, 0.5), width=0.5, height=0.5),
        ]
    )
    dc = _make_drift_correction(img_log=img_log, settings=settings)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        ),
    ]

    dc._log_image_shifts(img, matches)

    overlays = img_log.saved_images[0]["overlays"]
    red_overlays = [o for o in overlays if o.color == "red"]
    assert len(red_overlays) == 2


def test_log_image_shifts_adds_blue_overlay_for_high_confidence_match():
    img_log = MemoryImageLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)],
        min_confidence=0.5,
    )
    dc = _make_drift_correction(img_log=img_log, settings=settings)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=4, dy=4, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        )
    ]

    dc._log_image_shifts(img, matches)

    overlays = img_log.saved_images[0]["overlays"]
    blue_overlays = [o for o in overlays if o.color == "blue"]
    assert len(blue_overlays) == 1


def test_log_image_shifts_skips_blue_overlay_for_low_confidence_match():
    img_log = MemoryImageLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)],
        min_confidence=0.9,
    )
    dc = _make_drift_correction(img_log=img_log, settings=settings)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=4, dy=4, confidence=0.5, heatmap=np.zeros((32, 32), dtype=np.float32)
        )
    ]

    dc._log_image_shifts(img, matches)

    overlays = img_log.saved_images[0]["overlays"]
    blue_overlays = [o for o in overlays if o.color == "blue"]
    assert len(blue_overlays) == 0


def test_log_image_shifts_blue_overlay_is_shifted_by_match_dx_dy():
    img_log = MemoryImageLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)],
        min_confidence=0.5,
    )
    dc = _make_drift_correction(img_log=img_log, settings=settings)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=4, dy=6, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        )
    ]

    dc._log_image_shifts(img, matches)

    overlays = img_log.saved_images[0]["overlays"]
    red = next(o for o in overlays if o.color == "red")
    blue = next(o for o in overlays if o.color == "blue")
    assert blue.x == red.x + 4
    assert blue.y == red.y + 6


def test_log_image_shifts_logs_warning_on_save_failure():
    class FailingImageLogger(MemoryImageLogger):
        def save_image(
            self,
            filename: str,
            img: NDArray[np.floating],
            overlays: Sequence[Overlay] | None = None,
            title: str | None = None,
        ) -> None:
            _ = filename, img, overlays, title
            raise RuntimeError("save failed")

    txt_log = MemoryTextLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)]
    )
    dc = _make_drift_correction(
        txt_log=txt_log, img_log=FailingImageLogger(), settings=settings
    )
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((32, 32), dtype=np.float32)
        )
    ]

    dc._log_image_shifts(img, matches)

    assert any(r.level == "warning" for r in txt_log.records)
    assert any(
        "Could not log a template matching drift correction result image" in r.message
        for r in txt_log.records
    )


def test_construct_template_name_returns_correct_filename():
    dc = _make_drift_correction()

    assert dc._construct_template_name(0) == "test_drift_correction_template_0.tif"


def test_construct_template_name_uses_index():
    dc = _make_drift_correction()

    assert dc._construct_template_name(3) == "test_drift_correction_template_3.tif"


def test_construct_template_name_replaces_spaces_with_underscores():
    dc = _make_drift_correction()

    assert " " not in dc._construct_template_name(0)


def _make_memory_image_store(ctx: SliceContext) -> MemoryImageStore[Image8Bit]:
    return MemoryImageStore(ctx, Image8Bit, "templates")


def test_save_template_writes_to_own_store_by_default():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    dc._image_store = store
    template = Image8Bit(np.zeros((32, 32), dtype=np.uint8), pixel_size=2.0)

    dc._save_template(template, index=0)

    assert store.exists(dc._construct_template_name(0))


def test_save_template_writes_to_given_store():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    template = Image8Bit(np.zeros((32, 32), dtype=np.uint8), pixel_size=2.0)

    dc._save_template(template, index=0, image_store=alternate_store)

    assert alternate_store.exists(dc._construct_template_name(0))


def test_load_template_reads_from_own_store_by_default():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    dc._image_store = store
    template = Image8Bit(np.zeros((32, 32), dtype=np.uint8), pixel_size=2.0)
    dc._save_template(template, index=0)

    result = dc._load_template(index=0)

    assert np.array_equal(result, template)


def test_load_template_reads_from_given_store():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    alternate_store = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 100, pixel_size=2.0)
    dc._save_template(template, index=1, image_store=alternate_store)

    result = dc._load_template(index=1, image_store=alternate_store)

    assert np.array_equal(result, template)


def test_save_and_load_template_roundtrip():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    dc._image_store = store
    rng = np.random.default_rng(42)
    template = Image8Bit(rng.integers(0, 255, (32, 32), dtype=np.uint8), pixel_size=2.0)

    dc._save_template(template, index=0)
    result = dc._load_template(index=0)

    assert np.array_equal(result, template)
    assert np.isclose(result.pixel_size, template.pixel_size)


def test_copy_template_copies_image_to_destination_store():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    src = _make_memory_image_store(ctx)
    dest = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 50, pixel_size=2.0)
    dc._save_template(template, index=0, image_store=src)

    dc._copy_template(0, src, dest)

    assert dest.exists(dc._construct_template_name(0))
    result = dest.read(dc._construct_template_name(0))
    assert np.array_equal(result, template)


def test_copy_template_does_not_modify_source():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    src = _make_memory_image_store(ctx)
    dest = _make_memory_image_store(ctx)
    dc = _make_drift_correction()
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 50, pixel_size=2.0)
    dc._save_template(template, index=0, image_store=src)

    dc._copy_template(0, src, dest)

    assert np.array_equal(src.read(dc._construct_template_name(0)), template)


def test_update_templates_copies_template_unchanged_when_confidence_too_low():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=1)
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)],
        min_confidence=0.9,
        rescan=1,
    )
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 42, pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.5, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    dc._update_templates(img, matches)

    result = store.next.read(dc._construct_template_name(0))
    assert np.array_equal(result, template)


def test_update_templates_copies_template_when_not_rescan_slice():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=1)
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)],
        min_confidence=0.5,
        rescan=10,
    )
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 42, pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)
    img = Image8Bit(np.zeros((64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    dc._update_templates(img, matches)

    result = store.next.read(dc._construct_template_name(0))
    assert np.array_equal(result, template)


def test_update_templates_crops_new_template_on_rescan_slice():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=10)
    area = RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)
    settings = TemplateMatchingSettings(
        areas=[area],
        min_confidence=0.5,
        rescan=10,
    )
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 42, pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)
    rng = np.random.default_rng(42)
    img = Image8Bit(rng.integers(0, 255, (64, 64), dtype=np.uint8), pixel_size=2.0)
    matches = [
        TemplateMatchResult(
            dx=0, dy=0, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    dc._update_templates(img, matches)

    result = store.next.read(dc._construct_template_name(0))
    expected = img.crop(area)
    assert np.array_equal(result, expected)


def test_update_templates_new_template_is_shifted_by_match_dx_dy():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=10)
    area = RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)
    settings = TemplateMatchingSettings(
        areas=[area],
        min_confidence=0.5,
        rescan=10,
    )
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)
    template = Image8Bit(np.ones((32, 32), dtype=np.uint8) * 42, pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)
    rng = np.random.default_rng(42)
    img = Image8Bit(rng.integers(0, 255, (64, 64), dtype=np.uint8), pixel_size=2.0)
    dx, dy = 4, 4
    matches = [
        TemplateMatchResult(
            dx=dx, dy=dy, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    dc._update_templates(img, matches)

    result = store.next.read(dc._construct_template_name(0))
    shifted_area = area.shifted(PixelPoint(x=dx, y=dy).to_relative(img.resolution))
    expected = img.crop(shifted_area)
    assert np.array_equal(result, expected)


def test_create_templates_raises_when_no_areas_configured():
    settings = TemplateMatchingSettings(areas=[])
    dc = _make_drift_correction(settings=settings)

    with pytest.raises(
        DriftCorrectionError, match="No template matching areas defined"
    ):
        dc.create_templates()


def test_create_templates_saves_one_template_per_area():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    settings = TemplateMatchingSettings(
        areas=[
            RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5),
            RelativeArea(origin=RelativePoint(0.5, 0.5), width=0.5, height=0.5),
        ]
    )
    dc = _make_drift_correction(
        ctx=ctx,
        settings=settings,
        image_store=store,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )

    dc.create_templates()

    assert store.exists(dc._construct_template_name(0))
    assert store.exists(dc._construct_template_name(1))


def test_create_templates_saves_correct_crop_for_each_area():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    area = RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)
    settings = TemplateMatchingSettings(areas=[area])
    dc = _make_drift_correction(
        ctx=ctx,
        settings=settings,
        image_store=store,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )

    dc.create_templates()

    result = store.read(dc._construct_template_name(0))
    assert isinstance(result, Image8Bit)
    assert result.shape == (4, 4)  # MockBeamControl grabs 8x8, half of that is 4x4


def test_create_templates_logs_info_message():
    txt_log = MemoryTextLogger()
    settings = TemplateMatchingSettings(
        areas=[RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)]
    )
    dc = _make_drift_correction(
        txt_log=txt_log,
        settings=settings,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )

    dc.create_templates()

    assert any("Acquiring template image" in r.message for r in txt_log.records)


def test_calculate_match_returns_template_match_result():
    template = Image8Bit(np.ones((16, 16), dtype=np.uint8) * 200, pixel_size=2.0)
    image = Image8Bit(np.ones((48, 48), dtype=np.uint8) * 200, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert isinstance(result, TemplateMatchResult)


def test_calculate_match_returns_heatmap_of_correct_shape():
    template = Image8Bit(np.ones((16, 16), dtype=np.uint8) * 200, pixel_size=2.0)
    image = Image8Bit(np.ones((48, 48), dtype=np.uint8) * 200, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert result.heatmap.shape == (33, 33)


def test_calculate_match_zero_shift_when_template_centered_in_image():
    rng = np.random.default_rng(42)
    pattern = rng.integers(50, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)

    image_data = np.zeros((48, 48), dtype=np.uint8)
    image_data[16:32, 16:32] = pattern
    image = Image8Bit(image_data, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert result.dx == 0
    assert result.dy == 0


def test_calculate_match_detects_positive_shift():
    rng = np.random.default_rng(42)
    pattern = rng.integers(50, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)

    image_data = np.zeros((48, 48), dtype=np.uint8)
    image_data[20:36, 20:36] = pattern
    image = Image8Bit(image_data, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert result.dx == 4
    assert result.dy == 4


def test_calculate_match_detects_negative_shift():
    rng = np.random.default_rng(42)
    pattern = rng.integers(50, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)

    image_data = np.zeros((48, 48), dtype=np.uint8)
    image_data[12:28, 12:28] = pattern
    image = Image8Bit(image_data, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert result.dx == -4
    assert result.dy == -4


def test_calculate_match_perfect_match_has_high_confidence():
    rng = np.random.default_rng(42)
    pattern = rng.integers(50, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)

    image_data = np.zeros((48, 48), dtype=np.uint8)
    image_data[16:32, 16:32] = pattern
    image = Image8Bit(image_data, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    assert result.confidence > 0.99


def test_calculate_match_blur_zero_does_not_call_gaussian_filter():
    from unittest.mock import patch

    template = Image8Bit(np.ones((16, 16), dtype=np.uint8) * 100, pixel_size=2.0)
    image = Image8Bit(np.ones((48, 48), dtype=np.uint8) * 100, pixel_size=2.0)

    with patch(
        "fibsem_maestro.drift_correction.template_matching.ndimage.gaussian_filter"
    ) as mock_filter:
        TemplateMatchingDriftCorrection._calculate_match(template, image, blur=0)

    mock_filter.assert_not_called()


def test_calculate_match_blur_reduces_noise_sensitivity():
    # add noise to the image
    rng = np.random.default_rng(42)
    pattern = rng.integers(100, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)

    image_data = rng.integers(0, 30, (48, 48), dtype=np.uint8)
    image_data[16:32, 16:32] = pattern
    image = Image8Bit(image_data, pixel_size=2.0)

    result = TemplateMatchingDriftCorrection._calculate_match(template, image, blur=3)

    assert result.dx == 0
    assert result.dy == 0


def test_matches_to_beam_shift_returns_beam_shift_instance():
    dc = _make_drift_correction(settings=TemplateMatchingSettings(min_confidence=0.5))
    matches = [
        TemplateMatchResult(
            dx=10, dy=5, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert isinstance(result, BeamShift)


def test_matches_to_beam_shift_converts_pixel_shift_to_nm():
    dc = _make_drift_correction(settings=TemplateMatchingSettings(min_confidence=0.5))
    matches = [
        TemplateMatchResult(
            dx=10, dy=5, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert np.isclose(result.x, 20.0)
    assert np.isclose(result.y, 10.0)


def test_matches_to_beam_shift_averages_multiple_matches():
    dc = _make_drift_correction(settings=TemplateMatchingSettings(min_confidence=0.5))
    matches = [
        TemplateMatchResult(
            dx=10, dy=4, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=20, dy=8, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert np.isclose(result.x, 30.0)
    assert np.isclose(result.y, 12.0)


def test_matches_to_beam_shift_ignores_low_confidence_matches():
    dc = _make_drift_correction(settings=TemplateMatchingSettings(min_confidence=0.8))
    matches = [
        TemplateMatchResult(
            dx=10, dy=4, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=100, dy=100, confidence=0.3, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert np.isclose(result.x, 20.0)
    assert np.isclose(result.y, 8.0)


def test_matches_to_beam_shift_logs_warning_for_low_confidence_match():
    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(
        txt_log=txt_log,
        settings=TemplateMatchingSettings(min_confidence=0.8),
    )
    matches = [
        TemplateMatchResult(
            dx=10, dy=4, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
        TemplateMatchResult(
            dx=5, dy=2, confidence=0.3, heatmap=np.zeros((8, 8), dtype=np.float32)
        ),
    ]

    dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert any(r.level == "warning" for r in txt_log.records)
    assert any("too low" in r.message for r in txt_log.records)


def test_matches_to_beam_shift_returns_zero_shift_when_all_confidence_too_low():
    dc = _make_drift_correction(
        settings=TemplateMatchingSettings(
            min_confidence=0.9,
            stop_acquisition_at_failure=False,
        )
    )
    matches = [
        TemplateMatchResult(
            dx=10, dy=5, confidence=0.5, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert np.isclose(result.x, 0.0)
    assert np.isclose(result.y, 0.0)


def test_matches_to_beam_shift_raises_when_all_confidence_too_low_and_stop_enabled():
    dc = _make_drift_correction(
        settings=TemplateMatchingSettings(
            min_confidence=0.9,
            stop_acquisition_at_failure=True,
        )
    )
    matches = [
        TemplateMatchResult(
            dx=10, dy=5, confidence=0.5, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    with pytest.raises(DriftCorrectionError):
        dc._matches_to_beam_shift(matches, pixel_size=2.0)


def test_matches_to_beam_shift_applies_image_to_beam_shift_factor():
    # MockBeamControl.image_to_beam_shift = (1.0, 1.0) by default
    # manually set to (-2.0, 3.0) to verify scaling
    dc = _make_drift_correction(settings=TemplateMatchingSettings(min_confidence=0.5))
    dc._microscope.beam._image_to_beam_shift = (-2.0, 3.0)
    matches = [
        TemplateMatchResult(
            dx=5, dy=5, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]

    result = dc._matches_to_beam_shift(matches, pixel_size=2.0)

    assert np.isclose(result.x, -20.0)
    assert np.isclose(result.y, 30.0)


def test_get_template_matches_returns_one_result_per_area():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    settings = TemplateMatchingSettings(
        areas=[
            RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5),
            RelativeArea(origin=RelativePoint(0.5, 0.5), width=0.5, height=0.5),
        ],
        correction_margin=0.0,
    )
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)

    rng = np.random.default_rng(42)
    img = Image8Bit(rng.integers(0, 255, (64, 64), dtype=np.uint8), pixel_size=2.0)

    # save templates matching the areas
    for i, area in enumerate(settings.areas):
        template = img.crop(area)
        store.write(dc._construct_template_name(i), template)

    matches = dc._get_template_matches(img)

    assert len(matches) == 2


def test_get_template_matches_returns_template_match_result_instances():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    area = RelativeArea(origin=RelativePoint(0.0, 0.0), width=0.5, height=0.5)
    settings = TemplateMatchingSettings(areas=[area], correction_margin=0.0)
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)

    rng = np.random.default_rng(42)
    img = Image8Bit(rng.integers(0, 255, (64, 64), dtype=np.uint8), pixel_size=2.0)
    template = Image8Bit(img.crop(area), pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)

    matches = dc._get_template_matches(img)

    assert all(isinstance(m, TemplateMatchResult) for m in matches)


def test_get_template_matches_finds_correct_shift():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    area = RelativeArea.full()
    settings = TemplateMatchingSettings(areas=[area], correction_margin=0.0, blur=0)
    dc = _make_drift_correction(ctx=ctx, settings=settings, image_store=store)

    rng = np.random.default_rng(42)
    pattern = rng.integers(100, 200, (16, 16), dtype=np.uint8)
    template = Image8Bit(pattern, pixel_size=2.0)
    store.write(dc._construct_template_name(0), template)

    image_data = np.zeros((64, 64), dtype=np.uint8)
    image_data[24:40, 24:40] = pattern
    img = Image8Bit(image_data, pixel_size=2.0)

    matches = dc._get_template_matches(img)

    assert matches[0].dx == 0
    assert matches[0].dy == 0


def _make_dummy_matches() -> list[TemplateMatchResult]:
    return [
        TemplateMatchResult(
            dx=2, dy=2, confidence=0.9, heatmap=np.zeros((8, 8), dtype=np.float32)
        )
    ]


def test_correct_drift_logs_acquiring_image():
    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(
        txt_log=txt_log,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(0.0, 0.0),
        _make_dummy_matches(),
    )

    dc.correct_drift()

    assert any("Acquiring drift correction image" in r.message for r in txt_log.records)


def test_correct_drift_applies_beam_shift():
    dc = _make_drift_correction(
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(10.0, 20.0),
        _make_dummy_matches(),
    )

    dc.correct_drift()

    assert np.isclose(dc._microscope.beam.beam_shift.x, 10.0)
    assert np.isclose(dc._microscope.beam.beam_shift.y, 20.0)


def test_correct_drift_writes_properties_for_next_slice():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    settings = TemplateMatchingSettings()
    props_store = MemoryPropsStore(ctx)
    props_store.write(
        str(settings.properties_file),
        GlobalProperties(electron_beam=BeamProperties(working_distance=5_000_000.0)),
    )
    dc = _make_drift_correction(
        ctx=ctx,
        settings=settings,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    dc._props_store = props_store
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(0.0, 0.0),
        _make_dummy_matches(),
    )

    dc.correct_drift()

    assert props_store.next.exists(str(settings.properties_file))


def test_correct_drift_updates_templates():
    ctx = SliceContext(root_dir=Path("/tmp"), current_slice=0)
    store = MemoryImageStore(ctx, Image8Bit, "templates")
    dc = _make_drift_correction(
        ctx=ctx,
        image_store=store,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    template = Image8Bit(np.zeros((4, 4), dtype=np.uint8), pixel_size=1.0)
    store.write(dc._construct_template_name(0), template)
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(0.0, 0.0),
        _make_dummy_matches(),
    )

    dc.correct_drift()

    assert store.next.exists(dc._construct_template_name(0))


def test_correct_drift_logs_fine_tuning_when_beam_shift_fails():
    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(
        txt_log=txt_log,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(10.0, 20.0),
        _make_dummy_matches(),
    )

    original_type = type(dc._microscope.beam)
    original_property = original_type.beam_shift
    call_count = [0]

    def raising_on_first_set(self_inner: Any, value: BeamShift) -> None:
        call_count[0] += 1
        if call_count[0] == 1:
            raise RuntimeError("Beam shift out of range")
        original_property.fset(self_inner, value)

    original_type.beam_shift = property(original_property.fget, raising_on_first_set)

    try:
        dc.correct_drift()
    finally:
        original_type.beam_shift = original_property

    assert any("Fine-tuning" in r.message for r in txt_log.records)


def test_correct_drift_does_not_log_fine_tuning_when_beam_shift_succeeds():
    txt_log = MemoryTextLogger()
    dc = _make_drift_correction(
        txt_log=txt_log,
        props=GlobalProperties(
            electron_beam=BeamProperties(working_distance=5_000_000.0)
        ),
    )
    dc._calculate_correction_beam_shift = lambda _: (
        BeamShift(10.0, 20.0),
        _make_dummy_matches(),
    )

    dc.correct_drift()

    assert not any("Fine-tuning" in r.message for r in txt_log.records)
