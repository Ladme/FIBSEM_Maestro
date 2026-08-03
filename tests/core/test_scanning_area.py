# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.core.area import (
    MArea,
    NMArea,
    PixelArea,
    RelativeArea,
)
from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, RelativePoint
from fibsem_maestro.core.resolution import Resolution


def test_scanning_area_update():
    origin1 = PixelPoint(x=10, y=20)
    area1 = PixelArea(origin=origin1, width=100, height=200)
    origin2 = PixelPoint(x=30, y=40)
    area2 = PixelArea(origin=origin2, width=50, height=60)
    area1.update(area2)
    assert area1.origin.x == 30
    assert area1.origin.y == 40
    assert area1.width == 50
    assert area1.height == 60


def test_relative_scanning_area_to_pixels():
    origin = RelativePoint(x=0.2, y=0.3)
    resolution = Resolution(200, 100)
    relative_area = RelativeArea(origin=origin, width=0.4, height=0.5)
    pixel_area = relative_area.to_pixels(resolution)
    assert pixel_area.origin.x == 40
    assert pixel_area.origin.y == 30
    assert pixel_area.width == 80
    assert pixel_area.height == 50


def test_relative_scanning_area_to_pixels_no_area():
    origin = RelativePoint(x=0.0, y=0.0)
    resolution = Resolution(200, 100)
    relative_area = RelativeArea(origin=origin, width=0.0, height=0.0)
    pixel_area = relative_area.to_pixels(resolution)
    assert pixel_area.origin.x == 0
    assert pixel_area.origin.y == 0
    assert pixel_area.width == 0
    assert pixel_area.height == 0


def test_relative_scanning_area_to_nanometers():
    origin = RelativePoint(x=0.2, y=0.3)
    resolution = Resolution(200, 100)
    pixel_size_nm = 10.0
    relative_area = RelativeArea(origin=origin, width=0.4, height=0.5)
    nm_area = relative_area.to_nanometers(resolution, pixel_size_nm)
    assert nm_area.origin.x == 40 * pixel_size_nm
    assert nm_area.origin.y == 30 * pixel_size_nm
    assert nm_area.width == 80 * pixel_size_nm
    assert nm_area.height == 50 * pixel_size_nm


def test_relative_scanning_area_to_nanometers_no_area():
    origin = RelativePoint(x=0.0, y=0.0)
    resolution = Resolution(200, 100)
    pixel_size_nm = 10.0
    relative_area = RelativeArea(origin=origin, width=0.0, height=0.0)
    nm_area = relative_area.to_nanometers(resolution, pixel_size_nm)
    assert nm_area.origin.x == 0
    assert nm_area.origin.y == 0
    assert nm_area.width == 0
    assert nm_area.height == 0


def test_relative_scanning_area_to_meters():
    origin = RelativePoint(x=0.2, y=0.3)
    resolution = Resolution(200, 100)
    pixel_size_m = 1e-6
    relative_area = RelativeArea(origin=origin, width=0.4, height=0.5)
    m_area = relative_area.to_meters(resolution, pixel_size_m)
    assert m_area.origin.x == 40 * pixel_size_m
    assert m_area.origin.y == 30 * pixel_size_m
    assert m_area.width == 80 * pixel_size_m
    assert m_area.height == 50 * pixel_size_m


def test_relative_scanning_area_to_meters_no_area():
    origin = RelativePoint(x=0.0, y=0.0)
    resolution = Resolution(200, 100)
    pixel_size_m = 1e-6
    relative_area = RelativeArea(origin=origin, width=0.0, height=0.0)
    m_area = relative_area.to_meters(resolution, pixel_size_m)
    assert m_area.origin.x == 0
    assert m_area.origin.y == 0
    assert m_area.width == 0
    assert m_area.height == 0


