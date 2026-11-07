"""Comprobaciones públicas reutilizadas por CLI y pruebas en vivo."""

from pathlib import Path

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.run import health
from vinted_hunter.sources.vinted.catalog import parse_catalog
from vinted_hunter.sources.vinted.client import VintedClient
from vinted_hunter.sources.vinted.parse import ParseError
from vinted_hunter.storage.sqlite_store import SQLiteStore

KNOWN_QUERY = "stone island"


def configured_ids(root: Path) -> list[str]:
    config = load_config(root)
    ids = config.ids
    missing = [f"marca {p.brand}" for p in config.profiles if p.brand not in ids.brand_ids]
    missing += [f"talla {size}" for size in ("L", "XL") if size not in ids.size_ids]
    for key in ("sweatshirts", "sweatshirts_parent", "jumpers", "knitted"):
        if key not in ids.catalog_ids:
            missing.append(f"categoría {key}")
    return missing


def check(root: Path) -> list[tuple[str, bool, str]]:
    config = load_config(root)
    capture = config.scoring.capture
    results = []
    with SQLiteStore(root / "data" / "vh.sqlite") as store:
        current = health(store, config)
        retry_at = store.setting("retry_at")
    missing = configured_ids(root)
    results.append(("Filtros utilizados", not missing, ", ".join(missing) or "IDs documentados"))
    results.append(("Salud", current in {"healthy", "unknown"}, current))
    if retry_at:
        from datetime import UTC, datetime

        if datetime.now(UTC) < datetime.fromisoformat(retry_at):
            return [*results, ("Red", False, f"Circuito en espera hasta {retry_at}")]
    with VintedClient(wait=capture.wait) as client:
        client.home()
        results.append(("Portada y cookies", bool(client.session.cookies), "HTTP 200"))
        response = client.get(
            "/catalog", "catalog", {
                "search_text": KNOWN_QUERY, "order": "newest_first",
                "catalog[]": config.ids.catalog_ids["sweatshirts_parent"],
            }
        )
        try:
            catalog = parse_catalog(response.text, client.base)
        except ParseError as error:
            raise ParseError(
                f"HTTP {response.status_code} · 0 anuncios reales · {error}"
            ) from error
        count = len(catalog.listings)
        results.append(
            ("Parser", count >= 10, f"HTTP {response.status_code} · {count} anuncios reales")
        )
        stone = config.ids.brand_ids.get("Stone Island")
        category = config.ids.catalog_ids.get("sweatshirts_parent")
        supreme = config.ids.brand_ids.get("Supreme")
        if stone and supreme and category:
            response = client.get(
                "/catalog",
                "catalog",
                {
                    "catalog[]": str(category),
                    "order": "newest_first",
                    "brand_ids[]": [str(stone[0]), str(supreme[0])],
                },
            )
            combined = parse_catalog(response.text, client.base).listings
            brands = {item.brand for item in combined}
            results.append(
                (
                    "Marcas combinadas",
                    brands == {"Stone Island", "Supreme"},
                    f"{len(combined)} anuncios · "
                    + ", ".join(sorted(brand or "sin marca" for brand in brands)),
                )
            )
        for label in ("L", "XL"):
            size = config.ids.size_ids.get(label)
            if not (size and stone and category):
                continue
            response = client.get(
                "/catalog",
                "catalog",
                {
                    "catalog[]": category,
                    "brand_ids[]": stone[0],
                    "size_ids[]": size,
                    "order": "newest_first",
                },
            )
            filtered = parse_catalog(response.text, client.base).listings
            coherent = bool(filtered) and all(
                item.brand == "Stone Island" and item.size == label for item in filtered
            )
            results.append((f"Filtro {label}", coherent, f"{len(filtered)} Stone Island {label}"))
    return results
