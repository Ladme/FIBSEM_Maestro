# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from pathlib import Path

import cv2
import numpy as np
import pytest
import tifffile

from fibsem_maestro.core.area import RelativeArea
from fibsem_maestro.core.format import ImageFormat
from fibsem_maestro.core.image import Image, Image8Bit, ImageError
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.provenance import Provenance


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


def test_blured_none_sigma_returns_equal_copy():
    arr = np.arange(64 * 64, dtype=np.int32).reshape(64, 64) % 256
    img = Image(arr, pixel_size=2.0)

    result = img.blured(None)

    assert np.array_equal(result, img)
    assert result is not img


def test_blured_zero_sigma_returns_equal_copy():
    arr = np.arange(64 * 64, dtype=np.int32).reshape(64, 64) % 256
    img = Image(arr, pixel_size=2.0)

    result = img.blured(0)

    assert np.array_equal(result, img)
    assert result is not img


def test_blured_none_sigma_preserves_pixel_size():
    img = Image(np.ones((32, 32), dtype=np.int32), pixel_size=2.0)

    assert np.isclose(img.blured(None).pixel_size, 2.0)


def test_blured_preserves_pixel_size():
    """Blurring changes intensities, never the spatial calibration."""
    arr = np.arange(64 * 64, dtype=np.int32).reshape(64, 64) % 256
    img = Image(arr, pixel_size=2.0)

    assert np.isclose(img.blured(3).pixel_size, 2.0)


def test_blured_preserves_shape_and_dtype():
    arr = np.arange(64 * 64, dtype=np.int32).reshape(64, 64) % 256
    img = Image(arr, pixel_size=2.0)

    result = img.blured(3)

    assert result.shape == (64, 64)
    assert result.dtype == np.int32


def test_blured_does_not_modify_original():
    arr = np.zeros((33, 33), dtype=np.int32)
    arr[16, 16] = 10000
    img = Image(arr.copy(), pixel_size=2.0)

    img.blured(2)

    assert np.array_equal(img, arr)


def test_blured_constant_image_stays_constant():
    img = Image(np.full((32, 32), 100, dtype=np.int32), pixel_size=2.0)

    result = img.blured(3)

    assert np.array_equal(result, img)


def test_blured_spreads_isolated_peak():
    arr = np.zeros((33, 33), dtype=np.int32)
    arr[16, 16] = 10000
    img = Image(arr, pixel_size=2.0)

    result = img.blured(2)

    assert result.max() < 10000
    assert result[14, 14] > 0


def test_blured_larger_sigma_smooths_more():
    arr = np.zeros((65, 65), dtype=np.int32)
    arr[32, 32] = 10000
    img = Image(arr, pixel_size=2.0)

    assert img.blured(5).max() < img.blured(2).max()


