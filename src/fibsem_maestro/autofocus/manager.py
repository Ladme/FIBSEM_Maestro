# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.autofunctions.autofocus import AutofocusStatus
from fibsem_maestro.autofunctions.autofunction import Autofunction
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope import Microscope
from fibsem_maestro.notifications.notification_service import NotificationService
from fibsem_maestro.settings.settings import Settings


class AutofunctionManager:
    def __init__(
        self,
        microscope: Microscope,
        settings: Settings,
        txt_log: TextLogger,
        img_log: ImageLogger,
        notifier: NotificationService | None,
    ):
        self._microscope = microscope
        self._settings = settings
        self._txt_log = txt_log
        self._img_log = img_log
        self._notifier = notifier

        self._create_autofunctions()
        self._queue: list[Autofunction] = []

        self._active: Autofunction | None = None

        # we only reconstruct the list of autofunctions if an autofunction is removed/added
        # internal changes of the autofunctions themselves are handled inside the Autofunction class
        self._settings.on_change(self._update)

    def _update(self, settings: Settings) -> None:
        self._settings = settings

        # if the number of autofunctions defined in the settings has changed,
        # we have to reconstruct the list
        if len(self._settings.autofunctions) != len(self._autofunctions):
            self._create_autofunctions()

    def _create_autofunctions(self) -> None:
        self._autofunctions: list[Autofunction] = []
        for name, settings in self._settings.autofunctions.items():
            self._autofunctions.append(
                Autofunction(
                    name,
                    settings,
                    self._microscope,
                    self._settings.criteria,
                    self._settings.imaging,
                    self._settings.masks,
                    self._txt_log.derive(name),
                    self._img_log,
                )
            )

    def tick(self, slice_number: int, image_resolution: float | None) -> None:
        # schedule autofunctions execution
        for af in self._autofunctions:
            if (
                af.should_execute(slice_number, image_resolution)
                and af not in self._queue
            ):
                af.sweeping.set_base()
                self._queue.append(af)

        # if a step-wise autofunction is already running, continue it
        if self._active is not None:
            if self._active.execute() == AutofocusStatus.DONE:
                self._active = None

        # start the next autofunction in queue
        if not self._queue:
            return
