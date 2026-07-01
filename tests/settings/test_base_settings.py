# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from pathlib import Path
from typing import Any, ClassVar, Self

from fibsem_maestro.serializer.serializer import Serializer
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.reactive import ReactiveNode


class FakeSerializer(Serializer):
    """
    A simple in-memory serializer.

    It behaves like a real Serializer but stores data in a class-level dict
    instead of using the filesystem.
    """

    _storage: ClassVar[dict[Path, dict[str, Any]]] = {}

    @classmethod
    def load(cls, file: Path) -> dict[str, Any]:
        return dict(cls._storage[file])

    @classmethod
    def write(cls, file: Path, data: dict[str, Any]) -> None:
        cls._storage[file] = dict(data)


class Node(BaseSettings):
    x: int = 0
    y: int = 0
    child: Self | None = None


class HookCounter:
    count: int
    calls: list[ReactiveNode]

    def __init__(self) -> None:
        self.count = 0
        self.calls = []

    def hook(self, root: ReactiveNode) -> None:
        self.count += 1
        self.calls.append(root)


def test_from_file_loads_using_serializer():
    file = Path("config.yaml")

    FakeSerializer._storage.clear()
    FakeSerializer._storage[file] = {"x": 10, "y": 20}

    s = Node.from_file(file, FakeSerializer)

    assert s.x == 10
    assert s.y == 20
    assert isinstance(s, Node)


def test_from_file_creates_nested_reactive_children():
    file = Path("nested.yaml")

    FakeSerializer._storage.clear()
    FakeSerializer._storage[file] = {
        "x": 1,
        "y": 2,
        "child": {"x": 5, "y": 9},
    }

    s = Node.from_file(file, FakeSerializer)

    assert isinstance(s.child, Node)
    assert s.child.x == 5
    assert s.child._parent is s


def test_to_file_writes_using_serializer():
    file = Path("output.yaml")
    FakeSerializer._storage.clear()

    s = Node(x=7, y=9)

    s.to_file(file, FakeSerializer)

    assert file in FakeSerializer._storage
    assert FakeSerializer._storage[file] == {"x": 7, "y": 9}


def test_reload_overwrites_fields_and_triggers_hooks_once():
    file = Path("reload.yaml")

    FakeSerializer._storage.clear()
    FakeSerializer._storage[file] = {"x": 99, "y": 100}

    s = Node(x=1, y=2)

    counter = HookCounter()
    s.on_change(counter.hook)

    s.reload(file, FakeSerializer)

    assert s.x == 99
    assert s.y == 100
    assert counter.count == 1


def test_reload_replaces_nested_children_and_propagates_parent():
    file = Path("nested_reload.yaml")

    FakeSerializer._storage.clear()
    FakeSerializer._storage[file] = {
        "x": 100,
        "y": 200,
        "child": {"x": 300, "y": 400},
    }

    s = Node(x=1, y=2, child=Node(x=3, y=4))

    counter = HookCounter()
    s.on_change(counter.hook)

    s.reload(file, FakeSerializer)

    assert s.x == 100
    assert s.y == 200
    assert s.child is not None
    assert s.child.x == 300
    assert s.child.y == 400
    assert s.child._parent is s
    assert counter.count == 1


def test_from_file_to_file_roundtrip():
    file_in = Path("in.yaml")
    file_out = Path("out.yaml")

    FakeSerializer._storage.clear()

    FakeSerializer._storage[file_in] = {
        "x": 5,
        "y": 6,
        "child": {"x": 7, "y": 8},
    }

    s = Node.from_file(file_in, FakeSerializer)

    s.to_file(file_out, FakeSerializer)

    assert FakeSerializer._storage[file_out] == {
        "x": 5,
        "y": 6,
        "child": {"x": 7, "y": 8},
    }
