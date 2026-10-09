# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Callable

from PyQt6.QtCore import Qt, QThread
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_panel._call_worker import CallWorker
from fibsem_maestro.gui.action_panel._icon_button import (
    ICON_APPLY,
    ICON_EDIT,
    ICON_PREPARE,
    ICON_TEST,
    IconButton,
)
from fibsem_maestro.gui.action_panel._propagations_widget import PropagationsWidget
from fibsem_maestro.gui.action_panel._props_dialog import PropertiesDialog
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.common import class_name_to_label
from fibsem_maestro.gui.form_builder.builder import FormBuilder
from fibsem_maestro.gui.form_builder.widgets.object import ObjectWidget
from fibsem_maestro.gui.workflow_manager import WorkflowManager

_EDITABLE_STATES: frozenset[AppState] = frozenset(
    {
        AppState.EDITING,
        AppState.PAUSED,
        AppState.RELOADED,
        AppState.FINISHED,
        AppState.INTERRUPTED,
    }
)


class ActionPanel(QWidget):
    """
    A scrollable panel for editing a single Action's settings.

    Binds directly to a live Action instance. The settings form is
    pre-populated from action.settings and writes back to it reactively
    on every change. The propagations section mutates the Propagations
    manager directly. The header holds tool buttons for capturing, editing,
    and applying the action's stored properties for its current slice, and
    for testing the action.
    """

    def __init__(
        self,
        action: Action,
        workflow_manager: WorkflowManager,
        form_builder: FormBuilder,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._action = action
        self._manager = workflow_manager
        self._txt_log = self._manager.workflow.ctx.text_logger
        self._form_builder = form_builder

        # the running worker-thread task, if any
        self._task_thread: QThread | None = None
        self._task_worker: CallWorker | None = None
        self._task_description = ""
        self._task_on_success: Callable[[], None] | None = None
        self._task_failed = False

        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
                QWidget[dataclass_form="true"] QWidget[highlighted="true"] {
                    border: 1px solid #346792;
                    border-radius: 3px;
                }
            """)
        outer_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)

        layout.addWidget(self._build_header(action))

        # settings
        self._settings_widget = self._form_builder.build_form(
            action.settings,
            self._manager,
            txt_log=self._txt_log,
            fields=None,
            action=self._action,
        )
        layout.addWidget(self._settings_widget)

        # propagations
        self._propagations_widget = PropagationsWidget(
            current_action=action,
            workflow_manager=self._manager,
        )
        layout.addWidget(self._propagations_widget)

        layout.addStretch()

        # sets read-only state of the form, propagations and buttons
        self.on_app_state_changed(self._manager.state)

    def _build_header(self, action: Action) -> QFrame:
        """
        Build the header: name, type and beam labels, with the tool buttons beside them.

        Args:
            action: The action shown in the panel.

        Returns:
            The header frame.
        """
        title_frame = QFrame()
        title_frame.setFrameShape(QFrame.Shape.StyledPanel)
        header_layout = QHBoxLayout(title_frame)
        header_layout.setContentsMargins(8, 6, 8, 6)
        header_layout.setSpacing(0)

        labels_layout = QVBoxLayout()
        labels_layout.setSpacing(2)

        self._name_label = QLabel(action.name)
        self._name_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        labels_layout.addWidget(self._name_label)

        self._type_label = QLabel(
            f"   > type: {class_name_to_label(type(action).__name__)}"
        )
        self._type_label.setStyleSheet("font-size: 11px; color: #888888;")
        labels_layout.addWidget(self._type_label)

        self._beam_label = QLabel(self._beam_text(action))
        self._beam_label.setStyleSheet("font-size: 11px; color: #888888")
        labels_layout.addWidget(self._beam_label)

        self._prepare_btn = IconButton(
            ICON_PREPARE,
            "<b>Prepare</b><br>"
            "Capture the action's properties from the microscope and store them "
            "for the current slice, replacing any stored ones. Some actions do "
            "more, e.g. drift correction also acquires its reference templates.<br>"
            "<i>Microscope -> stored properties</i>",
            "Prepare action",
        )
        self._edit_btn = IconButton(
            ICON_EDIT,
            "<b>Edit</b><br>"
            "View and edit the properties stored for the current slice.<br>"
            "Unavailable until properties are stored.",
            "Edit properties",
        )
        self._apply_btn = IconButton(
            ICON_APPLY,
            "<b>Apply</b><br>"
            "Set the properties stored for the current slice on the microscope.<br>"
            "<i>Stored properties -> microscope</i><br>"
            "Unavailable until properties are stored.",
            "Apply properties",
        )
        self._test_btn = IconButton(
            ICON_TEST,
            "<b>Test</b><br>"
            "Run the action once outside the acquisition, using the stored "
            "properties if there are any.",
            "Test action",
        )
        self._prepare_btn.clicked.connect(self._prepare_action)
        self._edit_btn.clicked.connect(self._edit_properties)
        self._apply_btn.clicked.connect(self._apply_properties)
        self._test_btn.clicked.connect(self._test_action)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)
        for btn in (self._prepare_btn, self._edit_btn, self._apply_btn, self._test_btn):
            buttons_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)

        header_layout.addLayout(labels_layout)
        header_layout.addSpacing(50)
        header_layout.addLayout(buttons_layout)
        header_layout.addStretch(1)

        return title_frame

    @staticmethod
    def _beam_text(action: Action) -> str:
        """
        Header text describing the action's beam.

        Args:
            action: The action shown in the panel.

        Returns:
            The beam label text.
        """
        beam = str(action.beam_type) if action.beam_type is not None else "—"
        return f"   > beam: {beam}"

    def _update_buttons(self) -> None:
        """Enable the header buttons according to app state, running task and stored props."""
        idle = self._manager.state in _EDITABLE_STATES and self._task_thread is None
        has_props = idle and self._action.has_stored_properties()

        self._prepare_btn.setEnabled(idle)
        self._edit_btn.setEnabled(has_props)
        self._apply_btn.setEnabled(has_props)
        self._test_btn.setEnabled(idle)

    def _prepare_action(self) -> None:
        """Prepare the action on a worker thread."""
        self._start_task(
            self._action.prepare,
            f"Preparing '{self._action.name}'",
            on_success=lambda: self._manager.notify_action_changed(self._action),
        )

    def _edit_properties(self) -> None:
        """Open the stored properties of the current slice for editing."""
        # the file may have disappeared since the buttons were last updated
        if not self._action.has_stored_properties():
            self._update_buttons()
            return

        try:
            props = self._action.read_properties()
        except Exception as e:
            self._action.ctx.text_logger.error(
                f"Reading properties for '{self._action.name}' failed: {e}"
            )
            return

        edited = PropertiesDialog.review(
            properties=props,
            workflow_manager=self._manager,
            txt_log=self._action.ctx.text_logger,
            title=f"Properties of '{self._action.name}'",
            hint=(
                f"Properties stored for slice {self._action.ctx.slice}. "
                "Edit them if needed, then save."
            ),
            parent=self,
        )
        if edited is None:
            return

        try:
            self._action.write_properties(edited)
        except Exception as e:
            self._action.ctx.text_logger.error(
                f"Saving properties for '{self._action.name}' failed: {e}"
            )
            return

        self._manager.notify_action_changed(self._action)

    def _apply_properties(self) -> None:
        """Set the stored properties of the current slice on the microscope, on a worker thread."""
        # the file may have disappeared since the buttons were last updated
        if not self._action.has_stored_properties():
            self._update_buttons()
            return

        self._start_task(
            self._action.read_and_set_properties,
            f"Applying properties of '{self._action.name}'",
        )

    def _test_action(self) -> None:
        """Test the action on a worker thread."""
        self._start_task(self._action.test, f"Testing '{self._action.name}'")

    def _start_task(
        self,
        fn: Callable[[], None],
        description: str,
        on_success: Callable[[], None] | None = None,
    ) -> None:
        """
        Run a microscope task on a worker thread; at most one runs at a time.

        Args:
            fn: The task to run.
            description: Human-readable description, for error messages.
            on_success: Called on the GUI thread if the task did not raise.
        """
        if self._task_thread is not None:
            return

        thread = QThread()
        worker = CallWorker(fn)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.finished.connect(thread.quit)
        # bound methods of this panel run on the GUI thread (queued connections)
        worker.error.connect(self._on_task_failed)
        thread.finished.connect(self._on_task_finished)

        self._task_thread = thread
        self._task_worker = worker
        self._task_description = description
        self._task_on_success = on_success
        self._task_failed = False

        self._action.ctx.text_logger.info(f"{description}...")
        self._update_buttons()
        thread.start()

    def _on_task_failed(self, error: Exception) -> None:
        """
        Log a failed task.

        Args:
            error: The exception raised by the task.
        """
        self._task_failed = True
        self._action.ctx.text_logger.error(f"{self._task_description} failed: {error}")

    def _on_task_finished(self) -> None:
        """Release the finished task and run its success callback."""
        assert self._task_thread is not None
        # `finished` is emitted just before the thread exits; wait so that
        # dropping the last reference cannot destroy a still-running QThread
        self._task_thread.wait()

        if not self._task_failed:
            self._action.ctx.text_logger.info(f"{self._task_description} completed.")

        on_success = None if self._task_failed else self._task_on_success
        self._task_thread = None
        self._task_worker = None
        self._task_on_success = None

        if on_success is not None:
            on_success()
        self._update_buttons()

    def on_app_state_changed(self, state: AppState) -> None:
        """
        Update read-only state and buttons for a new app state.

        Args:
            state: The new app state.
        """
        read_only = state not in _EDITABLE_STATES
        self._settings_widget.set_read_only(read_only)
        self._propagations_widget.set_read_only(read_only)
        # the slice, and with it the props file, may have changed while running
        self._update_buttons()

    def on_action_changed(self, action: Action) -> None:
        """
        Refresh the header if the changed action is the one shown.

        Args:
            action: The action that changed.
        """
        if self._action is action:
            self._name_label.setText(action.name)
            self._beam_label.setText(self._beam_text(action))
            self._update_buttons()

    def has_form_errors(self) -> bool:
        """
        Check whether any field of the settings form shows an error.

        An erroneous value is not written to the settings, so the form and the
        settings disagree until it is fixed.

        Returns:
            True if a field of the form, at any depth, reports an error.
        """
        forms = [
            child
            for child in [
                self._settings_widget,
                *self._settings_widget.findChildren(ObjectWidget),
            ]
            if isinstance(child, ObjectWidget)
        ]

        return any(form.has_errors() for form in forms)

    def reload_values(self) -> None:
        """
        Re-read every field from the live settings, leaving the form intact.
        """
        self._settings_widget.set_value(self._action.settings)
