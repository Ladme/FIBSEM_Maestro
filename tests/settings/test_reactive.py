# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF


from fibsem_maestro.settings.reactive import (
    ReactiveDict,
    ReactiveList,
    ReactiveModel,
    ReactiveNode,
)


class Node(ReactiveNode):
    pass


class HookCounter:
    count: int
    calls: list[ReactiveNode]

    def __init__(self) -> None:
        self.count = 0
        self.calls = []

    def hook(self, node: ReactiveNode) -> None:
        self.count += 1
        self.calls.append(node)


def test_reactive_node_init_has_no_parent_and_no_hooks():
    node = Node()
    assert node._parent is None
    assert node._hooks == []


def test_reactive_node_on_change_registers_hook():
    node = Node()
    ctr = HookCounter()

    node.on_change(ctr.hook)

    assert len(node._hooks) == 1
    assert ctr.hook in node._hooks


def test_reactive_node_call_hooks_invokes_local_hooks():
    node = Node()
    ctr = HookCounter()

    node.on_change(ctr.hook)
    node._call_hooks()

    assert ctr.count == 1
    assert ctr.calls == [node]


def test_reactive_node_call_hooks_with_no_local_hooks_is_noop():
    node = Node()
    node._call_hooks()


def test_reactive_node_multiple_hooks_invoked():
    node = Node()
    c1 = HookCounter()
    c2 = HookCounter()
    c3 = HookCounter()

    node.on_change(c1.hook)
    node.on_change(c2.hook)
    node.on_change(c3.hook)

    node._call_hooks()

    assert c1.count == 1
    assert c2.count == 1
    assert c3.count == 1
    assert c1.calls == [node]
    assert c2.calls == [node]
    assert c3.calls == [node]


def test_reactive_node_hooks_propagate_to_parent():
    root = Node()
    child = Node()
    child._parent = root

    c_child = HookCounter()
    c_root = HookCounter()

    child.on_change(c_child.hook)
    root.on_change(c_root.hook)

    child._call_hooks()

    assert c_child.count == 1
    assert c_child.calls == [child]
    assert c_root.count == 1
    assert c_root.calls == [root]


def test_reactive_node_hook_propagation_three_levels():
    root = Node()
    mid = Node()
    leaf = Node()

    mid._parent = root
    leaf._parent = mid

    c_root = HookCounter()
    c_mid = HookCounter()
    c_leaf = HookCounter()

    root.on_change(c_root.hook)
    mid.on_change(c_mid.hook)
    leaf.on_change(c_leaf.hook)

    leaf._call_hooks()

    assert c_leaf.calls == [leaf]
    assert c_mid.calls == [mid]
    assert c_root.calls == [root]


def test_reactive_node_parent_event_does_not_propagate_to_children():
    parent = Node()
    child = Node()
    child._parent = parent

    c_parent = HookCounter()
    c_child = HookCounter()

    parent.on_change(c_parent.hook)
    child.on_change(c_child.hook)

    parent._call_hooks()

    # parent hook should fire
    assert c_parent.count == 1
    assert c_parent.calls == [parent]

    # child hook must NOT fire
    assert c_child.count == 0
    assert c_child.calls == []


class Child(ReactiveModel):
    value: int = 0


class Parent(ReactiveModel):
    child: Child


def test_reactive_model_init_sets_parent_none_and_no_hooks():
    p = Parent(child=Child(value=1))
    assert p._parent is None
    assert p._hooks == []
    assert p.child._parent is p


def test_nested_reactive_models_have_parent_set_automatically():
    p = Parent(child=Child(value=123))
    assert p.child._parent is p


def test_reactive_model_field_assignment_triggers_hook():
    p = Parent(child=Child(value=1))
    ctr = HookCounter()

    p.on_change(ctr.hook)
    p.child = Child(value=99)

    assert ctr.count == 1
    assert ctr.calls == [p]


