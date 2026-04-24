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
from fibsem_maestro.settings.autofunction_settings import (
    AutofunctionSettings,
    AutoscriptMode,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from collections.abc import Generator


class Autofunction(Action):
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AutofunctionSettings,
        imaging: Imaging,
        props_store: PropsStore,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._props_store = props_store
        self._txt_log = txt_log
        self._img_log = img_log

        self._microscope = microscope
        self._imaging = imaging

        self._settings = settings

        self._mode = AutofocusRegistry.get(self._settings.mode.type)()

        if isinstance(self._settings.mode, AutoscriptMode):
            # sweeping and criterion are not used in the Autoscript mode
            self._sweeping = None
            self._criterion = None
        else:
            self._sweeping = Sweeping(
                self._microscope.electron_beam
                if self._settings.beam_type is BeamType.ELECTRON
                else self._microscope.ion_beam,
                self._settings.mode.sweeping,
                self._settings.target_attribute,
                self._txt_log.derive("sweeping"),
            )

            self._criterion = Criterion(
                f"{self._name} criterion",
                self._settings.mode.criterion,
                self._txt_log.derive("criterion"),
                self._img_log,
            )

        self._ctx = AutofunctionContext(
            self._microscope,
            self._settings.target_attribute,
            self._sweeping,
            self._criterion,
            self._imaging,
            self._settings,
            self._txt_log,
        )

        self._jobs = JobsManager(
            executor=ThreadPoolExecutor(self._settings.max_workers),
        )

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

    def perform_autofocus(self, slice_number: int) -> None:
        """
        Advance the autofocus execution by one step.

        For single-shot modes (basic, line) this runs to completion on the first
        call. For step mode it advances one sweep step per slice, resuming across
        calls until the sweep is exhausted.

        Args:
            slice_number: The current slice index, used for frequency gating.
        """
        # if we have a running autofocus, continue executing it
        if self._active_gen is not None:
            # mid-execution: keep going regardless of gating checks
            self._advance()
            if self._active_gen is not None:  # type: ignore
                self.write_properties(self.read_properties(), self._props_store.next)
            return

        # remove the results from previous slice
        self._jobs.clear()

        # wait for the sharpness of the image from the previous slice
        image_sharpness = self._imaging.wait_for_sharpness()
        self._txt_log.debug(f"Last image sharpness: {image_sharpness}.")
        # evaluate whether the autofocus should be performed based on the sharpness of the image from the previous slice
        if not self._should_execute(slice_number, image_sharpness):
            # if the autofocus should not be run, we still need to copy the props file to the next slice
            self.write_properties(self.read_properties(), self._props_store.next)
            return

        # read the microscope properties for autofocus from a file and set them
        self.read_and_set_properties()

        # execute the autofocus
        self._active_gen = self._mode.execute(self._ctx, self._jobs)
        self._advance()

        # if we have started a long-running autofocus, we need to explicitly copy
        # the microscope properties for the autofocus to the next slice
        # type checker may think that self._active_gen cannot be None, but we can set it to None inside self._advance()
        if self._active_gen is not None:  # type: ignore
            # mid-sweep - copy the props file to the next slice
            self.write_properties(self.read_properties(), self._props_store.next)

    def _should_execute(self, slice_number: int, image_sharpness: float | None) -> bool:
        # always execute autofocus in the first slice
        if slice_number == 1:
            self._txt_log.info("Executing autofocus: this is the first slice.")
            return True

        if (
            self._settings.execution_frequency is not None
            and slice_number % self._settings.execution_frequency == 0
        ):
            self._txt_log.info(
                f"Executing autofocus: slice {slice_number} matches execution frequency ({self._settings.execution_frequency})."
            )
            return True

        if (
            self._settings.sharpness_limit is not None
            and image_sharpness is not None
            and image_sharpness < self._settings.sharpness_limit
        ):
            self._txt_log.info(
                f"Executing autofocus: image sharpness ({image_sharpness:.4f}) is below the limit ({self._settings.sharpness_limit:.4f})."
            )
            return True

        self._txt_log.info("Skipping autofocus.")
        return False

    def _advance(self) -> None:
        assert self._active_gen is not None
        try:
            next(self._active_gen)
            # we always need to wait for the current jobs to finish
            self._jobs.wait()
        except StopIteration:
            if self._sweeping is None:
                return

            results = self._jobs.wait_and_collect()
            best = self._sweeping.evaluate_best_sweep(results)
            self._txt_log.info(f"Best sweep attribute value: {best}.")

            # set the microscope to the best attribute value
            self._sweeping.set_attribute_value(best)
            self._active_gen = None

            # sweep finished: record the new best value for the next slice
            self.collect_and_write_properties(self._props_store.next)
        except Exception:
            self._active_gen.close()
            self._active_gen = None
            raise
