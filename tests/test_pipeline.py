import gzip
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import numpy as np
import pytest
import qrcode

from vinted_hunter.config import Config, load_config
from vinted_hunter.pipeline.dedupe import distance, is_drop, photo_dedupe
from vinted_hunter.pipeline.gates import ATTRIBUTE_GATES, gate
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
        ({"price": Decimal(100)}, None, None, "price"),
        ({"size": "XXL"}, None, None, "size"),
        ({"category_id": 5492}, None, None, "not_sweatshirt"),
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
    if reason in ATTRIBUTE_GATES:
        assert gate(listing, profile, config)[0] is None
    rejected, passed = gate(
        listing, profile, config, seller, evidence, detailed=reason in ATTRIBUTE_GATES
    )
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
    assert (
        gate(no_hood.model_copy(update={"size": "L"}), supreme, config, detailed=True)[0] == "hood"
    )
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
    price = price_signals(listing, profile, market, 8, False, config.scoring, seller_verified=True)
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


def test_explicit_seller_size_overrides_conflicting_catalog(
    config: Config, candidate: Listing
) -> None:
    rhude = next(profile for profile in config.profiles if profile.id == "rhude")
    listing = candidate.model_copy(
        update={
            "title": "Sudadera RHUDE – Talla S (Oversize)",
            "size": "L",
        }
    )
    assert gate(listing, rhude, config, detailed=True)[0] == "size"


def test_unknown_attributes_pass_catalog_and_detail(config: Config, candidate: Listing) -> None:
    profile = config.profiles[0]
    listing = candidate.model_copy(
        update={
            "size": None,
            "status": None,
            "color": None,
            "category_id": None,
            "photos": candidate.photos * profile.min_photos,
        }
    )
    assert gate(listing, profile, config)[0] is None
    reason, evidence = gate(listing, profile, config, detailed=True)
    assert reason is None
    assert {f"{name}_unconfirmed" for name in ATTRIBUTE_GATES} <= set(evidence)


def test_detail_supersedes_catalogue_attributes(config: Config, candidate: Listing) -> None:
    from vinted_hunter.sources.vinted.item import parse_item

    profile = config.profiles[0].model_copy(update={"color": None})
    tile = candidate.model_copy(update={"size": "S", "status": "satisfactory", "color": None})
    assert gate(tile, profile, config)[0] is None
    body = gzip.decompress((ROOT / "tests/fixtures/item.html.gz").read_bytes()).decode()
    detail = parse_item(body, tile, NOW)
    assert detail.size == "XL" and detail.status == "very_good"
    assert gate(detail, profile, config, detailed=True)[0] is None


def test_funnel_tracks_each_listing_once(
    config: Config, candidate: Listing, tmp_path: Path
) -> None:
    from vinted_hunter.pipeline.run import Pipeline

    profile = config.profiles[0]
    other = candidate.model_copy(update={"id": candidate.id + 1})
    with SQLiteStore(tmp_path / "vh.sqlite") as store:
        store.save(
            candidate, profile.id, "rejected", 0, {"gate_rejected": "color", "enriched": True}, True
        )
        pipe = Pipeline(tmp_path, store, config, NOW)
        pipe.fetched_details.add(candidate.id)
        counts = pipe.backfill_funnel(
            {
                candidate.id: (candidate, profile, False),
                other.id: (other, profile, False),
            }
        )[profile.id]
    assert counts["seen"] == 2
    assert counts["enriched"] == counts["fetched"] == 1
    assert counts["tiers"] == {"rejected": 1, "pending": 1}
    assert counts["rejected"] == {"color": 1}
    assert counts["ids_by_outcome"] == {"rejected:color": [candidate.id], "pending": [other.id]}


@pytest.mark.parametrize("phrase", ["Doesn't fit", "Taglia sbagliata", "Passt nicht"])
def test_motivated_seller_across_languages(config: Config, phrase: str) -> None:
    assert matches(phrase, config.scoring.words["motivated"])


