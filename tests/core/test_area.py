# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np

from fibsem_maestro.core.area import MArea, NMArea, PixelArea, RelativeArea
from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, RelativePoint
from fibsem_maestro.core.resolution import Resolution


def test_area_update_replaces_origin_width_height():
    area = RelativeArea(origin=RelativePoint(0.0, 0.0), width=1.0, height=1.0)
    other = RelativeArea(origin=RelativePoint(0.25, 0.5), width=0.5, height=0.75)

    area.update(other)

    assert np.isclose(area.origin.x, 0.25)
    assert np.isclose(area.origin.y, 0.5)
    assert np.isclose(area.width, 0.5)
    assert np.isclose(area.height, 0.75)


def test_area_shifted_returns_new_area_with_offset_origin():
    area = RelativeArea(origin=RelativePoint(0.1, 0.2), width=0.5, height=0.5)

    shifted = area.shifted(RelativePoint(0.1, 0.1))

    assert np.isclose(shifted.origin.x, 0.2)
    assert np.isclose(shifted.origin.y, 0.3)
    assert np.isclose(shifted.width, 0.5)
    assert np.isclose(shifted.height, 0.5)


def test_area_shifted_does_not_modify_original():
    area = RelativeArea(origin=RelativePoint(0.1, 0.2), width=0.5, height=0.5)

    area.shifted(RelativePoint(0.1, 0.1))

    assert np.isclose(area.origin.x, 0.1)
    assert np.isclose(area.origin.y, 0.2)


def test_relative_area_full_covers_entire_frame():
    area = RelativeArea.full()

    assert np.isclose(area.origin.x, 0.0)
    assert np.isclose(area.origin.y, 0.0)
    assert np.isclose(area.width, 1.0)
    assert np.isclose(area.height, 1.0)


def test_relative_area_is_full_frame_returns_true_for_full():
    assert RelativeArea.full().is_full_frame() is True


def test_relative_area_is_full_frame_returns_false_for_partial():
    area = RelativeArea(origin=RelativePoint(0.1, 0.0), width=0.9, height=1.0)

    assert area.is_full_frame() is False


def test_relative_area_to_pixels_correct_coordinates():
    area = RelativeArea(origin=RelativePoint(0.5, 0.25), width=0.5, height=0.5)
    resolution = Resolution(width=200, height=100)

    px = area.to_pixels(resolution)

    assert px.origin.x == 100
    assert px.origin.y == 25
    assert px.width == 100
    assert px.height == 50


def test_relative_area_to_nanometers_correct_values():
    area = RelativeArea(origin=RelativePoint(0.5, 0.25), width=0.5, height=0.5)
    resolution = Resolution(width=200, height=100)

    nm = area.to_nanometers(resolution, pixel_size_nm=2.0)

    assert np.isclose(nm.origin.x, 200.0)
    assert np.isclose(nm.origin.y, 50.0)
    assert np.isclose(nm.width, 200.0)
    assert np.isclose(nm.height, 100.0)


def test_relative_area_to_meters_correct_values():
    area = RelativeArea(origin=RelativePoint(0.5, 0.25), width=0.5, height=0.5)
    resolution = Resolution(width=200, height=100)

    m = area.to_meters(resolution, pixel_size_m=2e-9)

    assert np.isclose(m.origin.x, 200e-9)
    assert np.isclose(m.origin.y, 50e-9)
    assert np.isclose(m.width, 200e-9)
    assert np.isclose(m.height, 100e-9)


def test_pixel_area_to_relative_correct_coordinates():
    area = PixelArea(origin=PixelPoint(100, 25), width=100, height=50)
    resolution = Resolution(width=200, height=100)

    rel = area.to_relative(resolution)

    assert np.isclose(rel.origin.x, 0.5)
    assert np.isclose(rel.origin.y, 0.25)
    assert np.isclose(rel.width, 0.5)
    assert np.isclose(rel.height, 0.5)


