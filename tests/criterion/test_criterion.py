import numpy as np
import pytest

from fibsem_maestro.core.detail_band import DetailBand
from fibsem_maestro.core.image import Image
from fibsem_maestro.criterion.criterion import Criterion
from fibsem_maestro.criterion.error import CriterionError
from fibsem_maestro.logging.image.memory import MemoryImageLogger
from fibsem_maestro.logging.text.memory import MemoryTextLogger
from fibsem_maestro.settings.criterion_settings import (
    BandpassMetric,
    CriterionSettings,
    FrcMetric,
    MultiTileMode,
)


def _criterion(settings: CriterionSettings) -> Criterion:
    return Criterion(
        settings, MemoryTextLogger(lambda: 0), MemoryImageLogger(lambda: 0)
    )


def _noise_image(side: int = 64) -> Image:
    rng = np.random.default_rng(0)
    return Image(rng.integers(0, 255, (side, side)).astype(np.uint8), 1.0)


def test_sharpness_without_any_tile_raises() -> None:
    settings = CriterionSettings(
        sharpness_metric=BandpassMetric(detail=DetailBand(low=2.0, high=8.0)),
        tiling_mode=MultiTileMode(tile_size=1e6),
    )
    with pytest.raises(CriterionError):
        _criterion(settings).calculate_sharpness(_noise_image())


def test_sharpness_of_image_the_metric_rejects_raises() -> None:
    flat = Image(np.full((64, 64), 7, np.uint8), 1.0)
    with pytest.raises(CriterionError):
        _criterion(CriterionSettings(sharpness_metric=FrcMetric())).calculate_sharpness(
            flat
        )


def test_multi_tile_sharpness_ignores_only_failed_tiles() -> None:
    settings = CriterionSettings(
        sharpness_metric=BandpassMetric(detail=DetailBand(low=2.0, high=8.0)),
        tiling_mode=MultiTileMode(tile_size=32.0),
    )
    value = _criterion(settings).calculate_sharpness(_noise_image())
    assert np.isfinite(value)
