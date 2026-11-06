import gzip
from datetime import UTC, datetime, timedelta
from pathlib import Path

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.pricing import timing
from vinted_hunter.sources.vinted.catalog import parse_catalog

ROOT = Path(__file__).parents[1]


def test_heat_uses_favourites_and_age_only() -> None:
    fixture = ROOT / "tests/fixtures/catalog-stone-island.html.gz"
    listing = parse_catalog(gzip.decompress(fixture.read_bytes()).decode()).listings[0]
    now = datetime(2026, 11, 6, tzinfo=UTC)
    listing.uploaded_at = now - timedelta(minutes=2)
    listing.favourites = 10
    scoring = load_config(ROOT).scoring
    baseline = timing(listing, now, scoring)
    assert baseline["age_minutes"] == 2
    assert baseline["heat"] == 10 / scoring.thresholds["heat_min_age"]
    listing.views = 100_000
    assert timing(listing, now, scoring) == baseline
    listing.favourites = None
    assert timing(listing, now, scoring)["heat"] == 0
