# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

"""The stack showing the selected action's panel, keeping a panel per action shown so far."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PyQt6.QtWidgets import QStackedWidget, QWidget

from fibsem_maestro.ui.views.action_panel.panel import ActionPanel

if TYPE_CHECKING:
    from fibsem_maestro.action.action import Action
    from fibsem_maestro.ui.app.action_status import ActionStatus
    from fibsem_maestro.ui.app.commands import AppCommands
    from fibsem_maestro.ui.app.edit_policy import EditPolicy
    from fibsem_maestro.ui.app.form_validity import FormValidity
    from fibsem_maestro.ui.app.run_controller import RunController
    from fibsem_maestro.ui.app.session import WorkflowSession
    from fibsem_maestro.ui.composition import FormContexts
    from fibsem_maestro.ui.forms.builder import FormBuilder


class ActionPanelFactory:
    """
    Creates the panel of an action, with everything a panel needs.

    Args:
        session: The workflow session.
        run: The run controller.
        commands: Every user intent.
        policy: The permissions.
        status: The per-action indicators.
        validity: Which settings forms show errors.
        form_builder: Builds the forms.
        form_contexts: The environments of the forms.
    """

    def __init__(
        self,
        session: WorkflowSession,
        run: RunController,
        commands: AppCommands,
        policy: EditPolicy,
        status: ActionStatus,
        validity: FormValidity,
        form_builder: FormBuilder,
        form_contexts: FormContexts,
    ) -> None:
        self._session = session
        self._run = run
        self._commands = commands
        self._policy = policy
        self._status = status
        self._validity = validity
        self._form_builder = form_builder
        self._form_contexts = form_contexts

    def create(self, action: Action) -> ActionPanel:
        """
        Build the panel of an action.

        Args:
            action: The action.

        Returns:
            The new panel.
        """
        return ActionPanel(
            action=action,
            session=self._session,
            run=self._run,
            commands=self._commands,
            policy=self._policy,
            status=self._status,
            validity=self._validity,
            form_builder=self._form_builder,
            form_contexts=self._form_contexts,
        )


class ActionPanelHost(QStackedWidget):
    """
    Shows the panel of the selected action, or an empty widget.

    Panels are created the first time their action is shown and kept, so that
    collapsed groups, expanded area viewers and loaded images survive switching
    between actions. A panel is discarded when its action is removed, and all
    panels when the workflow is replaced.

    Args:
        factory: Creates panels.
        session: The workflow session (removals, replacement).
        validity: Forgets the validity of discarded panels' forms.
        parent: Parent widget.
    """

    def __init__(
        self,
        factory: ActionPanelFactory,
        session: WorkflowSession,
        validity: FormValidity,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._factory = factory
        self._validity = validity
        self._panels: dict[Action, ActionPanel] = {}

        self._empty_panel = QWidget()
        self.addWidget(self._empty_panel)
        self.setCurrentWidget(self._empty_panel)

        session.action_removed.connect(self._on_action_removed)
        session.workflow_replaced.connect(self._on_workflow_replaced)

    def show_action(self, action: Action | None) -> None:
        """
        Show the panel of an action, creating it on first use.

        Args:
            action: The action, or None for the empty panel.
        """
        if action is None:
            self.setCurrentWidget(self._empty_panel)
            return

        panel = self._panels.get(action)
        if panel is None:
            panel = self._factory.create(action)
            self._panels[action] = panel
            self.addWidget(panel)
        self.setCurrentWidget(panel)

    def panel(self, action: Action) -> ActionPanel | None:
        """
        The cached panel of an action.

        Args:
            action: The action.

        Returns:
            The panel, or None if it was never shown or was discarded.
        """
        return self._panels.get(action)

    def _on_action_removed(self, action: Action) -> None:
        self._discard(action)

    def _on_workflow_replaced(self) -> None:
        for action in list(self._panels):
            self._discard(action)

    def _discard(self, action: Action) -> None:
        panel = self._panels.pop(action, None)
        if panel is None:
            return

        if self.currentWidget() is panel:
            self.setCurrentWidget(self._empty_panel)

        self.removeWidget(panel)
        panel.dispose()
        self._validity.forget(action)
        panel.deleteLater()