def test_reactive_model_assignment_propagates_hooks_to_parent():
    p = Parent(child=Child(value=1))
    c = p.child

    ctr_p = HookCounter()
    ctr_c = HookCounter()

    p.on_change(ctr_p.hook)
    c.on_change(ctr_c.hook)

    c.value = 10

    assert ctr_c.count == 1
    assert ctr_c.calls == [c]
    assert ctr_p.count == 1
    assert ctr_p.calls == [p]


def test_reactive_model_parent_event_does_not_propagate_downward():
    p = Parent(child=Child(value=1))
    c = p.child

    ctr_p = HookCounter()
    ctr_c = HookCounter()

    p.on_change(ctr_p.hook)
    c.on_change(ctr_c.hook)

    p._call_hooks()

    assert ctr_p.count == 1
    assert ctr_c.count == 0


def test_reactive_model_modifying_non_model_attribute_does_not_trigger_hooks():
    p = Parent(child=Child(value=1))
    ctr = HookCounter()
    p.on_change(ctr.hook)

    # not a model field defined in Pydantic
    p._some_internal = "abc"

    assert ctr.count == 0


def test_reactive_model_update_replaces_all_fields_and_triggers_once():
    p = Parent(child=Child(value=1))
    other = Parent(child=Child(value=999))

    ctr = HookCounter()
    p.on_change(ctr.hook)

    p.update(other)

    assert p.child.value == 999
    assert ctr.count == 1
    assert ctr.calls == [p]


def test_reactive_model_update_reparents_nested_models():
    p1 = Parent(child=Child(value=1))
    p2 = Parent(child=Child(value=2))

    p1.update(p2)

    assert p1.child._parent is p1


class GrandParent(ReactiveModel):
    parent: Parent


def test_reactive_model_deep_nested_hooks_propagate_correctly():
    g = GrandParent(parent=Parent(child=Child(value=10)))
    p = g.parent
    c = p.child

    ctr_g = HookCounter()
    ctr_p = HookCounter()
    ctr_c = HookCounter()

    g.on_change(ctr_g.hook)
    p.on_change(ctr_p.hook)
    c.on_change(ctr_c.hook)

    c.value = 5

    assert ctr_c.calls == [c]
    assert ctr_p.calls == [p]
    assert ctr_g.calls == [g]


def test_reactive_model_reassigning_child_updates_parent_relationship():
    p = Parent(child=Child(value=1))
    new_child = Child(value=99)

    p.child = new_child
    assert new_child._parent is p


def test_reactive_model_reassigning_parent_changes_propagation_chain():
    p1 = Parent(child=Child(value=1))
    p2 = Parent(child=Child(value=2))

    c = p1.child
    # move child from p1 to p2
    p2.child = c

    ctr_p1 = HookCounter()
    ctr_p2 = HookCounter()
    ctr_c = HookCounter()

    p1.on_change(ctr_p1.hook)
    p2.on_change(ctr_p2.hook)
    c.on_change(ctr_c.hook)

    c.value = 100

    assert ctr_c.calls == [c]
    assert ctr_p1.calls == []  # no longer parent
    assert ctr_p2.calls == [p2]  # new parent receives event


def test_reactive_dict_init_sets_parent_none_and_attaches_existing_values():
    c1 = Node()
    d = ReactiveDict(a=c1)

    assert d._parent is None
    assert c1._parent is d


def test_reactive_dict_init_skips_non_reactive_values():
    d = ReactiveDict(a=123, b="x")
    assert d["a"] == 123
    assert d["b"] == "x"


def test_reactive_dict_setitem_triggers_hooks():
    d = ReactiveDict()
    ctr = HookCounter()

    d.on_change(ctr.hook)
    d["x"] = Node()

    assert ctr.count == 1
    assert ctr.calls == [d]


def test_reactive_dict_setitem_sets_parent_on_reactive_value():
    d = ReactiveDict()
    c = Node()

    d["child"] = c
    assert c._parent is d


