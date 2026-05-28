# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from abc import ABC, abstractmethod

from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore


class Action(ABC):
    @abstractmethod
    def execute(self, slice_number: int) -> None:
        """
        Execute the action on the given slice.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the action.
        """

    @property
    @abstractmethod
    def props_file(self) -> str:
        """
        Name of the file where microscope properties are stored for this action.
        """

    @property
    @abstractmethod
    def props_store(self) -> PropsStore:
        """
        Props store for the action.
        """

    @property
    @abstractmethod
    def beam_type(self) -> BeamType:
        """
        Type of beam this action works with.
        """

    @property
    @abstractmethod
    def props_to_collect(self) -> PropertyNames:
        """
        Names of properties that should be collected for this action.
        """

    @property
    @abstractmethod
    def microscope(self) -> Microscope:
        """
        Current microscope instance.
        """

    @property
    @abstractmethod
    def txt_log(self) -> TextLogger:
        """
        Text logger instance.
        """

    @property
    @abstractmethod
    def external_props(self) -> GlobalProperties:
        """
        External properties of the microscope to use for this action.
        """

    @property
    def name_with_underscores(self) -> str:
        """
        Name of the action with spaces replaced by underscores.
        """
        return self.name.replace(" ", "_")

    def read_and_set_properties(self, store: PropsStore | None = None) -> None:
        # default: current frame
        store = store or self.props_store

        self.txt_log.debug(
            f"Reading and setting microscope properties for {self.name}."
        )
        # read properties
        props = store.read(self.props_file)

        # select the beam used for this action
        self.microscope.set_beam(self.beam_type)

        # set properties to the microscope
        self.microscope.set_properties(props, beam=self.beam_type)

    def collect_and_write_properties(
        self,
        store: PropsStore | None = None,
    ) -> None:
        """
        Collect and write the properties of the microscope.
        """
        # default: current frame
        store = store or self.props_store

        self.txt_log.debug(
            f"Collecting and saving microscope properties for {self.name}."
        )

        # collect the properties from the microscope while respecting external props
        with self.microscope.set_temporary_properties(self.external_props):
            props = self.microscope.collect_properties(self.props_to_collect)

        # write the properties
        store.write(self.props_file, props)

    def read_properties(self, store: PropsStore | None = None) -> GlobalProperties:
        """
        Read properties of the microscope from the properties file.
        """
        store = store or self.props_store
        return store.read(self.props_file)

    def write_properties(
        self, props: GlobalProperties, store: PropsStore | None = None
    ) -> None:
        """
        Write properties of the microscope to the properties file.
        """
        store = store or self.props_store
        store.write(self.props_file, props)