def test_upsampled_doubles_shape():
    img = Image(np.ones((64, 64), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(2.0)

    assert result.shape == (128, 128)


def test_upsampled_scales_non_square_image_on_both_axes():
    img = Image(np.ones((30, 70), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(2.0)

    assert result.shape == (60, 140)


def test_upsampled_divides_pixel_size():
    """Twice the pixels across the same field means half the pixel size."""
    img = Image(np.ones((64, 64), dtype=np.uint16), pixel_size=2.0)

    assert np.isclose(img.upsampled(2.0).pixel_size, 1.0)


def test_upsampled_preserves_physical_field_of_view():
    """The invariant a multiply/divide slip in the pixel size would break."""
    img = Image(np.ones((64, 64), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(4.0)

    assert np.isclose(
        result.shape[1] * result.pixel_size, img.shape[1] * img.pixel_size
    )


def test_upsampled_below_one_downsamples_and_grows_pixel_size():
    img = Image(np.ones((64, 64), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(0.5)

    assert result.shape == (32, 32)
    assert np.isclose(result.pixel_size, 4.0)


def test_upsampled_unit_factor_is_identity():
    rng = np.random.default_rng(42)
    img = Image(rng.integers(0, 4096, (64, 64), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(1.0)

    assert np.array_equal(result, img)
    assert np.isclose(result.pixel_size, 2.0)


def test_upsampled_returns_same_type_and_dtype():
    img = Image(np.ones((32, 32), dtype=np.uint16), pixel_size=2.0)

    result = img.upsampled(2.0)

    assert isinstance(result, Image)
    assert result.dtype == np.uint16


def test_upsampled_interpolates_between_source_pixels():
    """Bilinear, not nearest-neighbour: new samples land between the originals."""
    arr = np.array([[0, 0], [0, 200]], dtype=np.uint16)
    img = Image(arr, pixel_size=2.0)

    result = img.upsampled(4.0)

    assert np.any((result > 0) & (result < 200))


def test_upsampled_does_not_modify_original():
    img = Image(np.ones((32, 32), dtype=np.uint16), pixel_size=2.0)

    img.upsampled(2.0)

    assert img.shape == (32, 32)
    assert np.isclose(img.pixel_size, 2.0)


def test_upsampled_raises_on_zero_factor():
    img = Image(np.ones((16, 16), dtype=np.uint16), pixel_size=2.0)

    with pytest.raises(cv2.error):
        img.upsampled(0.0)


def test_from_file_roundtrip(tmp_path):
    arr = np.arange(64 * 64, dtype=np.uint16).reshape(64, 64)
    img = Image(arr, pixel_size=2.5)
    path = tmp_path / "image.tif"
    img.save(path, ImageFormat.TIF)

    loaded = Image.from_file(path)

    assert np.array_equal(loaded, img)
    assert np.isclose(loaded.pixel_size, 2.5)


def test_from_file_defaults_to_maestro_provenance(tmp_path):
    arr = np.ones((16, 16), dtype=np.uint16)
    path = tmp_path / "image.tif"
    Image(arr, pixel_size=3.0).save(path, ImageFormat.TIF)

    assert np.isclose(
        Image.from_file(path).pixel_size,
        Image.from_file(path, origin=Provenance.MAESTRO).pixel_size,
    )


def test_from_file_returns_requested_subclass(tmp_path):
    path = tmp_path / "image.tif"
    Image8Bit(np.ones((16, 16), dtype=np.uint8), pixel_size=2.0).save(
        path, ImageFormat.TIF
    )

    assert isinstance(Image8Bit.from_file(path), Image8Bit)


def test_from_file_raises_on_missing_metadata(tmp_path):
    path = tmp_path / "no_meta.tif"
    tifffile.imwrite(path, np.ones((16, 16), dtype=np.uint16))

    with pytest.raises(ImageError, match="Missing metadata"):
        Image.from_file(path)


def test_from_file_closes_the_file_handle(tmp_path):
    path = tmp_path / "image.tif"
    Image(np.ones((16, 16), dtype=np.uint16), pixel_size=2.0).save(
        path, ImageFormat.TIF
    )

    Image.from_file(path)
    path.unlink()

    assert not path.exists()


def test_array_finalize_defaults_pixel_size_to_one_for_plain_view():
    """A bare ndarray viewed as an Image carries no calibration; the fallback is 1 nm."""
    result = np.ones((8, 8), dtype=np.int32).view(Image)

    assert np.isclose(result.pixel_size, 1)


def test_pixel_size_preserved_through_copy():
    img = Image(np.ones((8, 8), dtype=np.int32), pixel_size=2.0)

    assert np.isclose(img.copy().pixel_size, 2.0)


def test_pixel_size_preserved_through_arithmetic():
    img = Image(np.ones((8, 8), dtype=np.int32), pixel_size=2.0)

    result = img * 2

    assert isinstance(result, Image)
    assert np.isclose(result.pixel_size, 2.0)


def test_pixel_size_preserved_through_transpose():
    img = Image(np.ones((8, 16), dtype=np.int32), pixel_size=2.0)

    assert np.isclose(img.T.pixel_size, 2.0)


def test_getitem_row_index_returns_same_type_with_pixel_size():
    img = Image(np.arange(64, dtype=np.int32).reshape(8, 8), pixel_size=2.0)

    row = img[0]

    assert isinstance(row, Image)
    assert np.isclose(row.pixel_size, 2.0)


def test_image_8bit_stores_pixel_size_and_dtype():
    img = Image8Bit(np.ones((8, 8), dtype=np.uint8), pixel_size=2.0)

    assert np.isclose(img.pixel_size, 2.0)
    assert img.dtype == np.uint8


def test_image_8bit_slice_returns_image_8bit():
    img = Image8Bit(np.ones((16, 16), dtype=np.uint8), pixel_size=2.0)

    assert isinstance(img[4:8, 4:8], Image8Bit)


def test_image_8bit_resolution_matches_shape():
    img = Image8Bit(np.ones((100, 200), dtype=np.uint8), pixel_size=2.0)

    assert img.resolution.width == 200
    assert img.resolution.height == 100


def test_image_8bit_crop_preserves_type_and_pixel_size():
    img = Image8Bit(np.ones((100, 200), dtype=np.uint8), pixel_size=1.5)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop(area)

    assert isinstance(result, Image8Bit)
    assert np.isclose(result.pixel_size, 1.5)


def test_from_file_raises_image_error_on_missing_file(tmp_path):
    with pytest.raises(ImageError, match="Could not load TIFF"):
        Image.from_file(tmp_path / "does_not_exist.tif")


def test_from_file_raises_image_error_on_directory(tmp_path):
    with pytest.raises(ImageError, match="Could not load TIFF"):
        Image.from_file(tmp_path)


def test_from_file_raises_image_error_on_non_tiff_content(tmp_path):
    path = tmp_path / "garbage.tif"
    path.write_bytes(b"not a tiff at all")

    with pytest.raises(ImageError, match="Could not load TIFF"):
        Image.from_file(path)


def test_from_file_raises_image_error_on_empty_file(tmp_path):
    path = tmp_path / "empty.tif"
    path.write_bytes(b"")

    with pytest.raises(ImageError, match="Could not load TIFF"):
        Image.from_file(path)


def test_from_file_raises_image_error_on_truncated_file(tmp_path):
    good = tmp_path / "good.tif"
    Image(np.ones((16, 16), dtype=np.uint16), pixel_size=2.0).save(
        good, ImageFormat.TIF
    )
    truncated = tmp_path / "truncated.tif"
    truncated.write_bytes(good.read_bytes()[:40])

    with pytest.raises(ImageError, match="Could not load TIFF"):
        Image.from_file(truncated)


def test_from_file_error_names_the_offending_path(tmp_path):
    path = tmp_path / "missing_frame_0042.tif"

    with pytest.raises(ImageError, match="missing_frame_0042.tif"):
        Image.from_file(path)


def test_crop_returns_copy_not_view():
    img = Image(np.zeros((100, 200), dtype=np.int32), pixel_size=1.5)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    cropped = img.crop(area)

    assert not np.shares_memory(cropped, img)


def test_crop_writes_do_not_reach_the_source_image():
    img = Image(np.zeros((100, 200), dtype=np.int32), pixel_size=1.5)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    cropped = img.crop(area)
    cropped[:] = 999

    assert img.max() == 0


def test_crop_source_writes_do_not_reach_the_crop():
    img = Image(np.zeros((100, 200), dtype=np.int32), pixel_size=1.5)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    cropped = img.crop(area)
    img[:] = 999

    assert cropped.max() == 0


def test_crop_full_frame_returns_copy():
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=1.5)

    cropped = img.crop(RelativeArea.full())

    assert np.array_equal(cropped, img)
    assert not np.shares_memory(cropped, img)


def test_crop_zero_area_copy_preserves_type_and_pixel_size():
    img = Image(np.ones((100, 200), dtype=np.int32), pixel_size=1.5)
    area = RelativeArea(origin=RelativePoint(0.5, 0.5), width=0.0, height=0.0)

    cropped = img.crop(area)

    assert cropped.shape == (0, 0)
    assert isinstance(cropped, Image)
    assert np.isclose(cropped.pixel_size, 1.5)


def test_crop_with_padding_returns_copy_not_view():
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)

    assert not np.shares_memory(result, img)


def test_crop_with_padding_writes_do_not_reach_the_source_image():
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)
    result[:] = 999

    assert img.max() == 0


def test_crop_with_padding_does_not_retain_the_padded_buffer():
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=4.0)

    assert result.base is None


def test_crop_with_padding_zero_padding_returns_copy():
    img = Image(np.zeros((64, 64), dtype=np.int32), pixel_size=2.0)
    area = RelativeArea(origin=RelativePoint(0.25, 0.25), width=0.5, height=0.5)

    result = img.crop_with_padding(area, padding_nm=0.0)

    assert not np.shares_memory(result, img)