def test_tag_condition_rule_waits_for_detail(config: Config, candidate: Listing) -> None:
    palm = next(profile for profile in config.profiles if profile.id == "palm-angels")
    listing = candidate.model_copy(
        update={
            "title": "Felpa con cappuccio",
            "size": "L",
            "photos": candidate.photos * palm.min_photos,
        }
    )
    unknown = listing.model_copy(update={"status": None})
    reason, passed = gate(unknown, palm, config, detailed=True)
    assert reason is None
    assert {"hood", "status_unconfirmed"} <= set(passed)
    tagged = listing.model_copy(update={"status": "new_with_tags"})
    assert gate(tagged, palm, config)[0] is None
    assert gate(tagged, palm, config, detailed=True)[0] == palm.brand_rules[0].reason


def test_regular_offer_and_drop_offer(config: Config, candidate: Listing) -> None:
    profile = config.profiles[0]
    ordinary = price_signals(candidate, profile, summarize([]), 90, False, config.scoring)
    dropped = price_signals(candidate, profile, summarize([]), 90, True, config.scoring)
    assert ordinary["offer"] == "35" and not ordinary["negotiable"]
    assert dropped["offer"] == "30" and dropped["negotiable"]


def test_seen_id_skips_unchanged_and_detects_drop(
    config: Config,
    candidate: Listing,
    tmp_path: Path,
) -> None:
    from vinted_hunter.pipeline.run import Pipeline
    from vinted_hunter.sources.vinted.client import VintedClient

    profile = config.profiles[0]
    with SQLiteStore(tmp_path / "vh.sqlite") as store, VintedClient(enrich_limit=0) as client:
        store.observe_price(candidate, profile.id, (NOW - timedelta(minutes=2)).isoformat())
        store.save(candidate, profile.id, "good", 70, {"enriched": True}, False)
        pipe = Pipeline(tmp_path, store, config, NOW - timedelta(minutes=1))
        pipe.process(client, {candidate.id: (candidate, profile, True)}, False, None)
        assert pipe.run["new"] == pipe.run["candidates"] == 0
        cheaper = candidate.model_copy(update={"price": Decimal(35)})
        pipe = Pipeline(tmp_path, store, config, NOW)
        pipe.process(client, {cheaper.id: (cheaper, profile, True)}, False, None)
        assert pipe.run["new"] == pipe.run["candidates"] == 1
        assert store.record(cheaper.id)["trace"]["evidence"]["price_drop"]


def test_legacy_catalogue_reject_is_reopened(
    config: Config,
    candidate: Listing,
    tmp_path: Path,
) -> None:
    from vinted_hunter.pipeline.run import Pipeline
    from vinted_hunter.sources.vinted.client import VintedClient

    profile = config.profiles[0]
    tile = candidate.model_copy(update={"size": "S"})
    with SQLiteStore(tmp_path / "vh.sqlite") as store, VintedClient(enrich_limit=0) as client:
        store.observe_price(tile, profile.id, (NOW - timedelta(minutes=1)).isoformat())
        store.save(tile, profile.id, "rejected", 0, {"gate_rejected": "size"}, False)
        pipe = Pipeline(tmp_path, store, config, NOW)
        pipe.process(client, {tile.id: (tile, profile, True)}, False, None)
        assert pipe.run["candidates"] == 1 and pipe.run["new"] == 0
        assert store.record(tile.id)["tier"] is None


def test_revalidate_requires_ficha_evidence_for_attribute_rejects(
    config: Config,
    candidate: Listing,
    tmp_path: Path,
) -> None:
    from vinted_hunter.pipeline.run import Pipeline

    profile = config.profiles[0]
    listing = candidate.model_copy(update={"size": "M", "photos": candidate.photos * 3})
    with SQLiteStore(tmp_path / "vh.sqlite") as store:
        pipe = Pipeline(tmp_path, store, config, NOW)
        store.save(listing, profile.id, "good", 70, {}, False)
        assert pipe.revalidate() == 0
        assert store.record(listing.id)["tier"] == "good"
        store.save(listing, profile.id, "good", 70, {"enriched": True}, False)
        assert pipe.revalidate() == 1
        assert store.record(listing.id)["trace"]["gate_rejected"] == "size"


