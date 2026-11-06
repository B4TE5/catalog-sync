"""Perfil público y primera página del armario."""

import json
import re

from pydantic import ValidationError

from vinted_hunter.pipeline.models import Listing, Seller
from vinted_hunter.sources.vinted.catalog import product_listing
from vinted_hunter.sources.vinted.parse import ParseError, flight_payload, values

WARDROBE = re.compile(r'"initialWardrobeItems":(\{)')


def parse_user(body: str, seller_id: int) -> Seller:
    try:
        user = json.loads(body)["user"]
        if user["id"] != seller_id:
            raise ParseError("El ID del perfil no coincide")
        reputation = user.get("feedback_reputation")
        return Seller(
            id=seller_id,
            feedback_count=user.get("feedback_count"),
            rating=round(5 * reputation, 2) if reputation is not None else None,
            country=user.get("country_code"),
            city=user.get("city"),
            last_seen=user.get("last_loged_on_ts"),
            active_count=user.get("item_count"),
            professional=user.get("business"),
        )
    except (TypeError, KeyError, json.JSONDecodeError, ValidationError) as error:
        raise ParseError("Perfil sin datos de vendedor válidos") from error


def parse_wardrobe(html: str, base: str) -> list[Listing]:
    wardrobe = next(values(flight_payload(html), WARDROBE), None)
    if wardrobe is None or not isinstance(wardrobe.get("items"), list):
        raise ParseError("Armario sin initialWardrobeItems.items")
    listings = []
    for product in wardrobe["items"]:
        try:
            listings.append(product_listing(product, base))
        except (KeyError, TypeError, AttributeError, ValueError):
            continue
    return listings
