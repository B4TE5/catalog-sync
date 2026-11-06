from pathlib import Path

import numpy as np

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.catalog_photo import catalog_style_photo

ROOT = Path(__file__).parents[1]


def test_catalog_photo_styles() -> None:
    limits = load_config(ROOT).scoring.thresholds
    product = np.full((320, 240, 3), 250, dtype=np.uint8)
    product[65:270, 50:190] = (40, 49, 58)
    assert catalog_style_photo(product, limits)

    bed = np.random.default_rng(0).integers(45, 180, (320, 240, 3), dtype=np.uint8)
    bed[:, :120, 0] //= 4
    bed[:150, :, 1] //= 3
    bed[100:250, 45:195] = (85, 45, 73)
    assert not catalog_style_photo(bed, limits)

    screenshot = bed.copy()
    screenshot[:28] = 230
    screenshot[:12] = 30
    assert catalog_style_photo(screenshot, limits)
