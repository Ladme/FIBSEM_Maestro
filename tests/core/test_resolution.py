# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.core.resolution import Resolution


def test_resolution_stores_width_and_height():
    resolution = Resolution(width=1536, height=1024)

    assert resolution.width == 1536
    assert resolution.height == 1024


def test_resolution_positional_order_is_width_then_height():
    resolution = Resolution(1536, 1024)

    assert resolution.width == 1536
    assert resolution.height == 1024


def test_resolution_str_formats_as_width_by_height():
    assert str(Resolution(width=1536, height=1024)) == "1536x1024"


def test_resolution_to_tuple_returns_width_then_height():
    resolution = Resolution(width=1536, height=1024)

    assert resolution.to_tuple() == (1536, 1024)


def test_resolution_equality_compares_both_fields():
    assert Resolution(width=1536, height=1024) == Resolution(width=1536, height=1024)
    assert Resolution(width=1536, height=1024) != Resolution(width=1536, height=768)
    assert Resolution(width=1536, height=1024) != Resolution(width=768, height=1024)


def test_resolution_transposed_resolutions_are_not_equal():
    assert Resolution(width=1536, height=1024) != Resolution(width=1024, height=1536)
