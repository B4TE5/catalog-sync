"""Ficha, vendedor y caché de imágenes por URL."""

import hashlib
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlsplit

from vinted_hunter.config import Capture
from vinted_hunter.pipeline.models import Listing, Seller
from vinted_hunter.sources.vinted.client import BudgetExhausted, VintedClient
from vinted_hunter.sources.vinted.item import parse_item
from vinted_hunter.sources.vinted.user import parse_user, parse_wardrobe
from vinted_hunter.storage.base import StateStore


def get_item(client: VintedClient, listing: Listing, now: datetime) -> Listing:
    response = client.get(str(listing.url), "enrich")
    return parse_item(response.text, listing, now)


def get_seller(
    client: VintedClient,
    store: StateStore,
    seller_id: int,
    now: datetime,
    settings: Capture,
) -> Seller:
    seller = store.seller(seller_id, now - timedelta(hours=settings.seller_hours))
    if seller and seller.closet is not None:
        return seller
    if seller is None:
        response = client.get(f"/api/v2/users/{seller_id}", "enrich")
        seller = parse_user(response.text, seller_id)
        store.cache_seller(seller, now)
    response = client.get(f"/member/{seller_id}", "enrich")
    seller.closet = parse_wardrobe(response.text, client.base)
    store.cache_seller(seller, now)
    return seller


def image_path(cache: Path, url: str) -> Path:
    return cache / hashlib.sha256(url.encode()).hexdigest()


def image_bytes(
    client: VintedClient,
    listing: Listing,
    cache: Path,
    settings: Capture,
    *,
    require_budget: bool = False,
) -> list[bytes]:
    cache.mkdir(parents=True, exist_ok=True)
    images = []
    for photo in listing.photos[: settings.max_photos]:
        url = str(photo)
        parts = urlsplit(url)
        if parts.scheme != "https" or not (parts.hostname or "").endswith(".vinted.net"):
            continue
        path = image_path(cache, url)
        if path.exists():
            images.append(path.read_bytes())
            continue
        try:
            response = client.get(url, "enrich")
        except BudgetExhausted:
            if require_budget:
                raise
            break
        if response.headers.get("Content-Type", "").startswith("image/"):
            with NamedTemporaryFile("wb", dir=cache, delete=False) as file:
                temporary = Path(file.name)
                file.write(response.content)
            try:
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)
            images.append(response.content)
    return images
