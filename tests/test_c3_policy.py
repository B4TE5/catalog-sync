import gzip
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.gates import garment_reason, gate
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.pipeline.run import enrichment_priority
from vinted_hunter.sources.vinted.item import listing_from_item
from vinted_hunter.sources.vinted.search import plan_searches

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


def test_notifications_are_enabled_with_the_requested_profile_thresholds() -> None:
    config = load_config(ROOT)
    assert config.scoring.shadow_mode is False
    assert {p.id: p.notify_min_tier for p in config.profiles} == {
        "stone-island": "top", "twojeys": "top", "yzy-gap": "top",
        "heron-preston": "top", "rhude": "top",
    }
    assert {p.id for p in config.profiles if p.notify_enabled} == {"stone-island"}


def test_catalog_size_fallback_cannot_confirm_a_detail_mismatch() -> None:
    config = load_config(ROOT)
    item = listing_from_item(
        gzip.decompress((ROOT / "tests/recall/10690539539/item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater", datetime.now(UTC),
    )
    fallback = item.model_copy(update={"size": "M", "size_source": "catalog"})
    reason, passed = gate(fallback, config.profiles[0], config, detailed=True)
    assert reason is None and "size_unconfirmed" in passed
    assert gate(fallback.model_copy(update={"size_source": "detail"}), config.profiles[0],
                config, detailed=True)[0] == "size"


def test_enrichment_prioritizes_requested_size_without_discarding_unknowns() -> None:
    config = load_config(ROOT)
    now = datetime.now(UTC)
    item = listing_from_item(
        gzip.decompress((ROOT / "tests/recall/10690539539/item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10690539539-stone-island-sweater", now,
    )
    wanted = item.model_copy(update={"size_source": "catalog"})
    unknown = item.model_copy(update={"size": None, "price": Decimal("30")})
    mismatch = unknown.model_copy(update={"size": "M", "size_source": "catalog"})
    profile = config.profiles[0]
    def priority(listing: Listing) -> tuple:
        return enrichment_priority(listing, profile, False, now)

    assert priority(wanted) < priority(unknown) < priority(mismatch)
    assert gate(unknown, profile, config)[0] is None
    assert gate(mismatch, profile, config)[0] is None
    # Las novedades conservan prioridad sobre el stock antiguo.
    assert enrichment_priority(mismatch, profile, True, now) < priority(wanted)


def test_existing_real_case_can_use_profile_specific_type_rules() -> None:
    config = load_config(ROOT)
    item = listing_from_item(
        gzip.decompress((ROOT / "tests/precision/10683026176/item.html.gz").read_bytes()).decode(),
        "https://www.vinted.es/items/10683026176", datetime.now(UTC),
    )
    original = next(p for p in config.profiles if p.id == "twojeys")
    assert garment_reason(item, original, config, detailed=True) == "not_sweatshirt"
    assert item.category_id is not None
    categories = original.categories.model_copy(update={
        "search": [item.category_id], "accept": [item.category_id],
        "conditional": [], "exclude": [],
    })
    configured = original.model_copy(update={
        "categories": categories, "type_keywords_exclude": [],
        "material_keywords_exclude": [], "material_keywords_exclude_exact": [],
        "hood": None, "size": None,
    })
    configured_config = config.model_copy(update={"profiles": [configured]})
    assert garment_reason(item, configured, configured_config, detailed=True) is None
    queries, _ = plan_searches(configured_config)
    assert queries and all(q.params["catalog[]"] == str(item.category_id) for q in queries)
