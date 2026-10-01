# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from collections.abc import Iterator

import pytest

from fibsem_maestro.logging.logging import (
    logging_context,
    reset_current_logger,
    set_current_logger,
)
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger


class SlicePointer:
    """Mutable slice pointer for tests; callable so it satisfies `Callable[[], int]`."""

    def __init__(self, slice_index: int = 0) -> None:
        self.slice_index = slice_index

    def __call__(self) -> int:
        return self.slice_index


@pytest.fixture(autouse=True)
def clear_context() -> Iterator[None]:
    """The ContextVar is process-wide; pin it to None so tests cannot leak into each other."""
    token = set_current_logger(None)  # ty: ignore[invalid-argument-type]
    yield
    reset_current_logger(token)


@pytest.fixture
def pointer() -> SlicePointer:
    return SlicePointer()


@pytest.fixture
def fallback(pointer: SlicePointer) -> MemoryTextLogger:
    return MemoryTextLogger(pointer, "fallback")


@pytest.fixture
def contextual(fallback: MemoryTextLogger) -> ContextualTextLogger:
    return ContextualTextLogger(fallback)


def flat(logger: MemoryTextLogger) -> list[tuple[int, str, str, str]]:
    """Flatten a record store to (slice, name, level, message), ordered by slice."""
    return [
        (record.slice_index, record.name, record.level, record.message)
        for slice_index in sorted(logger.records)
        for record in logger.records[slice_index]
    ]


