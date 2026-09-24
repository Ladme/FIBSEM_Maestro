# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import dataclasses

import numpy as np
import pytest

from fibsem_maestro.logging.image.plot_element import Curve, VerticalLine


@pytest.fixture
def image() -> np.ndarray:
    return np.arange(16, dtype=np.uint8).reshape(4, 4)


def test_curve_stores_its_fields() -> None:
    curve = Curve(color="red", linewidth=1.5, x=[0.0, 1.0], y=[2.0, 3.0])

    assert curve.color == "red"
    assert curve.linewidth == pytest.approx(1.5)
    assert curve.x == [0.0, 1.0]
    assert curve.y == [2.0, 3.0]


def test_curve_positional_order_is_color_linewidth_x_y() -> None:
    assert [f.name for f in dataclasses.fields(Curve)] == [
        "color",
        "linewidth",
        "x",
        "y",
    ]

    curve = Curve("red", 1.5, [0.0], [2.0])

    assert curve.x == [0.0]
    assert curve.y == [2.0]


def test_vertical_line_stores_its_fields() -> None:
    line = VerticalLine(color="black", linewidth=2.0, x=5.0)

    assert line.color == "black"
    assert line.linewidth == pytest.approx(2.0)
    assert line.x == pytest.approx(5.0)


def test_vertical_line_positional_order_is_color_linewidth_x() -> None:
    assert [f.name for f in dataclasses.fields(VerticalLine)] == [
        "color",
        "linewidth",
        "x",
    ]
    assert VerticalLine("black", 2.0, 5.0).x == pytest.approx(5.0)
