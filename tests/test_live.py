from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vinted_hunter.config import load_config
from vinted_hunter.diagnostics import configured_ids
from vinted_hunter.sources.vinted.catalog import CatalogResult, parse_catalog
from vinted_hunter.sources.vinted.client import VintedClient
from vinted_hunter.sources.vinted.item import parse_item
from vinted_hunter.sources.vinted.user import parse_user, parse_wardrobe

pytestmark = pytest.mark.live
ROOT = Path(__file__).parents[1]


@pytest.fixture(scope="module")
def client() -> Iterator[VintedClient]:
    with VintedClient() as instance:
        response = instance.home()
        assert response.status_code == 200
        assert len(instance.session.cookies) > 0
        yield instance


@pytest.fixture(scope="module")
def catalog(client: VintedClient) -> CatalogResult:
    response = client.get(
        "/catalog", "catalog", {
            "search_text": "stone island", "order": "newest_first",
            "catalog[]": load_config(ROOT).ids.catalog_ids["sweatshirts_parent"],
        }
    )
    return parse_catalog(response.text, client.base)


def test_live_catalog(catalog: CatalogResult) -> None:
    assert len(catalog.listings) >= 10
    assert catalog.invalid_count < catalog.raw_count


def test_live_detail_seller_and_wardrobe(client: VintedClient, catalog: CatalogResult) -> None:
    listing = next(item for item in catalog.listings if item.seller_id is not None)
    response = client.get(str(listing.url), "enrich")
    detail = parse_item(response.text, listing, datetime.now(UTC))
    assert detail.photos and detail.seller_id
    response = client.get(f"/api/v2/users/{detail.seller_id}", "enrich")
    seller = parse_user(response.text, detail.seller_id)
    assert seller.feedback_count is not None
    response = client.get(f"/member/{detail.seller_id}", "enrich")
    closet = parse_wardrobe(response.text, client.base)
    assert closet or seller.active_count == 0


@pytest.mark.parametrize("label", ["L", "XL"])
def test_live_filtered_catalog(client: VintedClient, label: str) -> None:
    ids = load_config(ROOT).ids
    assert not configured_ids(ROOT)
    size = ids.size_ids[label]
    response = client.get(
        "/catalog",
        "catalog",
        {
            "catalog[]": ids.catalog_ids["sweatshirts_parent"],
            "brand_ids[]": ids.brand_ids["Stone Island"][0],
            "size_ids[]": size,
            "order": "newest_first",
        },
    )
    result = parse_catalog(response.text, client.base)
    assert result.listings, (
        f"Stone Island {label}: el filtro público devolvió {result.raw_count} tarjetas. "
        f"Taxonomía pendiente: {', '.join(configured_ids(ROOT))}"
    )
    assert all(item.brand == "Stone Island" and item.size == label for item in result.listings)
