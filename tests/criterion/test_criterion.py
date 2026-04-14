# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Sequence

import numpy as np
import pytest
from numpy.typing import NDArray

from fibsem_maestro.core.area import PixelArea, RelativeArea
from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import PixelPoint, RelativePoint
from fibsem_maestro.core.resolution import Resolution
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.criterion.criterion_registry import CriterionRegistry
from fibsem_maestro.criterion.error import CriterionError
from fibsem_maestro.criterion.reductors_registry import ReductorsRegistry
from fibsem_maestro.criterion.result import SharpnessMap
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.image.overlay import Overlay, RectangleOverlay
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.criterion_settings import (
    CriterionSettings,
    MultiTileMode,
    SingleTileMode,
)


def test_constructor_stores_name():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion(
        "criterion", settings, MemoryTextLogger(), MemoryImageLogger()
    )

    assert criterion._name == "criterion"


def test_constructor_loads_metric_function_from_registry():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    assert criterion._sharpness_metric_fn is CriterionRegistry.get("bandpass")


def test_constructor_initialises_tile_reduction_for_multi_tile_mode():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=MultiTileMode(
            tile_reduction_fn="mean",
            tile_size=500.0,
            relative_overlap=0.1,
        ),
    )
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    assert criterion._tile_reduction_fn is ReductorsRegistry.get("mean")
    assert criterion._tile_size == 500.0
    assert criterion._tile_relative_overlap == 0.1


def test_name_returns_configured_name():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion(
        "criterion", settings, MemoryTextLogger(), MemoryImageLogger()
    )

    assert criterion.name == "criterion"


def test_name_with_underscores_replaces_spaces():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion(
        "some criterion name", settings, MemoryTextLogger(), MemoryImageLogger()
    )

    assert criterion.name_with_underscores == "some_criterion_name"


def test_name_with_underscores_is_unchanged_when_no_spaces():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    criterion = Criterion("bandpass", settings, MemoryTextLogger(), MemoryImageLogger())

    assert criterion.name_with_underscores == "bandpass"


def test_tiles_to_pixels_full_criterion_area_no_offset():
    # criterion area covers the entire image, so no offset is applied
    # a tile covering the full cropped image should map to the same pixel
    # coordinates in the full image.
    full_resolution = Resolution(width=200, height=100)
    cropped_resolution = Resolution(width=200, height=100)
    criterion_area = RelativeArea.full()
    tiles = [RelativeArea.full()]

    result = list(
        Criterion._tiles_to_pixels_in_full_image(
            tiles, criterion_area, full_resolution, cropped_resolution
        )
    )

    assert len(result) == 1
    assert result[0].origin.x == 0
    assert result[0].origin.y == 0
    assert result[0].width == 200
    assert result[0].height == 100


def test_tiles_to_pixels_applies_criterion_area_offset():
    # criterion area starts at (0.5, 0.25) of a 200x100 image so the pixel offset is (100, 25)
    # tile at the origin of the cropped image must be shifted by this offset in the full image
    full_resolution = Resolution(width=200, height=100)
    cropped_resolution = Resolution(width=100, height=75)
    criterion_area = RelativeArea(
        origin=RelativePoint(x=0.5, y=0.25), width=0.5, height=0.75
    )
    tiles = [RelativeArea(origin=RelativePoint(x=0.0, y=0.0), width=0.5, height=0.5)]

    result = list(
        Criterion._tiles_to_pixels_in_full_image(
            tiles, criterion_area, full_resolution, cropped_resolution
        )
    )

    assert len(result) == 1
    assert result[0].origin.x == 100
    assert result[0].origin.y == 25


def test_tiles_to_pixels_converts_multiple_tiles():
    # two tiles side by side in the cropped image
    # both should be shifted by the criterion area offset in the full image.
    full_resolution = Resolution(width=200, height=100)
    cropped_resolution = Resolution(width=100, height=100)
    criterion_area = RelativeArea(
        origin=RelativePoint(x=0.5, y=0.0), width=0.5, height=1.0
    )
    tiles = [
        RelativeArea(origin=RelativePoint(x=0.0, y=0.0), width=0.5, height=1.0),
        RelativeArea(origin=RelativePoint(x=0.5, y=0.0), width=0.5, height=1.0),
    ]

    result = list(
        Criterion._tiles_to_pixels_in_full_image(
            tiles, criterion_area, full_resolution, cropped_resolution
        )
    )

    assert len(result) == 2
    assert result[0].origin.x == 100
    assert result[1].origin.x == 150