def test_reactive_dict_overwrite_existing_value_triggers_hook():
    d = ReactiveDict(x=Node())
    ctr = HookCounter()

    d.on_change(ctr.hook)
    d["x"] = Node()

    assert ctr.count == 1
    assert ctr.calls == [d]


def test_reactive_dict_update_assigns_parents_and_triggers_once():
    d = ReactiveDict()
    c1 = Node()
    c2 = Node()

    ctr = HookCounter()
    d.on_change(ctr.hook)

    d.update({"a": c1, "b": c2})

    assert c1._parent is d
    assert c2._parent is d
    assert ctr.count == 1
    assert ctr.calls == [d]


def test_reactive_dict_update_reactive_and_non_reactive_values():
    d = ReactiveDict()
    c = Node()

    d.update({"a": 5, "b": c})
    assert isinstance(d["a"], int)
    assert d["b"] is c
    assert c._parent is d


def test_reactive_dict_pop_triggers_hook():
    c = Node()
    d = ReactiveDict(x=c)

    ctr = HookCounter()
    d.on_change(ctr.hook)

    removed = d.pop("x")

    assert removed is c
    assert ctr.count == 1
    assert ctr.calls == [d]


def test_reactive_dict_clear_triggers_hook():
    d = ReactiveDict(x=Node(), y=Node())

    ctr = HookCounter()
    d.on_change(ctr.hook)

    d.clear()
    assert ctr.count == 1
    assert ctr.calls == [d]
    assert not d.items()


def test_reactive_dict_child_event_propagates_to_parent_dict():
    c = Node()
    d = ReactiveDict(child=c)

    ctr_dict = HookCounter()
    ctr_child = HookCounter()

    d.on_change(ctr_dict.hook)
    c.on_change(ctr_child.hook)

    # trigger event on child
    c._call_hooks()

    assert ctr_child.calls == [c]
    assert ctr_dict.calls == [d]


def test_reactive_dict_nested_propagation_three_levels():
    c = Node()
    d = ReactiveDict(child=c)
    root = ReactiveDict(inner=d)

    ctr_root = HookCounter()
    ctr_d = HookCounter()
    ctr_c = HookCounter()

    root.on_change(ctr_root.hook)
    d.on_change(ctr_d.hook)
    c.on_change(ctr_c.hook)

    c._call_hooks()

    assert ctr_c.calls == [c]
    assert ctr_d.calls == [d]
    assert ctr_root.calls == [root]


def test_reactive_dict_parent_event_does_not_propagate_to_children():
    d = ReactiveDict(child=Node())
    c = d["child"]

    ctr_d = HookCounter()
    ctr_c = HookCounter()

    d.on_change(ctr_d.hook)
    c.on_change(ctr_c.hook)

    d._call_hooks()

    assert ctr_d.count == 1
    assert ctr_c.count == 0


def test_reactive_dict_ultiple_hooks_fire_in_order():
    d = ReactiveDict()
    c1 = HookCounter()
    c2 = HookCounter()
    c3 = HookCounter()

    d.on_change(c1.hook)
    d.on_change(c2.hook)
    d.on_change(c3.hook)

    d["x"] = Node()

    assert c1.calls == [d]
    assert c2.calls == [d]
    assert c3.calls == [d]


def test_reactive_dict_reassigning_child_updates_parent_pointer():
    d1 = ReactiveDict()
    d2 = ReactiveDict()
    c = Node()

    d1["x"] = c
    assert c._parent is d1

    d2["x"] = c  # move c into new dict
    assert c._parent is d2


def test_reactive_dict_reassigning_child_changes_propagation_chain():
    d1 = ReactiveDict(child=Node())
    c = d1["child"]
    d2 = ReactiveDict()

    ctr_d1 = HookCounter()
    ctr_d2 = HookCounter()
    ctr_c = HookCounter()

    d1.on_change(ctr_d1.hook)
    d2.on_change(ctr_d2.hook)
    c.on_change(ctr_c.hook)

    # move child into new dict
    d2["child"] = c

    assert c._parent is d2

    # trigger event from child
    c._call_hooks()

    assert c._parent is d2

    assert ctr_c.calls == [c]
    assert ctr_d1.calls == []  # old parent should no longer receive events
    assert ctr_d2.calls == [
        d2,
        d2,
    ]  # two calls, since the move of the child also triggers an event


