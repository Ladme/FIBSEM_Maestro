# Released under MIT License.
# Copyright (c) 2024-2026 CEMCOF

from fibsem_maestro.core.image import Image
from fibsem_maestro.logging.image.image_logger import ImageLogger
from fibsem_maestro.logging.text.text_logger import TextLogger
from fibsem_maestro.settings.mask_settings import MaskSettings


class Mask:
    def __init__(
        self,
        settings: MaskSettings,
        txt_log: TextLogger,
        img_log: ImageLogger,
    ):
        self._txt_log = txt_log
        self._img_log = img_log

    def mask_image(self, img: Image, line_number: int | None = None) -> list[Image]:
        return [img]
