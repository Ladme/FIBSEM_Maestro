# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import numpy as np
import pytest
from numpy.typing import NDArray

from fibsem_maestro.autofocus.error import AutofunctionError
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweeping_registry import SweepingRegistry
from fibsem_maestro.autofocus.sweeping_strategy import SweepingStrategy
from fibsem_maestro.settings.sweeping_settings import (
    BasicStrategySettings,
    SweepingStrategySettings,
)


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
    class BasicSweep(SweepingStrategy):
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = repetition
            return np.linspace(base + range[0], base + range[1], steps)

        def evaluate(self, results: list[AutofocusResult]) -> float:
            # not used in this test
            return float(results[0].value)  # type: ignore[attr-defined]

    cls = SweepingRegistry.get("basic")
    assert cls is BasicSweep

    # instantiate and use the basic strategy
    strategy = cls(BasicStrategySettings())  # type: ignore[call-arg]
    out = strategy.generate(10.0, (-1.0, 1.0), 3, 0)
    assert isinstance(out, np.ndarray)
    assert np.allclose(out, np.array([9.0, 10.0, 11.0]))


def test_get_raises_for_missing_name():
    with pytest.raises(AutofunctionError, match=r"not registered"):
        SweepingRegistry.get("does-not-exist")


def test_register_raises_on_duplicate_name():
    @SweepingRegistry.register("dup")
    class Sweep1(SweepingStrategy):  # type: ignore
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = range, steps, repetition
            return np.array([base])

        def evaluate(self, results: list[AutofocusResult]) -> float:
            return float(results[0].value)  # type: ignore[attr-defined]

    with pytest.raises(AutofunctionError, match=r"already registered"):

        @SweepingRegistry.register("dup")
        class Sweep2(SweepingStrategy):  # type: ignore
            def __init__(self, settings: SweepingStrategySettings):
                self.settings = settings

            def generate(
                self,
                base: float,
                range: tuple[float, float],
                steps: int,
                repetition: int,
            ) -> NDArray[np.floating]:
                _ = range, steps, repetition
                return np.array([base + 1])

            def evaluate(self, results: list[AutofocusResult]) -> float:
                return float(results[0].value)  # type: ignore[attr-defined]


def test_register_decorator_returns_function_unchanged():
    class Identity(SweepingStrategy):
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = range, steps, repetition
            return np.array([base])

        def evaluate(self, results: list[AutofocusResult]) -> float:
            return float(results[0].value)  # type: ignore[attr-defined]

    decorated = SweepingRegistry.register("identity")(Identity)
    assert decorated is Identity
    assert SweepingRegistry.get("identity") is Identity


def test_has_reflects_registration_state():
    assert SweepingRegistry.has("x") is False

    @SweepingRegistry.register("x")
    class SweepX(SweepingStrategy):  # type: ignore
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = range, steps, repetition
            return np.array([base])

        def evaluate(self, results: list[AutofocusResult]) -> float:
            return float(results[0].value)  # type: ignore[attr-defined]

    assert SweepingRegistry.has("x") is True


def test_allowed_lists_registered_names():
    assert SweepingRegistry.allowed() == []

    @SweepingRegistry.register("a")
    class SweepA(SweepingStrategy):  # type: ignore
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = range, steps, repetition
            return np.array([base])

        def evaluate(self, results: list[AutofocusResult]) -> float:
            return float(results[0].value)  # type: ignore[attr-defined]

    @SweepingRegistry.register("b")
    class SweepB(SweepingStrategy):  # type: ignore
        def __init__(self, settings: SweepingStrategySettings):
            self.settings = settings

        def generate(
            self,
            base: float,
            range: tuple[float, float],
            steps: int,
            repetition: int,
        ) -> NDArray[np.floating]:
            _ = range, steps, repetition
            return np.array([base])

        def evaluate(self, results: list[AutofocusResult]) -> float:
            return float(results[0].value)  # type: ignore[attr-defined]

    allowed = SweepingRegistry.allowed()
    assert allowed == ["a", "b"]
