# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from fibsem_maestro.core.action import Action
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_props import GlobalProperties
from fibsem_maestro.settings.state import (
    StateControlSettings,
    StateSettings,
)
from fibsem_maestro.state.error import StateError
from fibsem_maestro.store.props.props_store import PropsStore


class State:
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: StateSettings,
        props_store: PropsStore,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self.name = name
        self.props_store = props_store
        self._microscope = microscope
        self._settings = settings
        self._txt_log = txt_log
        self._img_log = img_log

        self._properties: GlobalProperties = GlobalProperties()

    def load_and_write(self, store: PropsStore | None = None) -> None:
        self.load()
        self.write(store)

    def read_and_set(self, store: PropsStore | None = None) -> None:
        self.read(store)
        self.set()

    def read_and_write(self, src: PropsStore | None, dst: PropsStore | None) -> None:
        self.read(src)
        self.write(dst)

    def load(self) -> None:
        self._txt_log.debug(
            f"Loading microscope properties from the microscope for state '{self.name}'."
        )

        self._state = self._microscope.collect_properties(
            self._settings.properties_to_collect
        )

    def set(self) -> None:
        self._txt_log.debug(
            f"Setting microscope properties to the microscope for state '{self.name}'."
        )

        self._microscope.set_properties(self._state, beam=None)

    def read(self, store: PropsStore | None = None) -> None:
        store = store or self.props_store

        self._txt_log.debug(
            f"Reading microscope properties from the state store for state '{self.name}'."
        )

        self._state = store.read(self._settings.props_file)

    def write(self, store: PropsStore | None = None) -> None:
        store = store or self.props_store

        self._txt_log.debug(
            f"Writing microscope properties to the state store for state '{self.name}'."
        )

        store.write(self._settings.props_file, self._state)

    def propagate_to_next(self, store: PropsStore | None = None) -> None:
        src = store or self.props_store
        self._txt_log.debug(
            f"Propagating state '{self.name}' from slice {src.slice} to slice {src.next.slice}."
        )

        self.read_and_write(src, src.next)


class StateControl(Action):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: StateControlSettings,
        states: list[State],
        txt_log: TextLogger,
    ):
        self._name = name
        self._microscope = microscope
        self._txt_log = txt_log

        self._state = next((x for x in states if x.name == settings.state), None)
        if self._state is None:
            raise StateError(f"State '{settings.state}' not found.")

    @property
    def name(self) -> str:
        return self._name


class RestoreState(StateControl):
    def execute(self, slice_number: int) -> None:
        _ = slice_number
        assert self._state is not None
        self._txt_log.info(f"Restoring microscope to state '{self._state.name}'.")
        self._state.read_and_set()


class SaveState(StateControl):
    def execute(self, slice_number: int) -> None:
        _ = slice_number
        assert self._state is not None
        self._txt_log.info(
            f"Saving current microscope properties to state '{self._state.name}'."
        )
        self._state.load_and_write()
