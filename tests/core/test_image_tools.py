# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import numpy as np

from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.core.image_tools import center_cropping, center_padding, get_stripes


def test_center_padding_output_shape_matches_target():
    img = Image(np.ones((32, 32), dtype=np.int32), pixel_size=2.0)

    result = center_padding(img, (64, 64))

    assert result.shape == (64, 64)


def test_center_padding_preserves_pixel_size():
    img = Image(np.ones((32, 32), dtype=np.int32), pixel_size=2.0)

    result = center_padding(img, (64, 64))

    assert np.isclose(result.pixel_size, 2.0)


def test_center_padding_pads_with_zeros():
    img = Image(np.ones((32, 32), dtype=np.int32) * 255, pixel_size=2.0)

    result = center_padding(img, (64, 64))

    # corners of the output must be zero-padded
    assert result[0, 0] == 0
    assert result[0, -1] == 0
    assert result[-1, 0] == 0
    assert result[-1, -1] == 0


def test_center_padding_centers_original_content():
    # 4x4 image padded to 8x8 - padding is 2 on each side
    img = Image(np.ones((4, 4), dtype=np.int32) * 100, pixel_size=2.0)

    result = center_padding(img, (8, 8))

    assert np.all(result[2:6, 2:6] == 100)
    assert np.all(result[:2, :] == 0)
    assert np.all(result[6:, :] == 0)
    assert np.all(result[:, :2] == 0)
    assert np.all(result[:, 6:] == 0)


def test_center_padding_odd_padding_goes_to_bottom_right():
    img = Image(np.ones((3, 3), dtype=np.int32) * 100, pixel_size=2.0)

    result = center_padding(img, (6, 6))

    assert np.all(result[1:4, 1:4] == 100)
    assert np.all(result[:1, :] == 0)
    assert np.all(result[4:, :] == 0)


def test_center_padding_crops_when_image_is_larger_than_target():
    img = Image(np.ones((64, 64), dtype=np.int32) * 100, pixel_size=2.0)

    result = center_padding(img, (32, 32))

    assert result.shape == (32, 32)
    assert np.all(result == 100)


def test_center_padding_equal_shape_returns_identical_content():
    arr = np.arange(16, dtype=np.int32).reshape(4, 4)
    img = Image(arr, pixel_size=2.0)

    result = center_padding(img, (4, 4))

    assert result.shape == (4, 4)
    assert np.array_equal(result, arr)


def test_center_padding_returns_image_instance():
    img = Image(np.ones((32, 32), dtype=np.int32), pixel_size=2.0)

    result = center_padding(img, (64, 64))

    assert isinstance(result, Image)


def test_center_cropping_output_shape_matches_target():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)

    result = center_cropping(img, (32, 32))

    assert result.shape == (32, 32)


def test_center_cropping_preserves_pixel_size():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)

    result = center_cropping(img, (32, 32))

    assert np.isclose(result.pixel_size, 2.0)


def test_center_cropping_returns_central_content():
    # 8x8 image cropped to 4x4 - crop 2 from each side
    arr = np.zeros((8, 8), dtype=np.int32)
    arr[2:6, 2:6] = 100
    img = Image(arr, pixel_size=2.0)

    result = center_cropping(img, (4, 4))

    assert np.all(result == 100)


def test_center_cropping_odd_crop_removes_more_from_bottom_right():
    arr = np.zeros((7, 7), dtype=np.int32)
    arr[1:5, 1:5] = 100
    img = Image(arr, pixel_size=2.0)

    result = center_cropping(img, (4, 4))

    assert np.all(result == 100)


def test_center_cropping_returns_unchanged_when_smaller_than_target():
    arr = np.ones((16, 16), dtype=np.int32) * 100
    img = Image(arr, pixel_size=2.0)

    result = center_cropping(img, (32, 32))

    assert result.shape == (16, 16)
    assert np.array_equal(result, arr)


def test_center_cropping_equal_shape_returns_identical_content():
    arr = np.arange(16, dtype=np.int32).reshape(4, 4)
    img = Image(arr, pixel_size=2.0)

    result = center_cropping(img, (4, 4))

    assert result.shape == (4, 4)
    assert np.array_equal(result, arr)


def test_center_cropping_returns_image_instance():
    img = Image(np.ones((64, 64), dtype=np.int32), pixel_size=2.0)

    result = center_cropping(img, (32, 32))

    assert isinstance(result, Image)


def _make_striped_image(
    stripe_rows: list[int],
    separator_rows: list[int],
    width: int,
    stripe_value: int = 200,
    separator_value: int = 0,
    total_rows: int | None = None,
) -> Image8Bit:
    """Build an 8-bit image with horizontal stripes and dark separator rows."""
    height = total_rows or (max(stripe_rows + separator_rows) + 1)
    data = np.full((height, width), stripe_value, dtype=np.uint8)
    for r in separator_rows:
        data[r, :] = separator_value
    return Image8Bit(data, pixel_size=2.0)


def test_get_stripes_yields_rows_between_separators():
    img = _make_striped_image(
        stripe_rows=list(range(1, 9)),
        separator_rows=[0, 10],
        width=32,
        total_rows=12,
    )

    stripes = list(get_stripes(img, separate_value=1, minimal_stripe_width=3))

    assert len(stripes) == 1
    assert np.array_equal(stripes[0], np.arange(1, 9, dtype=int))


def test_get_stripes_yields_multiple_stripes():
    img = _make_striped_image(
        stripe_rows=list(range(1, 4)) + list(range(6, 10)),
        separator_rows=[0, 5, 11],
        width=32,
        total_rows=13,
    )

    stripes = list(get_stripes(img, separate_value=1, minimal_stripe_width=3))

    assert len(stripes) == 2
    assert np.array_equal(stripes[0], np.arange(1, 4, dtype=int))
    assert np.array_equal(stripes[1], np.arange(6, 10, dtype=int))


def test_get_stripes_excludes_narrow_regions():
    img = _make_striped_image(
        stripe_rows=list(range(1, 2)) + list(range(3, 9)),
        separator_rows=[0, 2, 10],
        width=32,
        total_rows=12,
    )

    stripes = list(get_stripes(img, separate_value=1, minimal_stripe_width=3))

    assert len(stripes) == 1
    assert np.array_equal(stripes[0], np.arange(3, 9, dtype=int))


def test_get_stripes_yields_nothing_when_no_separators():
    data = np.full((16, 32), 200, dtype=np.uint8)
    img = Image8Bit(data, pixel_size=2.0)

    stripes = list(get_stripes(img, separate_value=1, minimal_stripe_width=3))

    assert stripes == []


def test_get_stripes_uses_row_projection_not_column():
    # dark columns but no dark rows -> no stripes
    data = np.full((16, 32), 200, dtype=np.uint8)
    data[:, 8] = 0
    data[:, 16] = 0
    img = Image8Bit(data, pixel_size=2.0)

    stripes = list(get_stripes(img, separate_value=1, minimal_stripe_width=3))

    assert stripes == []
