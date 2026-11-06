# Released under GPL-3.0 License.
# Copyright (c) 2024-2026 CEMCOF

from typing import TYPE_CHECKING, Annotated, Literal

from pydantic import Field

from fibsem_maestro.action.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.frequency import Every, Frequency
from fibsem_maestro.milling.milling import Milling
from fibsem_maestro.settings.base_settings import BaseSettings
from fibsem_maestro.settings.form_utils import FieldUnit, FormHint, WidgetType
from fibsem_maestro.settings.property_names import PropertyNames

if TYPE_CHECKING:
    from fibsem_maestro.core.beam_type import BeamType


class ManualMode(BaseSettings):
    type: Literal["manual"] = Field(
        default="manual",
        description="Shifts the image and working distance by fixed amounts.",
    )
    y_correction: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="Vertical image shift added to the corrected actions on every run.",
    )
    wd_correction: Annotated[float, FieldUnit(suffix="nm")] = Field(
        default=0.0,
        description="Working-distance change added to the corrected actions on every run.",
    )


class DynamicFocusMode(BaseSettings):
    """
    Shifts computed from the linked milling's slice distance.

    The geometry is that of electron-beam images of the cross-section face,
    with the ion beam at 52° to the electron beam; the corrected actions are
    assumed to image with the electron beam.
    """

    type: Literal["dynamic_focus"] = Field(
        default="dynamic_focus",
        description="Computes the shifts from the linked milling's slice distance.",
    )


PostMillingCorrectionMode = Annotated[
    ManualMode | DynamicFocusMode, Field(discriminator="type")
]


class PostMillingCorrectionSettings(BaseSettings):
    """
    Settings of the post-milling correction.

    The correction stores no microscope properties of its own and works on no
    beam of its own: it adds its shifts to the upcoming properties of the
    corrected actions, each on its own beam.
    """

    linked_milling: Annotated[
        str, FormHint(widget=WidgetType.ACTION_SELECTOR, action_type_filter=[Milling])
    ] = Field(default="", description="Milling linked to this post-milling correction.")
    corrected_actions: Annotated[
        list[str],
        FormHint(
            widget=WidgetType.MULTI_ACTION_SELECTOR,
            action_type_filter=[Action],
        ),
    ] = Field(
        default_factory=list,
        description="Actions whose image position and working distance follow the "
        "receding cross-section face.",
    )
    correction_mode: PostMillingCorrectionMode = Field(
        default_factory=ManualMode,
        description="Mode of post milling correction to use.",
    )
    execution_frequency: Frequency = Field(
        default_factory=Every,
        description="How often the action runs",
    )

    @property
    def beam_type(self) -> BeamType | None:
        """
        None: every corrected action is corrected on its own beam.

        So the action never selects a beam on the microscope.
        """
        return None

    @property
    def properties_to_collect(self) -> PropertyNames:
        """
        Nothing: the correction changes the corrected actions' properties, not the microscope.

        Stored properties of its own would only be applied before every run,
        imposing stale values on the microscope.
        """
        return PropertyNames()
