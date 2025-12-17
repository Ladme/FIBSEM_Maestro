# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np
import pytest
from numpy.typing import NDArray

from fibsem_maestro.autofunctions.error import AutofunctionError
from fibsem_maestro.autofunctions.sweeping_registry import SweepingRegistry


@pytest.fixture(autouse=True)
def isolate_registry():
    """Ensure SweepingRegistry is clean for each test."""
    original = dict(SweepingRegistry._registry)
    SweepingRegistry._registry.clear()
    try:
        yield
    finally:
        SweepingRegistry._registry.clear()
        SweepingRegistry._registry.update(original)


def test_register_and_get_returns_same_function_object():
    @SweepingRegistry.register("basic")
    def basic_sweep(
        base: float, sweep_range: tuple[float, float], steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.linspace(base + sweep_range[0], base + sweep_range[1], steps)

    fn = SweepingRegistry.get("basic")
    assert fn is basic_sweep

    out = fn(10.0, (-1.0, 1.0), 3, 0)
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, np.array([9.0, 10.0, 11.0]))


def test_get_raises_for_missing_name():
    with pytest.raises(AutofunctionError, match=r"not registered"):
        SweepingRegistry.get("does-not-exist")


def test_register_raises_on_duplicate_name():
    @SweepingRegistry.register("dup")
    def sweep1(  # type: ignore
        base: float, _sweep_range: tuple[float, float], _steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.array([base])

    with pytest.raises(AutofunctionError, match=r"already registered"):

        @SweepingRegistry.register("dup")
        def sweep2(  # type: ignore
            base: float,
            _sweep_range: tuple[float, float],
            _steps: int,
            _repetition: int,
        ) -> NDArray[np.floating]:
            return np.array([base + 1])


def test_register_decorator_returns_function_unchanged():
    def fn(
        base: float, _sweep_range: tuple[float, float], _steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.array([base])

    decorated = SweepingRegistry.register("identity")(fn)
    assert decorated is fn
    assert SweepingRegistry.get("identity") is fn


def test_has_reflects_registration_state():
    assert SweepingRegistry.has("x") is False

    @SweepingRegistry.register("x")
    def sweep(  # type: ignore
        base: float, _sweep_range: tuple[float, float], _steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.array([base])

    assert SweepingRegistry.has("x") is True


def test_allowed_lists_registered_names():
    assert SweepingRegistry.allowed() == []

    @SweepingRegistry.register("a")
    def sweep_a(  # type: ignore
        base: float, _sweep_range: tuple[float, float], _steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.array([base])

    @SweepingRegistry.register("b")
    def sweep_b(  # type: ignore
        base: float, _sweep_range: tuple[float, float], _steps: int, _repetition: int
    ) -> NDArray[np.floating]:
        return np.array([base])

    allowed = SweepingRegistry.allowed()
    assert allowed == ["a", "b"]
