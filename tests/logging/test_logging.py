# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

import logging
import re
from collections.abc import Iterator
from pathlib import Path

import pytest

from fibsem_maestro.logging.logging import (
    get_current_logger,
    logging_context,
    reset_current_logger,
    set_current_logger,
    with_logging_context,
)
from fibsem_maestro.logging.text.contextual import ContextualTextLogger
from fibsem_maestro.logging.text.file import FileTextLogger, close_all_log_files
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.slice.slice_view import SliceView

LINE = re.compile(r"^\S+ \S+ \[(?P<name>[^\]]*)\] (?P<level>\w+): (?P<message>.*)$")


class SliceCursor:
    """Mutable stand-in for the run loop's slice pointer; `SliceView` is immutable."""

    def __init__(self, action_dir: Path, slice_index: int = 0) -> None:
        self._action_dir = action_dir
        self._view = SliceView(action_dir, slice_index)

    def __call__(self) -> SliceView:
        return self._view

    def advance_to(self, slice_index: int) -> None:
        self._view = SliceView(self._action_dir, slice_index)

    def log_path(self, slice_index: int) -> Path:
        return SliceView(self._action_dir, slice_index).path() / "run.log"


class FakeContext:
    """Minimal stand-in for `ActionContext`; only `text_logger` is read."""

    def __init__(self, text_logger: TextLogger) -> None:
        self.text_logger = text_logger


class Action:
    """
    Stand-in for a pipeline action.
    """

    def __init__(self, ctx: FakeContext, microscope_log: TextLogger) -> None:
        self.ctx = ctx
        self._log = microscope_log

    @with_logging_context
    def execute(self, message: str) -> str:
        self._log.info(message)
        return message

    @with_logging_context
    def fail(self) -> None:
        self._log.info("before failure")
        raise RuntimeError("stage move failed")


@pytest.fixture(autouse=True)
def isolate() -> Iterator[None]:
    token = set_current_logger(None)  # ty: ignore[invalid-argument-type]
    yield
    reset_current_logger(token)
    close_all_log_files()


@pytest.fixture
def fallback_cursor(tmp_path: Path) -> SliceCursor:
    return SliceCursor(tmp_path / "root")


@pytest.fixture
def fallback(fallback_cursor: SliceCursor) -> FileTextLogger:
    return FileTextLogger(fallback_cursor, "app", level=logging.DEBUG)


@pytest.fixture
def microscope_log(fallback: FileTextLogger) -> ContextualTextLogger:
    return ContextualTextLogger(fallback).derive("microscope")


def records(path: Path) -> list[re.Match]:
    lines = path.read_text().splitlines()
    matches = [m for line in lines if (m := LINE.match(line))]
    if len(matches) != len(lines):
        raise ValueError(f"unparsable lines in {path}")
    return matches


def test_set_and_get_round_trip(fallback: FileTextLogger) -> None:
    token = set_current_logger(fallback)
    try:
        assert get_current_logger() is fallback
    finally:
        reset_current_logger(token)


def test_get_returns_none_by_default() -> None:
    assert get_current_logger() is None


def test_reset_restores_the_previous_logger(fallback: FileTextLogger) -> None:
    outer = FileTextLogger(lambda: SliceView(Path("/tmp"), 0), "outer")

    first = set_current_logger(outer)
    second = set_current_logger(fallback)
    reset_current_logger(second)

    assert get_current_logger() is outer
    reset_current_logger(first)


def test_logging_context_activates_and_restores(fallback: FileTextLogger) -> None:
    with logging_context(fallback):
        assert get_current_logger() is fallback

    assert get_current_logger() is None


def test_logging_context_restores_after_an_exception(fallback: FileTextLogger) -> None:
    with pytest.raises(RuntimeError), logging_context(fallback):
        raise RuntimeError("boom")

    assert get_current_logger() is None


