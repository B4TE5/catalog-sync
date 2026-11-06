"""Ficha pública y atributos de un anuncio."""

import re
from datetime import datetime, timedelta

from vinted_hunter.pipeline.models import Listing
from vinted_hunter.sources.vinted.catalog import STATUS
from vinted_hunter.sources.vinted.parse import ParseError, flight_payload, values

ITEM = re.compile(r'"item":(\{"brand_dto":)')
ATTRIBUTES = re.compile(r'"attributes":(\[)')
DESCRIPTION = re.compile(r'"description":(")')
PHOTOS = re.compile(r'"photos":(\[)')
FAVOURITES = re.compile(r'"favourite_count":(\d)')
RELATIVE_DATE = re.compile(r"hace (\d+|un|una) (minutos?|horas?|días?|semanas?)")


def approximate_upload(label: str, observed: datetime) -> datetime | None:
    match = RELATIVE_DATE.fullmatch(label)
    if match is None:
        return None
    count = int(match[1]) if match[1].isdigit() else 1
    unit = {"m": "minutes", "h": "hours", "d": "days", "s": "weeks"}[match[2][0]]
    return observed - timedelta(**{unit: count})


def parse_item(html: str, listing: Listing, observed: datetime) -> Listing:
    payload = flight_payload(html)
    item = next((item for item in values(payload, ITEM)
                 if str(item.get("id")) == str(listing.id)), None)
    if item is None:
        raise ParseError(f"Ficha sin datos del anuncio {listing.id}")
    attributes = {
        row["code"]: row["data"].get("value")
        for row in next(values(payload, ATTRIBUTES), [])
    }
    photo_groups = list(values(payload, PHOTOS))
    photos = max(photo_groups, key=len, default=[])
    data = listing.model_dump()
    data.update(
        brand=attributes.get("brand") or listing.brand,
        size=attributes.get("size") or listing.size,
        status=STATUS.get(attributes.get("status"), listing.status),
        color=attributes.get("color"),
        category_id=item.get("catalog_id"),
        seller_id=item.get("seller_id") or listing.seller_id,
        description=next(values(payload, DESCRIPTION), None),
        photos=[photo["url"] for photo in photos if photo.get("url")] or listing.photos,
        favourites=next(values(payload, FAVOURITES), listing.favourites),
        uploaded_at=approximate_upload(attributes.get("upload_date") or "", observed),
    )
    return Listing.model_validate(data)