def test_tiles_to_pixels_no_crop_is_identity():
    # MultiTileMode with no cropping
    # tile pixel coordinates must be identical to what to_pixels() would
    # produce directly on the full image, with no offset applied
    full_resolution = Resolution(width=200, height=100)
    criterion_area = RelativeArea.full()
    tiles = [
        RelativeArea(origin=RelativePoint(x=0.0, y=0.0), width=0.5, height=1.0),
        RelativeArea(origin=RelativePoint(x=0.5, y=0.0), width=0.5, height=1.0),
    ]

    result = list(
        Criterion._tiles_to_pixels_in_full_image(
            tiles, criterion_area, full_resolution, full_resolution
        )
    )

    assert len(result) == 2
    assert result[0].origin.x == 0
    assert result[0].origin.y == 0
    assert result[0].width == 100
    assert result[1].origin.x == 100
    assert result[1].origin.y == 0
    assert result[1].width == 100


def test_calculate_sharpness_for_tile_returns_float_for_valid_image():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=1.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_tile(img, RelativeArea.full())

    assert isinstance(result, float)
    assert result >= 0.0


def test_calculate_sharpness_for_tile_returns_nan_and_logs_warning_on_failure():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=1.0)
    txt_log = MemoryTextLogger()
    criterion = Criterion("test", settings, txt_log, MemoryImageLogger())

    def failing_metric(
        image: Image, s: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = image, s, log
        raise RuntimeError("metric failure")

    criterion._sharpness_metric_fn = failing_metric

    result = criterion._calculate_sharpness_for_tile(img, RelativeArea.full())

    assert np.isnan(result)
    assert any(r.level == "warning" for r in txt_log.records)
    assert any("Resolution calculation failed" in r.message for r in txt_log.records)


def test_iter_tiles_no_overlap_produces_correct_tile_count():
    # 64x64 px image, pixel_size 2nm -> 128x128 nm
    # tile_size 64 nm -> tile_size_px 32 px
    # 4 tiles in total
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    tiles = list(criterion._iter_tiles(img, tile_size=64.0, overlap=0.0))

    assert len(tiles) == 4
    assert all(np.isclose(t.width, 0.5) and np.isclose(t.height, 0.5) for t in tiles)
    assert all(
        np.isclose(t.origin.x, 0.0) or np.isclose(t.origin.x, 0.5) for t in tiles
    )
    assert all(
        np.isclose(t.origin.y, 0.0) or np.isclose(t.origin.y, 0.5) for t in tiles
    )


def test_iter_tiles_overlap_produces_correct_tile_count():
    # 64x64 px image, pixel_size 2nm -> 128x128 nm
    # tile_size 64 nm -> tile_size_px 32 px but 50% overlap so step is just 16 px
    # 9 tiles in total
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    tiles = list(criterion._iter_tiles(img, tile_size=64.0, overlap=0.5))

    assert len(tiles) == 9
    assert all(np.isclose(t.width, 0.5) and np.isclose(t.height, 0.5) for t in tiles)
    assert all(
        np.isclose(t.origin.x, 0.0)
        or np.isclose(t.origin.x, 0.25)
        or np.isclose(t.origin.x, 0.5)
        for t in tiles
    )
    assert all(
        np.isclose(t.origin.y, 0.0)
        or np.isclose(t.origin.y, 0.25)
        or np.isclose(t.origin.y, 0.5)
        for t in tiles
    )


def test_iter_tiles_are_generated_left_to_right_top_to_bottom():
    # 64x64 px image, pixel_size 2nm -> 128x128 nm
    # tile_size 64 nm -> tile_size_px 32 px
    # expected pixel origins in order: (0,0), (32,0), (0,32), (32,32)
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    tiles = list(criterion._iter_tiles(img, tile_size=64.0, overlap=0.0))

    assert all(np.isclose(t.width, 0.5) and np.isclose(t.height, 0.5) for t in tiles)
    assert np.isclose(tiles[0].origin.x, 0.0) and np.isclose(tiles[0].origin.y, 0.0)
    assert np.isclose(tiles[1].origin.x, 0.5) and np.isclose(tiles[1].origin.y, 0.0)
    assert np.isclose(tiles[2].origin.x, 0.0) and np.isclose(tiles[2].origin.y, 0.5)
    assert np.isclose(tiles[3].origin.x, 0.5) and np.isclose(tiles[3].origin.y, 0.5)


def test_iter_tiles_omits_tiles_exceeding_image_boundary():
    # 25x25 px image, pixel_size 2nm
    # tile_size 32 nm -> tile_size_px 16px
    # 1 tile
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((25, 25), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    tiles = list(criterion._iter_tiles(img, tile_size=32.0, overlap=0.0))

    assert len(tiles) == 1
    assert np.isclose(tiles[0].width, 16 / 25) and np.isclose(tiles[0].height, 16 / 25)
    assert np.isclose(tiles[0].origin.x, 0.0) and np.isclose(tiles[0].origin.y, 0.0)


def test_iter_tiles_tile_size_is_divisible_by_4():
    # tile_size 60nm, pixel_size 2nm -> tile_size_px 30, rounded down to 28.
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    tiles = list(criterion._iter_tiles(img, tile_size=60.0, overlap=0.0))

    assert all(np.isclose(t.width, 28 / 64) for t in tiles)


def test_iter_tiles_raises_when_tile_size_is_too_small():
    # 25x25 px image, pixel_size 2nm
    # tile_size 4 nm -> tile_size_px 2px rounded to 0px
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((25, 25), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    with pytest.raises(CriterionError, match=r"Tile size is smaller than 4x4 pixels"):
        list(criterion._iter_tiles(img, tile_size=4.0, overlap=0.0))


def test_iter_tiles_raises_when_overlap_is_1():
    # full overlap between the tiles
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    with pytest.raises(
        CriterionError, match=r"Overlap is too large or tiles are too small"
    ):
        list(criterion._iter_tiles(img, tile_size=32.0, overlap=1.0))


def test_create_sharpness_map_returns_sharpness_map_instance():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._create_sharpness_map(img, [], [])

    assert isinstance(result, SharpnessMap)


def test_create_sharpness_map_has_same_shape_as_full_image():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._create_sharpness_map(img, [], [])

    assert result.shape == img.shape


def test_create_sharpness_map_uncovered_pixels_are_zero():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())
    tiles = [PixelArea(origin=PixelPoint(0, 0), width=32, height=32)]

    result = criterion._create_sharpness_map(img, tiles, [1.0])

    assert np.all(result[32:, :] == 0.0)
    assert np.all(result[:, 32:] == 0.0)


def test_create_sharpness_map_fills_tile_regions_with_correct_sharpness():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())
    tiles = [
        PixelArea(origin=PixelPoint(0, 0), width=32, height=32),
        PixelArea(origin=PixelPoint(32, 32), width=32, height=32),
    ]

    result = criterion._create_sharpness_map(img, tiles, [0.8, 0.5])

    assert np.all(result[0:32, 0:32] == 0.8)
    assert np.all(result[32:64, 32:64] == 0.5)


def test_calculate_sharpness_for_image_single_tile_mode_returns_positive_sharpness():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=SingleTileMode(),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert isinstance(result.sharpness, float)
    assert result.sharpness >= 0.0
    assert len(result.tiles_px) == 1


def test_calculate_sharpness_for_image_multi_tile_mode_applies_reduction():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=MultiTileMode(
            tile_reduction_fn="mean",
            tile_size=64.0,
            relative_overlap=0.0,
        ),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (128, 128), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    # 4 tiles, result must equal their mean
    tiles = list(criterion._iter_tiles(img, tile_size=64.0, overlap=0.0))
    sharpnesses = [criterion._calculate_sharpness_for_tile(img, t) for t in tiles]
    assert np.isclose(result.sharpness, float(np.mean(sharpnesses)))


def test_calculate_sharpness_for_image_cropping_offsets_tiles_px():
    criterion_area = RelativeArea(
        origin=RelativePoint(x=0.5, y=0.0), width=0.5, height=1.0
    )
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=SingleTileMode(),
        area=criterion_area,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    # criterion_area starts at x=0.5 of a 64px-wide image → offset of 32px
    assert result.tiles_px[0].origin.x == 32
    assert result.tiles_px[0].origin.y == 0


def test_calculate_sharpness_for_image_best_tile_is_none_when_disabled():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        log_best_tile=False,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert result.best_tile is None


def test_calculate_sharpness_for_image_best_tile_is_image_when_enabled():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=SingleTileMode(),
        log_best_tile=True,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert result.best_tile is not None
    assert isinstance(result.best_tile, Image)
    assert result.best_tile.shape == img.shape


def test_calculate_sharpness_for_image_best_tile_corresponds_to_highest_sharpness():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=MultiTileMode(
            tile_reduction_fn="mean",
            tile_size=64.0,
            relative_overlap=0.0,
        ),
        log_best_tile=True,
    )
    # 4 tiles in total in the image
    # fill the bottom-right tile [32:64, 32:64] with a sine wave inside the bandpass band
    # all other tiles are flat and score near zero
    img_array = np.zeros((64, 64), dtype=np.int32)
    x = np.arange(32)
    img_array[32:64, 32:64] = (np.sin(2 * np.pi * x / 16.0) * 1000).astype(np.int32)
    img = Image(img_array, pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert result.best_tile is not None
    assert result.best_tile.shape == (32, 32)
    assert np.array_equal(result.best_tile, img_array[32:64, 32:64])


def test_calculate_sharpness_for_image_sharpness_map_is_none_when_disabled():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        log_sharpness_map=False,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert result.sharpness_map is None


def test_calculate_sharpness_for_image_sharpness_map_has_correct_shape_when_enabled():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        log_sharpness_map=True,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion._calculate_sharpness_for_image(img)

    assert isinstance(result.sharpness_map, SharpnessMap)
    assert result.sharpness_map.shape == img.shape


def test_calculate_sharpness_for_image_nan_tile_excluded_from_reduction():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=MultiTileMode(
            tile_reduction_fn="mean",
            tile_size=64.0,
            relative_overlap=0.0,
        ),
        log_best_tile=True,
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (128, 128), dtype=np.int32), pixel_size=2.0)
    txt_log = MemoryTextLogger()
    criterion = Criterion("test", settings, txt_log, MemoryImageLogger())

    call_count = 0

    def failing_on_first_tile(
        image: Image, s: CriterionSettings, log: TextLogger
    ) -> np.floating:
        nonlocal call_count
        _ = image, s, log
        call_count += 1
        if call_count == 1:
            raise RuntimeError("simulated failure")
        return np.float64(0.8)

    criterion._sharpness_metric_fn = failing_on_first_tile

    result = criterion._calculate_sharpness_for_image(img)

    assert not np.isnan(result.sharpness)
    assert np.isclose(result.sharpness, 0.8)
    assert result.best_tile is not None