@pytest.mark.parametrize(
    "title",
    [
        "Pulsera TwoJeys",
        "Stone Island tee",
        "Lunettes Rhude",
        "Pantaloni Heron Preston",
        "Palm Angels Sonnenbrille",
    ],
)
def test_garment_prefilter_rejects_other_types(config: Config, candidate: Listing, title: str):
    tile = candidate.model_copy(update={"title": title})
    assert gate(tile, config.profiles[0], config)[0] == "not_sweatshirt"


def test_below_floor_needs_certilogo_and_can_only_be_reviewed(config: Config, candidate: Listing):
    profile = config.profiles[0]
    listing = candidate.model_copy(update={"price": Decimal(25)})
    assert gate(listing, profile, config)[0] is None
    assert gate(listing, profile, config, evidence=Evidence())[0] == "too_cheap_for_brand"
    proof = Evidence(qr="certilogo_ok", qr_decoded=True)
    assert gate(listing, profile, config, evidence=proof)[0] is None
    prices = price_signals(
        listing, profile, summarize([]), 1, False, config.scoring, seller_verified=True
    )
    result = score(
        listing, profile, Seller(id=1, rating=5, feedback_count=100), proof, config, [], prices
    )
    assert result.tier == "maybe" and result.flags
    assert not prices["buy_now"]
    assert not price_signals(candidate, profile, summarize([]), 1, False, config.scoring)["buy_now"]


def test_pending_has_no_score_or_purchase_recommendation(
    config: Config, candidate: Listing, tmp_path: Path
):
    from vinted_hunter.pipeline.run import Pipeline

    with SQLiteStore(tmp_path / "state.sqlite") as store:
        Pipeline(tmp_path, store, config, NOW).record(
            candidate,
            config.profiles[0],
            [],
            Evidence(),
            False,
            pending=True,
            enriched=True,
        )
        row = store.record(candidate.id)
        assert (
            row["tier"] is row["score"] is row["trace"]["score"] is row["trace"]["pricing"] is None
        )


def test_market_requires_enriched_sweatshirt_and_excludes_fake(
    config: Config, candidate: Listing, tmp_path: Path
):
    from vinted_hunter.pipeline.run import market_for

    profile = config.profiles[0]
    item = candidate.model_copy(update={"category_id": config.ids.catalog_ids["sweatshirts"]})
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        for offset, category, enriched, tier, points in (
            (0, item.category_id, True, "good", 65),
            (1, item.category_id, True, "top", 90),
            (2, 5492, True, "top", 95),
            (3, item.category_id, False, "top", 90),
            (4, item.category_id, True, "rejected", 85),
            (5, item.category_id, True, "maybe", 59),
        ):
            row = item.model_copy(update={"id": item.id + offset, "category_id": category})
            store.save(row, profile.id, tier, points, {"enriched": enriched}, False)
        store.label(item.id + 1, "fake", NOW.isoformat())
        market = market_for(store, profile, config)
        assert market.count == 1 and market.median == item.price


def test_catalog_only_gate_keeps_enough_own_photos(config: Config, candidate: Listing) -> None:
    profile = config.profiles[0]
    listing = candidate.model_copy(update={"photos": candidate.photos * 5})
    three_own = Evidence(stock_photo=True, catalog_photo_count=2, catalog_first=True)
    assert gate(listing, profile, config, evidence=three_own)[0] == "catalog_photos_only"
    four_own = Evidence(stock_photo=True, catalog_photo_count=1, catalog_first=True)
    assert gate(listing, profile, config, evidence=four_own)[0] is None
    result = score(listing, profile, None, four_own, config, [], {"bargain": False})
    assert result.points["stock_photo"] == -20


def test_enrichment_prioritizes_fresh_before_backlog(config: Config, candidate: Listing) -> None:
    from vinted_hunter.pipeline.run import enrichment_priority

    profile = config.profiles[0]
    fresh = candidate.model_copy(update={"first_seen": NOW, "price": Decimal(50)})
    cheap_fresh = fresh.model_copy(update={"price": Decimal(40)})
    backlog = cheap_fresh.model_copy(update={"first_seen": NOW - timedelta(days=4)})
    ordered = sorted(
        [(backlog, False), (fresh, True), (cheap_fresh, True)],
        key=lambda job: enrichment_priority(job[0], profile, job[1], NOW),
    )
    assert [job[0] for job in ordered] == [cheap_fresh, fresh, backlog]