def test_pixel_area_to_nanometers_correct_values():
    area = PixelArea(origin=PixelPoint(100, 25), width=100, height=50)

    nm = area.to_nanometers(pixel_size_nm=2.0)

    assert np.isclose(nm.origin.x, 200.0)
    assert np.isclose(nm.origin.y, 50.0)
    assert np.isclose(nm.width, 200.0)
    assert np.isclose(nm.height, 100.0)


def test_pixel_area_to_meters_correct_values():
    area = PixelArea(origin=PixelPoint(100, 25), width=100, height=50)

    m = area.to_meters(pixel_size_m=2e-9)

    assert np.isclose(m.origin.x, 200e-9)
    assert np.isclose(m.origin.y, 50e-9)
    assert np.isclose(m.width, 200e-9)
    assert np.isclose(m.height, 100e-9)


def test_nm_area_to_pixels_correct_coordinates():
    area = NMArea(origin=NMPoint(200.0, 50.0), width=200.0, height=100.0)

    px = area.to_pixels(pixel_size_nm=2.0)

    assert px.origin.x == 100
    assert px.origin.y == 25
    assert px.width == 100
    assert px.height == 50


def test_nm_area_to_relative_correct_coordinates():
    area = NMArea(origin=NMPoint(200.0, 50.0), width=200.0, height=100.0)
    resolution = Resolution(width=200, height=100)

    rel = area.to_relative(resolution, pixel_size_nm=2.0)

    assert np.isclose(rel.origin.x, 0.5)
    assert np.isclose(rel.origin.y, 0.25)
    assert np.isclose(rel.width, 0.5)
    assert np.isclose(rel.height, 0.5)


def test_nm_area_to_meters_correct_values():
    area = NMArea(origin=NMPoint(200.0, 50.0), width=200.0, height=100.0)

    m = area.to_meters()

    assert np.isclose(m.origin.x, 200e-9)
    assert np.isclose(m.origin.y, 50e-9)
    assert np.isclose(m.width, 200e-9)
    assert np.isclose(m.height, 100e-9)


def test_m_area_to_pixels_correct_coordinates():
    area = MArea(origin=MPoint(200e-9, 50e-9), width=200e-9, height=100e-9)

    px = area.to_pixels(pixel_size_m=2e-9)

    assert px.origin.x == 100
    assert px.origin.y == 25
    assert px.width == 100
    assert px.height == 50


def test_m_area_to_relative_correct_coordinates():
    area = MArea(origin=MPoint(200e-9, 50e-9), width=200e-9, height=100e-9)
    resolution = Resolution(width=200, height=100)

    rel = area.to_relative(resolution, pixel_size_m=2e-9)

    assert np.isclose(rel.origin.x, 0.5)
    assert np.isclose(rel.origin.y, 0.25)
    assert np.isclose(rel.width, 0.5)
    assert np.isclose(rel.height, 0.5)


def test_m_area_to_nanometers_correct_values():
    area = MArea(origin=MPoint(200e-9, 50e-9), width=200e-9, height=100e-9)

    nm = area.to_nanometers()

    assert np.isclose(nm.origin.x, 200.0)
    assert np.isclose(nm.origin.y, 50.0)
    assert np.isclose(nm.width, 200.0)
    assert np.isclose(nm.height, 100.0)


def test_relative_area_to_pixels_and_back_is_identity():
    area = RelativeArea(origin=RelativePoint(0.5, 0.25), width=0.5, height=0.5)
    resolution = Resolution(width=200, height=100)

    result = area.to_pixels(resolution).to_relative(resolution)

    assert np.isclose(result.origin.x, area.origin.x)
    assert np.isclose(result.origin.y, area.origin.y)
    assert np.isclose(result.width, area.width)
    assert np.isclose(result.height, area.height)


def test_nm_area_to_meters_and_back_is_identity():
    area = NMArea(origin=NMPoint(200.0, 50.0), width=200.0, height=100.0)

    result = area.to_meters().to_nanometers()

    assert np.isclose(result.origin.x, area.origin.x)
    assert np.isclose(result.origin.y, area.origin.y)
    assert np.isclose(result.width, area.width)
    assert np.isclose(result.height, area.height)
