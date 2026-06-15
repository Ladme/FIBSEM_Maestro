# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from pathlib import Path

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QMainWindow,
    QPlainTextEdit,
    QProgressBar,
    QScrollArea,
    QSplitter,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_list_panel.panel import ActionListPanel
from fibsem_maestro.gui.action_panel.action_panel import ActionPanel
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.window._top_bar import TopBar
from fibsem_maestro.workflow.workflow import Workflow


class MainWindow(QMainWindow):
    app_state_changed = pyqtSignal(object)

    def __init__(
        self,
        workflow: Workflow,
        workflow_dir: Path,
    ) -> None:
        super().__init__()
        self._workflow = workflow
        self._microscope = workflow.microscope
        self._workflow_dir = workflow_dir

        self._app_state = AppState.EDITING

        self._form_builder = FormBuilder()
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
            workflow=workflow,
            workflow_dir=workflow_dir,
            form_builder=self._form_builder,
        )
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
            workflow=workflow,
            microscope=self._microscope,
            workflow_dir=workflow_dir,
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
        bottom = QWidget()
        bottom_layout = QVBoxLayout(bottom)
        bottom_layout.setContentsMargins(4, 4, 4, 4)
        bottom_layout.setSpacing(4)

        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedHeight(14)
        self.progress_bar.setTextVisible(True)
        bottom_layout.addWidget(self.progress_bar)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(1000)
        self.log_view.setFixedHeight(120)
        bottom_layout.addWidget(self.log_view)

        v_splitter.addWidget(bottom)
        v_splitter.setStretchFactor(0, 1)
        v_splitter.setStretchFactor(1, 0)

        h_splitter.setSizes([300, 1080])

        # wiring signals
        self._top_bar.run_requested.connect(
            lambda: self.set_app_state(AppState.RUNNING)
        )
        self._top_bar.pause_requested.connect(
            lambda: self.set_app_state(AppState.PAUSED)
        )
        self.app_state_changed.connect(self._top_bar.on_app_state_changed)

        self._action_list.action_selected.connect(self._on_action_selected)
        self.app_state_changed.connect(self._action_list.on_app_state_changed)

    def append_log(self, message: str) -> None:
        self.log_view.appendPlainText(message)

    def set_progress(self, value: int) -> None:
        """Set progress bar value (0–100)."""
        self.progress_bar.setValue(value)

    def set_app_state(self, state: AppState) -> None:
        """Transition to a new application state and notify all widgets."""
        self._app_state = state
        self.app_state_changed.emit(state)

    def _on_action_selected(self, action: Action) -> None:
        if action not in self._panels:
            panel = ActionPanel(
                action=action,
                propagations=self._workflow.propagations,
                all_actions=self._workflow.actions,
                microscope=self._microscope,
                form_builder=self._form_builder,
            )
            self.app_state_changed.connect(panel.on_app_state_changed)
            panel.on_app_state_changed(self._app_state)
            self._panels[action] = panel
            self._stack.addWidget(panel)

        self._stack.setCurrentWidget(self._panels[action])
