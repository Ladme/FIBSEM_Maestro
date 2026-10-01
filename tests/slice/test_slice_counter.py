# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


import threading

import pytest

from fibsem_maestro.slice.slice_counter import SliceCounter


@pytest.fixture
def counter() -> SliceCounter:
    return SliceCounter()


def test_starts_at_zero_by_default(counter: SliceCounter) -> None:
    assert counter.current == 0


def test_accepts_a_custom_initial_value() -> None:
    assert SliceCounter(initial=41).current == 41


def test_first_advance_yields_one(counter: SliceCounter) -> None:
    assert counter.advance() == 1


def test_advance_returns_the_new_value(counter: SliceCounter) -> None:
    assert [counter.advance() for _ in range(3)] == [1, 2, 3]


def test_advance_updates_current(counter: SliceCounter) -> None:
    counter.advance()
    counter.advance()

    assert counter.current == 2


def test_current_does_not_advance(counter: SliceCounter) -> None:
    counter.current
    counter.current

    assert counter.current == 0


def test_advance_continues_from_a_custom_initial_value() -> None:
    assert SliceCounter(initial=10).advance() == 11


def test_instances_are_independent() -> None:
    """Each action owns its own counter; one advancing must not move another."""
    first = SliceCounter()
    second = SliceCounter()

    first.advance()
    first.advance()

    assert first.current == 2
    assert second.current == 0


def test_concurrent_advances_hand_out_distinct_indices() -> None:
    """Two slices sharing an index would overwrite each other's directory."""
    counter = SliceCounter()
    per_thread = 200
    threads_count = 8
    seen: list[list[int]] = [[] for _ in range(threads_count)]

    def work(index: int) -> None:
        for _ in range(per_thread):
            seen[index].append(counter.advance())

    threads = [threading.Thread(target=work, args=(i,)) for i in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    handed_out = [value for values in seen for value in values]
    assert sorted(handed_out) == list(range(1, threads_count * per_thread + 1))


def test_concurrent_advances_leave_the_expected_final_value() -> None:
    counter = SliceCounter()
    per_thread = 200
    threads_count = 8

    def work() -> None:
        for _ in range(per_thread):
            counter.advance()

    threads = [threading.Thread(target=work) for _ in range(threads_count)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert counter.current == threads_count * per_thread


def test_each_thread_sees_a_monotonic_sequence() -> None:
    counter = SliceCounter()
    results: list[int] = []
    lock = threading.Lock()

    def work() -> None:
        local = [counter.advance() for _ in range(100)]
        with lock:
            results.extend(local)
        assert local == sorted(local)

    threads = [threading.Thread(target=work) for _ in range(4)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(set(results)) == len(results)


def test_negative_initial_value_is_rejected() -> None:
    with pytest.raises(ValueError, match="must not be negative"):
        SliceCounter(initial=-1)


def test_rejection_names_the_offending_value() -> None:
    with pytest.raises(ValueError, match="got -5"):
        SliceCounter(initial=-5)


def test_zero_initial_value_is_accepted() -> None:
    assert SliceCounter(initial=0).current == 0
