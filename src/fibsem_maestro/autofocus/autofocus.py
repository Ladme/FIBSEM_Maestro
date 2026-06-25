# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from dataclasses import field
from typing import TYPE_CHECKING, Any

import numpy as np

from fibsem_maestro.action.action import Action
from fibsem_maestro.action.registry import ACTION_REGISTRY
from fibsem_maestro.action.state import ActionState
from fibsem_maestro.action_context.action_context import ActionContext
from fibsem_maestro.autofocus import AUTOFOCUS_MODES, LineMode, StepMode
from fibsem_maestro.autofocus.autofocus_context import AutofocusContext
from fibsem_maestro.autofocus.error import AutofocusError
from fibsem_maestro.autofocus.jobs_manager import JobsManager
from fibsem_maestro.autofocus.result import AutofocusResult
from fibsem_maestro.autofocus.sweeping import Sweeping
from fibsem_maestro.core.beam_type import BeamType
from fibsem_maestro.core.point import PixelPoint
from fibsem_maestro.imaging.imaging import Imaging
from fibsem_maestro.logging.image.overlay import PolylineOverlay
from fibsem_maestro.logging.image.plot_element import Curve, PlotElement, VerticalLine
from fibsem_maestro.logging.logging import with_logging_context
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.properties.global_properties import GlobalProperties
from fibsem_maestro.settings.autofocus_settings import (
    AutofocusSettings,
    AutoscriptMode,
)
from fibsem_maestro.settings.property_names import PropertyNames
from fibsem_maestro.workflow.actions import Actions

if TYPE_CHECKING:
    from collections.abc import Generator


class AutofocusState(ActionState):
    sweep_base_value: Any | None = None
    sweep_in_progress: bool = False
    current_step_index: int = 0
    collected_results: list[AutofocusResult] = field(default_factory=list)


