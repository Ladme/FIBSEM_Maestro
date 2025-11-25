# Released under MIT License.
# Copyright (c) 2024-2025 CEMCOF


from typing import Any

import numpy as np


class Image(np.ndarray):
    @property
    def pixel_size(self) -> Any:
        pass
