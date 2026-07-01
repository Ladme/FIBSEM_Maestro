# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path

import numpy as np
import pytest
import tifffile

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import Image, Image8Bit, ImageError
from fibsem_maestro.core.point import RelativePoint


def test_image_base_pixel_size_preserved_on_slice():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)

    sliced = img[10:20, 10:20]

    assert np.isclose(sliced.pixel_size, 2.0)


def test_image_base_slice_returns_same_type():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)

    sliced = img[10:20, 10:20]

    assert isinstance(sliced, Image)


def test_image_base_resolution_returns_correct_width_and_height():
    img = Image(np.ones((100, 200), dtype=np.int32), pixel_size=2.0)

    assert img.resolution.width == 200
    assert img.resolution.height == 100


def test_image_base_from_tiff_roundtrip(tmp_path: Path):
    arr = np.arange(64 * 64, dtype=np.uint16).reshape(64, 64)
    img = Image(arr, pixel_size=2.0)
    path = tmp_path / "test.tif"
    img.save(path, ImageFormat.TIF)

    with tifffile.TiffFile(path) as tif:
        loaded = Image.from_tiff(tif)

    assert np.array_equal(loaded, img)
    assert np.isclose(loaded.pixel_size, 2.0)


def test_image_base_from_tiff_raises_on_missing_metadata(tmp_path: Path):
    arr = np.ones((64, 64), dtype=np.uint16)
    path = tmp_path / "no_meta.tif"
    tifffile.imwrite(path, arr)

    with (
        pytest.raises(ImageError, match="Missing metadata"),
        tifffile.TiffFile(path) as tif,
    ):
        Image.from_tiff(tif)


def test_crop_center():
    rng = np.random.default_rng(42)
    image_data = rng.integers(0, 255, (100, 200), dtype=np.int32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeArea(
        origin=RelativePoint(x=0.25, y=0.25), width=0.5, height=0.5
    )

    cropped_image = image.crop(relative_area)

    expected_height = int(round(0.5 * image.shape[0]))
    expected_width = int(round(0.5 * image.shape[1]))

    assert cropped_image.shape == (expected_height, expected_width)
    assert cropped_image.pixel_size == pixel_size


def test_crop_upper_left_edge():
    rng = np.random.default_rng(42)
    image_data = rng.integers(0, 255, (100, 200), dtype=np.int32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeArea(
        origin=RelativePoint(x=0.0, y=0.0),
        width=0.3,
        height=0.1,
    )

    cropped_image = image.crop(relative_area)

    expected_height = int(round(0.1 * image.shape[0]))
    expected_width = int(round(0.3 * image.shape[1]))
    assert cropped_image.shape == (expected_height, expected_width)
    assert cropped_image.pixel_size == pixel_size


def test_crop_full_image():
    rng = np.random.default_rng(42)
    image_data = rng.integers(0, 255, (100, 200), dtype=np.int32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeArea(
        origin=RelativePoint(x=0.0, y=0.0), width=1.0, height=1.0
    )

    cropped_image = image.crop(relative_area)

    assert np.array_equal(image, cropped_image)


def test_crop_zero_area():
    rng = np.random.default_rng(42)
    image_data = rng.integers(0, 255, (100, 200), dtype=np.int32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeArea(
        origin=RelativePoint(x=0.5, y=0.5), width=0.0, height=0.0
    )

    cropped_image = image.crop(relative_area)

    assert cropped_image.shape == (0, 0)
    assert cropped_image.pixel_size == pixel_size


def test_crop_with_padding_returns_correct_shape():
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)

    assert result.shape == (36, 36)


def test_crop_with_padding_preserves_pixel_size():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)

    assert np.isclose(result.pixel_size, 2.0)


def test_crop_with_padding_includes_border_content():
    arr = np.zeros((64, 64), dtype=np.int32)
    arr[14:16, 14:16] = 999
    img = Image(arr, pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)

    assert np.any(result == 999)


def test_crop_with_padding_zero_padding_equals_plain_crop():
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 255, (64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result_padded = img.crop_with_padding(area, padding_nm=0.0)
    result_crop = img.crop(area)

    assert np.array_equal(result_padded, result_crop)


def test_crop_with_padding_larger_than_image_does_not_raise():
    img = Image(np.ones((16, 16), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea.full()

    result = img.crop_with_padding(area, padding_nm=200.0)

    assert result.shape[0] > 16
    assert result.shape[1] > 16


def test_estimate_bit_depth_and_range_8bit():
    img = Image(np.full((8, 8), 255, dtype=np.int32), pixel_size=2.0)

    bit_depth, (lo, hi) = img._estimate_bit_depth_and_range()

    assert bit_depth == 8
    assert lo == 0
    assert hi == 255


def test_estimate_bit_depth_and_range_8bit_alternative():
    img = Image(np.full((8, 8), 144, dtype=np.int32), pixel_size=2.0)

    bit_depth, (lo, hi) = img._estimate_bit_depth_and_range()

    assert bit_depth == 8
    assert lo == 0
    assert hi == 255


def test_estimate_bit_depth_and_range_16bit():
    img = Image(np.full((8, 8), 65535, dtype=np.int32), pixel_size=2.0)

    bit_depth, (lo, hi) = img._estimate_bit_depth_and_range()

    assert bit_depth == 16
    assert lo == 0
    assert hi == 65535


def test_estimate_bit_depth_and_range_16bit_alternative():
    img = Image(np.full((8, 8), 63124, dtype=np.int32), pixel_size=2.0)

    bit_depth, (lo, hi) = img._estimate_bit_depth_and_range()

    assert bit_depth == 16
    assert lo == 0
    assert hi == 65535


def test_to_8bit_returns_image8bit_instance():
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)

    result = img.to_8bit()

    assert isinstance(result, Image8Bit)


def test_to_8bit_preserves_pixel_size():
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)

    result = img.to_8bit()

    assert np.isclose(result.pixel_size, 2.0)


def test_to_8bit_values_already_within_range_are_unchanged():
    arr = np.arange(64, dtype=np.int32).reshape(8, 8)
    img = Image(arr, pixel_size=2.0)

    result = img.to_8bit()

    assert np.array_equal(result, arr.astype(np.uint8))


def test_to_8bit_scales_values_exceeding_255():
    arr = np.full((8, 8), 1024, dtype=np.int32)
    img = Image(arr, pixel_size=2.0)

    result = img.to_8bit()

    assert np.all(result == 255)


def test_to_8bit_result_dtype_is_uint8():
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)

    result = img.to_8bit()

    assert result.dtype == np.uint8


def test_save_png_creates_file(tmp_path: Path):
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)
    path = tmp_path / "test.png"

    img.save(path, ImageFormat.PNG)

    assert path.exists()


def test_save_png_creates_valid_png(tmp_path: Path):
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)
    path = tmp_path / "test.png"

    img.save(path, ImageFormat.PNG)

    from PIL import Image as PILImage

    loaded = PILImage.open(path)
    assert loaded.format == "PNG"
