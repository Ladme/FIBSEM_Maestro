# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF

from abc import ABC, abstractmethod

from fibsem_maestro.core.drift import Drift
from fibsem_maestro.core.image import Image, Image8Bit
from fibsem_maestro.drift_correction.drift_calculation_registry import (
    DriftCalculationRegistry,
)
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.settings.drift_correction_settings import DriftCorrectionMode
from fibsem_maestro.settings.template_matching_settings import TemplateMatchingSettings
from fibsem_maestro.store.image.image_store import ImageStore
from fibsem_maestro.template_matching.template_matching import TemplateMatching


class DriftCalculationMode(ABC):
    """
    Abstract interface for drift calculation implementations.

    Defines the lifecycle of a drift calculation method, consisting of a
    one-time setup step and three per-slice hooks: an optional pre-processing
    step, the core drift calculation, and an optional post-processing step.
    The pre and post hooks do nothing by default and can be overridden by
    concrete subclasses to implement slice-level state management such as
    template updates or confidence tracking.

    Concrete subclasses are registered with `DriftCalculationRegistry` and
    retrieved by name at runtime.

    Args:
        name: Human-readable identifier for this instance.
        microscope: Interface to the electron microscope.
        settings: Drift correction mode configuration.
        image_store: Store for persisting and retrieving images.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for annotated images.
    """

    @abstractmethod
    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: DriftCorrectionMode,
        image_store: ImageStore[Image8Bit],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        pass

    @abstractmethod
    def calculate_drift(self, image: Image, slice_number: int) -> Drift:
        """
        Calculate the drift of the current image relative to a reference.

        Args:
            image: The current frame to compare against a reference.
            slice_number: The current slice index.

        Returns:
            A `Drift` instance containing the measured x and y shift in
            nanometers and the associated confidence score.
        """

    def setup(self) -> None:
        """
        Perform one-time initialization before acquisition begins.

        Called once by `DriftCorrection.setup` before the first slice is
        acquired. Does nothing by default - override to perform initialization
        such as acquiring reference templates.
        """
        pass

    def before_calculate_drift(self, slice_number: int) -> None:
        """
        Perform per-slice preparation before drift calculation.

        Called once per slice before `calculate_drift`.
        Does nothing by default - override to perform slice-level pre-processing.

        Args:
            slice_number: The current slice index.
        """
        pass

    def after_calculate_drift(self, slice_number: int) -> None:
        """
        Perform per-slice cleanup after drift calculation.

        Called once per slice after `calculate_drift`.
        Does nothing by default - override to perform slice-level
        post-processing such as updating reference templates.

        Args:
            slice_number: The current slice index.
        """
        pass


@DriftCalculationRegistry.register("template_matching")
class TemplateMatchingDrift(DriftCalculationMode):
    """
    Drift calculation mode based on normalized cross-correlation template matching.

    Delegates drift measurement to a `TemplateMatching` instance.

    Args:
        name: Human-readable identifier for this instance.
        microscope: Interface to the electron microscope.
        settings: Template matching configuration.
        image_store: Store for persisting and retrieving template images.
        txt_log: Logger for diagnostic and status messages.
        img_log: Logger for heatmap and overlay images.
    """

    def __init__(
        self,
        name: str,
        microscope: Microscope,
        settings: TemplateMatchingSettings,
        image_store: ImageStore[Image8Bit],
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._template_matching = TemplateMatching(
            name, microscope, settings, image_store, txt_log, img_log
        )

        self._last_confidence: float | None = None

    def setup(self) -> None:
        self._template_matching.create_templates()

    def calculate_drift(self, image: Image, slice_number: int) -> Drift:
        _ = slice_number

        drift = self._template_matching.calculate_drift(image)
        self._last_confidence = drift.confidence

        return drift

    def after_calculate_drift(self, slice_number: int) -> None:
        assert self._last_confidence is not None

        self._template_matching.update_templates(slice_number, self._last_confidence)

        self._last_confidence = None