def test_delegates_to_the_active_logger(
    contextual: ContextualTextLogger,
    fallback: MemoryTextLogger,
    pointer: SlicePointer,
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.info("x")

    assert flat(active) == [(0, "action", "info", "x")]
    assert flat(fallback) == []


def test_falls_back_when_no_logger_is_active(
    contextual: ContextualTextLogger, fallback: MemoryTextLogger
) -> None:
    contextual.info("x")

    assert flat(fallback) == [(0, "fallback", "info", "x")]


def test_resolves_the_active_logger_per_call(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    """No destination is cached; the ContextVar is read on every call."""
    first = MemoryTextLogger(pointer, "first")
    second = MemoryTextLogger(pointer, "second")

    with logging_context(first):
        contextual.info("a")
    with logging_context(second):
        contextual.info("b")

    assert flat(first) == [(0, "first", "info", "a")]
    assert flat(second) == [(0, "second", "info", "b")]


def test_returns_to_fallback_after_the_context_exits(
    contextual: ContextualTextLogger,
    fallback: MemoryTextLogger,
    pointer: SlicePointer,
) -> None:
    with logging_context(MemoryTextLogger(pointer, "action")):
        contextual.info("inside")
    contextual.info("outside")

    assert flat(fallback) == [(0, "fallback", "info", "outside")]


@pytest.mark.parametrize(
    ("method", "level"),
    [
        ("info", "info"),
        ("warning", "warning"),
        ("error", "error"),
        ("debug", "debug"),
        ("exception", "exception"),
    ],
)
def test_every_level_is_forwarded(
    contextual: ContextualTextLogger,
    pointer: SlicePointer,
    method: str,
    level: str,
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        getattr(contextual, method)("x")

    assert flat(active) == [(0, "action", level, "x")]


def test_nested_contexts_use_the_innermost(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    outer = MemoryTextLogger(pointer, "outer")
    inner = MemoryTextLogger(pointer, "inner")

    with logging_context(outer):
        with logging_context(inner):
            contextual.info("deep")
        contextual.info("shallow")

    assert flat(inner) == [(0, "inner", "info", "deep")]
    assert flat(outer) == [(0, "outer", "info", "shallow")]


def test_derive_appends_to_the_active_name(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.derive("microscope").info("x")

    assert flat(active) == [(0, "action.microscope", "info", "x")]


def test_derive_accumulates(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.derive("microscope").derive("beam").info("x")

    assert flat(active) == [(0, "action.microscope.beam", "info", "x")]


def test_derived_suffix_follows_a_context_switch(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    """The suffix is stored and applied per call, not bound at derive time."""
    derived = contextual.derive("microscope")
    first = MemoryTextLogger(pointer, "first")
    second = MemoryTextLogger(pointer, "second")

    with logging_context(first):
        derived.info("a")
    with logging_context(second):
        derived.info("b")

    assert flat(first) == [(0, "first.microscope", "info", "a")]
    assert flat(second) == [(0, "second.microscope", "info", "b")]


def test_derive_applies_to_the_fallback_too(
    contextual: ContextualTextLogger, fallback: MemoryTextLogger
) -> None:
    contextual.derive("microscope").info("x")

    assert flat(fallback) == [(0, "fallback.microscope", "info", "x")]


def test_derive_returns_a_contextual_logger(
    contextual: ContextualTextLogger,
) -> None:
    assert type(contextual.derive("microscope")) is ContextualTextLogger


def test_derive_does_not_change_the_parent(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    contextual.derive("microscope")
    with logging_context(active):
        contextual.info("x")

    assert flat(active) == [(0, "action", "info", "x")]


def test_records_are_tagged_with_the_current_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.info("zero")
        pointer.slice_index = 1
        contextual.info("one")

    assert flat(active) == [
        (0, "action", "info", "zero"),
        (1, "action", "info", "one"),
    ]


def test_slice_reports_the_active_loggers_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    pointer.slice_index = 9

    with logging_context(MemoryTextLogger(pointer, "action")):
        assert contextual.slice == 9


def test_slice_falls_back_when_no_context_is_active(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    pointer.slice_index = 3

    assert contextual.slice == 3


def test_at_writes_to_the_requested_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.at(7).info("out of band")

    assert flat(active) == [(7, "action", "info", "out of band")]


def test_at_reports_the_requested_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    with logging_context(MemoryTextLogger(pointer, "action")):
        assert contextual.at(7).slice == 7


def test_at_view_stays_bound_after_the_context_exits(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    """Views are pinned at call time, so a correction still reaches its action."""
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        view = contextual.at(7)
    view.info("late")

    assert flat(active) == [(7, "action", "info", "late")]


def test_at_view_is_unaffected_by_a_later_slice_change(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        view = contextual.at(3)
        pointer.slice_index = 9
        view.info("still three")

    assert flat(active) == [(3, "action", "info", "still three")]


def test_at_carries_the_derived_suffix(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.derive("drift").at(3).info("x")

    assert flat(active) == [(3, "action.drift", "info", "x")]


def test_at_uses_the_fallback_when_no_context_is_active(
    contextual: ContextualTextLogger, fallback: MemoryTextLogger
) -> None:
    contextual.at(4).info("x")

    assert flat(fallback) == [(4, "fallback", "info", "x")]


def test_next_writes_to_the_following_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    pointer.slice_index = 4
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.next.info("correction applied")

    assert flat(active) == [(5, "action", "info", "correction applied")]


def test_next_reports_the_following_slice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    pointer.slice_index = 2

    with logging_context(MemoryTextLogger(pointer, "action")):
        assert contextual.next.slice == 3


def test_next_view_stays_bound_after_the_context_exits(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    pointer.slice_index = 1
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        view = contextual.next
    view.info("late")

    assert flat(active) == [(2, "action", "info", "late")]


def test_next_carries_the_derived_suffix(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.derive("drift").next.info("x")

    assert flat(active) == [(1, "action.drift", "info", "x")]


def test_next_of_next_advances_twice(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.next.next.info("x")

    assert flat(active) == [(2, "action", "info", "x")]


def test_close_does_not_close_the_active_logger(
    contextual: ContextualTextLogger, pointer: SlicePointer
) -> None:
    """This logger owns neither destination; closing here would break a live action."""
    active = MemoryTextLogger(pointer, "action")

    with logging_context(active):
        contextual.close()

    assert active.closed is False


def test_close_does_not_close_the_fallback(pointer: SlicePointer) -> None:
    fallback = MemoryTextLogger(pointer, "fallback")

    ContextualTextLogger(fallback).close()

    assert fallback.closed is False


def test_close_does_not_prevent_further_logging(
    contextual: ContextualTextLogger, fallback: MemoryTextLogger
) -> None:
    contextual.close()
    contextual.info("x")

    assert flat(fallback) == [(0, "fallback", "info", "x")]
