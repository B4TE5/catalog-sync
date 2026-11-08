"""Ficha pública y atributos de un anuncio."""

import re
from datetime import datetime, timedelta
from decimal import Decimal
from html.parser import HTMLParser
from urllib.parse import urlsplit

from vinted_hunter.pipeline.models import Availability, Listing
from vinted_hunter.sources.vinted.catalog import STATUS
from vinted_hunter.sources.vinted.parse import ParseError, flight_payload, values

ITEM = re.compile(r'"item":(\{"brand_dto":)')
ATTRIBUTES = re.compile(r'"attributes":(\[)')
DESCRIPTION = re.compile(r'"description":(")')
PHOTOS = re.compile(r'"photos":(\[)')
PRICE = re.compile(r'"price":(\{)')
CANONICAL = re.compile(r'<link[^>]*rel="canonical"[^>]*href="([^"]+)"')
FAVOURITES = re.compile(r'"favourite_count":(\d)')
RELATIVE_DATE = re.compile(
    r"hace (\d+|un|una) (minutos?|horas?|días?|semanas?|mes(?:es)?|años?)"
)


class SaleBanner(HTMLParser):
    """Lee el banner renderizado; ignora las traducciones dentro de scripts."""

    def __init__(self) -> None:
        super().__init__()
        self.stack: list[tuple[str, str]] = []
        self.sold = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack.append((tag, dict(attrs).get("class") or ""))

    def handle_endtag(self, tag: str) -> None:
        for index in range(len(self.stack) - 1, -1, -1):
            if self.stack[index][0] == tag:
                del self.stack[index:]
                break

    def handle_data(self, data: str) -> None:
        if any(tag in {"script", "style"} for tag, _ in self.stack):
            return
        if data.strip() in {"Vendido", "Sold"} and any(
            "web_ui__Cell__success" in classes for _, classes in self.stack
        ):
            self.sold = True


def item_availability(html: str, item: dict) -> Availability:
    if item.get("is_hidden") is True:
        return "hidden"
    if item.get("is_reserved") is True:
        return "reserved"
    banner = SaleBanner()
    banner.feed(html)
    if banner.sold:
        return "sold"
    return "active" if item.get("can_buy") is True else "unknown"


def approximate_upload(label: str, observed: datetime) -> datetime | None:
    match = RELATIVE_DATE.fullmatch(label)
    if match is None:
        return None
    count = int(match[1]) if match[1].isdigit() else 1
    if match[2].startswith(("mes", "año")):
        from calendar import monthrange

        months = count if match[2].startswith("mes") else count * 12
        year, month = divmod(observed.year * 12 + observed.month - 1 - months, 12)
        return observed.replace(year=year, month=month + 1,
                                day=min(observed.day, monthrange(year, month + 1)[1]))
    unit = {"m": "minutes", "h": "hours", "d": "days", "s": "weeks"}[match[2][0]]
    return observed - timedelta(**{unit: count})


def parse_item(html: str, listing: Listing, observed: datetime) -> Listing:
    payload = flight_payload(html)
    item = next(
        (item for item in values(payload, ITEM) if str(item.get("id")) == str(listing.id)), None
    )
    if item is None:
        raise ParseError(f"Ficha sin datos del anuncio {listing.id}")
    attributes = {
        row["code"]: row["data"].get("value") for row in next(values(payload, ATTRIBUTES), [])
    }
    photo_groups = list(values(payload, PHOTOS))
    photos = max(photo_groups, key=len, default=[])
    data = listing.model_dump()
    actual_size = attributes.get("size") or attributes.get("size_familiar")
    availability = item_availability(html, item)
    actual_price = next(values(payload, PRICE), None)
    data.update(
        brand=attributes.get("brand") or listing.brand,
        title=item.get("title") or listing.title,
        size=actual_size or listing.size,
        size_source="detail" if actual_size else
        listing.size_source if listing.size else "absent",
        status=STATUS.get(attributes.get("status")),
        color=attributes.get("color"),
        material=attributes.get("material"),
        category_id=item.get("catalog_id"),
        seller_id=item.get("seller_id") or listing.seller_id,
        description=next(values(payload, DESCRIPTION), None),
        photos=[photo["url"] for photo in photos if photo.get("url")] or listing.photos,
        favourites=next(values(payload, FAVOURITES), listing.favourites),
        uploaded_at=approximate_upload(attributes.get("upload_date") or "", observed)
        or listing.uploaded_at,
        availability=availability,
        availability_checked_at=observed,
        last_active_at=observed if availability == "active" else listing.last_active_at,
    )
    if actual_price:
        data.update(price=actual_price["amount"], currency=actual_price["currency_code"])
        if Decimal(str(actual_price["amount"])) != listing.price:
            data["protected_total"] = None
    if availability in {"sold", "reserved", "hidden", "gone"}:
        data["closed_observed_at"] = (
            listing.closed_observed_at or observed
            if listing.availability == availability else observed
        )
    if availability == "sold":
        data["observed_sale_price"] = data["price"]
    elif availability == "active":
        data.update(closed_observed_at=None, observed_sale_price=None)
    return Listing.model_validate(data)


def listing_from_item(html: str, url: str, observed: datetime) -> Listing:
    """Arranca el análisis desde una ficha pública, incluida una prenda vendida."""
    parts = urlsplit(url)
    identifier = re.fullmatch(r"/items/([1-9][0-9]*)(?:-[^/]*)?/?", parts.path)
    if parts.scheme != "https" or parts.hostname != "www.vinted.es" or not identifier:
        raise ValueError("Se requiere una ficha HTTPS de www.vinted.es")
    payload = flight_payload(html)
    item = next(
        (row for row in values(payload, ITEM) if str(row.get("id")) == identifier[1]), None
    )
    price = next(values(payload, PRICE), None)
    photos = max(values(payload, PHOTOS), key=len, default=[])
    if item is None or not price or not photos:
        raise ParseError("Ficha sin precio, fotos o datos del anuncio")
    canonical = CANONICAL.search(html)
    if canonical:
        actual = urlsplit(canonical[1])
        actual_id = re.match(r"/items/([0-9]+)(?:-|/|$)", actual.path)
        if (
            actual.scheme == "https" and actual.hostname == parts.hostname
            and actual_id and actual_id[1] == identifier[1]
        ):
            url = canonical[1]
    listing = Listing(
        id=int(identifier[1]), title=item["title"], price=price["amount"],
        currency=price["currency_code"], url=url,
        photos=[photo["url"] for photo in photos if photo.get("url")],
    )
    return parse_item(html, listing, observed)
