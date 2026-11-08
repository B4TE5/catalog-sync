import gzip
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.sources.vinted.item import listing_from_item

ROOT = Path(__file__).parents[1]


def test_stone_sixty_euros_is_inclusive_and_excludes_fees() -> None:
    config = load_config(ROOT)
    item = listing_from_item(
        gzip.decompress((ROOT / "tests/recall/10690539539/item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater", datetime.now(UTC),
    )
    assert item.price == Decimal("60")
    expensive_total = item.model_copy(update={"protected_total": Decimal("100")})
    assert gate(expensive_total, config.profiles[0], config, detailed=True)[0] is None
    assert gate(item.model_copy(update={"price": Decimal("60.01")}), config.profiles[0],
                config, detailed=True)[0] == "price"


def test_active_profiles_only_accept_the_three_allowed_conditions() -> None:
    config = load_config(ROOT)
    allowed = {"new_without_tags", "very_good", "new_with_tags"}
    assert config.profiles
    assert all(set(profile.allowed_status) == allowed for profile in config.profiles)
