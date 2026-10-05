# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from collections.abc import Callable

from PyQt6.QtCore import QSize, Qt, QThread
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.action_panel._action_test_worker import ActionTestWorker
from fibsem_maestro.gui.action_panel._icon_button import (
    ICON_APPLY,
    ICON_CAPTURE,
    ICON_EDIT,
    ICON_TEST,
    IconButton,
)
from fibsem_maestro.gui.action_panel._propagations_widget import PropagationsWidget
from fibsem_maestro.gui.action_panel._props_dialog import PropertiesDialog
from fibsem_maestro.gui.app_state import AppState
from fibsem_maestro.gui.common import class_name_to_label
from fibsem_maestro.gui.form_builder.builder import FormBuilder
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

        self._test_thread: QThread | None = None
        self._test_worker: ActionTestWorker | None = None

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

        # header: labels, then the tool buttons right next to them
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

        self._capture_btn = IconButton(
            ICON_CAPTURE,
            "<b>Capture</b><br>"
            "Read the action's properties from the microscope and store them "
            "for the current slice, replacing any stored ones.<br>"
            "<i>Microscope -> stored properties</i>",
            "Capture properties",
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
        self._capture_btn.clicked.connect(self._capture_properties)
        self._edit_btn.clicked.connect(self._edit_properties)
        self._apply_btn.clicked.connect(self._apply_properties)
        self._test_btn.clicked.connect(self._test_action)

        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(4)
        for btn in (self._capture_btn, self._edit_btn, self._apply_btn, self._test_btn):
            buttons_layout.addWidget(btn, 0, Qt.AlignmentFlag.AlignVCenter)

        header_layout.addLayout(labels_layout)
        header_layout.addSpacing(50)
        header_layout.addLayout(buttons_layout)
        header_layout.addStretch(1)

        layout.addWidget(title_frame)

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

        self.on_app_state_changed(self._manager.state)

    def _make_header_button(
        self,
        pixmap: QStyle.StandardPixmap,
        accessible_name: str,
        tooltip: str,
        slot: Callable[[], None],
    ) -> QToolButton:
        """
        Create an icon-only tool button for the header.

        Args:
            pixmap: Standard style icon for the button.
            accessible_name: Name announced by screen readers.
            tooltip: Help text shown on hover (rich text).
            slot: Called when the button is clicked.

        Returns:
            The configured button.
        """
        btn = QToolButton()
        btn.setIcon(self.style().standardIcon(pixmap))
        btn.setIconSize(QSize(20, 20))
        btn.setAutoRaise(True)
        btn.setToolTip(tooltip)
        btn.setAccessibleName(accessible_name)
        btn.clicked.connect(slot)
        return btn

    def _update_buttons(self) -> None:
        """Enable the header buttons according to app state, test state and stored props."""
        idle = self._manager.state in _EDITABLE_STATES and not self._test_running()
        has_props = idle and self._action.has_stored_properties()

        self._capture_btn.setEnabled(idle)
        self._edit_btn.setEnabled(has_props)
        self._apply_btn.setEnabled(has_props)
        self._test_btn.setEnabled(idle)

    def _test_running(self) -> bool:
        """Whether a test of this action is currently running."""
        return self._test_thread is not None and self._test_thread.isRunning()

    def _capture_properties(self) -> None:
        """Collect the action's properties from the microscope and store them."""
        try:
            props = self._action.collect_properties()
            self._action.write_properties(props)
        except Exception as e:
            self._txt_log.error(
                f"Capturing properties for '{self._action.name}' failed: {e}"
            )
            return

        self._txt_log.info(
            f"Captured properties for '{self._action.name}' "
            f"(slice {self._action.ctx.slice})."
        )
        self._manager.notify_action_changed(self._action)
        self._update_buttons()

    def _edit_properties(self) -> None:
        """Open the stored properties of the current slice for editing."""
        # the file may have disappeared since the buttons were last updated
        if not self._action.has_stored_properties():
            self._update_buttons()
            return

        try:
            props = self._action.read_properties()
        except Exception as e:
            self._txt_log.error(
                f"Reading properties for '{self._action.name}' failed: {e}"
            )
            return

        edited = PropertiesDialog.review(
            properties=props,
            workflow_manager=self._manager,
            txt_log=self._txt_log,
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
            self._txt_log.error(
                f"Saving properties for '{self._action.name}' failed: {e}"
            )
            return

        self._manager.notify_action_changed(self._action)

    def _apply_properties(self) -> None:
        """Set the stored properties of the current slice on the microscope."""
        if not self._action.has_stored_properties():
            self._update_buttons()
            return

        try:
            self._action.read_and_set_properties()
        except Exception as e:
            self._txt_log.error(
                f"Applying properties for '{self._action.name}' failed: {e}"
            )
            return

        self._txt_log.info(
            f"Applied properties of '{self._action.name}' "
            f"(slice {self._action.ctx.slice}) to the microscope."
        )

    def _test_action(self) -> None:
        """Run the action's test on a worker thread."""
        # prevent overlapping runs
        if self._test_running():
            return

        self._test_thread = QThread()
        self._test_worker = ActionTestWorker(self._action)
        self._test_worker.moveToThread(self._test_thread)

        self._test_thread.started.connect(self._test_worker.run)
        self._test_worker.finished.connect(self._test_thread.quit)
        self._test_worker.finished.connect(self._test_worker.deleteLater)
        self._test_worker.finished.connect(lambda: setattr(self, "_test_worker", None))
        self._test_thread.finished.connect(self._test_thread.deleteLater)
        self._test_thread.finished.connect(lambda: setattr(self, "_test_thread", None))
        # connected after the reset above, so the buttons see the thread as gone
        self._test_thread.finished.connect(self._update_buttons)
        self._test_worker.error.connect(
            lambda e: self._action.ctx.text_logger.error(f"Test failed: {e}")
        )

        self._test_thread.start()
        self._update_buttons()

    def on_app_state_changed(self, state: AppState) -> None:
        read_only = state not in _EDITABLE_STATES
        self._settings_widget.set_read_only(read_only)
        self._propagations_widget.set_read_only(read_only)
        # the slice, and with it the props file, may have changed while running
        self._update_buttons()

    def on_action_changed(self, action: Action) -> None:
        if self._action is action:
            self._name_label.setText(action.name)
            self._beam_label.setText(self._beam_text(action))
            self._update_buttons()

    def reload_values(self) -> None:
        """
        Re-read every field from the live settings, leaving the form intact.
        """
        self._settings_widget.set_value(self._action.settings)

    @staticmethod
    def _beam_text(action: Action) -> str:
        """Header text describing the action's beam."""
        return f"   > beam: {str(action.beam_type) if action.beam_type is not None else '—'}"
