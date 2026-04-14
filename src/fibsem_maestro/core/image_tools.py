# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from collections.abc import Iterator

import numpy as np
from numpy.typing import NDArray

from fibsem_maestro.core.image import Image, Image8Bit


def center_padding(image: Image, target_shape: tuple[int, int]) -> Image:
    """
    Pad or crop an image to exactly match the given target shape, centering
    the original image.

    If the input image is smaller than `target_shape` in either dimension,
    it is padded with zeros. If it is larger, it is cropped. Both operations
    center the original image content within the output.

    Args:
        image (Image): The 2D input image to be padded or cropped.
        target_shape (tuple[int, int]): The desired output spatial dimensions
            as `(target_height, target_width)`.

    Returns:
        Image: A new Image with shape exactly equal to `target_shape` and
        the same pixel size as the input.
    """
    h, w = image.shape[:2]
    th, tw = target_shape

    pad_h = max(th - h, 0)
    pad_w = max(tw - w, 0)

    pad_top = pad_h // 2
    pad_bottom = pad_h - pad_top
    pad_left = pad_w // 2
    pad_right = pad_w - pad_left

    padded = np.pad(
        image, ((pad_top, pad_bottom), (pad_left, pad_right)), mode="constant"
    )

    return Image(padded[:th, :tw], image.pixel_size)


def center_cropping(image: Image, target_shape: tuple[int, int]) -> Image:
    """
    Centrally crop an image to the given target shape.

    If the input image is larger than `target_shape` in either dimension,
    it is cropped symmetrically around the centre. If it is smaller, it is
    returned unchanged.

    Args:
        image (Image): The 2D input image to be cropped.
        target_shape (tuple[int, int]): The desired output spatial dimensions
            as `(target_height, target_width)`.

    Returns:
        Image: A new Image with shape no larger than `target_shape` and
        the same pixel size as the input.
    """
    h, w = image.shape[:2]
    th, tw = target_shape

    crop_h = max(h - th, 0)
    crop_w = max(w - tw, 0)

    crop_top = crop_h // 2
    crop_bottom = crop_h - crop_top
    crop_left = crop_w // 2
    crop_right = crop_w - crop_left

    cropped = image[crop_top : h - crop_bottom, crop_left : w - crop_right]

    return cropped[:th, :tw]


def get_stripes(
    img: Image8Bit,
    separate_value: int,
    minimal_stripe_width: int,
) -> Iterator[NDArray[np.integer]]:
    """
    Yields horizontal image stripes separated by darker separator rows.

    Args:
        img: An 8-bit grayscale image.
        separate_value: Threshold on the row-sum projection. Rows with
            summed intensity lower than this value are considered separator ("dark") rows.
        minimal_stripe_width: Minimum distance (in rows) between two separator
            rows required to consider the region a valid stripe.

    Yields:
        1D NumPy array of row indices belonging to the stripe, excluding the
        separator rows.
    """
    # sum intensities per row
    row_sums = np.sum(img, axis=1)

    # separator rows are those that are dark enough
    separator_rows = np.where(row_sums < separate_value)[0]

    # each stripe is the region between two consecutive separator rows
    for top, bottom in zip(separator_rows[:-1], separator_rows[1:]):
        # if separators are far enough apart, we treat the region as a stripe
        if (bottom - top) >= minimal_stripe_width:
            # exclude the separator rows themselves
            rows = np.arange(top + 1, bottom - 1, dtype=int)
            yield rows
