"""Ficha, vendedor y caché de imágenes por URL."""

import hashlib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
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
    return parse_item(response.text, listing, datetime.now(UTC))


def get_seller(
    client: VintedClient,
    store: StateStore,
    seller_id: int,
    now: datetime,
    settings: Capture,
) -> Seller:
    flags = store.seller_flags(seller_id)
    if "fake" in flags:
        return Seller(id=seller_id, blacklisted=True)
    seller = store.seller(seller_id, now - timedelta(hours=settings.seller_hours))
    if seller and seller.closet is not None:
        return seller.model_copy(update={"blacklisted": False, "trusted": "good" in flags})
    if seller is None:
        response = client.get(f"/api/v2/users/{seller_id}", "enrich")
        seller = parse_user(response.text, seller_id)
        store.cache_seller(seller, now)
    response = client.get(f"/member/{seller_id}", "enrich")
    seller.closet = parse_wardrobe(response.text, client.base)
    store.cache_seller(seller, now)
    return seller.model_copy(update={"blacklisted": False, "trusted": "good" in flags})


def image_path(cache: Path, url: str) -> Path:
    return cache / hashlib.sha256(url.encode()).hexdigest()


def image_bytes(
    client: VintedClient,
    listing: Listing,
    cache: Path,
    settings: Capture,
    *,
    require_budget: bool = False,
) -> list[bytes | None]:
    cache.mkdir(parents=True, exist_ok=True)
    photos = listing.photos[: settings.max_photos]
    images: list[bytes | None] = [None] * len(photos)
    missing = []
    for index, photo in enumerate(photos):
        url = str(photo)
        parts = urlsplit(url)
        if parts.scheme != "https" or not (parts.hostname or "").endswith(".vinted.net"):
            continue
        path = image_path(cache, url)
        if path.is_file():
            images[index] = path.read_bytes()
        else:
            missing.append((index, url, path))

    def fetch(job: tuple[int, str, Path]) -> tuple[int, bytes | None]:
        index, url, path = job
        try:
            response = client.get_cdn(url, settings.cdn_timeout)
        except BudgetExhausted:
            return index, None
        if not response.headers.get("Content-Type", "").startswith("image/"):
            return index, None
        with NamedTemporaryFile("wb", dir=cache, delete=False) as file:
            temporary = Path(file.name)
            file.write(response.content)
        try:
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        return index, response.content

    quota = client.remaining("enrich")
    if missing and quota:
        with ThreadPoolExecutor(max_workers=settings.cdn_workers) as pool:
            for index, image in pool.map(fetch, missing[:quota]):
                images[index] = image
    if require_budget and (
        len(missing) > quota
        or (
            client.remaining("enrich") == 0
            and any(images[index] is None for index, _, _ in missing)
        )
    ):
        raise BudgetExhausted("Cuota de imágenes agotada")
    return images
