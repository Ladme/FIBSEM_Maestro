# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.adjust_props_settings import AdjustPropsSettings
from fibsem_maestro.settings.property_names import PropertyNames

if TYPE_CHECKING:
    from fibsem_maestro.properties.beam_properties import BeamProperties
    from fibsem_maestro.properties.microscope_properties import MicroscopeProperties


class AdjustPropsState(ActionState):
    pass


@ACTION_REGISTRY.register("adjust_props")
class AdjustProps(Action[AdjustPropsSettings, None, AdjustPropsState]):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AdjustPropsSettings,
        ctx: ActionContext,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx

    @classmethod
    def settings_cls(cls) -> type[AdjustPropsSettings]:
        return AdjustPropsSettings

    @classmethod
    def state_cls(cls) -> type[AdjustPropsState]:
        return AdjustPropsState

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def name_with_underscores(self) -> str:
        return self._name.replace(" ", "_")

    @property
    def beam_type(self) -> BeamType | None:
        return None

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def external_props(self) -> GlobalProperties:
        return GlobalProperties()

    @property
    def settings(self) -> AdjustPropsSettings:
        return self._settings

    @property
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def state(self) -> AdjustPropsState:
        # AdjustProps action has no persistent internal state
        return AdjustPropsState()

    def set_state(self, state: AdjustPropsState, links: None = None) -> None:
        _ = state, links

    @with_logging_context
    def execute(self, links: None = None) -> None:
        _ = links

        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (self._ctx.slice - 1) % self._settings.execution_frequency != 0
        ):
            self._ctx.text_logger.info(
                f"Skipping '{self.name}' for slice {self._ctx.slice}."
            )
            # even if adjusting is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._ctx.props_store.next)
            return

        # set the properties of the microscope
        self.read_and_set_properties()

        # get the relevant properties of the microscope
        props = self.microscope.collect_properties(
            self._settings.properties_to_adjust.get_property_names()
        )

        # adjust the old properties
        for beam_type in [BeamType.ELECTRON, BeamType.ION, None]:
            beam_props: BeamProperties | MicroscopeProperties | None = getattr(
                self._settings.properties_to_adjust,
                self._settings.properties_to_adjust.get_properties_attr_name(beam_type),
            )
            if beam_props is None:
                continue

            for field_name in beam_props.model_fields:
                value = getattr(beam_props, field_name)
                if value is None:
                    continue

                self._ctx.text_logger.debug(
                    f"Adjusting property '{field_name}' by '{value}' on beam '{beam_type}'."
                )
                props.accumulate_property(field_name, value, beam_type)

        # set the updated properties
        self.microscope.set_properties(props, None)

        # update the microscope properties for the next frame
        self.collect_and_write_properties(self._ctx.props_store.next)

    def wait_for_background_threads(self) -> None:
        # no background threads to wait for
        pass
