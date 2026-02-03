# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import pytest

from fibsem_maestro.core.point import PixelPoint, RelativePoint
from fibsem_maestro.core.scanning_area import PixelScanningArea, RelativeScanningArea


def test_relative_scanning_area_to_pixels():
    origin = RelativePoint(x=0.2, y=0.3)
    img_shape = (100, 200)
    relative_area = RelativeScanningArea(origin=origin, width=0.4, height=0.5)
    pixel_area = relative_area.to_pixels(img_shape)
    assert pixel_area.origin.x == 40
    assert pixel_area.origin.y == 30
    assert pixel_area.width == 80
    assert pixel_area.height == 50


def test_relative_scanning_area_to_pixels_no_area():
    origin = RelativePoint(x=0.0, y=0.0)
    img_shape = (100, 200)
    relative_area = RelativeScanningArea(origin=origin, width=0.0, height=0.0)
    pixel_area = relative_area.to_pixels(img_shape)
    assert pixel_area.origin.x == 0
    assert pixel_area.origin.y == 0
    assert pixel_area.width == 0
    assert pixel_area.height == 0


def test_pixel_scanning_area_to_relative():
    origin = PixelPoint(x=50, y=75)
    img_shape = (150, 100)
    pixel_area = PixelScanningArea(origin=origin, width=30, height=40)
    relative_area = pixel_area.to_relative(img_shape)
    assert relative_area.origin.x == pytest.approx(0.5)
    assert relative_area.origin.y == pytest.approx(0.5)
    assert relative_area.width == pytest.approx(0.3)
    assert relative_area.height == pytest.approx(0.26666666666666666)


def test_pixel_scanning_area_to_relative_no_area():
    origin = PixelPoint(x=100, y=150)
    img_shape = (150, 100)
    pixel_area = PixelScanningArea(origin=origin, width=0, height=0)
    relative_area = pixel_area.to_relative(img_shape)
    assert relative_area.origin.x == pytest.approx(1.0)
    assert relative_area.origin.y == pytest.approx(1.0)
    assert relative_area.width == pytest.approx(0.0)
    assert relative_area.height == pytest.approx(0.0)
