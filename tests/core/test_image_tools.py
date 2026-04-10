# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np

from fibsem_maestro.core.image import Image8Bit
from fibsem_maestro.core.image_tools import get_stripes


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
