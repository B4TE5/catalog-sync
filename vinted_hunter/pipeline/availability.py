"""Comprobaciones públicas de disponibilidad e intervalos observados de venta."""

from collections import defaultdict
from datetime import datetime
from statistics import mean
from typing import Any

from vinted_hunter.pipeline.enrich import get_item
from vinted_hunter.pipeline.models import Listing
from vinted_hunter.sources.vinted.client import HttpFailure, VintedClient
from vinted_hunter.storage.base import StateStore

CLOSED = frozenset({"sold", "reserved", "hidden", "gone"})


def check_listing(
    client: VintedClient, store: StateStore, listing: Listing, now: datetime,
) -> Listing:
    try:
        current = get_item(client, listing, now)
    except HttpFailure as error:
        if error.status != 404:
            raise
        current = listing.model_copy(update={
            "availability": "gone", "availability_checked_at": now,
            "closed_observed_at": listing.closed_observed_at or now,
            "size_source": listing.size_source if listing.size else "unavailable",
        })
    store.update_listing(current, now)
    if current.price != listing.price and (row := store.record(listing.id)):
        store.observe_price(current, row["profile"], now.isoformat())
        if current.price < listing.price:
            row["trace"].setdefault("evidence", {})["price_drop"] = True
            store.save(current, row["profile"], row["tier"], row["score"],
                       row["trace"], bool(row["backfill"]))
    return current


def sale_statistics(rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    groups: dict[str, list[Listing]] = defaultdict(list)
    for row in rows:
        item = Listing.model_validate(row["body"])
        if item.availability == "sold" and row["tier"] in {"top", "good", "maybe", "low"}:
            groups[row["profile"]].append(item)

    def summarize(items: list[Listing]) -> dict[str, Any]:
        bounds = []
        for item in items:
            if item.uploaded_at and item.last_active_at and item.closed_observed_at:
                lower = max(0, (item.last_active_at - item.uploaded_at).total_seconds() / 60)
                upper = max(lower, (item.closed_observed_at - item.uploaded_at).total_seconds()/60)
                bounds.append((lower, upper))
        return {
            "count": len(items), "timed_count": len(bounds),
            "mean_minutes": round(mean((low + high) / 2 for low, high in bounds))
            if bounds else None,
            "mean_lower_minutes": round(mean(low for low, _ in bounds)) if bounds else None,
            "mean_upper_minutes": round(mean(high for _, high in bounds)) if bounds else None,
            "estimated": True, "price_source": "displayed_at_detection",
        }

    result = {}
    for profile, items in groups.items():
        prices: dict[str, list[Listing]] = defaultdict(list)
        for item in items:
            prices[f"{item.observed_sale_price or item.price:.2f}"].append(item)
        result[profile] = {
            **summarize(items),
            "by_price": {price: summarize(values) for price, values in prices.items()},
        }
    return result
