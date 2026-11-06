"""Anuncios del catálogo público español."""

import re
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlsplit

from pydantic import ValidationError

from vinted_hunter.pipeline.models import Listing
from vinted_hunter.sources.vinted.parse import ParseError, flight_payload, values

ITEMS = re.compile(r'"items"\s*:\s*\{\s*"items"\s*:\s*(\[)')
STATUS = {
    "Nuevo con etiquetas": "new_with_tags",
    "Nuevo sin etiquetas": "new_without_tags",
    "Muy bueno": "very_good",
    "Bueno": "good",
    "Satisfactorio": "satisfactory",
}


@dataclass
class CatalogResult:
    listings: list[Listing]
    raw_count: int
    invalid_count: int


def product_listing(product: dict[str, Any], base: str) -> Listing:
    box = product.get("itemBox") or {}
    size, _, condition = (box.get("secondLine") or "").partition(" · ")
    if not condition and size in STATUS:
        size, condition = "", size
    photos = [photo["url"] for photo in product.get("photos", []) if photo.get("url")]
    if not photos and product.get("thumbnailUrl"):
        photos.append(product["thumbnailUrl"])
    item_id = product["id"]
    path = product["url"]
    if not urlsplit(path).path.startswith(f"/items/{item_id}-"):
        raise ValueError("La ruta del anuncio no coincide con su ID")
    return Listing(
        id=item_id,
        title=product["title"],
        price=product["price"]["amount"],
        currency=product["price"]["currencyCode"],
        url=urljoin(base, path),
        photos=photos,
        seller_id=(product.get("user") or {}).get("id"),
        brand=box.get("firstLine"),
        size=size or None,
        status=STATUS.get(condition),
        favourites=product.get("favouriteCount"),
        protected_total=(product.get("totalItemPrice") or {}).get("amount"),
    )


def parse_catalog(html: str, base: str = "https://www.vinted.es/") -> CatalogResult:
    payload = flight_payload(html)
    groups = list(values(payload, ITEMS))
    if not groups:
        raise ParseError("RSC sin items.items")
    listings = {}
    raw_count = invalid_count = 0
    for group in groups:
        for row in group:
            raw_count += 1
            try:
                listing = product_listing(row["productItem"], base)
            except (KeyError, TypeError, AttributeError, ValidationError, ValueError):
                invalid_count += 1
                continue
            listings[listing.id] = listing
    if raw_count and not listings:
        raise ParseError(f"Ninguna de las {raw_count} tarjetas es válida")
    return CatalogResult(list(listings.values()), raw_count, invalid_count)
