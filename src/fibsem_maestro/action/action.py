# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Generic, TypeVar

from fibsem_maestro.action.state import ActionState
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.settings.base_settings import BaseSettings

if TYPE_CHECKING:
    from fibsem_maestro.action_context.action_context import ActionContext
    from fibsem_maestro.core.beam_type import BeamType
    from fibsem_maestro.microscope.microscope import Microscope
    from fibsem_maestro.properties.global_properties import GlobalProperties
    from fibsem_maestro.settings.property_names import PropertyNames
    from fibsem_maestro.store.props.props_store import PropsStore


@abstractmethod
class LinkedActions:
    """Base class for action links."""


TSettings = TypeVar("TSettings", bound=BaseSettings)
TLinkedActions = TypeVar("TLinkedActions", bound=LinkedActions | None)
TState = TypeVar("TState", bound=ActionState)


class Action(ABC, Generic[TSettings, TLinkedActions, TState]):
    @classmethod
    def settings_cls(cls) -> type[BaseSettings]:
        """
        Class of the class used for the action's settings.
        """
        raise NotImplementedError(f"settings_type not implemented for {cls.__name__}")

    @abstractmethod
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: TSettings,
        ctx: ActionContext,
    ):
        """
        Initialize the action.
        """

    @abstractmethod
    def set_state(self, state: TState, links: TLinkedActions) -> None:
        """
        Set the state of the action.
        """

    @abstractmethod
    def execute(self, links: TLinkedActions) -> None:
        """
        Execute the action while providing references to other actions.
        """

    @abstractmethod
    def wait_for_background_threads(self) -> None:
        """
        Wait for ALL background threads spawned by this action to complete.
        """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Name of the action.
        """

    @name.setter
    @abstractmethod
    def name(self, value: str) -> None:
        """
        Set the name of the action.
        """

    @property
    @abstractmethod
    def ctx(self) -> ActionContext:
        """
        Slice navigation and access to all logging and storage resources for this action.
        """

    @property
    @abstractmethod
    def beam_type(self) -> BeamType | None:
        """
        Type of beam this action works with.
        None if the action works with both beams or neither of them.
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
    def external_props(self) -> GlobalProperties:
        """
        External properties of the microscope to use for this action.
        """

    @property
    @abstractmethod
    def settings(self) -> BaseSettings:
        """
        Settings for the action.
        """

    @property
    @abstractmethod
    def state(self) -> ActionState:
        """
        Internal state of the action.
        """

    @property
    def name_with_underscores(self) -> str:
        """
        Name of the action with spaces replaced by underscores.
        """
        return self.name.replace(" ", "_")

    @with_logging_context
    def read_and_set_properties(self, store: PropsStore | None = None) -> None:
        # default: current frame
        store = store or self.ctx.props_store

        self.ctx.text_logger.debug(
            f"Reading and setting microscope properties for {self.name}."
        )
        # read properties
        props = store.read("props.yaml")

        # select the beam used for this action
        if self.beam_type is not None:
            self.microscope.set_beam(self.beam_type)

        # set properties to the microscope
        self.microscope.set_properties(props, beam=self.beam_type)

    @with_logging_context
    def collect_and_write_properties(
        self,
        store: PropsStore | None = None,
    ) -> None:
        """
        Collect and write the properties of the microscope.
        """
        # default: current frame
        store = store or self.ctx.props_store

        self.ctx.text_logger.debug(
            f"Collecting and saving microscope properties for {self.name}."
        )

        # collect the properties from the microscope while respecting external props
        with self.microscope.set_temporary_properties(self.external_props):
            props = self.microscope.collect_properties(self.props_to_collect)

        # write the properties
        store.write("props.yaml", props)

    @with_logging_context
    def read_properties(self, store: PropsStore | None = None) -> GlobalProperties:
        """
        Read properties of the microscope from the properties file.
        """
        store = store or self.ctx.props_store
        return store.read("props.yaml")

    @with_logging_context
    def write_properties(
        self, props: GlobalProperties, store: PropsStore | None = None
    ) -> None:
        """
        Write properties of the microscope to the properties file.
        """
        store = store or self.ctx.props_store
        store.write("props.yaml", props)
