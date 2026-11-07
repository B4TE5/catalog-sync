import gzip
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.run import Pipeline, enrichment_priority
from vinted_hunter.pipeline.text import matches
from vinted_hunter.sources.vinted.client import VintedClient
from vinted_hunter.sources.vinted.item import listing_from_item
from vinted_hunter.sources.vinted.search import plan_searches
from vinted_hunter.storage.sqlite_store import SQLiteStore

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


def test_priority_prefers_fresh_then_stone_then_relative_price() -> None:
    root = ROOT / "tests/recall/10690539539"
    item = listing_from_item(
        gzip.decompress((root / "item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater", datetime.now(UTC),
    )
    config = load_config(ROOT)
    stone = config.profiles[0]
    other = config.profiles[1]
    now = datetime.now(UTC)
    assert enrichment_priority(item, stone, True, now) < enrichment_priority(item, other, True, now)
    assert enrichment_priority(item, other, True, now) < enrichment_priority(
        item, stone, False, now
    )


def test_backlog_is_enriched_without_reappearing_in_catalog(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = ROOT / "tests/recall/10690539539"
    item = listing_from_item(
        gzip.decompress((root / "item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater", datetime.now(UTC),
    )
    calls = []
    with SQLiteStore(tmp_path / "state.sqlite") as store, VintedClient() as client:
        store.save(item, "stone-island", None, None, {"pending": True}, False)
        pipeline = Pipeline(ROOT, store, load_config(ROOT), datetime.now(UTC))
        monkeypatch.setattr(pipeline, "candidate", lambda *args: calls.append(args[1].id))
        pipeline.process(client, {}, False, None)
        assert calls == [item.id]
        assert pipeline.run["candidates"] == 1
