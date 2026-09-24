# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import pytest

from fibsem_maestro.logging.image.overlay import RectangleOverlay


def test_rectangle_overlay_stores_geometry() -> None:
    rect = RectangleOverlay(x=1.0, y=2.0, width=3.0, height=4.0)

    assert (rect.x, rect.y, rect.width, rect.height) == (1.0, 2.0, 3.0, 4.0)


def test_rectangle_overlay_style_defaults() -> None:
    rect = RectangleOverlay(x=1.0, y=2.0, width=3.0, height=4.0)

    assert rect.color == "black"
    assert rect.alpha == pytest.approx(1.0)
    assert rect.linewidth == pytest.approx(1.0)


def test_rectangle_overlay_style_can_be_overridden() -> None:
    rect = RectangleOverlay(1.0, 2.0, 3.0, 4.0, color="red", alpha=0.3, linewidth=2.5)

    assert (rect.color, rect.alpha, rect.linewidth) == ("red", 0.3, 2.5)
