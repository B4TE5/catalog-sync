import gzip
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.text import matches
from vinted_hunter.sources.vinted.item import listing_from_item
from vinted_hunter.sources.vinted.search import plan_searches

ROOT = Path(__file__).parents[1]


def test_all_queries_use_verified_parent_category() -> None:
    config = load_config(ROOT)
    assert {p.id for p in config.profiles}.isdisjoint({"supreme", "palm-angels", "palace"})
    for selftest in (False, True):
        for cursor in (0, 2, 8):
            searches, _ = plan_searches(config, cursor, selftest)
            assert searches
            assert all(query.params["catalog[]"] == "79" for query in searches)


@pytest.mark.parametrize(
    ("update", "expected"),
    [
        ({"material": "Lana"}, "knitwear"),
        ({"description": "Gebreide trui van wol"}, "knitwear"),
        ({"description": "Camisola de malha, lã"}, "knitwear"),
        ({"description": "Sweatshirt de algodão com código de autenticidade"}, None),
        ({"description": "Crewneck van katoen, QR-code"}, None),
    ],
)
def test_jumper_category_requires_sweatshirt_evidence(update: dict, expected: str | None) -> None:
    path = ROOT / "tests/recall/10690539539"
    item = listing_from_item(
        gzip.decompress((path / "item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater",
        datetime.now(UTC),
    ).model_copy(update=update)
    config = load_config(ROOT)
    assert gate(item, config.profiles[0], config, detailed=True)[0] == expected


def test_nl_and_pt_signals_have_word_boundaries() -> None:
    words = load_config(ROOT).scoring.words
    for text in ("past niet, te groot, cadeau", "não me serve, presente"):
        assert matches(text, words["motivated"])
    for text in ("nep, niet origineel", "não original, imitação"):
        assert matches(text, words["replica"])
    assert matches("kassabon en factuur", words["proof"])
    assert matches("recibo e fatura", words["proof"])
    assert not matches("equatorial", words["authenticity_mentioned"])
