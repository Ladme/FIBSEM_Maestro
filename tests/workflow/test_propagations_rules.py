# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Callable

from fibsem_maestro.action.action import Action
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.propagations import PropagationRule, Propagations
from fibsem_maestro.workflow.workflow import Workflow


def test_propagations_rename_action_rewrites_parent_and_dependents_in_place() -> None:
    propagations = Propagations()
    propagations.register_rule("a", ["b", "a", "c"], PropertyNames())
    propagations.register_rule("c", ["a"], PropertyNames())
    first, second = propagations.rules
    dependents = first.dependent_names

    propagations.rename_action("a", "z")

    assert propagations.rules[0] is first and propagations.rules[1] is second
    assert first.parent_name == "z"
    assert first.dependent_names is dependents
    assert first.dependent_names == ["b", "z", "c"]
    assert second.parent_name == "c" and second.dependent_names == ["z"]


def test_propagation_rule_is_complete_needs_dependents_and_properties() -> None:
    names = PropertyNames(electron_beam=["working_distance"])
    assert PropagationRule("a", ["b"], names).is_complete()
    assert not PropagationRule("a", [], names).is_complete()
    assert not PropagationRule("a", ["b"], PropertyNames()).is_complete()


def test_propagate_skips_rule_without_dependents(
    workflow: Workflow, add_action: Callable[..., Action]
) -> None:
    parent = add_action("adjust_props", "parent")
    # a rule naming a property the parent never produces would raise if applied
    workflow.propagations.register_rule(
        "parent", [], PropertyNames(electron_beam=["working_distance"])
    )
    workflow.propagations.propagate(
        parent, GlobalProperties(), workflow.actions, workflow.ctx.text_logger
    )


def test_propagate_skips_rule_without_properties(
    workflow: Workflow, add_action: Callable[..., Action]
) -> None:
    parent = add_action("adjust_props", "parent")
    add_action("adjust_props", "child")
    workflow.propagations.register_rule("parent", ["child"], PropertyNames())
    # the child has no props file; a non-skipped rule would try to read it
    workflow.propagations.propagate(
        parent, GlobalProperties(), workflow.actions, workflow.ctx.text_logger
    )
