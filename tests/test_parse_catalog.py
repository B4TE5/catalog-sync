import gzip
from pathlib import Path

import pytest

from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.sources.vinted.parse import ParseError

FIXTURES = Path(__file__).parent / "fixtures"


def test_real_stone_island_catalog() -> None:
    with gzip.open(FIXTURES / "catalog-stone-island.html.gz", "rt", encoding="utf-8") as body:
        result = parse_catalog(body.read())
    assert len(result.listings) == result.raw_count == 96
    assert result.invalid_count == 0
    first = result.listings[0]
    assert first.id == 10683035041
    assert first.brand == "Stone Island"
    assert first.size == "M"
    assert first.status == "new_without_tags"
    assert first.seller_id == 3209195522
    assert first.currency == "EUR"
    assert first.photos[0].scheme == "https"


def test_missing_payload_is_not_an_empty_search() -> None:
    with pytest.raises(ParseError, match="RSC"):
        parse_catalog("")


def test_verified_empty_filter_has_valid_structure() -> None:
    with gzip.open(FIXTURES / "catalog-empty-size.html.gz", "rt", encoding="utf-8") as body:
        result = parse_catalog(body.read())
    assert result.raw_count == result.invalid_count == 0
    assert not result.listings


def test_real_combined_brand_catalog() -> None:
    with gzip.open(FIXTURES / "catalog-combined.html.gz", "rt", encoding="utf-8") as body:
        result = parse_catalog(body.read())
    assert len(result.listings) == 96
    assert {item.brand for item in result.listings} == {"Stone Island", "Supreme"}

@pytest.mark.parametrize("label", ["L", "XL"])
def test_real_mens_size_filter(label: str) -> None:
    with gzip.open(FIXTURES / f"catalog-size-{label}.html.gz", "rt", encoding="utf-8") as body:
        result = parse_catalog(body.read())
    assert result.listings
    assert {(item.brand, item.size) for item in result.listings} == {("Stone Island", label)}
