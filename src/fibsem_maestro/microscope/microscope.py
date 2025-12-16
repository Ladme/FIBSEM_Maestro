# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.microscope.microscope_registry import MicroscopeRegistry
from fibsem_maestro.settings.microscope_settings import MicroscopeSettings


class Microscope:
    def __init__(
        self,
        settings: MicroscopeSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._txt_log = txt_log
        self._img_log = img_log

        self._apply_settings(settings)
        self._settings.on_change(self._update)

    def _apply_settings(self, settings: MicroscopeSettings) -> None:
        self._settings = settings
        self._control = MicroscopeRegistry.get(settings.control)

    def _update(self, settings: MicroscopeSettings) -> None:
        self._apply_settings(settings)
