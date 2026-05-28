# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from typing import TYPE_CHECKING

from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.adjust_props_settings import AdjustPropsSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from fibsem_maestro.properties.beam_properties import BeamProperties
    from fibsem_maestro.properties.microscope_properties import MicroscopeProperties


class AdjustProps(Action):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AdjustPropsSettings,
        props_store: PropsStore,
        txt_log: TextLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._props_store = props_store
        self._txt_log = txt_log

    @property
    def name(self) -> str:
        return self._name

    @property
    def name_with_underscores(self) -> str:
        return self._name.replace(" ", "_")

    @property
    def props_file(self) -> str:
        return str(self._settings.properties_file)

    @property
    def props_store(self) -> PropsStore:
        return self._props_store

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
    def txt_log(self) -> TextLogger:
        return self._txt_log

    @property
    def external_props(self) -> GlobalProperties:
        return GlobalProperties()

    def execute(self, slice_number: int) -> None:
        if (
            self._settings.execution_frequency is None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            or (slice_number - 1) % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(f"Skipping '{self.name}' for slice {slice_number}.")
            # even if adjusting is skipped, we need to write properties for the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
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

                self._txt_log.debug(
                    f"Adjusting property '{field_name}' by '{value}' on beam '{beam_type}'."
                )
                props.accumulate_property(field_name, value, beam_type)

        # set the updated properties
        self.microscope.set_properties(props, None)

        # update the microscope properties for the next frame
        self.collect_and_write_properties(self._props_store.next)
