# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.autofunction_settings import AutofunctionSettings


class Autofunction:
    def __init__(
        self,
        name: str,
        settings: AutofunctionSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._name = name
        self._txt_log = txt_log
        self._img_log = img_log
