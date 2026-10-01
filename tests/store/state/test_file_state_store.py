# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from pathlib import Path
from typing import Any, cast

import pytest
import yaml
from pydantic import Field, ValidationError

from fibsem_maestro.action.state import ActionState
from fibsem_maestro.slice.slice_view import SliceView
from fibsem_maestro.store.state.file import FileStateStore


class SampleState(ActionState):
    """Stand-in for an action's state."""

    base_value: Any | None = None
    in_progress: bool = False
    current_step_index: int = 0
    collected: list[float] = Field(default_factory=list)


class StrictOtherState(ActionState):
    """A different state model, to check `read` honours the requested class."""

    model_config = {"extra": "forbid"}

    passes: int = 1


class SliceCursor:
    """Mutable stand-in for the run loop's slice pointer; `SliceView` is immutable."""

    def __init__(self, action_dir: Path, slice_index: int = 0) -> None:
        self._action_dir = action_dir
        self._view = SliceView(action_dir, slice_index)

    def __call__(self) -> SliceView:
        return self._view

    def advance_to(self, slice_index: int) -> None:
        self._view = SliceView(self._action_dir, slice_index)

    def dir(self, slice_index: int) -> Path:
        return SliceView(self._action_dir, slice_index).expected_path

    @property
    def action_dir(self) -> Path:
        return self._action_dir


@pytest.fixture
def cursor(tmp_path: Path) -> SliceCursor:
    return SliceCursor(tmp_path)


@pytest.fixture
def store(cursor: SliceCursor) -> FileStateStore:
    return FileStateStore(cursor)


@pytest.fixture
def state() -> SampleState:
    return SampleState(
        base_value=4.123456789e-3,
        in_progress=True,
        current_step_index=7,
        collected=[0.1, 0.5, 0.8],
    )


