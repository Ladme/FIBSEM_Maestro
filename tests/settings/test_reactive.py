# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF


from typing import Literal

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


def test_reactive_dict_multiple_hooks_fire_in_order():
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


def test_reactive_model_parent_write_is_visible_on_read():
    p = Parent(child=Child(value=0))
    c = Child(value=1)

    c._parent = p

    assert c.__pydantic_private__["_parent"] is p  # ty: ignore[not-subscriptable]
    assert c._parent is p


class PatchChild(ReactiveModel):
    a: int | None = None
    b: int | None = None


class PatchParent(ReactiveModel):
    child: PatchChild | None = None
    name: str | None = None
    tags: ReactiveList | None = None


class PatchGrandParent(ReactiveModel):
    parent: PatchParent | None = None


def test_patch_applies_non_none_fields():
    model = PatchParent(name="original")

    model.patch(PatchParent(name="updated"))

    assert model.name == "updated"


def test_patch_skips_none_fields():
    model = PatchParent(name="original")

    model.patch(PatchParent(name=None))

    assert model.name == "original"


def test_patch_cannot_clear_a_field():
    model = PatchParent(name="original")

    model.patch(PatchParent())

    assert model.name == "original"


def test_patch_applies_falsy_values():
    """Only None is skipped - 0 and '' are real values."""
    model = PatchParent(name="original")
    child = PatchChild(a=5)

    model.patch(PatchParent(name=""))
    child.patch(PatchChild(a=0))

    assert model.name == ""
    assert child.a == 0


def test_patch_recurses_into_nested_models():
    model = PatchParent(child=PatchChild(a=1, b=2))

    model.patch(PatchParent(child=PatchChild(a=99)))

    assert model.child is not None
    assert model.child.a == 99
    assert model.child.b == 2


def test_patch_keeps_nested_model_identity():
    """Nested models are patched in place, not replaced, so existing hooks survive."""
    model = PatchParent(child=PatchChild(a=1))
    original_child = model.child

    model.patch(PatchParent(child=PatchChild(a=9)))

    assert model.child is original_child


def test_patch_does_not_adopt_the_nested_model_of_other():
    source = PatchParent(child=PatchChild(a=1))
    target = PatchParent(child=PatchChild(a=2))

    target.patch(source)

    assert target.child is not source.child
    assert source.child is not None
    assert source.child._parent is source


def test_patch_recurses_through_two_levels():
    model = PatchGrandParent(
        parent=PatchParent(name="keep", child=PatchChild(a=1, b=2))
    )

    model.patch(PatchGrandParent(parent=PatchParent(child=PatchChild(a=9))))

    assert model.parent is not None
    assert model.parent.child is not None
    assert model.parent.child.a == 9
    assert model.parent.child.b == 2
    assert model.parent.name == "keep"


def test_patch_reparents_children():
    model = PatchParent(child=PatchChild(a=1))

    model.patch(PatchParent(child=PatchChild(a=5)))

    assert model.child is not None
    assert model.child._parent is model


def test_patch_fires_hooks_once_for_a_flat_patch():
    model = PatchParent(name="original", child=PatchChild(a=1))
    ctr = HookCounter()
    model.on_change(ctr.hook)

    model.patch(PatchParent(name="updated"))

    assert ctr.count == 1
    assert ctr.calls == [model]


def test_patch_fires_hooks_even_when_nothing_changes():
    """An all-None patch still emits; callers must tolerate a no-op event."""
    model = PatchParent(name="original")
    ctr = HookCounter()
    model.on_change(ctr.hook)

    model.patch(PatchParent())

    assert ctr.count == 1


def test_patch_fires_nested_hooks_on_the_patched_child():
    model = PatchParent(child=PatchChild(a=1))
    ctr = HookCounter()
    assert model.child is not None
    model.child.on_change(ctr.hook)

    model.patch(PatchParent(child=PatchChild(a=9)))

    assert ctr.count == 1
    assert ctr.calls == [model.child]


def test_patch_fires_root_hooks_once_regardless_of_depth():
    model = PatchGrandParent(parent=PatchParent(child=PatchChild(a=1)))
    ctr = HookCounter()
    model.on_change(ctr.hook)

    model.patch(PatchGrandParent(parent=PatchParent(child=PatchChild(a=9))))

    assert ctr.count == 1
    assert ctr.calls == [model]