@ACTION_REGISTRY.register("autofocus")
class Autofocus(Action[AutofocusSettings, AutofocusState]):
    """Orchestrates the autofocus pipeline for a single configured mode.

    Manages the full autofocus lifecycle: deciding when to execute based on
    slice number and image sharpness, setting up the appropriate mode, advancing
    the execution generator, collecting sharpness results, and writing the best sweep value
    back to the microscope and property store.

    For single-shot modes (basic, line, Autoscript) the sweep completes in a
    single `perform_autofocus` call. For step mode, execution is resumed
    across successive calls, one sweep step per slice, until the sweep is
    exhausted.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: AutofocusSettings,
        ctx: ActionContext,
        actions: Actions,
    ):
        self._name = name
        self._microscope = microscope
        self._settings = settings
        self._ctx = ctx
        self._actions = actions

        self._jobs = JobsManager(
            executor=ThreadPoolExecutor(self._settings.max_workers),
        )

        self._active_gen: Generator[None, None, None] | None = None

        self._sweep_base_value: Any | None = None
        self._current_step_index = 0

        # build mode/sweeping/context from current settings
        self._rebuild()

        # rebuild whenever the settings change
        self._settings.on_change(lambda _: self._rebuild())

    def _rebuild(self) -> None:
        """Rebuild mode, sweeping, and autofocus context from current settings."""
        self._mode = AUTOFOCUS_MODES.get(self._settings.mode.type)()

        if isinstance(self._settings.mode, AutoscriptMode):
            # sweeping is not used in the Autoscript mode
            self._sweeping = None
        else:
            self._sweeping = Sweeping(
                self._microscope.electron_beam
                if self._settings.beam_type is BeamType.ELECTRON
                else self._microscope.ion_beam,
                self._settings.mode.sweeping,
                self._settings.target_attribute,
                self._ctx.text_logger.derive("sweeping"),
            )

        self._autofocus_ctx = AutofocusContext(
            self._microscope,
            self._settings.target_attribute,
            self._sweeping,
            self._settings,
            self._ctx,
        )

    @classmethod
    def settings_cls(cls) -> type[AutofocusSettings]:
        return AutofocusSettings

    @classmethod
    def state_cls(cls) -> type[AutofocusState]:
        return AutofocusState

    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = value

    @property
    def name_with_underscores(self) -> str:
        return self._name.replace(" ", "_")

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
    def ctx(self) -> ActionContext:
        return self._ctx

    @property
    def settings(self) -> AutofocusSettings:
        return self._settings

    @property
    def external_props(self) -> GlobalProperties:
        return self._settings.external_props

    @property
    def state(self) -> AutofocusState:
        return AutofocusState(
            sweep_base_value=self._sweep_base_value,
            sweep_in_progress=self._active_gen is not None,
            current_step_index=self._current_step_index,
            collected_results=self._jobs.collect_completed()
            if self._active_gen is not None
            else [],
        )

    def set_state(self, state: AutofocusState) -> None:
        self._sweep_base_value = state.sweep_base_value
        self._current_step_index = state.current_step_index

        if state.sweep_in_progress:
            self.ctx.text_logger.info(
                f"Restoring state of '{self.name}': sweep in progress, resuming from global step index {state.current_step_index}."
            )
            # re-submit already-collected results into the job manager
            # so that advance's wait_and_collect sees the full result set
            for result in state.collected_results:
                self._jobs.submit(lambda r=result: r)

            # construct the generator
            self._active_gen = self._mode.execute(
                self._autofocus_ctx,
                self._jobs,
                self._resolve_imaging(),
                resume_from=state.current_step_index,
            )

    @with_logging_context
    def execute(self) -> None:
        """
        Advance the autofocus execution by one step for the current slice.

        If a multi-step autofocus is already in progress, resumes it by one
        step regardless of gating conditions. Otherwise, evaluates whether
        autofocus should run based on the slice number and the sharpness of
        the previously acquired image, and starts a new execution if so.

        In all cases, the microscope properties for autofocus are propagated
        to the next slice's property store so that the next action always has
        up-to-date properties to read.
        """
        # if we have a running autofocus, continue executing it
        if self._active_gen is not None:
            # mid-execution: keep going regardless of gating checks
            self._advance()
            if self._active_gen is not None:
                self.write_properties(
                    self.read_properties(), self._ctx.props_store.next
                )
            return

        # remove the jobs and results from previous slice
        self._jobs.wait_and_clear()

        # wait for the sharpness of the image from the previous slice
        image_sharpness = self._resolve_imaging().wait_for_sharpness()
        self._ctx.text_logger.debug(f"Last image sharpness: {image_sharpness}.")
        # evaluate whether the autofocus should be performed based on the sharpness of the image from the previous slice
        if not self._should_execute(self._ctx.slice, image_sharpness):
            # if the autofocus should not be run, we still need to copy the props file to the next slice
            self.write_properties(self.read_properties(), self._ctx.props_store.next)
            return

        # read the microscope properties for autofocus from a file and set them
        self.read_and_set_properties()

        # get the base value for the current sweep
        self._sweep_base_value: float | None = (
            self._sweeping.get_attribute_value() if self._sweeping is not None else None
        )
        # reset the sweep index
        self._current_step_index = 0
        # execute the autofocus
        self._active_gen = self._mode.execute(
            self._autofocus_ctx, self._jobs, self._resolve_imaging()
        )
        self._advance()

        # if we have started a long-running autofocus, we need to explicitly copy
        # the microscope properties for the autofocus to the next slice
        if self._active_gen is not None:
            # mid-sweep - copy the props file to the next slice
            self.write_properties(self.read_properties(), self._ctx.props_store.next)

    @with_logging_context
    def test(self) -> None:
        """
        Run the autofocus pipeline once and apply the best sweep value.

        Intended for manual testing and diagnostics outside the normal acquisition
        loop. Unlike `perform_autofocus`, this method bypasses all gating
        conditions and does not interact with the props store.

        Step mode is not supported since it spreads execution across multiple
        slices and cannot be run in a single call.
        """
        self._ctx.text_logger.info(f"Started test for {self.name}.")
        # clear any existing jobs
        self._jobs.wait_and_clear()

        if isinstance(self._mode, StepMode):
            raise AutofocusError("Test is not supported for step mode")

        # external properties for the action are temporarily set
        with self._microscope.set_temporary_properties(self._settings.external_props):
            # get the current sweep base value
            self._sweep_base_value: float | None = (
                self._sweeping.get_attribute_value()
                if self._sweeping is not None
                else None
            )

            # we provide `None` instead of imaging; imaging is only needed for step mode which is not testable
            for _ in self._mode.execute(self._autofocus_ctx, self._jobs, None):
                self._jobs.wait()

            results = self._jobs.wait_and_collect()
            if self._sweeping is not None:
                best = self._sweeping.evaluate_best_sweep(results)
                self._ctx.text_logger.info(f"Best sweep attribute value: {best}.")
                self._sweeping.set_attribute_value(best)

                # log images
                self._log_af_curve(results, best, self._sweep_base_value)
                if isinstance(self._mode, LineMode):
                    self._log_line_focus_image(results)

        self._ctx.text_logger.info(f"Completed test for {self.name}.")

    def wait_for_background_threads(self) -> None:
        self._jobs.wait()

    def _resolve_imaging(self) -> Imaging:
        imaging = self._actions.named(self._settings.linked_imaging)
        if not isinstance(imaging, Imaging):
            raise AutofocusError(
                f"Linked action is not an Imaging action: {imaging.name}"
            )
        return imaging

    def _should_execute(self, slice_number: int, image_sharpness: float | None) -> bool:
        """
        Decide whether autofocus should run for the current slice.

        Autofocus runs if any of the following conditions are met:

        - The slice number - 1 is a multiple of the configured execution frequency.
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
        if (
            self._settings.execution_frequency is not None
            # the first slice is 1, so we use slice_number - 1 to get the 0-indexed slice number
            and (slice_number - 1) % self._settings.execution_frequency == 0
        ):
            self._ctx.text_logger.info(
                f"Executing {self.name}: slice {slice_number} matches execution frequency ({self._settings.execution_frequency})."
            )
            return True

        if (
            self._settings.sharpness_limit is not None
            and image_sharpness is not None
            and image_sharpness < self._settings.sharpness_limit
        ):
            self._ctx.text_logger.info(
                f"Executing {self.name}: image sharpness ({image_sharpness:.4f}) is below the limit ({self._settings.sharpness_limit:.4f})."
            )
            return True

        self._ctx.text_logger.info(f"Skipping {self.name}.")
        return False

    def _advance(self) -> None:
        """
        Advance the active autofocus generator by one step.

        Calls `next` on the active generator to execute one sweep step.

        On `StopIteration` the sweep is considered complete: results are
        collected, the best sweep value is determined and applied to the
        microscope, the generator is cleared, and the new properties are
        written to the next slice's store.

        On any other exception the generator is closed, cleared, and the
        exception is re-raised so the caller can handle it.
        """
        assert self._active_gen is not None

        self._current_step_index += 1
        try:
            next(self._active_gen)
            # wait for all background threads to finish
            # this is not strictly necessary for the basic functionality,
            # but without this, the state will not contain all the information
            # (some background threads may still be running when the state is stored)
            # then restoring the state after interrupt becomes complicated/messy
            self._jobs.wait()
        except StopIteration:
            if self._sweeping is not None:
                results = self._jobs.wait_and_collect()

                # set the microscope to the best attribute value
                best = self._sweeping.evaluate_best_sweep(results)
                self._ctx.text_logger.info(f"Best sweep attribute value: {best}.")
                self._sweeping.set_attribute_value(best)

                # log images
                self._log_af_curve(results, best, self._sweep_base_value)
                if isinstance(self._mode, LineMode):
                    self._log_line_focus_image(results)

            self._active_gen = None
            # sweep finished: record the new best value for the next slice
            self.collect_and_write_properties(self._ctx.props_store.next)
            self._current_step_index = 0
        except Exception:
            self._active_gen.close()
            self._active_gen = None
            self._current_step_index = 0
            raise

    def _log_af_curve(
        self, results: list[AutofocusResult], best: float, base: Any | None
    ) -> None:
        """
        Log the autofocus criterion curve with markers for the base sweep and best value.

        Args:
            results: Autofocus results collected during the sweep.
            best: The sweep value selected as optimal.
        """
        if not results:
            return

        sorted_results = sorted(results, key=lambda r: r.sweep.index)

        # average sharpness per (repetition, sweep value) to handle line mode
        # where multiple results share the same sweep value
        averaged: dict[tuple[int, float], list[float]] = defaultdict(list)
        for r in sorted_results:
            averaged[(r.sweep.repetition, r.sweep.value)].append(r.sharpness)

        repetitions: dict[int, list[tuple[float, float]]] = defaultdict(list)
        for (rep, value), sharpnesses in averaged.items():
            repetitions[rep].append((value, float(np.mean(sharpnesses))))

        _CURVE_COLORS = [
            "#0000FF",
            "#3355DD",
            "#6699BB",
            "#BB6699",
            "#DD5533",
            "#FF0000",
        ]

        # plot the criterion values
        elements: list[PlotElement] = [
            Curve(
                x=[v for v, _ in sorted(rep_points, key=lambda p: p[0])],
                y=[s for _, s in sorted(rep_points, key=lambda p: p[0])],
                color=_CURVE_COLORS[rep % len(_CURVE_COLORS)],
                linewidth=1.0,
            )
            for rep, rep_points in repetitions.items()
        ]

        # mark the base value
        if base is not None:
            elements.append(VerticalLine(x=float(base), color="orange", linewidth=1.0))
        # mark the best value
        elements.append(VerticalLine(x=best, color="green", linewidth=1.0))

        self._ctx.image_logger.save_plot(
            filename="af_curve",
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
            image = self._autofocus_ctx.microscope.beam.get_image()
        except Exception as e:
            self._ctx.text_logger.warning(
                f"Could not retrieve line focus image for logging: {e}"
            )
            return

        # the sharpness evaluation jobs can be completed in any order
        sorted_results = sorted(results, key=_get_line_index)
        sharpness_values = [r.sharpness for r in sorted_results]
        line_indices = [
            r.sweep.line_index for r in sorted_results if r.sweep.line_index is not None
        ]

        if max(sharpness_values) == 0:
            self._ctx.text_logger.warning(
                "Max sharpness value is 0. Unable to normalize the sharpness, skipping logging."
            )
            return

        # scale for normalizing sharpness to fit the image
        scale = image.shape[1] / max(sharpness_values)

        self._ctx.image_logger.save_image(
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
