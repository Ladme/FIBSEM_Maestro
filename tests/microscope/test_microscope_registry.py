# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from unittest.mock import MagicMock

import pytest

from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry


@pytest.fixture(autouse=True)
def isolate_registry():
    """Ensure MicroscopeRegistry is clean for each test."""
    original = dict(MicroscopeRegistry._registry)
    MicroscopeRegistry._registry.clear()
    try:
        yield
    finally:
        MicroscopeRegistry._registry.clear()
        MicroscopeRegistry._registry.update(original)


def test_register_and_get_returns_same_class():
    @MicroscopeRegistry.register("test_control")
    class TestMicroscope(MagicMock):
        pass

    assert MicroscopeRegistry.get("test_control") is TestMicroscope


def test_get_raises_for_missing_name():
    with pytest.raises(MicroscopeError, match="not registered"):
        MicroscopeRegistry.get("does-not-exist")


def test_register_raises_on_duplicate_name():
    @MicroscopeRegistry.register("dup")
    class Microscope1(MagicMock):  # type: ignore
        pass

    with pytest.raises(MicroscopeError, match="already registered"):

        @MicroscopeRegistry.register("dup")
        class Microscope2(MagicMock):  # type: ignore
            pass


def test_register_decorator_returns_class_unchanged():
    class MyMicroscope(MagicMock):
        pass

    decorated = MicroscopeRegistry.register("my_microscope")(MyMicroscope)

    assert decorated is MyMicroscope
    assert MicroscopeRegistry.get("my_microscope") is MyMicroscope


def test_has_returns_false_before_registration():
    assert MicroscopeRegistry.has("test_control") is False


def test_has_returns_true_after_registration():
    @MicroscopeRegistry.register("test_control")
    class SomeMicroscope(MagicMock):  # type: ignore
        pass

    assert MicroscopeRegistry.has("test_control") is True


def test_allowed_returns_empty_list_when_registry_is_empty():
    assert MicroscopeRegistry.allowed() == []


def test_allowed_lists_all_registered_names():
    @MicroscopeRegistry.register("a")
    class MicroscopeA(MagicMock):  # type: ignore
        pass

    @MicroscopeRegistry.register("b")
    class MicroscopeB(MagicMock):  # type: ignore
        pass

    assert MicroscopeRegistry.allowed() == ["a", "b"]