def test_reactive_dict_parent_pointer_set_on_assignment():
    d = ReactiveDict()
    c = Node()

    d["key"] = c

    assert c._parent is d


def test_reactive_list_init_parents_assigned_for_reactive_items():
    c1 = Node()
    c2 = Node()
    rl = ReactiveList([c1, c2])

    assert c1._parent is rl
    assert c2._parent is rl


def test_reactive_list_init_skips_non_reactive_items():
    rl = ReactiveList([1, "x", None])
    assert rl == [1, "x", None]


def test_reactive_list_append_triggers_hook():
    rl: ReactiveList[Node] = ReactiveList()
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.append(Node())

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_append_triggers_hook_even_if_not_reactive():
    rl: ReactiveList[int] = ReactiveList()
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.append(8)

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_extend_triggers_hook_once():
    rl: ReactiveList[Node] = ReactiveList()
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.extend([Node(), Node()])

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_extend_triggers_hook_once_even_if_not_reactive():
    rl: ReactiveList[int] = ReactiveList()
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.extend([4, 5])

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_insert_triggers_hook():
    rl = ReactiveList([Node()])
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.insert(0, Node())

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_insert_triggers_hook_even_if_not_reactive():
    rl = ReactiveList([11])
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl.insert(0, 4)

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_setitem_triggers_hook():
    rl = ReactiveList([Node()])
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl[0] = Node()

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_setitem_triggers_hook_even_if_not_reactive():
    rl = ReactiveList([8])
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl[0] = 9

    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_setitem_slice_triggers_hook_and_parents():
    a = Node()
    b = Node()
    rl = ReactiveList([Node(), Node()])
    ctr = HookCounter()

    rl.on_change(ctr.hook)
    rl[0:2] = [a, b]

    assert ctr.count == 1
    assert a._parent is rl
    assert b._parent is rl


def test_reactive_list_pop_triggers_hook():
    c = Node()
    rl = ReactiveList([c])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    popped = rl.pop()

    assert len(rl) == 0
    assert popped is c
    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_pop_triggers_hook_even_if_not_reactive():
    rl = ReactiveList([8])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    popped = rl.pop()

    assert len(rl) == 0
    assert popped == 8
    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_remove_triggers_hook():
    c1 = Node()
    c2 = Node()
    rl = ReactiveList([c1, c2])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    rl.remove(c2)

    assert len(rl) == 1
    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_remove_triggers_hook_even_if_not_reactive():
    rl = ReactiveList([4, 2])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    rl.remove(4)

    assert len(rl) == 1
    assert ctr.count == 1
    assert ctr.calls == [rl]


def test_reactive_list_clear_triggers_hook():
    rl = ReactiveList([Node(), Node()])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    rl.clear()

    assert not rl
    assert ctr.count == 1
    assert rl == []


def test_reactive_list_clear_triggers_hook_even_if_not_reactive():
    rl = ReactiveList([4, 2])

    ctr = HookCounter()
    rl.on_change(ctr.hook)

    rl.clear()

    assert not rl
    assert ctr.count == 1
    assert rl == []


def test_reactive_list_child_event_propagates_upward():
    c = Node()
    rl = ReactiveList([c])

    ctr_list = HookCounter()
    ctr_child = HookCounter()

    rl.on_change(ctr_list.hook)
    c.on_change(ctr_child.hook)

    c._call_hooks()

    assert ctr_child.calls == [c]
    assert ctr_list.calls == [rl]


