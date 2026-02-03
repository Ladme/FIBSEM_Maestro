# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np

from fibsem_maestro.core.image import Image
from fibsem_maestro.core.point import RelativePoint
from fibsem_maestro.core.scanning_area import RelativeScanningArea


def test_crop_center():
    rng = np.random.default_rng()
    image_data = rng.random((100, 200)).astype(np.float32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeScanningArea(
        origin=RelativePoint(x=0.25, y=0.25), width=0.5, height=0.5
    )

    cropped_image = image.crop(relative_area)

    expected_height = int(round(0.5 * image.shape[0]))
    expected_width = int(round(0.5 * image.shape[1]))

    assert cropped_image.shape == (expected_height, expected_width)
    assert cropped_image.pixel_size == pixel_size


def test_crop_upper_left_edge():
    rng = np.random.default_rng()
    image_data = rng.random((100, 200)).astype(np.float32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeScanningArea(
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
    rng = np.random.default_rng()
    image_data = rng.random((100, 200)).astype(np.float32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeScanningArea(
        origin=RelativePoint(x=0.0, y=0.0), width=1.0, height=1.0
    )

    cropped_image = image.crop(relative_area)

    assert np.array_equal(image, cropped_image)


def test_crop_zero_area():
    rng = np.random.default_rng()
    image_data = rng.random((100, 200)).astype(np.float32)
    pixel_size = 1.5
    image = Image(image_data, pixel_size)

    relative_area = RelativeScanningArea(
        origin=RelativePoint(x=0.5, y=0.5), width=0.0, height=0.0
    )

    cropped_image = image.crop(relative_area)

    assert cropped_image.shape == (0, 0)
    assert cropped_image.pixel_size == pixel_size
