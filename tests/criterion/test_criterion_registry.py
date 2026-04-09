# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
import pytest

from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.criterion_registry import CriterionRegistry
from fibsem_maestro.criterion.error import CriterionError
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.criterion_settings import CriterionSettings


@pytest.fixture(autouse=True)
def isolate_registry():
    """Ensure CriterionRegistry is clean for each test."""
    original = dict(CriterionRegistry._registry)
    CriterionRegistry._registry.clear()
    try:
        yield
    finally:
        CriterionRegistry._registry.clear()
        CriterionRegistry._registry.update(original)


def test_register_and_get_returns_same_function_object():
    @CriterionRegistry.register("sharpness")
    def sharpness_criterion(
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(0.0)

    assert CriterionRegistry.get("sharpness") is sharpness_criterion


def test_get_raises_for_missing_name():
    with pytest.raises(CriterionError, match=r"not registered"):
        CriterionRegistry.get("does-not-exist")


def test_register_raises_on_duplicate_name():
    @CriterionRegistry.register("dup")
    def criterion_1(  # type: ignore
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(0.0)

    with pytest.raises(CriterionError, match=r"already registered"):

        @CriterionRegistry.register("dup")
        def criterion_2(  # type: ignore
            img: Image, settings: CriterionSettings, log: TextLogger
        ) -> np.floating:
            _ = img, settings, log
            return np.float64(1.0)


def test_register_decorator_returns_function_unchanged():
    def my_criterion(
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(0.0)

    decorated = CriterionRegistry.register("my_criterion")(my_criterion)

    assert decorated is my_criterion
    assert CriterionRegistry.get("my_criterion") is my_criterion


def test_has_reflects_registration_state():
    assert CriterionRegistry.has("bandpass") is False

    @CriterionRegistry.register("bandpass")
    def bandpass_criterion(  # type: ignore
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(0.0)

    assert CriterionRegistry.has("bandpass") is True


def test_allowed_lists_registered_names():
    assert CriterionRegistry.allowed() == []

    @CriterionRegistry.register("a")
    def criterion_a(  # type: ignore
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(0.0)

    @CriterionRegistry.register("b")
    def criterion_b(  # type: ignore
        img: Image, settings: CriterionSettings, log: TextLogger
    ) -> np.floating:
        _ = img, settings, log
        return np.float64(1.0)

    assert CriterionRegistry.allowed() == ["a", "b"]
