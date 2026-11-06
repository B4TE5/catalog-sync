"""Dedupe por ID, precio y fotografía principal."""

from decimal import Decimal

from vinted_hunter.pipeline.models import Evidence, Listing
from vinted_hunter.storage.sqlite_store import SQLiteStore


def distance(left: str, right: str) -> int:
    return (int(left, 16) ^ int(right, 16)).bit_count()


def is_drop(listing: Listing, previous: Decimal | None) -> bool:
    return previous is not None and listing.price < previous


def photo_dedupe(
    store: SQLiteStore,
    listing: Listing,
    evidence: Evidence,
    threshold: int,
) -> bool:
    if listing.seller_id is None:
        return False
    relisted = False
    for row in store.matching_hashes(listing.seller_id):
        if row["label"] == "fake" and row["hash"] in evidence.hashes:
            evidence.blacklisted_photo = True
        if (
            row["listing_id"] != listing.id
            and row["seller_id"] == listing.seller_id
            and row["is_primary"]
            and evidence.primary_hash is not None
            and distance(row["hash"], evidence.primary_hash) <= threshold
        ):
            relisted = True
            evidence.price_drop |= is_drop(listing, Listing.model_validate_json(row["body"]).price)
    evidence.shared_photo = any(
        store.shared_hash(value, listing.seller_id) for value in evidence.hashes
    )
    return relisted and not evidence.price_drop
