import gzip
from datetime import UTC, datetime
from pathlib import Path

from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.sources.vinted.item import parse_item
from vinted_hunter.sources.vinted.user import parse_user, parse_wardrobe

FIXTURES = Path(__file__).parent / "fixtures"


def fixture(name: str) -> str:
    return gzip.decompress((FIXTURES / name).read_bytes()).decode()


def test_real_item_detail() -> None:
    catalog = parse_catalog(fixture("catalog-stone-island.html.gz"))
    listing = next(item for item in catalog.listings if item.id == 10682766478)
    observed = datetime(2026, 11, 6, 7, 30, tzinfo=UTC)
    detail = parse_item(fixture("item.html.gz"), listing, observed)
    assert len(detail.photos) == 5
    assert detail.description == "taglia xl comodo e calda"
    assert detail.color == "Blanco"
    assert detail.status == "very_good"
    assert detail.category_id == 267
    assert detail.favourites == 0
    assert detail.uploaded_at == datetime(2026, 11, 5, 23, 30, tzinfo=UTC)


def test_real_user_and_wardrobe() -> None:
    seller = parse_user(fixture("seller.json.gz"), 3139641830)
    closet = parse_wardrobe(fixture("seller.html.gz"), "https://www.vinted.es")
    assert seller.country == "IT"
    assert seller.feedback_count == 12
    assert seller.rating == 4.7
    assert len(closet) == seller.active_count == 18
    assert closet[0].id == 10682766478
    assert closet[0].brand == "Stone Island"
