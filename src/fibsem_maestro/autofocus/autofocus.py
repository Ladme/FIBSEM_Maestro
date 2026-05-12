# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from fibsem_maestro.autofocus import LineMode
from fibsem_maestro.autofocus.autofocus_context import AutofocusContext
from fibsem_maestro.autofocus.autofocus_registry import AutofocusRegistry
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.action import Action
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.image.overlay import PolylineOverlay
from fibsem_maestro.logging.image.plot_element import Curve, PlotElement, VerticalLine
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    AutoscriptMode,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.store.props.props_store import PropsStore

if TYPE_CHECKING:
    from collections.abc import Generator


class Autofocus(Action):
    """Orchestrates the autofocus pipeline for a single configured mode.

    Manages the full autofocus lifecycle: deciding when to execute based on
    slice number and image sharpness, setting up the appropriate mode, advancing
    the execution generator, collecting sharpness results, and writing the best sweep value
    back to the microscope and property store.

    For single-shot modes (basic, line, Autoscript) the sweep completes in a
    single `perform_autofocus` call. For step mode, execution is resumed
    across successive calls, one sweep step per slice, until the sweep is
    exhausted.

    Args:
        name: Human-readable identifier for this autofocus instance.
        microscope: Interface to the electron microscope.
        settings: Autofocus configuration.
        imaging: The imaging action whose sharpness result is used to decide
            whether autofocus should run.
        props_store: Store for reading and writing microscope properties.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for criterion images.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AutofocusSettings,
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

        self._ctx = AutofocusContext(
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

        self._sweep_base_value: Any | None = None

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

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    def perform_autofocus(self, slice_number: int) -> None:
        """
        Advance the autofocus execution by one step for the current slice.

        If a multi-step autofocus is already in progress, resumes it by one
        step regardless of gating conditions. Otherwise, evaluates whether
        autofocus should run based on the slice number and the sharpness of
        the previously acquired image, and starts a new execution if so.

        In all cases, the microscope properties for autofocus are propagated
        to the next slice's property store so that the next action always has
        up-to-date properties to read.

        Args:
            slice_number: The current slice index, used for frequency gating
                and first-slice detection.
        """
        # if we have a running autofocus, continue executing it
        if self._active_gen is not None:
            # mid-execution: keep going regardless of gating checks
            self._advance()
            if self._active_gen is not None:
                self.write_properties(self.read_properties(), self._props_store.next)
            return

        # remove the jobs and results from previous slice
        self._jobs.wait_and_clear()

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

        # get the base value for the current sweep
        self._sweep_base_value: float | None = (
            self._sweeping.get_attribute_value() if self._sweeping is not None else None
        )
        # execute the autofocus
        self._active_gen = self._mode.execute(self._ctx, self._jobs)
        self._advance()

        # if we have started a long-running autofocus, we need to explicitly copy
        # the microscope properties for the autofocus to the next slice
        if self._active_gen is not None:
            # mid-sweep - copy the props file to the next slice
            self.write_properties(self.read_properties(), self._props_store.next)

    def _should_execute(self, slice_number: int, image_sharpness: float | None) -> bool:
        """
        Decide whether autofocus should run for the current slice.

        Autofocus runs if any of the following conditions are met:

        - This is the first slice.
        - The slice number is a multiple of the configured execution frequency.
        - The sharpness of the previously acquired image is below the configured sharpness limit.

        If none of the conditions are met, autofocus is skipped and a
        corresponding message is logged.

        Args:
            slice_number: The current slice index.
            image_sharpness: Sharpness of the image acquired on the previous
                slice, or `None` if no criterion is configured or the
                calculation failed.

        Returns:
            `True` if autofocus should run, `False` if it should be skipped.
        """
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
        """
        Advance the active autofocus generator by one step.

        Calls `next` on the active generator to execute one sweep step.
        Waits for any submitted jobs to complete before returning.

        On `StopIteration` the sweep is considered complete: results are
        collected, the best sweep value is determined and applied to the
        microscope, the generator is cleared, and the new properties are
        written to the next slice's store.

        On any other exception the generator is closed, cleared, and the
        exception is re-raised so the caller can handle it.
        """
        assert self._active_gen is not None
        try:
            next(self._active_gen)
            # we always need to wait for the current jobs to finish
            self._jobs.wait()
        except StopIteration:
            if self._sweeping is not None:
                results = self._jobs.wait_and_collect()

                # set the microscope to the best attribute value
                best = self._sweeping.evaluate_best_sweep(results)
                self._txt_log.info(f"Best sweep attribute value: {best}.")
                self._sweeping.set_attribute_value(best)

                # log images
                self._log_af_curve(results, best, self._sweep_base_value)
                if isinstance(self._mode, LineMode):
                    self._log_line_focus_image(results)

            self._active_gen = None
            # sweep finished: record the new best value for the next slice
            self.collect_and_write_properties(self._props_store.next)
        except Exception:
            self._active_gen.close()
            self._active_gen = None
            raise

    def _log_af_curve(
        self, results: list[AutofocusResult], best: float, base: Any | None
    ) -> None:
        """
        Log the autofocus criterion curve with markers for the sweep center and best value.

        Args:
            results: Autofocus results collected during the sweep.
            best: The sweep value selected as optimal.
        """
        if not results:
            return

        # the sharpness evaluation jobs can be completed in any order
        sorted_results = sorted(results, key=lambda r: r.sweep.index)
        swept_values = [r.sweep.value for r in sorted_results]
        criterion_values = [r.sharpness for r in sorted_results]

        # plot the criterion values
        elements: list[PlotElement] = [
            Curve(x=swept_values, y=criterion_values, color="red", linewidth=1.0)
        ]
        # mark the base value
        if base is not None:
            elements.append(
                VerticalLine(x=float(base), color="lightblue", linewidth=1.0)
            )
        # mark the best value
        elements.append(VerticalLine(x=best, color="blue", linewidth=1.0))

        self._img_log.save_plot(
            filename=f"{self.name_with_underscores}_af_curve",
            elements=elements,
            title="Focus criterion",
            xlabel=self._settings.target_attribute,
            ylabel="Sharpness",
        )

    def _log_line_focus_image(self, results: list[AutofocusResult]) -> None:
        """
        Log the line focus image with per-line sharpness overlaid as a polyline.

        Args:
            results: Autofocus results collected during the sweep, one per line.
        """
        if not results:
            return

        try:
            # assuming the image used for line autofocus is still the current microscope image
            image = self._ctx.microscope.beam.get_image()
        except Exception as e:
            self._txt_log.warning(
                f"Could not retrieve line focus image for logging: {e}"
            )
            return

        # the sharpness evaluation jobs can be completed in any order
        sorted_results = sorted(results, key=_get_line_index)
        sharpness_values = [r.sharpness for r in sorted_results]
        line_indices = [r.sweep.index for r in sorted_results]

        if max(sharpness_values) == 0:
            self._txt_log.warning(
                "Max sharpness value is 0. Unable to normalize the sharpness, skipping logging."
            )
            return

        # scale for normalizing sharpness to fit the image
        scale = image.shape[1] / max(sharpness_values)

        self._img_log.save_image(
            filename=f"{self.name_with_underscores}_line_focus.png",
            img=image,
            overlays=[
                PolylineOverlay(
                    points=[
                        PixelPoint(x=int(v * scale), y=line_idx)
                        for v, line_idx in zip(sharpness_values, line_indices)
                    ],
                    color="red",
                )
            ],
            title="Line focus plot",
        )


@staticmethod
def _get_line_index(result: AutofocusResult) -> int:
    """Extract global index of the line in the image that this result corresponds to."""
    assert result.sweep.line_index is not None

    return result.sweep.line_index
