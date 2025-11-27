# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from fibsem_maestro.core.image import Image
from fibsem_maestro.core.subpixel_log import SubpixelLog


class Milling:
    def __init__(self):
        self._fiducial_image: Image | None = None
        self._fiducial_template: Image | None = None
        self._similarity_map: Image | None = None
        self._subpixel_log: SubpixelLog | None = None
