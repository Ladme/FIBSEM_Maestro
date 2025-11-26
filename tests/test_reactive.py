# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Self

from fibsem_maestro.settings.reactive import Reactive, propagate_parent


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


def test_parent_is_none_initially():
    n = Node()
    assert n._parent is None


def test_direct_child_inherits_parent():
    parent = Node(child=Node())
    assert parent.child is not None
    assert parent.child._parent is parent


def test_children_list_inherit_parent():
    parent = Node(children_list=[Node(), Node(value=5)])
    assert all(c._parent is parent for c in parent.children_list)


def test_children_dict_inherit_parent():
    parent = Node(children_dict={"a": Node(), "b": Node(value=3)})
    assert all(c._parent is parent for c in parent.children_dict.values())


def test_deep_mixed_structure_inherits_parent():
    node = Node(child=Node(children_list=[Node(children_dict={"z": Node()})]))

    assert node.child is not None
    assert node.child._parent is node
    assert node.child.children_list[0]._parent is node.child
    assert (
        node.child.children_list[0].children_dict["z"]._parent
        is node.child.children_list[0]
    )


def test_on_change_registers_hook_on_self():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)
    assert counter.hook in n._hooks


def test_on_change_registering_on_child_stores_on_child_only():
    parent = Node(child=Node())
    assert parent.child is not None

    counter = HookCounter()
    parent.child.on_change(counter.hook)

    assert counter.hook in parent.child._hooks
    assert counter.hook not in parent._hooks


def test_setattr_triggers_hooks_on_self():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)

    n.value = 10
    assert counter.count == 1


def test_setattr_does_not_trigger_on_private_attrs():
    n = Node()
    counter = HookCounter()
    n.on_change(counter.hook)

    n._parent = None
    assert counter.count == 0


def test_setattr_propagates_parent_into_new_child():
    parent = Node()
    new_child = Node()

    parent.child = new_child
    assert new_child._parent is parent


def test_setattr_propagates_parent_into_new_list_children():
    parent = Node()
    c1, c2 = Node(), Node()

    parent.children_list = [c1, c2]
    assert c1._parent is parent
    assert c2._parent is parent


def test_setattr_propagates_parent_into_new_dict_children():
    parent = Node()
    c1 = Node()

    parent.children_dict = {"x": c1}
    assert c1._parent is parent


def test_nested_child_change_triggers_ancestor_hooks_once():
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


def test_update_replaces_children_and_repropagates_parent():
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
    assert a.child._parent is a
    assert all(c._parent is a.child for c in a.children_list) is False
    assert all(c._parent is a for c in a.children_list)
    assert all(c._parent is a for c in a.children_dict.values())


def test_call_hooks_invokes_all_callbacks_on_self():
    n = Node()
    c1, c2 = HookCounter(), HookCounter()

    n.on_change(c1.hook)
    n.on_change(c2.hook)

    n._call_hooks()

    assert c1.count == 1
    assert c2.count == 1


def test_call_hooks_invokes_all_callbacks_on_self_and_ancestors():
    root = Node()
    parent = Node(child=Node())
    assert parent.child is not None

    root.child = parent
    assert parent._parent is root
    assert parent.child._parent is parent

    c_root = HookCounter()
    c_parent = HookCounter()
    c_child = HookCounter()

    root.on_change(c_root.hook)
    parent.on_change(c_parent.hook)
    parent.child.on_change(c_child.hook)

    parent.child._call_hooks()

    assert c_child.count == 1
    assert c_parent.count == 1
    assert c_root.count == 1

    # hooks are called with the node on which they are registered
    assert c_child.calls[0] is parent.child
    assert c_parent.calls[0] is parent
    assert c_root.calls[0] is root


def test_descendant_hooks_are_not_called_when_parent_changes():
    root = Node(child=Node(child=Node()))
    parent = root.child
    assert parent is not None

    child = parent.child
    assert child is not None

    c_root = HookCounter()
    c_parent = HookCounter()
    c_child = HookCounter()

    root.on_change(c_root.hook)
    parent.on_change(c_parent.hook)
    child.on_change(c_child.hook)

    parent._call_hooks()

    assert c_parent.count == 1
    assert c_root.count == 1

    assert c_child.count == 0


def test_propagate_parent_to_reactive():
    parent = Node()
    child = Node()
    propagate_parent(parent, child)

    assert child._parent is parent


def test_propagate_parent_into_list():
    parent = Node()
    lst = [Node(), Node()]

    propagate_parent(parent, lst)

    assert all(c._parent is parent for c in lst)


def test_propagate_parent_into_dict():
    parent = Node()
    d = {"a": Node(), "b": Node()}

    propagate_parent(parent, d)

    assert all(c._parent is parent for c in d.values())