def test_records_land_in_the_active_actions_file(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(
        FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )

    action.execute("beam current set")
    close_all_log_files()

    assert [r["message"] for r in records(cursor.log_path(0))] == ["beam current set"]


def test_record_name_combines_action_and_suffix(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(
        FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )

    action.execute("x")
    close_all_log_files()

    assert records(cursor.log_path(0))[0]["name"] == "milling.microscope"


def test_two_actions_write_to_their_own_files(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    """One shared `Microscope` logger, two destinations, chosen by context."""
    first_cursor = SliceCursor(tmp_path / "milling")
    second_cursor = SliceCursor(tmp_path / "imaging")
    first = Action(
        FakeContext(FileTextLogger(first_cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )
    second = Action(
        FakeContext(FileTextLogger(second_cursor, "imaging", level=logging.DEBUG)),
        microscope_log,
    )

    first.execute("milling message")
    second.execute("imaging message")
    close_all_log_files()

    assert [r["message"] for r in records(first_cursor.log_path(0))] == [
        "milling message"
    ]
    assert [r["message"] for r in records(second_cursor.log_path(0))] == [
        "imaging message"
    ]


def test_records_outside_any_action_go_to_the_fallback(
    fallback_cursor: SliceCursor, microscope_log: ContextualTextLogger
) -> None:
    microscope_log.info("idle")
    close_all_log_files()

    assert [r["message"] for r in records(fallback_cursor.log_path(0))] == ["idle"]


def test_context_is_restored_after_the_action_returns(
    tmp_path: Path,
    fallback_cursor: SliceCursor,
    microscope_log: ContextualTextLogger,
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(
        FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )

    action.execute("during")
    microscope_log.info("after")
    close_all_log_files()

    assert [r["message"] for r in records(cursor.log_path(0))] == ["during"]
    assert [r["message"] for r in records(fallback_cursor.log_path(0))] == ["after"]


def test_context_is_restored_when_the_action_raises(
    tmp_path: Path,
    fallback_cursor: SliceCursor,
    microscope_log: ContextualTextLogger,
) -> None:
    """A failed action must not leave its logger installed for the rest of the run."""
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(
        FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )

    with pytest.raises(RuntimeError):
        action.fail()
    microscope_log.info("recovered")
    close_all_log_files()

    assert [r["message"] for r in records(cursor.log_path(0))] == ["before failure"]
    assert [r["message"] for r in records(fallback_cursor.log_path(0))] == ["recovered"]


def test_nested_actions_restore_the_outer_context(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    outer_cursor = SliceCursor(tmp_path / "outer")
    inner_cursor = SliceCursor(tmp_path / "inner")
    inner = Action(
        FakeContext(FileTextLogger(inner_cursor, "inner", level=logging.DEBUG)),
        microscope_log,
    )

    class Outer(Action):
        @with_logging_context
        def execute(self, message: str) -> str:
            self._log.info("outer before")
            inner.execute("inner message")
            self._log.info("outer after")
            return message

    Outer(
        FakeContext(FileTextLogger(outer_cursor, "outer", level=logging.DEBUG)),
        microscope_log,
    ).execute("x")
    close_all_log_files()

    assert [r["message"] for r in records(outer_cursor.log_path(0))] == [
        "outer before",
        "outer after",
    ]
    assert [r["message"] for r in records(inner_cursor.log_path(0))] == [
        "inner message"
    ]


def test_decorator_preserves_the_return_value(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(FakeContext(FileTextLogger(cursor, "milling")), microscope_log)

    assert action.execute("payload") == "payload"


def test_decorator_preserves_the_method_name(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(FakeContext(FileTextLogger(cursor, "milling")), microscope_log)

    assert action.execute.__name__ == "execute"


def test_action_follows_its_own_slice(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    action = Action(
        FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG)),
        microscope_log,
    )

    action.execute("slice zero")
    cursor.advance_to(1)
    action.execute("slice one")
    close_all_log_files()

    assert [r["message"] for r in records(cursor.log_path(0))] == ["slice zero"]
    assert [r["message"] for r in records(cursor.log_path(1))] == ["slice one"]


def test_next_from_inside_an_action_targets_the_actions_next_slice(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    ctx = FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG))

    class Corrector(Action):
        @with_logging_context
        def execute(self, message: str) -> str:
            self._log.next.info(message)
            return message

    Corrector(ctx, microscope_log).execute("wd correction applied")
    close_all_log_files()

    assert [r["message"] for r in records(cursor.log_path(1))] == [
        "wd correction applied"
    ]


def test_slice_from_inside_an_action_reports_the_actions_slice(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling", slice_index=3)
    ctx = FakeContext(FileTextLogger(cursor, "milling"))
    seen: list[int] = []

    class Reader(Action):
        @with_logging_context
        def execute(self, message: str) -> str:
            seen.append(self._log.slice)
            return message

    Reader(ctx, microscope_log).execute("x")

    assert seen == [3]


def test_exception_from_inside_an_action_reaches_the_actions_file(
    tmp_path: Path, microscope_log: ContextualTextLogger
) -> None:
    cursor = SliceCursor(tmp_path / "milling")
    ctx = FakeContext(FileTextLogger(cursor, "milling", level=logging.DEBUG))

    class Failing(Action):
        @with_logging_context
        def execute(self, message: str) -> str:
            try:
                raise ValueError("beam shift limit reached")
            except ValueError:
                self._log.exception(message)
            return message

    Failing(ctx, microscope_log).execute("could not correct drift")
    close_all_log_files()

    contents = cursor.log_path(0).read_text()
    assert "could not correct drift" in contents
    assert "ValueError: beam shift limit reached" in contents