def test_patch_creates_nested_model_when_target_field_is_none():
    model = PatchParent(child=None)

    model.patch(PatchParent(child=PatchChild(a=1)))

    assert model.child is not None
    assert model.child.a == 1
    assert model.child._parent is model


def test_patch_created_nested_model_is_not_shared_with_source():
    source = PatchParent(child=PatchChild(a=1))
    target = PatchParent(child=None)

    target.patch(source)

    assert target.child is not source.child


def test_patch_copies_non_model_containers():
    source = PatchParent(tags=ReactiveList([1, 2]))
    target = PatchParent(tags=ReactiveList([9]))

    target.patch(source)

    assert target.tags is not None
    assert source.tags is not None
    assert list(target.tags) == [1, 2]
    assert target.tags is not source.tags
    assert source.tags._parent is source


def test_patch_copied_container_does_not_inherit_source_hooks():
    source = PatchParent(tags=ReactiveList([1, 2]))
    ctr = HookCounter()
    assert source.tags is not None
    source.tags.on_change(ctr.hook)
    target = PatchParent(tags=ReactiveList([9]))

    target.patch(source)
    assert target.tags is not None
    target.tags.append(3)

    assert ctr.count == 0


def test_patch_fires_nested_hooks_exactly_once():
    model = PatchGrandParent(parent=PatchParent(child=PatchChild(a=1)))
    ctr_parent = HookCounter()
    ctr_child = HookCounter()
    assert model.parent is not None
    assert model.parent.child is not None
    model.parent.on_change(ctr_parent.hook)
    model.parent.child.on_change(ctr_child.hook)

    model.patch(PatchGrandParent(parent=PatchParent(child=PatchChild(a=9))))

    assert ctr_parent.count == 1
    assert ctr_child.count == 1


def test_patch_creates_nested_model_with_required_fields():
    """`model_construct` sidesteps the no-default-constructor problem."""

    class Required(ReactiveModel):
        kind: Literal["imaging"]
        dwell_time_ns: int = 100

    class Holder(ReactiveModel):
        action: Required | None = None

    target = Holder(action=None)

    target.patch(Holder(action=Required(kind="imaging", dwell_time_ns=50)))

    assert target.action is not None
    assert target.action.kind == "imaging"
    assert target.action.dwell_time_ns == 50
    assert target.action._parent is target


def test_patch_copies_models_held_in_a_container():
    class Action(ReactiveModel):
        dwell_time_ns: int = 100

    class Pipeline(ReactiveModel):
        actions: ReactiveList | None = None

    source = Pipeline(actions=ReactiveList([Action(dwell_time_ns=50)]))
    target = Pipeline(actions=ReactiveList([]))

    target.patch(source)

    assert target.actions is not None
    assert source.actions is not None
    assert target.actions[0].dwell_time_ns == 50
    assert target.actions[0] is not source.actions[0]


def test_patch_leaves_source_container_items_parented_to_the_source():
    class Action(ReactiveModel):
        dwell_time_ns: int = 100

    class Pipeline(ReactiveModel):
        actions: ReactiveList | None = None

    source = Pipeline(actions=ReactiveList([Action(dwell_time_ns=50)]))
    target = Pipeline(actions=ReactiveList([]))

    target.patch(source)

    assert source.actions is not None
    assert source.actions[0]._parent is source.actions


def test_patch_copied_container_items_do_not_inherit_source_hooks():
    class Action(ReactiveModel):
        dwell_time_ns: int = 100

    class Pipeline(ReactiveModel):
        actions: ReactiveList | None = None

    source = Pipeline(actions=ReactiveList([Action(dwell_time_ns=50)]))
    ctr = HookCounter()
    assert source.actions is not None
    source.actions[0].on_change(ctr.hook)
    target = Pipeline(actions=ReactiveList([]))

    target.patch(source)
    assert target.actions is not None
    target.actions[0].dwell_time_ns = 99

    assert ctr.count == 0


def test_patch_copies_models_nested_inside_container_items():
    class Inner(ReactiveModel):
        value: int = 1

    class Action(ReactiveModel):
        inner: Inner | None = None

    class Pipeline(ReactiveModel):
        actions: ReactiveList | None = None

    source = Pipeline(actions=ReactiveList([Action(inner=Inner(value=5))]))
    target = Pipeline(actions=ReactiveList([]))

    target.patch(source)

    assert target.actions is not None
    assert source.actions is not None
    assert target.actions[0].inner.value == 5
    assert target.actions[0].inner is not source.actions[0].inner
    assert target.actions[0].inner._parent is target.actions[0]
