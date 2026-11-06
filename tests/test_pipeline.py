import gzip
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
import qrcode

from vinted_hunter.config import Config, load_config
from vinted_hunter.pipeline.dedupe import distance, is_drop, photo_dedupe
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.models import Evidence, Listing, Seller
from vinted_hunter.pipeline.pricing import price_signals, summarize, timing
from vinted_hunter.pipeline.score import score
from vinted_hunter.pipeline.text import matches
from vinted_hunter.pipeline.vision import ReferenceMatcher, phash, read_qr
from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]
NOW = datetime(2026, 11, 6, tzinfo=UTC)


@pytest.fixture(scope="module")
def config() -> Config:
    return load_config(ROOT)


@pytest.fixture
def candidate() -> Listing:
    path = ROOT / "tests" / "fixtures" / "catalog-stone-island.html.gz"
    items = parse_catalog(gzip.decompress(path.read_bytes()).decode()).listings
    return next(item for item in items if item.id == 10682766478)


@pytest.mark.parametrize(
    ("updates", "seller", "evidence", "reason"),
    [
        ({"price": Decimal(10)}, None, None, "price"),
        ({"size": "XXL"}, None, None, "size"),
        ({"category_id": 5492}, None, None, "category"),
        ({"description": "geïnspireerde groene"}, None, None, "replica"),
        ({"title": "Felpa con cappuccio"}, None, None, "hood"),
        ({"status": "satisfactory"}, None, None, "status"),
        ({"description": "une contrefaçon"}, None, None, "replica"),
        ({"color": "Blanco"}, None, None, "color"),
        ({}, Seller(id=1, feedback_count=2), None, "seller_feedback"),
        ({}, Seller(id=1, rating=4.4), None, "seller_rating"),
        ({}, None, Evidence(qr="qr_foreign_domain"), "fake_certilogo_domain"),
        ({}, None, Evidence(shared_photo=True), "shared_photo"),
        ({}, None, Evidence(blacklisted_photo=True), "blacklisted_photo"),
    ],
)
def test_gates(
    config: Config,
    candidate: Listing,
    updates: dict,
    seller: Seller | None,
    evidence: Evidence | None,
    reason: str,
) -> None:
    profile = config.profiles[0]
    listing = candidate.model_copy(update=updates)
    rejected, passed = gate(listing, profile, config, seller, evidence)
    assert rejected == reason
    assert (
        score(listing, profile, seller, evidence or Evidence(), config, passed, {}, rejected).tier
        == "rejected"
    )


def test_hood_and_brand_specific_rules(config: Config, candidate: Listing) -> None:
    stone = config.profiles[0]
    assert "hood_unconfirmed" in gate(candidate, stone, config)[1]
    no_hood = candidate.model_copy(update={"title": "Sans capuche"})
    assert "hood_unconfirmed" not in gate(no_hood, stone, config)[1]
    supreme = next(p for p in config.profiles if p.id == "supreme")
    box = candidate.model_copy(update={"size": "L", "title": "Box Logo Hoodie"})
    assert gate(box, supreme, config)[0] == supreme.brand_rules[0].reason
    assert gate(no_hood.model_copy(update={"size": "L"}), supreme, config)[0] == "hood"
    assert gate(candidate, stone, config, detailed=True)[0] == "photos"


def test_words(config: Config) -> None:
    words = config.scoring.words
    assert matches("Porté une fois", words["motivated"]) == ["porté une fois"]
    assert matches("No me queda y guardé la factura", words["proof"]) == ["factura"]
    assert matches("FAKE 1:1", words["replica"]) == ["1:1", "fake"]
    assert not matches("reparación preparada", words["replica"])
    assert matches("Desteñida", words["wear"]) == ["desteñida"]


