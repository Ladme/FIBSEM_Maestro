# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from dataclasses import dataclass

from fibsem_maestro.action.action import Action, LinkedActions
from fibsem_maestro.logging.text.text_logger import TextLogger


@dataclass
class LinkRule:
    action_name: str
    links: LinkedActions


class ActionLinks:
    """
    Manages links between actions in the workflow.

    Args:
        txt_log: Logger for debug and info messages.
    """

    def __init__(self, txt_log: TextLogger) -> None:
        self._txt_log = txt_log
        self.rules: list[LinkRule] = []

    def register_rule(
        self,
        action_name: str,
        links: LinkedActions,
    ) -> None:
        """Register a rule instance for the given action."""
        self.rules.append(
            LinkRule(
                action_name=action_name,
                links=links,
            )
        )

    def resolve(self, action: Action) -> LinkedActions | None:
        """Return the links instance for the given action, or None."""
        for rule in self.rules:
            if rule.action_name == action.name:
                return rule.links
        return None
