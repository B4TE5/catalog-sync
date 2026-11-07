"""Diagnóstico y casos de regresión derivados de fichas públicas reales."""

import gzip
import json
import shutil
import sqlite3
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any
from urllib.parse import urlsplit

from curl_cffi.requests import Response

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.enrich import image_path
from vinted_hunter.pipeline.gates import gate
from vinted_hunter.pipeline.models import Evidence
from vinted_hunter.pipeline.run import Pipeline, select_profiles
from vinted_hunter.pipeline.text import matches, normalize
from vinted_hunter.pipeline.vision import inspect_photos
from vinted_hunter.sources.vinted.client import Budget, VintedClient
from vinted_hunter.sources.vinted.item import listing_from_item
from vinted_hunter.sources.vinted.search import plan_searches
from vinted_hunter.sources.vinted.user import parse_user, parse_wardrobe
from vinted_hunter.storage.sqlite_store import SQLiteStore


class ReplayClient(VintedClient):
    def __init__(self) -> None:
        super().__init__(enrich_limit=24)
        self.captures: dict[str, bytes] = {}

    def get(
        self, path: str, budget: Budget | None = None, params: Any = None
    ) -> Response:
        response = super().get(path, budget, params)
        if budget == "enrich":
            self.captures[urlsplit(response.url).path] = response.content
        return response


def query_coverage(root: Path, record: dict[str, Any]) -> list[dict[str, Any]]:
    config = load_config(root)
    item = record["body"]
    searches, _ = plan_searches(config)
    covered = []
    text = f"{item['title']} {item.get('description') or ''}"
    for search in searches:
        if not any(p.id == record["profile"] for p in search.profiles):
            continue
        query = search.params.get("search_text")
        words = normalize(str(query or "")).split()
        text_match = all(matches(text, [word]) for word in words)
        size = search.params.get("size_ids[]")
        expected = config.ids.size_ids.get(item.get("size"))
        size_match = size is None or str(expected) == size
        category = item.get("category_id")
        category_match = category in {
            config.ids.catalog_ids.get(key)
            for key in ("sweatshirts", "zip_sweatshirts", "jumpers")
        }
        mismatches = []
        if not text_match:
            mismatches.append("El texto no contiene todos los términos de la consulta")
        if not size_match:
            mismatches.append("La talla difiere del filtro")
        if not category_match:
            mismatches.append("La categoría queda fuera del grupo de sudaderas y jerséis")
        covered.append({
            "query": search.query(1), "compatible": text_match and size_match and category_match,
            "reason": " · ".join(mismatches) or "Texto, talla y categoría compatibles",
        })
    return covered


def replay(root: Path, url: str, save_fixture: str | None = None) -> dict[str, Any]:
    parts = urlsplit(url)
    if (
        parts.scheme != "https" or parts.hostname != "www.vinted.es"
        or parts.username or parts.password or not parts.path.startswith("/items/")
    ):
        raise ValueError("Se requiere una ficha HTTPS de www.vinted.es")
    now = datetime.now(UTC)
    config = load_config(root, include_disabled=True)
    folder = root / "data"
    folder.mkdir(exist_ok=True)
    with TemporaryDirectory(dir=folder) as temporary, ReplayClient() as client:
        client.home()
        response = client.get(url, "enrich")
        listing = listing_from_item(response.text, url, now)
        profiles = select_profiles(listing, config.profiles, config)
        if not profiles:
            raise ValueError("La marca de la ficha no tiene perfil configurado")
        profile = profiles[0]
        path = Path(temporary) / "replay.sqlite"
        source = folder / "vh.sqlite"
        if source.is_file():
            with closing(sqlite3.connect(source.as_uri() + "?mode=ro", uri=True)) as original:
                with closing(sqlite3.connect(path)) as copy:
                    original.backup(copy)
        with SQLiteStore(path) as store:
            if listing.seller_id:
                store.db.execute("DELETE FROM sellers WHERE id=?", (listing.seller_id,))
            pipeline = Pipeline(root, store, config, now)
            pipeline.candidate(
                client, listing, profile, False, Evidence(), False, detail_loaded=True
            )
            record = store.record(listing.id)
            if record is None or record["trace"].get("pending"):
                raise ValueError("El anuncio no pudo completar el enriquecimiento")
        record["query_coverage"] = query_coverage(root, record)
        record["query_note"] = (
            "Compatibilidad con los filtros y el texto. La posición actual de un anuncio "
            "vendido y la coincidencia interna del buscador no se pueden reconstruir."
        )
        if save_fixture:
            destination = root / "tests" / save_fixture / str(listing.id)
            destination.mkdir(parents=True, exist_ok=True)
            for path, body in client.captures.items():
                name = "item.html.gz" if path.startswith("/items/") else (
                    "seller.json.gz" if path.startswith("/api/v2/users/")
                    else "wardrobe.html.gz"
                )
                (destination / name).write_bytes(gzip.compress(body, mtime=0))
            for index, photo in enumerate(record["body"]["photos"]):
                path = image_path(folder / "images", photo)
                if path.is_file():
                    shutil.copyfile(path, destination / f"photo-{index}.jpg")
            (destination / "capture.json").write_text(json.dumps({
                "url": str(listing.url), "captured": now.isoformat(), "profile": profile.id,
                "expected": save_fixture, "result": record["tier"],
            }, ensure_ascii=False, indent=2), encoding="utf-8")
        return record


def evaluate_fixture(root: Path, directory: Path) -> dict[str, Any]:
    (root / "data").mkdir(exist_ok=True)
    manifest = json.loads((directory / "capture.json").read_text(encoding="utf-8"))
    now = datetime.fromisoformat(manifest["captured"])
    item = listing_from_item(
        gzip.decompress((directory / "item.html.gz").read_bytes()).decode(), manifest["url"], now
    )
    config = load_config(root, include_disabled=True)
    profile = select_profiles(item, config.profiles, config)[0]
    seller = None
    if (directory / "seller.json.gz").is_file():
        seller = parse_user(
            gzip.decompress((directory / "seller.json.gz").read_bytes()).decode(), item.seller_id
        )
        if (directory / "wardrobe.html.gz").is_file():
            seller.closet = parse_wardrobe(
                gzip.decompress((directory / "wardrobe.html.gz").read_bytes()).decode(),
                "https://www.vinted.es",
            )
    images = [
        (directory / f"photo-{index}.jpg").read_bytes()
        if (directory / f"photo-{index}.jpg").is_file() else None
        for index in range(len(item.photos))
    ]
    evidence = inspect_photos(
        images, root / (profile.refs_dir or Path("refs") / profile.id),
        root / "refs/stock", config.scoring.thresholds, True,
    )
    reason, passed = gate(item, profile, config, seller, evidence, detailed=True)
    with TemporaryDirectory(dir=root / "data") as temporary:
        with SQLiteStore(Path(temporary) / "fixture.sqlite") as store:
            pipeline = Pipeline(root, store, config, now)
            pipeline.record(
                item, profile, passed, evidence, False, seller, reason, enriched=True
            )
            record = store.record(item.id)
            assert record is not None
            return record
