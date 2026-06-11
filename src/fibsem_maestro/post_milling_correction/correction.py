# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from dataclasses import dataclass

import numpy as np

from fibsem_maestro.action.action import Action, LinkedActions
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.core.beam_shift import BeamShift
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.direction import Direction
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.milling.milling import Milling
from fibsem_maestro.post_milling_correction.error import PostMillingCorrectionError
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.milling_settings import MillingSettings
from fibsem_maestro.settings.post_milling_correction_settings import (
    DynamicFocusMode,
    ManualMode,
    PostMillingCorrectionSettings,
)
from fibsem_maestro.settings.property_names import PropertyNames


@dataclass
class LinkedToPostMillingCorrection(LinkedActions):
    milling: Milling


class PostMillingCorrectionState(ActionState):
    pass


@ACTION_REGISTRY.register("post_milling_correction")
class PostMillingCorrection(
    Action[
        PostMillingCorrectionSettings,
        LinkedToPostMillingCorrection,
        PostMillingCorrectionState,
    ]
):
    """
    Corrects sample drift between slices by applying a compensating beam shift.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: PostMillingCorrectionSettings,
        ctx: ActionContext,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx

    @classmethod
    def settings_cls(cls) -> type[PostMillingCorrectionSettings]:
        """
        Class of the class used for the action's settings.
        """
        return PostMillingCorrectionSettings

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def beam_type(self) -> BeamType | None:
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    @property
    def settings(self) -> PostMillingCorrectionSettings:
        return self._settings

    @property
    def name_with_underscores(self) -> str:
        return self.name.replace(" ", "_")

    @property
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def state(self) -> PostMillingCorrectionState:
        # post milling correction has no persistent internal state
        return PostMillingCorrectionState()

    @with_logging_context
    def execute(self, links: LinkedToPostMillingCorrection | None = None) -> None:
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (self._ctx.slice - 1) % self._settings.execution_frequency != 0
        ):
            self._ctx.text_logger.info(
                f"Skipping {self.name} for slice {self._ctx.slice}."
            )
            # even if correction is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._ctx.props_store.next)
            return

        # set the properties of the microscope
        self.read_and_set_properties()

        match self._settings.correction_mode:
            case ManualMode() as mode:
                self._perform_manual_correction(mode)
            case DynamicFocusMode():
                if links is None:
                    raise PostMillingCorrectionError("Link to Milling not specified.")
                milling_settings = links.milling.settings

                self._perform_automatic_correction(milling_settings)

        # update the microscope properties for the next frame
        self.collect_and_write_properties(self._ctx.props_store.next)

    def _perform_manual_correction(self, mode: ManualMode) -> None:
        self._ctx.text_logger.info(
            f"Performing manual post milling correction: y_correction={mode.y_correction}, wd_correction={mode.wd_correction}."
        )

        self._microscope.add_beam_shift_with_verification(
            delta=BeamShift(0, mode.y_correction)
        )
        self._microscope.beam.working_distance += mode.wd_correction

    def _perform_automatic_correction(self, milling_settings: MillingSettings) -> None:
        # y_correction = cos 52° * slice_distance
        y_correction = float(np.cos(0.9076) * milling_settings.slice_distance)

        # wd correction = sqrt( slice_distance^2 - y_correction^2 )
        wd_correction = float(
            np.sqrt(milling_settings.slice_distance**2 - y_correction**2)
        )

        # we are milling up, so y_correction and wd_correction need to be inverted
        if milling_settings.milling_direction is Direction.UP:
            y_correction = -y_correction
            wd_correction = -wd_correction

        self._ctx.text_logger.info(
            f"Performing automatic post milling correction: y_correction={y_correction}, wd_correction={wd_correction} "
            f"based on slice_distance={milling_settings.slice_distance} and direction={milling_settings.milling_direction}."
        )

        self._microscope.add_beam_shift_with_verification(
            delta=BeamShift(0, y_correction)
        )
        self._microscope.beam.working_distance += wd_correction
