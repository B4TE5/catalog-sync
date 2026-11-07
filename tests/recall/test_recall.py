from pathlib import Path

import pytest

from vinted_hunter.replay import evaluate_fixture

ROOT = Path(__file__).parents[2]
CASES = sorted(path.parent for path in (ROOT / "tests/recall").glob("*/capture.json"))


@pytest.mark.parametrize("directory", CASES, ids=lambda path: path.name)
def test_real_recall_listing_reaches_good(directory: Path) -> None:
    result = evaluate_fixture(ROOT, directory)
    assert result["tier"] in {"good", "top"}, result["trace"]
    assert result["score"] >= 60
    assert result["trace"]["gate_rejected"] is None


def test_priority_listing_preserves_material_and_authenticity_signal() -> None:
    result = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    assert result["body"]["category_id"] == 1811
    assert result["body"]["material"] == "Algodón"
    assert result["trace"]["score"]["points"]["authenticity_mentioned"] == 10
    assert result["trace"]["evidence"]["catalog_photo_count"] == 0
