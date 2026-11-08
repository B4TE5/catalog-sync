import gzip
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.availability import sale_statistics
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.models import Seller
from vinted_hunter.pipeline.score import score
from vinted_hunter.replay import evaluate_fixture
from vinted_hunter.sources.vinted.item import ITEM, item_availability, listing_from_item
from vinted_hunter.sources.vinted.parse import flight_payload, values
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests/fixtures/c3"


def captured(name: str):
    manifest = json.loads((FIXTURES / "capture.json").read_text(encoding="utf-8"))
    row = next(row for row in manifest["items"] if row["fixture"] == name)
    html = gzip.decompress((FIXTURES / name).read_bytes()).decode()
    return html, listing_from_item(html, row["url"], datetime.now(UTC))


@pytest.mark.parametrize("name,expected", [
    ("item-sold.html.gz", "sold"), ("item-active.html.gz", "active"),
])
def test_real_availability_banners_and_flags(name: str, expected: str) -> None:
    _, item = captured(name)
    assert item.availability == expected
    assert item.size == "XL" and item.size_source == "detail"


def test_unbuyable_is_not_automatically_sold_and_flags_take_priority() -> None:
    html, _ = captured("item-active.html.gz")
    raw = next(values(flight_payload(html), ITEM))
    assert item_availability(html, {**raw, "can_buy": False}) == "unknown"
    assert item_availability(html, {**raw, "is_reserved": True}) == "reserved"
    assert item_availability(html, {**raw, "is_hidden": True}) == "hidden"


@pytest.mark.parametrize("identifier,expected", [(10705167057, "M"), (10706690299, "S")])
def test_real_familiar_size_attribute(identifier: int, expected: str) -> None:
    _, item = captured(f"item-size-{identifier}.html.gz")
    assert item.size == expected and item.size_source == "detail"


def test_sale_statistics_exclude_unobserved_sale_times(tmp_path: Path) -> None:
    _, sold = captured("item-sold.html.gz")
    now = datetime.now(UTC)
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(sold, "stone-island", "good", 65, {}, False)
        assert sale_statistics(store.records())["stone-island"]["timed_count"] == 0
        active = sold.model_copy(update={
            "availability": "active", "last_active_at": now - timedelta(minutes=10),
            "uploaded_at": now - timedelta(minutes=60), "closed_observed_at": None,
        })
        store.update_listing(active, now - timedelta(minutes=10))
        observed = active.model_copy(update={
            "availability": "sold", "closed_observed_at": now,
            "observed_sale_price": active.price,
        })
        store.update_listing(observed, now)
        stats = sale_statistics(store.records())["stone-island"]
        assert stats["timed_count"] == 1 and stats["mean_minutes"] == 55
        assert stats["mean_lower_minutes"] == 50 and stats["mean_upper_minutes"] == 60
        assert store.db.execute("SELECT count(*) FROM listing_events").fetchone()[0] == 2


def test_feedback_blacklists_and_reverts_seller_and_adds_trust(tmp_path: Path) -> None:
    config = load_config(ROOT)
    row = evaluate_fixture(ROOT, ROOT / "tests/recall/10690539539")
    from vinted_hunter.pipeline.models import Evidence, Listing

    item = Listing.model_validate(row["body"])
    seller = Seller.model_validate(row["trace"]["seller"])
    evidence = Evidence.model_validate(row["trace"]["evidence"])
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(item, "stone-island", "good", 65, row["trace"], False)
        store.label(item.id, "fake", datetime.now(UTC).isoformat())
        assert "fake" in store.seller_flags(seller.id)
        blocked = seller.model_copy(update={"blacklisted": True})
        assert gate(item, config.profiles[0], config, blocked)[0] == "seller_blacklisted"
        store.label(item.id, "meh", datetime.now(UTC).isoformat())
        assert "fake" not in store.seller_flags(seller.id)
        store.label(item.id, "good", datetime.now(UTC).isoformat())
        assert "good" in store.seller_flags(seller.id)
        trusted = seller.model_copy(update={"trusted": True})
        points = score(item, config.profiles[0], trusted, evidence, config, [], {"bargain": False})
        assert points.points["trusted_seller"] == 10
