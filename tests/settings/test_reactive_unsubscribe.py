# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from fibsem_maestro.settings.reactive import ChangePath, ReactiveModel


class _Child(ReactiveModel):
    value: int = 0


class _Parent(ReactiveModel):
    child: _Child = _Child()
    number: int = 0


def test_on_change_unsubscribe_removes_hook() -> None:
    model = _Parent()
    calls: list[object] = []
    unsubscribe = model.on_change(calls.append)
    model.number = 1
    unsubscribe()
    model.number = 2
    assert len(calls) == 1


def test_on_change_at_unsubscribe_removes_hook_on_nested_change() -> None:
    model = _Parent()
    paths: list[ChangePath] = []
    unsubscribe = model.on_change_at(paths.append)
    model.child.value = 1
    unsubscribe()
    model.child.value = 2
    assert paths == [("child", "value")]


def test_unsubscribe_is_idempotent_and_removes_one_registration() -> None:
    model = _Parent()
    calls: list[ChangePath] = []
    first = model.on_change_at(calls.append)
    model.on_change_at(calls.append)
    first()
    first()
    model.number = 1
    assert len(calls) == 1


def test_unsubscribe_inside_hook_does_not_skip_next_hook() -> None:
    model = _Parent()
    calls: list[str] = []

    def once(_path: ChangePath) -> None:
        calls.append("once")
        unsubscribe()

    unsubscribe = model.on_change_at(once)
    model.on_change_at(lambda _path: calls.append("second"))
    model.number = 1
    model.number = 2
    assert calls == ["once", "second", "second"]