def test_pixel_scanning_area_to_relative():
    origin = PixelPoint(x=50, y=75)
    resolution = Resolution(100, 150)
    pixel_area = PixelArea(origin=origin, width=30, height=40)
    relative_area = pixel_area.to_relative(resolution)
    assert relative_area.origin.x == pytest.approx(0.5)
    assert relative_area.origin.y == pytest.approx(0.5)
    assert relative_area.width == pytest.approx(0.3)
    assert relative_area.height == pytest.approx(0.26666666666666666)


def test_pixel_scanning_area_to_relative_no_area():
    origin = PixelPoint(x=100, y=150)
    resolution = Resolution(100, 150)
    pixel_area = PixelArea(origin=origin, width=0, height=0)
    relative_area = pixel_area.to_relative(resolution)
    assert relative_area.origin.x == pytest.approx(1.0)
    assert relative_area.origin.y == pytest.approx(1.0)
    assert relative_area.width == pytest.approx(0.0)
    assert relative_area.height == pytest.approx(0.0)


def test_pixel_scanning_area_to_nanometers():
    origin = PixelPoint(x=50, y=75)
    pixel_size_nm = 10.0
    pixel_area = PixelArea(origin=origin, width=30, height=40)
    nm_area = pixel_area.to_nanometers(pixel_size_nm)
    assert nm_area.origin.x == 50 * pixel_size_nm
    assert nm_area.origin.y == 75 * pixel_size_nm
    assert nm_area.width == 30 * pixel_size_nm
    assert nm_area.height == 40 * pixel_size_nm


def test_pixel_scanning_area_to_nanometers_no_area():
    origin = PixelPoint(x=0, y=0)
    pixel_size_nm = 10.0
    pixel_area = PixelArea(origin=origin, width=0, height=0)
    nm_area = pixel_area.to_nanometers(pixel_size_nm)
    assert nm_area.origin.x == 0
    assert nm_area.origin.y == 0
    assert nm_area.width == 0
    assert nm_area.height == 0


def test_pixel_scanning_area_to_meters():
    origin = PixelPoint(x=50, y=75)
    pixel_size_m = 1e-6
    pixel_area = PixelArea(origin=origin, width=30, height=40)
    m_area = pixel_area.to_meters(pixel_size_m)
    assert m_area.origin.x == 50 * pixel_size_m
    assert m_area.origin.y == 75 * pixel_size_m
    assert m_area.width == 30 * pixel_size_m
    assert m_area.height == 40 * pixel_size_m


def test_pixel_scanning_area_to_meters_no_area():
    origin = PixelPoint(x=0, y=0)
    pixel_size_m = 1e-6
    pixel_area = PixelArea(origin=origin, width=0, height=0)
    m_area = pixel_area.to_meters(pixel_size_m)
    assert m_area.origin.x == 0
    assert m_area.origin.y == 0
    assert m_area.width == 0
    assert m_area.height == 0


def test_nm_scanning_area_to_relative():
    origin = NMPoint(x=200, y=300)
    resolution = Resolution(200, 100)
    pixel_size_nm = 10.0
    nm_area = NMArea(origin=origin, width=400, height=500)
    relative_area = nm_area.to_relative(resolution, pixel_size_nm)
    assert relative_area.origin.x == 200 / (resolution.width * pixel_size_nm)
    assert relative_area.origin.y == 300 / (resolution.height * pixel_size_nm)
    assert relative_area.width == 400 / (resolution.width * pixel_size_nm)
    assert relative_area.height == 500 / (resolution.height * pixel_size_nm)


def test_nm_scanning_area_to_relative_no_area():
    origin = NMPoint(x=0, y=0)
    resolution = Resolution(200, 100)
    pixel_size_nm = 10.0
    nm_area = NMArea(origin=origin, width=0, height=0)
    relative_area = nm_area.to_relative(resolution, pixel_size_nm)
    assert relative_area.origin.x == 0
    assert relative_area.origin.y == 0
    assert relative_area.width == 0
    assert relative_area.height == 0