def test_calculate_sharpness_1d_image_returns_float():
    settings = CriterionSettings(
        sharpness_metric_fn="fft",
        detail=DetailBand(low=10.0, high=100.0),
    )
    x = np.arange(256)
    img = Image((np.sin(2 * np.pi * x / 32.0) * 1000).astype(np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion.calculate_sharpness(img)

    assert isinstance(result, float)
    assert result > 0.0


def test_calculate_sharpness_1d_image_skips_tiling():
    # a 1D image passed to a criterion configured with MultiTileMode must still return a result
    settings = CriterionSettings(
        sharpness_metric_fn="fft",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=MultiTileMode(
            tile_reduction_fn="mean",
            tile_size=64.0,
            relative_overlap=0.0,
        ),
    )
    x = np.arange(256)
    img = Image((np.sin(2 * np.pi * x / 32.0) * 1000).astype(np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion.calculate_sharpness(img)

    assert isinstance(result, float)
    assert result > 0.0


def test_calculate_sharpness_2d_image_basic_mode_returns_float():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=SingleTileMode(),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    criterion = Criterion("test", settings, MemoryTextLogger(), MemoryImageLogger())

    result = criterion.calculate_sharpness(img)

    assert isinstance(result, float)
    assert result >= 0.0


def test_calculate_sharpness_logs_start_and_finish():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    txt_log = MemoryTextLogger()
    criterion = Criterion("test", settings, txt_log, MemoryImageLogger())

    criterion.calculate_sharpness(img)

    messages = [r.message for r in txt_log.records]
    assert any("Sharpness calculation started" in m for m in messages)
    assert any("Finished sharpness calculation" in m for m in messages)


def test_calculate_sharpness_2d_image_saves_images_to_image_logger():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
        tiling_mode=SingleTileMode(),
    )
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    img_log = MemoryImageLogger()
    criterion = Criterion("test", settings, MemoryTextLogger(), img_log)

    criterion.calculate_sharpness(img)

    assert len(img_log.saved_images) >= 1


def test_log_image_with_tiles_saves_image_with_correct_filename():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    img_log = MemoryImageLogger()
    criterion = Criterion("criterion", settings, MemoryTextLogger(), img_log)
    tiles = [PixelArea(origin=PixelPoint(0, 0), width=32, height=32)]

    criterion._log_image_with_tiles("my_filename", img, tiles)

    assert len(img_log.saved_images) == 1
    assert img_log.saved_images[0]["filename"] == "my_filename"


def test_log_image_with_tiles_creates_correct_rectangle_overlays():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    img_log = MemoryImageLogger()
    criterion = Criterion("test", settings, MemoryTextLogger(), img_log)
    tiles = [
        PixelArea(origin=PixelPoint(0, 0), width=32, height=32),
        PixelArea(origin=PixelPoint(32, 32), width=32, height=32),
    ]

    criterion._log_image_with_tiles("test", img, tiles)

    overlays = img_log.saved_images[0]["overlays"]
    assert len(overlays) == 2
    assert all(isinstance(o, RectangleOverlay) for o in overlays)
    assert all(o.color == "red" for o in overlays)
    assert overlays[0].x == 0 and overlays[0].y == 0
    assert overlays[1].x == 32 and overlays[1].y == 32


def test_log_image_with_tiles_logs_warning_on_save_failure():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    txt_log = MemoryTextLogger()

    class FailingImageLogger(MemoryImageLogger):
        def save_image(
            self,
            filename: str,
            img: NDArray[np.floating],
            overlays: Sequence[Overlay] | None = None,
            title: str | None = None,
        ):
            _ = filename, img, overlays, title
            raise RuntimeError("save failed")

    criterion = Criterion("test", settings, txt_log, FailingImageLogger())

    criterion._log_image_with_tiles("test", img, [])

    assert any(r.level == "warning" for r in txt_log.records)
    assert any(
        "Could not log a criterion image with tiles" in r.message
        for r in txt_log.records
    )


def test_log_images_always_saves_full_image_with_tiles():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    img_log = MemoryImageLogger()
    criterion = Criterion("my criterion", settings, MemoryTextLogger(), img_log)

    criterion._log_images(img, [], best_tile=None, map=None)

    assert len(img_log.saved_images) == 1
    assert img_log.saved_images[0]["filename"] == "my_criterion"


def test_log_images_saves_sharpness_map_when_provided():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    sharpness_map = np.zeros((64, 64), dtype=np.float64).view(SharpnessMap)
    img_log = MemoryImageLogger()
    criterion = Criterion("my criterion", settings, MemoryTextLogger(), img_log)

    criterion._log_images(img, [], best_tile=None, map=sharpness_map)

    filenames = [s["filename"] for s in img_log.saved_images]
    assert "my_criterion_sharpness_map" in filenames


def test_log_images_saves_best_tile_when_provided():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    best_tile = Image(np.zeros((32, 32), dtype=np.int32), pixel_size=2.0)
    img_log = MemoryImageLogger()
    criterion = Criterion("my criterion", settings, MemoryTextLogger(), img_log)

    criterion._log_images(img, [], best_tile=best_tile, map=None)

    filenames = [s["filename"] for s in img_log.saved_images]
    assert "my_criterion_best_tile" in filenames


def test_log_images_failure_in_one_save_does_not_prevent_others():
    settings = CriterionSettings(
        sharpness_metric_fn="bandpass",
        detail=DetailBand(low=10.0, high=100.0),
    )
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    sharpness_map = np.zeros((64, 64), dtype=np.float64).view(SharpnessMap)
    best_tile = Image(np.zeros((32, 32), dtype=np.int32), pixel_size=2.0)
    txt_log = MemoryTextLogger()

    class FailOnSharpnessMap(MemoryImageLogger):
        def save_image(
            self,
            filename: str,
            img: NDArray[np.floating],
            overlays: Sequence[Overlay] | None = None,
            title: str | None = None,
        ):
            if "sharpness_map" in filename:
                raise RuntimeError("sharpness map save failed")
            super().save_image(filename, img, overlays, title)

    img_log = FailOnSharpnessMap()
    criterion = Criterion("my criterion", settings, txt_log, img_log)

    criterion._log_images(img, [], best_tile=best_tile, map=sharpness_map)

    filenames = [s["filename"] for s in img_log.saved_images]
    assert "my_criterion" in filenames
    assert "my_criterion_best_tile" in filenames
    assert any(r.level == "warning" for r in txt_log.records)
