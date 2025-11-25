# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Self

from fibsem_maestro.settings.reactive import Reactive, propagate_root


class Node(Reactive):
    value: int = 0
    child: Self | None = None
    children_list: list["Node"] = []
    children_dict: dict[str, "Node"] = {}


class HookCounter:
    count: int
    calls: list[Reactive]

    def __init__(self) -> None:
        self.count = 0
        self.calls = []

    def hook(self, root: Reactive) -> None:
        self.count += 1
        self.calls.append(root)


def test_root_is_self_initially():
    n = Node()
    assert n._root is n


def test_direct_child_inherits_root():
    parent = Node(child=Node())
    assert parent.child is not None
    assert parent.child._root is parent


def test_children_list_inherit_root():
    parent = Node(children_list=[Node(), Node(value=5)])
    assert all(c._root is parent for c in parent.children_list)


def test_children_dict_inherit_root():
    parent = Node(children_dict={"a": Node(), "b": Node(value=3)})
    assert all(c._root is parent for c in parent.children_dict.values())


def test_deep_mixed_structure_inherits_root():
    node = Node(child=Node(children_list=[Node(children_dict={"z": Node()})]))
    root = node

    assert node.child is not None
    assert node.child._root is root
    assert node.child.children_list[0]._root is root
    assert node.child.children_list[0].children_dict["z"]._root is root


def test_on_change_registers_hook_on_root():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)
    assert counter.hook in n._hooks


def test_on_change_registers_on_root_even_when_called_on_child():
    parent = Node(child=Node())
    counter = HookCounter()
    assert parent.child is not None
    parent.child.on_change(counter.hook)
    assert counter.hook in parent._hooks


def test_setattr_triggers_hooks():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)

    n.value = 10
    assert counter.count == 1


def test_setattr_does_not_trigger_on_private_attrs():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)

    n._root = n
    assert counter.count == 0


def test_setattr_propagates_root_into_new_child():
    parent = Node()
    new_child = Node()

    parent.child = new_child
    assert new_child._root is parent


def test_setattr_propagates_root_into_new_list_children():
    parent = Node()
    c1, c2 = Node(), Node()

    parent.children_list = [c1, c2]
    assert c1._root is parent
    assert c2._root is parent


def test_setattr_propagates_root_into_new_dict_children():
    parent = Node()
    c1 = Node()
    parent.children_dict = {"x": c1}
    assert c1._root is parent


def test_nested_child_change_triggers_root_hooks_once():
    parent = Node(child=Node(children_list=[Node(), Node()]))

    counter = HookCounter()
    parent.on_change(counter.hook)

    assert parent.child is not None
    parent.child.children_list[0].value = 777
    assert counter.count == 1


def test_update_copies_fields_and_calls_hooks_once():
    a = Node(value=1)
    b = Node(value=99)

    counter = HookCounter()
    a.on_change(counter.hook)

    a.update(b)
    assert a.value == 99
    assert counter.count == 1


def test_update_replaces_children_and_repropagates_root():
    a = Node(
        value=1,
        child=Node(value=2),
        children_list=[Node(value=3)],
        children_dict={"x": Node(value=4)},
    )

    b = Node(
        value=99,
        child=Node(value=77),
        children_list=[Node(value=88), Node(value=89)],
        children_dict={"q": Node(value=111)},
    )

    a.update(b)

    assert a.child is not None
    assert a.child._root is a
    assert all(c._root is a for c in a.children_list)
    assert all(c._root is a for c in a.children_dict.values())


def test_call_hooks_invokes_all_callbacks():
    n = Node()
    c1, c2 = HookCounter(), HookCounter()

    n.on_change(c1.hook)
    n.on_change(c2.hook)

    n._call_hooks()

    assert c1.count == 1
    assert c2.count == 1


def test_propagate_root_to_reactive():
    root = Node()
    child = Node()
    propagate_root(root, child)
    assert child._root is root


def test_propagate_root_into_list():
    root = Node()
    lst = [Node(), Node()]
    propagate_root(root, lst)
    assert all(c._root is root for c in lst)


def test_propagate_root_into_dict():
    root = Node()
    d = {"a": Node(), "b": Node()}
    propagate_root(root, d)
    assert all(c._root is root for c in d.values())
