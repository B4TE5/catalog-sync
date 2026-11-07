from pathlib import Path

import numpy as np
import pytest
from PIL import Image

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.catalog_photo import catalog_style_photo
from vinted_hunter.replay import evaluate_fixture

ROOT = Path(__file__).parents[2]
CASES = sorted(path.parent for path in (ROOT / "tests/precision").glob("*/capture.json"))


@pytest.mark.parametrize("directory", CASES, ids=lambda path: path.name)
def test_real_precision_listing_is_rejected(directory: Path) -> None:
    result = evaluate_fixture(ROOT, directory)
    assert result["tier"] == "rejected", result["trace"]
    assert result["trace"]["gate_rejected"]


def test_real_store_screenshot_remains_detected() -> None:
    photo = ROOT / "tests/precision/10685333948/photo-0.jpg"
    with Image.open(photo) as source:
        image = np.asarray(source.convert("RGB"))
    assert catalog_style_photo(image, load_config(ROOT).scoring.thresholds)
