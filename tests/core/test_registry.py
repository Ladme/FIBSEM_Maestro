# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections.abc import Callable

import pytest

from fibsem_maestro.core.registry import Registry, RegistryError


def test_register_and_get_class() -> None:
    registry: Registry[type] = Registry("thing")

    @registry.register("foo")
    class Foo:
        pass

    assert registry.get("foo") is Foo


def test_register_and_get_function() -> None:
    registry: Registry[Callable[..., int]] = Registry("operation")

    @registry.register("double")
    def double(x: int) -> int:
        return x * 2

    assert registry.get("double") is double
    assert registry.get("double")(3) == 6


def test_register_multiple_entries() -> None:
    registry: Registry[type] = Registry("shape")

    @registry.register("circle")
    class Circle:
        pass

    @registry.register("square")
    class Square:
        pass

    assert registry.get("circle") is Circle
    assert registry.get("square") is Square


def test_decorator_returns_object_unchanged() -> None:
    registry: Registry[type] = Registry("thing")

    @registry.register("bar")
    class Bar:
        pass

    instance = Bar()
    assert isinstance(instance, Bar)


def test_get_unknown_key_raises() -> None:
    registry: Registry[type] = Registry("widget")

    with pytest.raises(RegistryError, match="Unknown widget 'missing'"):
        registry.get("missing")


def test_get_error_lists_available_keys() -> None:
    registry: Registry[Callable] = Registry("func")

    @registry.register("alpha")
    def alpha() -> None:
        pass

    @registry.register("beta")
    def beta() -> None:
        pass

    with pytest.raises(RegistryError, match="Available: alpha, beta"):
        registry.get("gamma")


def test_duplicate_registration_raises() -> None:
    registry: Registry[type] = Registry("thing")

    @registry.register("dup")
    class First:
        pass

    with pytest.raises(RegistryError, match="'dup' is already registered"):

        @registry.register("dup")
        class Second:
            pass


def test_contains() -> None:
    registry: Registry[type] = Registry("thing")

    @registry.register("present")
    class Present:
        pass

    assert "present" in registry
    assert "absent" not in registry


def test_iter_yields_registered_keys() -> None:
    registry: Registry[Callable] = Registry("func")

    @registry.register("one")
    def one() -> None:
        pass

    @registry.register("two")
    def two() -> None:
        pass

    assert set(registry) == {"one", "two"}


def test_len() -> None:
    registry: Registry[type] = Registry("thing")
    assert len(registry) == 0

    @registry.register("a")
    class A:
        pass

    @registry.register("b")
    class B:
        pass

    assert len(registry) == 2


def test_repr_empty() -> None:
    registry: Registry[type] = Registry("gadget")
    assert repr(registry) == "Registry[gadget]()"


def test_repr_with_entries() -> None:
    registry: Registry[type] = Registry("gadget")

    @registry.register("beta")
    class Beta:
        pass

    @registry.register("alpha")
    class Alpha:
        pass

    assert repr(registry) == "Registry[gadget](alpha, beta)"


def test_separate_instances_are_independent() -> None:
    registry_a: Registry[type] = Registry("a")
    registry_b: Registry[type] = Registry("b")

    @registry_a.register("shared_name")
    class InA:
        pass

    @registry_b.register("shared_name")
    class InB:
        pass

    assert registry_a.get("shared_name") is InA
    assert registry_b.get("shared_name") is InB


def test_add_and_get() -> None:
    registry: Registry[Callable[..., float]] = Registry("func")

    def my_func(x: float) -> float:
        return x * 2

    registry.add("double", my_func)

    assert registry.get("double") is my_func


def test_add_duplicate_raises() -> None:
    registry: Registry[Callable] = Registry("func")

    def first() -> None:
        pass

    def second() -> None:
        pass

    registry.add("name", first)

    with pytest.raises(RegistryError, match="'name' is already registered"):
        registry.add("name", second)


def test_add_bulk() -> None:
    registry: Registry[int] = Registry("constant")
    values = {"one": 1, "two": 2, "three": 3}

    for key, val in values.items():
        registry.add(key, val)

    assert registry.get("one") == 1
    assert registry.get("two") == 2
    assert registry.get("three") == 3
    assert len(registry) == 3


def test_validate_returns_key_when_registered() -> None:
    registry: Registry[type] = Registry("thing")

    @registry.register("valid")
    class Valid:
        pass

    assert registry.validate("valid") == "valid"


def test_validate_raises_value_error_for_unknown_key() -> None:
    registry: Registry[type] = Registry("widget")

    @registry.register("known")
    class Known:
        pass

    with pytest.raises(ValueError, match="Unknown widget 'missing'"):
        registry.validate("missing")


def test_validate_error_lists_available_keys() -> None:
    registry: Registry[int] = Registry("constant")
    registry.add("alpha", 1)
    registry.add("beta", 2)

    with pytest.raises(ValueError, match="Available: alpha, beta"):
        registry.validate("gamma")


def test_validate_as_pydantic_after_validator() -> None:
    from typing import Annotated

    from pydantic import AfterValidator, BaseModel

    colors = Registry[str]("color")
    colors.add("red", "#ff0000")
    colors.add("blue", "#0000ff")

    class Config(BaseModel):
        color: Annotated[str, AfterValidator(colors.validate)]

    config = Config(color="red")
    assert config.color == "red"

    with pytest.raises(Exception, match="Unknown color 'green'"):
        Config(color="green")