def test_reactive_list_nested_three_level_propagation():
    c = Node()
    rl = ReactiveList([c])
    outer = ReactiveList([rl])

    ctr_outer = HookCounter()
    ctr_rl = HookCounter()
    ctr_c = HookCounter()

    outer.on_change(ctr_outer.hook)
    rl.on_change(ctr_rl.hook)
    c.on_change(ctr_c.hook)

    c._call_hooks()

    assert ctr_c.calls == [c]
    assert ctr_rl.calls == [rl]
    assert ctr_outer.calls == [outer]


def test_reactive_list_parent_event_does_not_propagate_to_children():
    c = Node()
    rl = ReactiveList([c])

    ctr_list = HookCounter()
    ctr_child = HookCounter()

    rl.on_change(ctr_list.hook)
    c.on_change(ctr_child.hook)

    rl._call_hooks()

    assert ctr_list.count == 1
    assert ctr_child.count == 0  # no downward propagation


def test_reactive_list_reassigning_child_updates_parent_pointer():
    rl1 = ReactiveList([Node()])
    c = rl1[0]
    rl2: ReactiveList[Node] = ReactiveList()

    rl2.append(c)
    assert c._parent is rl2


def test_reactive_list_reassigning_child_changes_propagation_chain():
    rl1 = ReactiveList([Node()])
    c = rl1[0]
    rl2: ReactiveList[Node] = ReactiveList()

    ctr_rl1 = HookCounter()
    ctr_rl2 = HookCounter()
    ctr_c = HookCounter()

    rl1.on_change(ctr_rl1.hook)
    rl2.on_change(ctr_rl2.hook)
    c.on_change(ctr_c.hook)

    rl2.append(c)
    c._call_hooks()

    assert ctr_c.calls == [c]
    assert ctr_rl1.calls == []
    assert ctr_rl2.calls == [
        rl2,
        rl2,
    ]  # two events since the append call is an event in itself


def test_reactive_list_multiple_hooks_invoked_in_order():
    rl: ReactiveList[int] = ReactiveList()
    c1 = HookCounter()
    c2 = HookCounter()
    c3 = HookCounter()

    rl.on_change(c1.hook)
    rl.on_change(c2.hook)
    rl.on_change(c3.hook)

    rl.append(8)

    assert c1.calls == [rl]
    assert c2.calls == [rl]
    assert c3.calls == [rl]


def test_deep_mixed_reactive_structure_propagation():
    class Leaf(ReactiveModel):
        value: int = 0

    class Branch(ReactiveModel):
        leaves: ReactiveList[Leaf]
        meta: ReactiveDict[str, Leaf]

    class Root(ReactiveModel):
        branches: ReactiveList[Branch]
        extra: ReactiveDict[str, int]

    leaf_a = Leaf(value=1)
    leaf_b = Leaf(value=2)

    branch1 = Branch(leaves=ReactiveList([leaf_a]), meta=ReactiveDict({"core": leaf_b}))

    root = Root(branches=ReactiveList([branch1]), extra=ReactiveDict({"aux": 42}))

    ctr_leaf_a = HookCounter()
    ctr_leaf_b = HookCounter()
    ctr_branch = HookCounter()
    ctr_root = HookCounter()

    leaf_a.on_change(ctr_leaf_a.hook)
    leaf_b.on_change(ctr_leaf_b.hook)

    branch1.on_change(ctr_branch.hook)
    root.on_change(ctr_root.hook)

    ctr_branches_list = HookCounter()
    ctr_meta_dict = HookCounter()
    ctr_extra_dict = HookCounter()

    root.branches.on_change(ctr_branches_list.hook)
    branch1.meta.on_change(ctr_meta_dict.hook)
    root.extra.on_change(ctr_extra_dict.hook)

    leaf_b.value = 999

    assert ctr_leaf_b.calls == [leaf_b]
    assert ctr_meta_dict.calls == [branch1.meta]
    assert ctr_branch.calls == [branch1]
    assert ctr_branches_list.calls == [root.branches]
    assert ctr_root.calls == [root]

    assert ctr_leaf_a.calls == []  # sibling leaf
    assert ctr_extra_dict.calls == []  # unrelated dict
