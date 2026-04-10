# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import pytest

from fibsem_maestro.autofocus.autofocus import AutofocusMode
from fibsem_maestro.autofocus.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
from fibsem_maestro.autofocus.error import AutofunctionError
from fibsem_maestro.autofocus.jobs_manager import JobsManager


@pytest.fixture(autouse=True)
def isolate_registry():
    """Ensure AutofocusRegistry is clean for each test."""
    original = dict(AutofocusRegistry._registry)
    AutofocusRegistry._registry.clear()
    try:
        yield
    finally:
        AutofocusRegistry._registry.clear()
        AutofocusRegistry._registry.update(original)


def test_register_and_get_returns_same_class():
    @AutofocusRegistry.register("basic")
    class BasicAutofocus(AutofocusMode):
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    assert AutofocusRegistry.get("basic") is BasicAutofocus


def test_get_raises_for_unknown_name():
    with pytest.raises(AutofunctionError, match="not registered"):
        AutofocusRegistry.get("does-not-exist")


def test_register_raises_on_duplicate_name():
    @AutofocusRegistry.register("dup")
    class Autofocus1(AutofocusMode):  # type: ignore
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    with pytest.raises(AutofunctionError, match="already registered"):

        @AutofocusRegistry.register("dup")
        class Autofocus2(AutofocusMode):  # type: ignore
            def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
                _ = ctx, jobs
                yield


def test_register_decorator_returns_class_unchanged():
    class MyAutofocus(AutofocusMode):
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    decorated = AutofocusRegistry.register("my")(MyAutofocus)

    assert decorated is MyAutofocus
    assert AutofocusRegistry.get("my") is MyAutofocus


def test_has_returns_false_before_registration():
    assert AutofocusRegistry.has("mode") is False


def test_has_returns_true_after_registration():
    @AutofocusRegistry.register("mode")
    class SomeAutofocus(AutofocusMode):  # type: ignore
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    assert AutofocusRegistry.has("mode") is True


def test_allowed_returns_empty_list_when_registry_is_empty():
    assert AutofocusRegistry.allowed() == []


def test_allowed_lists_all_registered_names():
    @AutofocusRegistry.register("a")
    class AutofocusA(AutofocusMode):  # type: ignore
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    @AutofocusRegistry.register("b")
    class AutofocusB(AutofocusMode):  # type: ignore
        def execute(self, ctx: AutofunctionContext, jobs: JobsManager):
            _ = ctx, jobs
            yield

    assert AutofocusRegistry.allowed() == ["a", "b"]
