# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING

from fibsem_maestro.autofocus.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofocus.autofunction_context import AutofunctionContext
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from collections.abc import Generator


class Autofunction(Action):
    def __init__(
        self,
        name: str,
        settings: AutofunctionSettings,
        microscope: Microscope,
        imagings: list[Imaging],
        props_store: PropsStore,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._props_store = props_store
        self._txt_log = txt_log
        self._img_log = img_log

        self._microscope = microscope
        self._imagings = imagings

        self._settings = settings

        self._sweeping = Sweeping(
            self._microscope,
            self._settings.sweeping,
            self._txt_log.derive("sweeping"),
        )

        self._criterion = Criterion(
            f"{self._name} criterion",
            self._settings.criterion,
            self._txt_log.derive("criterion"),
            self._img_log,
        )

        self._ctx = AutofunctionContext(
            self._microscope,
            self._sweeping,
            self._criterion,
            self._settings,
            self._txt_log,
        )

        self._jobs = JobsManager(
            executor=ThreadPoolExecutor(self._settings.max_workers),
        )

        self._mode = AutofocusRegistry.get(self._settings.mode.type)()

        self._active_gen: Generator[None, None, None] | None = None

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
    def beam_type(self) -> BeamType:
        return self._settings.beam_type

    @property
    def props_to_collect(self) -> PropertyNames:
        return self._settings.properties_to_collect

    @property
    def microscope(self) -> Microscope:
        return self._microscope

    @property
    def txt_log(self) -> TextLogger:
        return self._txt_log

    def perform_autofocus(
        self, slice_number: int, image_sharpness: float | None
    ) -> None:
        """
        Advance the autofocus execution by one step.

        For single-shot modes (basic, line) this runs to completion on the first
        call. For step mode it advances one sweep step per slice, resuming across
        calls until the sweep is exhausted.

        Args:
            slice_number: The current slice index, used for frequency gating.
            image_sharpness: Optional sharpness metric for threshold gating.
        """
        if self._active_gen is not None:
            # mid-execution: keep going regardless of gating checks
            self._advance()
            return

        if not self._should_execute(slice_number, image_sharpness):
            return

        self.read_and_set_properties()
        self._active_gen = self._mode.execute(self._ctx, self._jobs)
        self._advance()

    def _should_execute(self, slice_number: int, image_sharpness: float | None) -> bool:
        if (
            self._settings.execution_frequency is not None
            and slice_number % self._settings.execution_frequency != 0
        ):
            self._txt_log.info(
                f"Skipping autofunction: slice {slice_number} is not every {self._settings.execution_frequency}-th slice.",
            )
            return False

        if self._settings.sharpness_limit is not None:
            if image_sharpness is None:
                self._txt_log.info(
                    "Skipping autofunction: sharpness limit is set but image sharpness is unavailable."
                )
                return False
            if image_sharpness >= self._settings.sharpness_limit:
                self._txt_log.info(
                    f"Skipping autofunction: image sharpness {image_sharpness} is above limit {self._settings.sharpness_limit}.",
                )
                return False

        return True

    def _advance(self) -> None:
        assert self._active_gen is not None
        try:
            next(self._active_gen)
        except StopIteration:
            results = self._jobs.wait_and_collect()
            best = self._sweeping.evaluate_best_sweep(results)

            # update the associated imagings based on the autofocus results
            for imaging in self._imagings:
                self._txt_log.debug(
                    f"Updating microscope properties for '{imaging.name}'."
                )
                props = imaging.read_properties()
                props.set_property(
                    self._sweeping.sweep_attribute, best, imaging.beam_type
                )
                imaging.write_properties(props)

            # TODO: should we also update the autofocus for the following slice?

            self._active_gen = None
        except Exception:
            self._active_gen.close()
            self._active_gen = None
            raise
