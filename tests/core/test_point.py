# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.core.point import MPoint, NMPoint, PixelPoint, Point, RelativePoint
from fibsem_maestro.core.resolution import Resolution


def test_mul_int_scalar_on_float_point():
    p = Point(2.0, 3.0)
    result = p * 2
    assert result.x == pytest.approx(4.0)
    assert result.y == pytest.approx(6.0)


def test_mul_float_scalar_on_float_point():
    p = Point(2.0, 3.0)
    result = p * 0.5
    assert result.x == pytest.approx(1.0)
    assert result.y == pytest.approx(1.5)


def test_mul_float_scalar_on_int_point_raises():
    p = PixelPoint(2, 3)
    with pytest.raises(TypeError):
        _ = p * 0.5


def test_mul_int_scalar_on_int_point():
    p = PixelPoint(2, 3)
    result = p * 2
    assert result.x == 4
    assert result.y == 6


def test_mul_point_same_type():
    p1 = Point(2.0, 3.0)
    p2 = Point(4.0, 5.0)
    result = p1 * p2
    assert result.x == pytest.approx(8.0)
    assert result.y == pytest.approx(15.0)


def test_mul_point_different_type_raises():
    p1 = NMPoint(1.0, 2.0)
    p2 = PixelPoint(1, 2)
    with pytest.raises(TypeError):
        _ = p1 * p2


def test_add_same_type():
    p1 = Point(1.0, 2.0)
    p2 = Point(3.0, 4.0)
    result = p1 + p2
    assert result.x == pytest.approx(4.0)
    assert result.y == pytest.approx(6.0)


def test_add_different_type_raises():
    p1 = MPoint(1.0, 2.0)
    p2 = PixelPoint(3, 4)
    with pytest.raises(TypeError):
        _ = p1 + p2


def test_sub_same_type():
    p1 = Point(5.0, 7.0)
    p2 = Point(2.0, 3.0)
    result = p1 - p2
    assert result.x == pytest.approx(3.0)
    assert result.y == pytest.approx(4.0)


def test_sub_different_type_raises():
    p1 = NMPoint(5.0, 7.0)
    p2 = PixelPoint(2, 3)
    with pytest.raises(TypeError):
        _ = p1 - p2


def test_pixel_to_relative():
    p = PixelPoint(10, 20)
    resolution = Resolution(200, 100)
    r = p.to_relative(resolution)
    assert r.x == pytest.approx(0.05)
    assert r.y == pytest.approx(0.20)


def test_pixel_to_nanometers():
    p = PixelPoint(3, 4)
    nm = p.to_nanometers(10.0)
    assert nm.x == pytest.approx(30.0)
    assert nm.y == pytest.approx(40.0)


def test_pixel_to_meters():
    p = PixelPoint(3, 4)
    m = p.to_meters(1e-6)
    assert m.x == pytest.approx(3e-6)
    assert m.y == pytest.approx(4e-6)


def test_nm_to_meters():
    nm = NMPoint(2e9, 3e9)
    m = nm.to_meters()
    assert m.x == pytest.approx(2.0)
    assert m.y == pytest.approx(3.0)


def test_nm_to_pixels():
    nm = NMPoint(20.0, 41.0)
    px = nm.to_pixels(10.0)
    assert px.x == 2
    assert px.y == 4


def test_nm_to_relative():
    nm = NMPoint(50.0, 100.0)
    resolution = Resolution(200, 100)
    r = nm.to_relative(resolution, 10.0)
    assert r.x == pytest.approx(0.025)
    assert r.y == pytest.approx(0.1)


def test_m_to_nanometers():
    m = MPoint(2.0, 3.0)
    nm = m.to_nanometers()
    assert nm.x == pytest.approx(2e9)
    assert nm.y == pytest.approx(3e9)


def test_m_to_pixels():
    m = MPoint(5e-8, 1e-7)
    px = m.to_pixels(5e-9)
    assert px.x == 10
    assert px.y == 20


def test_m_to_relative():
    m = MPoint(5e-8, 1e-7)
    resolution = Resolution(200, 100)
    r = m.to_relative(resolution, 5e-9)
    assert r.x == pytest.approx(0.05)
    assert r.y == pytest.approx(0.2)


def test_relative_to_pixels():
    r = RelativePoint(0.5, 0.25)
    resolution = Resolution(200, 100)
    px = r.to_pixels(resolution)
    assert px.x == 100
    assert px.y == 25


def test_relative_to_nanometers():
    r = RelativePoint(0.1, 0.2)
    resolution = Resolution(200, 100)
    nm = r.to_nanometers(resolution, 10.0)
    assert nm.x == pytest.approx(200.0)
    assert nm.y == pytest.approx(200.0)


def test_relative_to_meters():
    r = RelativePoint(0.1, 0.2)
    resolution = Resolution(200, 100)
    m = r.to_meters(resolution, 1e-6)
    assert m.x == pytest.approx(2e-5)
    assert m.y == pytest.approx(2e-5)