def test_nm_scanning_area_to_pixels():
    origin = NMPoint(x=200, y=300)
    pixel_size_nm = 10.0
    nm_area = NMArea(origin=origin, width=400, height=500)
    pixel_area = nm_area.to_pixels(pixel_size_nm)
    assert pixel_area.origin.x == 20
    assert pixel_area.origin.y == 30
    assert pixel_area.width == 40
    assert pixel_area.height == 50


def test_nm_scanning_area_to_pixels_no_area():
    origin = NMPoint(x=0, y=0)
    pixel_size_nm = 10.0
    nm_area = NMArea(origin=origin, width=0, height=0)
    pixel_area = nm_area.to_pixels(pixel_size_nm)
    assert pixel_area.origin.x == 0
    assert pixel_area.origin.y == 0
    assert pixel_area.width == 0
    assert pixel_area.height == 0


def test_nm_scanning_area_to_meters():
    origin = NMPoint(x=200, y=300)
    nm_area = NMArea(origin=origin, width=400, height=500)
    m_area = nm_area.to_meters()
    assert m_area.origin.x == 200 * 1e-9
    assert m_area.origin.y == 300 * 1e-9
    assert m_area.width == 400 * 1e-9
    assert m_area.height == 500 * 1e-9


def test_nm_scanning_area_to_meters_no_area():
    origin = NMPoint(x=0, y=0)
    nm_area = NMArea(origin=origin, width=0, height=0)
    m_area = nm_area.to_meters()
    assert m_area.origin.x == 0
    assert m_area.origin.y == 0
    assert m_area.width == 0
    assert m_area.height == 0


def test_m_scanning_area_to_relative():
    origin = MPoint(x=100e-9, y=20e-9)
    resolution = Resolution(200, 100)
    pixel_size_m = 1e-9
    m_area = MArea(origin=origin, width=50e-9, height=10e-9)
    relative_area = m_area.to_relative(resolution, pixel_size_m)
    assert relative_area.origin.x == 0.5
    assert relative_area.origin.y == 0.2
    assert relative_area.width == 0.25
    assert relative_area.height == 0.1


def test_m_scanning_area_to_relative_no_area():
    origin = MPoint(x=0, y=0)
    resolution = Resolution(200, 100)
    pixel_size_m = 1e-9
    m_area = MArea(origin=origin, width=0, height=0)
    relative_area = m_area.to_relative(resolution, pixel_size_m)
    assert relative_area.origin.x == 0
    assert relative_area.origin.y == 0
    assert relative_area.width == 0
    assert relative_area.height == 0


def test_m_scanning_area_to_pixels():
    origin = MPoint(x=100e-9, y=20e-9)
    pixel_size_m = 1e-9
    m_area = MArea(origin=origin, width=50e-9, height=10e-9)
    pixel_area = m_area.to_pixels(pixel_size_m)
    assert pixel_area.origin.x == 100
    assert pixel_area.origin.y == 20
    assert pixel_area.width == 50
    assert pixel_area.height == 10


def test_m_scanning_area_to_pixels_no_area():
    origin = MPoint(x=0, y=0)
    pixel_size_m = 1e-9
    m_area = MArea(origin=origin, width=0, height=0)
    pixel_area = m_area.to_pixels(pixel_size_m)
    assert pixel_area.origin.x == 0
    assert pixel_area.origin.y == 0
    assert pixel_area.width == 0
    assert pixel_area.height == 0


def test_m_scanning_area_to_nanometers():
    origin = MPoint(x=200e-9, y=300e-9)
    m_area = MArea(origin=origin, width=400e-9, height=500e-9)
    nm_area = m_area.to_nanometers()
    assert nm_area.origin.x == 200
    assert nm_area.origin.y == 300
    assert nm_area.width == 400
    assert nm_area.height == 500


def test_m_scanning_area_to_nanometers_no_area():
    origin = MPoint(x=0, y=0)
    m_area = MArea(origin=origin, width=0, height=0)
    nm_area = m_area.to_nanometers()
    assert nm_area.origin.x == 0
    assert nm_area.origin.y == 0
    assert nm_area.width == 0
    assert nm_area.height == 0
