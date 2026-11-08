import gzip
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.run import Pipeline
from vinted_hunter.sources.vinted.catalog import ITEMS, parse_catalog, product_listing
from vinted_hunter.sources.vinted.client import VintedClient
from vinted_hunter.sources.vinted.item import listing_from_item
from vinted_hunter.sources.vinted.parse import flight_payload, values
from vinted_hunter.storage.sqlite_store import SQLiteStore

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests/fixtures/c4"
MANIFEST = json.loads((FIXTURES / "capture.json").read_text(encoding="utf-8"))


def body(name: str) -> str:
    return gzip.decompress((FIXTURES / name).read_bytes()).decode()


@pytest.mark.parametrize("capture", MANIFEST["items"], ids=lambda row: str(row["id"]))
def test_real_catalog_and_detail_size_agree(capture: dict) -> None:
    detail = listing_from_item(body(capture["fixture"]), capture["url"], datetime.now(UTC))
    assert detail.size == capture["detail_size"]
    matches = [listing for catalog in MANIFEST["catalogs"]
               for listing in parse_catalog(body(catalog["fixture"])).listings
               if listing.id == detail.id]
    assert matches and all(item.size == detail.size for item in matches)
    if detail.size is None:
        assert detail.size_source == "absent"
        assert all(item.size_source == "unknown" for item in matches)


def test_actual_accessibility_label_can_supply_size_without_second_line() -> None:
    capture = MANIFEST["items"][1]
    for catalog in MANIFEST["catalogs"]:
        for group in values(flight_payload(body(catalog["fixture"])), ITEMS):
            for row in group:
                product = row["productItem"]
                if int(product["id"]) != capture["id"]:
                    continue
                box = {**product["itemBox"]}
                box.pop("secondLine", None)  # Frontera controlada sobre el payload real.
                parsed = product_listing({**product, "itemBox": box}, "https://www.vinted.es")
                assert parsed.size == capture["detail_size"] and parsed.size_source == "catalog"
                return
    pytest.fail("La captura debe contener el anuncio comprobado")


def test_pending_refresh_never_erases_a_previously_confirmed_size(tmp_path: Path) -> None:
    capture = MANIFEST["items"][1]
    now = datetime.now(UTC)
    detail = listing_from_item(body(capture["fixture"]), capture["url"], now)
    refreshed = detail.model_copy(update={"size": None, "size_source": "unknown"})
    config = load_config(ROOT)
    profile = next(p for p in config.profiles if p.id == "stone-island")
    with SQLiteStore(tmp_path / "state.sqlite") as store:
        store.save(detail, profile.id, None, None, {"pending": True, "enriched": True}, False)
        store.save(refreshed, profile.id, None, None, {"pending": True}, False)
        assert store.listing(detail.id).size == detail.size
        pipeline = Pipeline(tmp_path, store, config, now)
        with VintedClient() as client:
            pipeline.process(client, {detail.id: (refreshed, profile, True)}, False, 0)
            assert client.requests == 0
        assert store.listing(detail.id).size == detail.size
        assert store.listing(detail.id).size_source == "detail"
