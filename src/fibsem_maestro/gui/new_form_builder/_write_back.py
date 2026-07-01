# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.action.action import Action
from fibsem_maestro.gui.new_form_builder.schema.field_info import FieldInfo
from fibsem_maestro.gui.new_form_builder.widgets.base import BaseWidget
from fibsem_maestro.gui.workflow_manager import WorkflowManager
from fibsem_maestro.settings.base_settings import BaseSettings


class WriteBack:
    """
    The single write-back for one top-level field.

    Threaded through the field's subtree as `on_change`. On any change it
    reassigns the whole field on the reactive root from the field widget's
    current value; a transiently-invalid value is dropped (whole-unit
    validation) so the field simply keeps its last valid value.

    The widget is bound after the subtree is built, since the callback must
    already exist while the subtree (and its dynamic children) is constructed.
    """

    def __init__(
        self,
        settings: BaseSettings,
        fi: FieldInfo,
        manager: WorkflowManager,
        action: Action | None,
    ) -> None:
        self._settings = settings
        self._fi = fi
        self._manager = manager
        self._action = action
        self._widget: BaseWidget | None = None

    def bind(self, widget: BaseWidget) -> None:
        """Attach the field widget this write-back reads from."""
        self._widget = widget

    def __call__(self) -> None:
        if self._widget is None:
            return

        try:
            setattr(self._settings, self._fi.name, self._widget.get_value())
        except Exception:
            # whole-unit validation failure: leave the field unchanged
            print("Unit validation failed.")
            return

        # exactly one write per edit, so the side effect also fires once
        if self._action is not None:
            self._manager.action_changed.emit(self._action)