def test_price_speed_and_top_tier(config: Config, candidate: Listing) -> None:
    profile = config.profiles[0]
    market = summarize([Decimal(x) for x in range(40, 80)])
    assert market.count == 40 and market.median == Decimal("59.5")
    assert market.p25 == Decimal("49.75") and market.p10 == Decimal("43.9")
    listing = candidate.model_copy(
        update={
            "uploaded_at": NOW - timedelta(minutes=8),
            "favourites": 8,
            "description": "Me la regalaron.\nTengo la factura.",
            "photos": candidate.photos * 5,
        }
    )
    clock = timing(listing, NOW, config.scoring)
    assert clock["hot"] and clock["age_minutes"] == 8
    price = price_signals(listing, profile, market, 8, False, config.scoring)
    assert price["buy_now"] and price["estimated"] and price["bargain"]
    old = price_signals(listing, profile, summarize([]), 8000, False, config.scoring)
    assert old["negotiable"] and old["offer"] == "30"
    seller = Seller(id=1, feedback_count=142, rating=4.9)
    result = score(listing, profile, seller, Evidence(qr="certilogo_ok"), config, [], price)
    assert result.tier == "top" and result.score == 100
    assert "Certilogo ✓" in result.reasons


@pytest.mark.parametrize(
    ("domain", "expected"),
    [
        ("www.certilogo.com", "certilogo_ok"),
        ("certilogo-check.com", "qr_foreign_domain"),
        ("certilogo.com.example.org", "qr_foreign_domain"),
    ],
)
def test_qr(domain: str, expected: str) -> None:
    img = qrcode.make(f"https://{domain}/example").convert("L")
    assert read_qr(np.array(img)) == expected


def test_phash_rescaled_and_empty_refs(config: Config, tmp_path: Path) -> None:
    img = qrcode.make("https://www.certilogo.com/test").convert("L")
    assert phash(img) == phash(img.resize((580, 580)))
    matcher = ReferenceMatcher(tmp_path, config.scoring.thresholds)
    assert matcher.parts(np.array(img)) == set()


def test_dedupe_and_blacklist(tmp_path: Path, candidate: Listing) -> None:
    profile = "stone-island"
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        assert store.observe_price(candidate, profile, NOW.isoformat()) is None
        cheaper = candidate.model_copy(update={"price": candidate.price - Decimal(5)})
        previous = store.observe_price(cheaper, profile, (NOW + timedelta(seconds=1)).isoformat())
        assert is_drop(cheaper, previous)
        assert distance("0", "f") == 4
        store.save(candidate, profile, "good", 60, {}, False)
        store.save_photos(candidate.id, ["0"], "0")
        another = candidate.model_copy(update={"id": candidate.id + 1})
        assert photo_dedupe(store, another, Evidence(primary_hash="f"), 6)
        reduced = another.model_copy(update={"price": cheaper.price})
        signals = Evidence(primary_hash="f")
        assert not photo_dedupe(store, reduced, signals, 6)
        assert signals.price_drop
        store.label(candidate.id, "fake", NOW.isoformat())
        other_seller = another.model_copy(update={"seller_id": 123})
        signals = Evidence(hashes=["0"], primary_hash="0")
        assert not photo_dedupe(store, other_seller, signals, 6)
        assert signals.blacklisted_photo and signals.shared_photo


def test_label_cli_from_real_fixture(
    candidate: Listing, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from typer.testing import CliRunner

    from vinted_hunter import cli

    monkeypatch.setattr(cli, "ROOT", tmp_path)
    database = tmp_path / "data" / "vh.sqlite"
    with SQLiteStore(database) as store:
        store.save(candidate, "stone-island", "good", 70, {}, False)
        store.save_photos(candidate.id, ["0"], "0")
    result = CliRunner().invoke(cli.app, ["label", str(candidate.id), "fake"])
    assert result.exit_code == 0
    assert "fake" in result.stdout
    with SQLiteStore(database) as store:
        assert store.matching_hashes(candidate.seller_id)[0]["label"] == "fake"


def test_search_groups_and_rotates(config: Config) -> None:
    from vinted_hunter.sources.vinted.search import plan_searches

    first, cursor = plan_searches(config)
    second, _ = plan_searches(config, cursor)
    groups = [search for search in first if "brand_ids[]" in search.params]
    assert len(groups) == 2
    assert len(groups[0].profiles) == 1
    ids = groups[1].params["brand_ids[]"]
    assert isinstance(ids, list) and len(ids) >= 2
    assert first != second
    assert any(search.params.get("search_text") == "stone island" for search in second)
    assert len(first) <= config.scoring.capture.catalog_limit
