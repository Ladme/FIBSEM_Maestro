# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.outcome import Produced, StepOutcome
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.adjust.error import AdjustPropsError
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.adjust_props_settings import AdjustPropsSettings
from fibsem_maestro.workflow.actions import Actions

if TYPE_CHECKING:
    from fibsem_maestro.properties.beam_properties import BeamProperties
    from fibsem_maestro.properties.microscope_properties import MicroscopeProperties


class AdjustPropsState(ActionState):
    pass


@ACTION_REGISTRY.register("adjust_props")
class AdjustProps(Action[AdjustPropsSettings, AdjustPropsState]):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AdjustPropsSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        super().__init__(name, microscope, settings, ctx, actions)

    @classmethod
    def settings_cls(cls) -> type[AdjustPropsSettings]:
        return AdjustPropsSettings

    @classmethod
    def state_cls(cls) -> type[AdjustPropsState]:
        return AdjustPropsState

    @property
    def state(self) -> AdjustPropsState:
        # AdjustProps action has no persistent internal state
        return AdjustPropsState()

    def set_state(self, state: AdjustPropsState) -> None:
        _ = state

    def _run_step(self) -> StepOutcome:
        adjustments = self._settings.properties_to_adjust
        names = adjustments.get_property_names()

        # `accumulate_property` treats a missing current value as zero and would
        # set the offset as an absolute value (a +10 nm WD offset becoming WD = 10 nm);
        # `select` raises if the microscope did not report every adjusted property
        try:
            props = self._microscope.collect_properties(names).select(names)
        except KeyError as e:
            raise AdjustPropsError(
                f"Cannot adjust properties the microscope did not report: {e}"
            ) from e

        for beam_type in (BeamType.ELECTRON, BeamType.ION, None):
            offsets: BeamProperties | MicroscopeProperties | None = getattr(
                adjustments, adjustments.get_properties_attr_name(beam_type)
            )
            if offsets is None:
                continue

            for name in offsets.get_property_names():
                value = getattr(offsets, name)
                self._ctx.text_logger.debug(
                    f"Adjusting property '{name}' by '{value}' on beam '{beam_type}'."
                )
                props.accumulate_property(name, value, beam_type)

        self._microscope.set_properties(props, beam=None)
        return Produced(self.collect_properties())

    def test(self) -> None:
        raise AdjustPropsError(f"Testing is not implemented for {self.name}")
