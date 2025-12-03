# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np

from fibsem_maestro.core.image import Image


def center_padding(image: Image, target_shape: tuple[int, int]) -> Image:
    """
    Pad an image to the given target shape, centering the original image.

    If the padded image exceeds the target shape due to uneven padding,
    it is cropped to exactly match `target_shape`.

    Args:
        image (Image): The input image to be padded.
        target_shape (tuple[int, int]): The desired output spatial dimensions
            as `(target_height, target_width)`.

    Returns:
        Image: A new Image object containing the padded (and possibly cropped)
        image with pixel size preserved and shape exactly equal to `target_shape`.
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

    Args:
        image (Image): The input image to be cropped.
        target_shape (tuple[int, int]): The desired output spatial dimensions
            as `(target_height, target_width)`.

    Returns:
        Image: A new Image object containing the centrally cropped image with
        pixel size preserved and shape no larger than `target_shape`.
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


def resize_to_match(image: Image, target_shape: tuple[int, int]):
    """
    Resize an image to exactly match the given shape using centered
    padding followed by centered cropping.

    Args:
        image (Image): The input image to be resized.
        target_shape (tuple[int, int]): The desired output spatial dimensions
            as `(target_height, target_width)`.

    Returns:
        Image: The resized image with shape exactly equal to `target_shape`.
    """
    # center pad + crop to match (H, W) exactly
    padded = center_padding(image, target_shape)
    cropped = center_cropping(padded, target_shape)
    return cropped  # noqa: RET504
