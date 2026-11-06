"""Precios observados, percentiles y oferta orientativa."""

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal

from vinted_hunter.config import Profile, Scoring
from vinted_hunter.pipeline.models import Listing


@dataclass
class Market:
    count: int = 0
    median: Decimal | None = None
    p25: Decimal | None = None
    p10: Decimal | None = None


def percentile(sorted_prices: list[Decimal], rank: Decimal) -> Decimal:
    position = rank * (len(sorted_prices) - 1)
    lower = int(position)
    upper = min(lower + 1, len(sorted_prices) - 1)
    return sorted_prices[lower] + (sorted_prices[upper] - sorted_prices[lower]) * (position - lower)


def summarize(prices: list[Decimal]) -> Market:
    if not prices:
        return Market()
    ordered = sorted(prices)
    return Market(
        len(prices), *(percentile(ordered, Decimal(rank)) for rank in ("0.5", "0.25", "0.10"))
    )


def timing(listing: Listing, now: datetime, scoring: Scoring) -> dict:
    source = listing.uploaded_at or listing.first_seen or now
    minutes = max(0, (now - source).total_seconds() / 60)
    heat = (listing.favourites or 0) / max(minutes, scoring.thresholds["heat_min_age"])
    return {
        "age_minutes": round(minutes),
        "age_estimated": listing.uploaded_at is None,
        "heat": round(heat, 3),
        "hot": heat > scoring.thresholds["heat"],
    }


def price_signals(
    listing: Listing,
    profile: Profile,
    market: Market,
    age: int,
    price_drop: bool,
    scoring: Scoring,
) -> dict:
    settings = scoring.pricing
    protected = listing.protected_total
    if protected is None:
        protected = (
            listing.price * (1 + settings["protection_fraction"]) + settings["protection_fixed"]
        )
    shipping = listing.shipping if listing.shipping is not None else settings["shipping_estimate"]
    p25 = market.p25 if market.count >= settings["minimum_samples"] else None
    fresh_limit = p25 if p25 is not None else profile.price_max * settings["fresh_ratio"]
    buy = age < settings["fresh_minutes"] and listing.price <= fresh_limit
    negotiable = age >= settings["negotiable_days"] * 24 * 60 or price_drop
    step = settings["round_euros"]
    offer = listing.price * settings["default_ratio"]
    if negotiable:
        offer = max(listing.price * settings["negotiable_ratio"], market.p10 or Decimal(0))
    offer = (offer / step).quantize(Decimal(1), rounding=ROUND_HALF_UP) * step
    return {
        "total": str((protected + shipping).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)),
        "estimated": listing.protected_total is None or listing.shipping is None,
        "bargain": p25 is not None and listing.price <= p25,
        "under_median": round(float(1 - listing.price / market.median) * 100, 1)
        if market.median
        else None,
        "buy_now": buy,
        "offer": None if buy else str(min(offer, listing.price)),
        "negotiable": negotiable,
    }
