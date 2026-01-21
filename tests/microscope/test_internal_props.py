# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import pytest

from fibsem_maestro.microscope.error import MicroscopeError
from fibsem_maestro.microscope.internal_props import InternalPropertiesRegistry


class C:
    def __init__(self) -> None:
        self._value = 0.0

    @property
    def value(self) -> float:
        return self._value

    @value.setter
    def value(self, v: float) -> None:
        self._value = float(v)

    @property
    def read_only(self) -> int:  # no setter; should not get registered
        return 123


class B:
    __slots__ = ("__property",)

    def __init__(self) -> None:
        self.__property = C()

    @property
    def b_value(self) -> int:
        return 1

    @b_value.setter
    def b_value(self, v: int) -> None:
        self._last_b_value = int(v)  # type: ignore[attr-defined]


class A:
    def __init__(self) -> None:
        self.property = B()


def test_registry_builds_and_lists_allowed_sorted():
    reg = InternalPropertiesRegistry(A())

    allowed = reg.allowed()
    assert allowed == sorted(allowed)
    assert "property.b_value" in allowed
    assert "property.property.value" in allowed
    assert "property.property.read_only" not in allowed


def test_has_returns_true_for_existing_and_false_for_missing():
    reg = InternalPropertiesRegistry(A())

    assert reg.has("property.b_value") is True
    assert reg.has("property.property.value") is True

    assert reg.has("does.not.exist") is False
    assert reg.has("property.property.read_only") is False


def test_get_returns_parameter_object():
    reg = InternalPropertiesRegistry(A())

    p = reg.get("property.property.value")
    assert hasattr(p, "get")
    assert hasattr(p, "set")


def test_get_raises_microscope_error_for_missing():
    reg = InternalPropertiesRegistry(A())

    with pytest.raises(MicroscopeError):
        reg.get("missing.path")


def test_setting_and_getting_through_registry_works():
    microscope_root = A()
    reg = InternalPropertiesRegistry(microscope_root)

    param = reg.get("property.property.value")

    # get through registry
    v0 = param.get()
    assert v0 == 0.0

    # set through registry
    param.set(12.5)
    assert param.get() == 12.5

    # get through registry again
    assert param.get() == 12.5

    # and ensure it really changed the underlying instance value
    assert microscope_root.property._B__property.value == 12.5  # type: ignore


def test_registry_keys_are_unique_by_path_even_with_same_type() -> None:
    # create a second C instance reachable via another member name -
    # ensure uniqueness comes from path, not type
    microscope_root = A()

    microscope_root.other = C()  # type: ignore[attr-defined]

    reg = InternalPropertiesRegistry(microscope_root)
    allowed = reg.allowed()

    assert "property.property.value" in allowed
    assert "other.value" in allowed
    assert reg.get("property.property.value") != reg.get("other.value")
