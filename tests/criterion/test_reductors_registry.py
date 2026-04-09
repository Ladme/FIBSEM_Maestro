# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


import numpy as np
import pytest

from fibsem_maestro.criterion.error import CriterionError
from fibsem_maestro.criterion.reductors_registry import (
    ReductorsRegistry,
    has_numpy_reduction_signature,
)


def test_has_numpy_reduction_signature_returns_true_for_reduction_function():
    assert has_numpy_reduction_signature(np.mean) is True


def test_has_numpy_reduction_signature_returns_false_for_private_function():
    def _private(a):  # type: ignore
        return a

    assert has_numpy_reduction_signature(_private) is False


def test_has_numpy_reduction_signature_returns_false_for_no_parameter_function():
    def no_params():
        pass

    assert has_numpy_reduction_signature(no_params) is False  # type: ignore


def test_has_numpy_reduction_signature_returns_false_for_non_callable():
    assert has_numpy_reduction_signature(42) is False  # type: ignore


def test_registry_get_returns_correct_numpy_function():
    assert ReductorsRegistry.get("mean") is np.mean


def test_registry_get_raises_criterion_error_for_unknown_name():
    with pytest.raises(CriterionError):
        ReductorsRegistry.get("not_a_real_function")


def test_registry_has_returns_true_for_registered_function():
    assert ReductorsRegistry.has("mean") is True


def test_registry_has_returns_false_for_unknown_name():
    assert ReductorsRegistry.has("not_a_real_function") is False


def test_registry_allowed_returns_sorted_list_containing_common_reductions():
    allowed = ReductorsRegistry.allowed()

    assert allowed == sorted(allowed)
    assert "mean" in allowed
    assert "std" in allowed
    assert "min" in allowed
    assert "max" in allowed


def test_registry_build_excludes_private_numpy_attributes():
    private_names = [
        name for name in ReductorsRegistry.allowed() if name.startswith("_")
    ]

    assert private_names == []
