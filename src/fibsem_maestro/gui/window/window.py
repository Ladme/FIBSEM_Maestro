# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

import os
from pathlib import Path
from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QCloseEvent
from PyQt6.QtWidgets import (
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_list_panel.panel import ActionListPanel
from fibsem_maestro.gui.action_panel.action_panel import ActionPanel
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.log_panel.panel import LogPanel
from fibsem_maestro.gui.window._top_bar import TopBar
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.workflow.actions import Actions
from fibsem_maestro.workflow.workflow import Workflow


class MainWindow(QMainWindow):
    def __init__(
        self,
        workflow: Workflow,
        workflow_dir: Path,
    ) -> None:
        super().__init__()
        self._manager = WorkflowManager(workflow)
        self._microscope = workflow.microscope
        self._workflow_dir = workflow_dir

        # store microscope settings and initial workflow state
        self._store_microscope_settings(self._microscope)
        self._store_workflow_state(self._manager.workflow.actions)

        self._panels: dict[Action, QWidget] = {}

        self.setWindowTitle("FIBSEM Maestro")
        self.resize(1280, 800)

        # root layout
        root = QWidget()
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        # top bar
        self._top_bar = TopBar(
            workflow_manager=self._manager,
            workflow_dir=workflow_dir,
            form_builder=FormBuilder(),
        )
        self._manager.app_state_changed.connect(self._top_bar.on_app_state_changed)
        self._manager.slice_finished.connect(self._top_bar.on_slice_changed)
        root_layout.addWidget(self._top_bar)

        # thin separator line below top bar
        separator = QWidget()
        separator.setFixedHeight(1)
        separator.setStyleSheet("background: #444444;")
        root_layout.addWidget(separator)

        # vertical splitter
        v_splitter = QSplitter(Qt.Orientation.Vertical)
        root_layout.addWidget(v_splitter)

        # horizontal splitter
        h_splitter = QSplitter(Qt.Orientation.Horizontal)
        v_splitter.addWidget(h_splitter)

        # scrollable panel with actions
        self._action_list = ActionListPanel(
            workflow_manager=self._manager,
            workflow_dir=workflow_dir,
            app_state=self._manager.state,
        )

        left_scroll = QScrollArea()
        left_scroll.setWidgetResizable(True)
        left_scroll.setMinimumWidth(120)
        left_placeholder = QWidget()
        left_scroll.setWidget(left_placeholder)
        h_splitter.addWidget(left_scroll)
        left_scroll.setWidget(self._action_list)

        # form panel
        self._stack = QStackedWidget()
        h_splitter.addWidget(self._stack)

        # splitter proportions
        h_splitter.setStretchFactor(0, 1)
        h_splitter.setStretchFactor(1, 4)

        # bottom panel
        self._log_panel = LogPanel(
            workflow_manager=self._manager,
            workflow_dir=workflow_dir,
        )
        v_splitter.addWidget(self._log_panel)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        h_splitter.setSizes([300, 1080])

        # wiring signals
        self._action_list.action_selected.connect(self._on_action_selected)
        self._manager.app_state_changed.connect(self._action_list.on_app_state_changed)

        # store the settings for each action every time the action changes
        self._manager.action_changed.connect(self._store_action_settings)

        # store the workflow state every time actions or propagations change
        self._manager.actions_changed.connect(self._store_workflow_state)
        self._manager.propagations_changed.connect(self._store_workflow_state)

        # store the microscope settings every time the microscope changes
        self._manager.microscope_changed.connect(self._store_microscope_settings)

        # check if the workflow is ready every time an action or workflow is changed
        self._manager.actions_changed.connect(self._check_workflow_ready)
        self._manager.action_changed.connect(self._check_workflow_ready)

        self._manager.slice_finished.connect(self._log_panel.on_slice_changed)
        self._manager.workflow_reset.connect(self._log_panel.on_slice_changed)
        self._manager.actions_changed.connect(self._log_panel.on_actions_changed)

        self._manager.workflow_interrupted.connect(self._on_workflow_interrupted)

    def _on_action_selected(self, action: Action) -> None:
        if action not in self._panels:
            panel = ActionPanel(
                action=action,
                workflow_manager=self._manager,
                form_builder=FormBuilder(),
            )
            self._manager.app_state_changed.connect(panel.on_app_state_changed)
            self._manager.action_changed.connect(panel.on_action_changed)
            self._panels[action] = panel
            self._stack.addWidget(panel)

        self._stack.setCurrentWidget(self._panels[action])

    def _store_action_settings(self, action: Action) -> None:
        action.ctx.settings_store.write("settings.yaml", action.settings)

    def _store_microscope_settings(self, microscope: Microscope) -> None:
        self._manager.workflow.ctx.settings_store.write(
            "microscope_settings.yaml", microscope.settings
        )

    def _store_workflow_state(self, actions: Actions) -> None:
        _ = actions
        self._manager.workflow.ctx.state_store.write(
            "state.yaml", self._manager.workflow.state
        )

    def _check_workflow_ready(self, _: Any) -> None:
        self._manager.preparedness_changed.emit(
            # there must be at least one action and all props must exist
            len(self._manager.workflow.actions) > 0
            and all(
                action.ctx.props_store.exists("props.yaml")
                for action in self._manager.workflow.actions
            )
        )

    def _on_workflow_interrupted(self, error: str) -> None:
        QMessageBox.critical(self, "Workflow error", error)

    def closeEvent(self, a0: QCloseEvent) -> None:
        _ = a0
        os._exit(0)