def test_write_creates_the_file(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert (cursor.dir(0) / "state.yaml").is_file()


def test_write_creates_the_slice_directory(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    assert not cursor.dir(0).exists()

    store.write("state.yaml", state)

    assert cursor.dir(0).is_dir()


def test_write_emits_plain_yaml_scalars(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)

    contents = (cursor.dir(0) / "state.yaml").read_text()
    assert "!!python" not in contents


def test_write_output_is_safe_loadable(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)

    data = yaml.safe_load((cursor.dir(0) / "state.yaml").read_text())

    assert data["current_step_index"] == 7


def test_write_overwrites_an_existing_file(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)
    store.write("state.yaml", SampleState(current_step_index=999))

    assert (
        cast("SampleState", store.read("state.yaml", SampleState)).current_step_index
        == 999
    )


def test_write_does_not_merge_with_the_previous_contents(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)
    store.write("state.yaml", SampleState())

    loaded = cast("SampleState", store.read("state.yaml", SampleState))
    assert loaded.base_value is None
    assert loaded.collected == []
    assert loaded.in_progress is False


def test_write_follows_the_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    cursor.advance_to(1)
    store.write("state.yaml", SampleState(current_step_index=999))

    assert (
        cast(
            "SampleState", store.at(0).read("state.yaml", SampleState)
        ).current_step_index
        == 7
    )
    assert (
        cast(
            "SampleState", store.at(1).read("state.yaml", SampleState)
        ).current_step_index
        == 999
    )


def test_distinct_filenames_stay_apart(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("before.yaml", state)
    store.write("after.yaml", SampleState(current_step_index=999))

    assert (
        cast("SampleState", store.read("before.yaml", SampleState)).current_step_index
        == 7
    )
    assert (
        cast("SampleState", store.read("after.yaml", SampleState)).current_step_index
        == 999
    )


def test_round_trip_preserves_every_field(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert store.read("state.yaml", SampleState) == state


def test_round_trip_preserves_a_float_base_value(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    loaded = cast("SampleState", store.read("state.yaml", SampleState))
    assert loaded.base_value == pytest.approx(4.123456789e-3)
    assert isinstance(loaded.base_value, float)


def test_round_trip_preserves_an_integer_base_value(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(base_value=7))

    loaded = cast("SampleState", store.read("state.yaml", SampleState))
    assert loaded.base_value == 7
    assert isinstance(loaded.base_value, int)


def test_round_trip_preserves_an_unset_base_value(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(base_value=None))

    assert cast("SampleState", store.read("state.yaml", SampleState)).base_value is None


def test_round_trip_preserves_a_zero_base_value(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(base_value=0.0))

    loaded = cast("SampleState", store.read("state.yaml", SampleState))
    assert loaded.base_value == 0.0
    assert loaded.base_value is not None


def test_round_trip_preserves_a_negative_base_value(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(base_value=-1.5e-6))

    assert cast(
        "SampleState", store.read("state.yaml", SampleState)
    ).base_value == pytest.approx(-1.5e-6)


def test_round_trip_preserves_a_boolean_flag(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert (
        cast("SampleState", store.read("state.yaml", SampleState)).in_progress is True
    )


def test_round_trip_preserves_a_false_flag(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(in_progress=False))

    assert (
        cast("SampleState", store.read("state.yaml", SampleState)).in_progress is False
    )


def test_round_trip_preserves_integer_type(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert isinstance(
        cast("SampleState", store.read("state.yaml", SampleState)).current_step_index,
        int,
    )


def test_round_trip_preserves_a_list_field(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert cast("SampleState", store.read("state.yaml", SampleState)).collected == [
        0.1,
        0.5,
        0.8,
    ]


def test_round_trip_preserves_list_order(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(collected=[3.0, 1.0, 2.0]))

    assert cast("SampleState", store.read("state.yaml", SampleState)).collected == [
        3.0,
        1.0,
        2.0,
    ]


def test_round_trip_preserves_an_empty_list(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(collected=[]))

    assert cast("SampleState", store.read("state.yaml", SampleState)).collected == []


def test_round_trip_preserves_float_precision(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState(collected=[0.123456789]))

    loaded = store.read("state.yaml", SampleState)

    assert cast("SampleState", loaded).collected[0] == pytest.approx(0.123456789)


def test_round_trip_of_defaults(store: FileStateStore) -> None:
    store.write("state.yaml", SampleState())

    assert store.read("state.yaml", SampleState) == SampleState()


def test_states_do_not_share_their_default_list(store: FileStateStore) -> None:
    first = SampleState()
    first.collected.append(1.0)

    store.write("state.yaml", SampleState())

    assert cast("SampleState", store.read("state.yaml", SampleState)).collected == []


def test_read_uses_the_requested_class(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert type(store.read("state.yaml", SampleState)) is SampleState


def test_read_with_a_mismatched_class_raises(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    with pytest.raises(ValidationError):
        store.read("state.yaml", StrictOtherState)


def test_read_raises_when_the_file_is_missing(store: FileStateStore) -> None:
    with pytest.raises(FileNotFoundError, match="No state file found"):
        store.read("state.yaml", SampleState)


def test_read_error_names_the_expected_path(store: FileStateStore) -> None:
    with pytest.raises(FileNotFoundError, match="state.yaml"):
        store.read("state.yaml", SampleState)


def test_read_is_per_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    cursor.advance_to(1)

    with pytest.raises(FileNotFoundError):
        store.read("state.yaml", SampleState)


def test_read_does_not_create_the_slice_directory(
    store: FileStateStore, cursor: SliceCursor
) -> None:
    with pytest.raises(FileNotFoundError):
        store.read("state.yaml", SampleState)

    assert not cursor.dir(0).exists()


def test_read_does_not_consume_the_file(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.read("state.yaml", SampleState)

    assert store.exists("state.yaml") is True


def test_read_closes_the_file(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    """Windows blocks deletion while a handle is open."""
    store.write("state.yaml", state)

    store.read("state.yaml", SampleState)
    (cursor.dir(0) / "state.yaml").unlink()

    assert store.exists("state.yaml") is False


def test_read_can_be_repeated(store: FileStateStore, state: SampleState) -> None:
    store.write("state.yaml", state)

    assert store.read("state.yaml", SampleState) == store.read(
        "state.yaml", SampleState
    )


def test_read_returns_independent_instances(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    first = cast("SampleState", store.read("state.yaml", SampleState))
    second = cast("SampleState", store.read("state.yaml", SampleState))
    first.collected.append(9.9)

    assert second.collected == [0.1, 0.5, 0.8]


def test_read_rejects_a_malformed_file(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    (cursor.dir(0) / "state.yaml").write_text("collected: [unclosed\n")

    with pytest.raises(yaml.YAMLError):
        store.read("state.yaml", SampleState)


def test_read_rejects_a_file_with_a_wrong_field_type(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    (cursor.dir(0) / "state.yaml").write_text("current_step_index: not a number\n")

    with pytest.raises(ValidationError):
        store.read("state.yaml", SampleState)


def test_read_fills_missing_fields_from_defaults(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    (cursor.dir(0) / "state.yaml").write_text("current_step_index: 4\n")

    loaded = cast("SampleState", store.read("state.yaml", SampleState))

    assert loaded.current_step_index == 4
    assert loaded.collected == []


def test_exists_is_false_before_writing(store: FileStateStore) -> None:
    assert store.exists("state.yaml") is False


def test_exists_is_true_after_writing(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert store.exists("state.yaml") is True


def test_exists_does_not_create_the_slice_directory(
    store: FileStateStore, cursor: SliceCursor
) -> None:
    store.exists("state.yaml")

    assert not cursor.dir(0).exists()


def test_exists_is_per_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    cursor.advance_to(1)

    assert store.exists("state.yaml") is False


def test_exists_is_per_filename(store: FileStateStore, state: SampleState) -> None:
    store.write("state.yaml", state)

    assert store.exists("other.yaml") is False


def test_copy_to_places_the_file_in_the_target_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.copy_to("state.yaml", store.at(3))

    assert (cursor.dir(3) / "state.yaml").is_file()


def test_copy_to_preserves_the_contents(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.copy_to("state.yaml", store.at(3))

    assert store.at(3).read("state.yaml", SampleState) == state


def test_copy_to_leaves_the_source_in_place(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.copy_to("state.yaml", store.at(3))

    assert store.exists("state.yaml") is True


def test_copy_to_creates_the_target_slice_directory(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.write("state.yaml", state)
    assert not cursor.dir(3).exists()

    store.copy_to("state.yaml", store.at(3))

    assert cursor.dir(3).is_dir()


def test_copy_to_overwrites_an_existing_target(
    store: FileStateStore, state: SampleState
) -> None:
    target = store.at(3)
    target.write("state.yaml", SampleState(current_step_index=999))
    store.write("state.yaml", state)

    store.copy_to("state.yaml", target)

    assert target.read("state.yaml", SampleState) == state


def test_copy_to_raises_when_the_source_is_missing(store: FileStateStore) -> None:
    with pytest.raises(FileNotFoundError, match="No state file found"):
        store.copy_to("state.yaml", store.at(3))


def test_copy_to_does_not_create_the_target_when_the_source_is_missing(
    store: FileStateStore, cursor: SliceCursor
) -> None:
    with pytest.raises(FileNotFoundError):
        store.copy_to("state.yaml", store.at(3))

    assert not cursor.dir(3).exists()


def test_copy_to_the_same_slice_is_a_no_op(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.copy_to("state.yaml", store)

    assert store.read("state.yaml", SampleState) == state


def test_copy_to_an_equivalent_view_is_a_no_op(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    store.copy_to("state.yaml", store.at(0))

    assert store.read("state.yaml", SampleState) == state


def test_copy_to_a_store_in_another_action(
    store: FileStateStore, tmp_path: Path, state: SampleState
) -> None:
    other = FileStateStore(SliceCursor(tmp_path / "other"))
    store.write("state.yaml", state)

    store.copy_to("state.yaml", other)

    assert other.read("state.yaml", SampleState) == state


def test_copy_to_is_independent_of_the_source_afterwards(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)
    target = store.at(3)
    store.copy_to("state.yaml", target)

    store.write("state.yaml", SampleState(current_step_index=999))

    assert (
        cast("SampleState", target.read("state.yaml", SampleState)).current_step_index
        == 7
    )


def test_slice_reports_the_current_index(
    store: FileStateStore, cursor: SliceCursor
) -> None:
    assert store.slice == 0

    cursor.advance_to(7)

    assert store.slice == 7


def test_at_addresses_the_requested_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.at(5).write("state.yaml", state)

    assert (cursor.dir(5) / "state.yaml").is_file()


def test_at_reports_the_requested_slice(store: FileStateStore) -> None:
    assert store.at(5).slice == 5


def test_at_does_not_move_the_original_store(
    store: FileStateStore, state: SampleState
) -> None:
    store.at(5).write("state.yaml", state)

    assert store.slice == 0
    assert store.exists("state.yaml") is False


def test_at_is_pinned_when_the_run_advances(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    pinned = store.at(3)

    cursor.advance_to(9)
    pinned.write("state.yaml", state)

    assert (cursor.dir(3) / "state.yaml").is_file()


def test_at_reads_back_what_it_wrote(store: FileStateStore, state: SampleState) -> None:
    store.at(5).write("state.yaml", state)

    assert store.at(5).read("state.yaml", SampleState) == state


def test_at_rejects_a_negative_slice(store: FileStateStore) -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        store.at(-1)


def test_at_accepts_the_current_slice(
    store: FileStateStore, state: SampleState
) -> None:
    store.write("state.yaml", state)

    assert store.at(0).exists("state.yaml") is True


def test_next_addresses_the_following_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.next.write("state.yaml", state)

    assert (cursor.dir(1) / "state.yaml").is_file()


def test_next_is_relative_to_the_current_slice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    cursor.advance_to(4)

    store.next.write("state.yaml", state)

    assert (cursor.dir(5) / "state.yaml").is_file()


def test_next_reports_the_following_slice(
    store: FileStateStore, cursor: SliceCursor
) -> None:
    cursor.advance_to(2)

    assert store.next.slice == 3


def test_next_is_pinned_at_access_time(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    view = store.next

    cursor.advance_to(9)
    view.write("state.yaml", state)

    assert (cursor.dir(1) / "state.yaml").is_file()


def test_next_of_next_advances_twice(
    store: FileStateStore, cursor: SliceCursor, state: SampleState
) -> None:
    store.next.next.write("state.yaml", state)

    assert (cursor.dir(2) / "state.yaml").is_file()
