"""Muestra visual independiente de las decisiones del embudo."""

import json
import random
import time
from collections import Counter
from collections.abc import Callable
from contextlib import ExitStack
from datetime import UTC, datetime, timedelta
from functools import partial
from pathlib import Path
from typing import Any, TypeVar

from curl_cffi.requests import RequestsError

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.enrich import get_item, image_bytes
from vinted_hunter.pipeline.run import EventLog
from vinted_hunter.pipeline.vision import inspect_photos
from vinted_hunter.sources.vinted.catalog import VintedCatalog
from vinted_hunter.sources.vinted.client import (
    BudgetExhausted,
    CircuitOpen,
    HttpFailure,
    VintedClient,
)
from vinted_hunter.sources.vinted.parse import ParseError
from vinted_hunter.storage.sqlite_store import SQLiteStore

T = TypeVar("T")


def vision_check(
    root: Path,
    profile_id: str,
    limit: int,
    progress: Callable[[str], None],
) -> tuple[Path, dict[str, Any]]:
    config = load_config(root)
    profile = next((profile for profile in config.profiles if profile.id == profile_id), None)
    if profile is None:
        raise ValueError(f"Perfil activo desconocido: {profile_id}")
    brand_ids = config.ids.brand_ids.get(profile.brand)
    category = config.ids.catalog_ids.get(profile.hood) or config.ids.catalog_ids.get("sweatshirts")
    if not brand_ids or not category:
        raise ValueError("El perfil necesita IDs verificados de marca y categoría")

    settings = config.scoring.capture
    output = root / "out" / f"vision-check-{profile_id}.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    report: dict[str, Any] = {
        "profile": profile_id,
        "limit": limit,
        "category": category,
        "samples": [],
        "errors": [],
        "batches": [],
    }
    emit = EventLog(root / "data" / "logs")
    with SQLiteStore(root / "data" / "vh.sqlite") as store, ExitStack() as sessions:
        client: VintedClient | None = None

        def new_batch() -> VintedClient:
            if client is not None:
                sessions.close()
                time.sleep(random.uniform(*settings.wait))
            active = sessions.enter_context(
                VintedClient(
                    f"https://www.{profile.domain}",
                    settings.catalog_limit,
                    settings.enrich_limit,
                    settings.wait,
                    emit,
                )
            )
            report["batches"].append(active.counts)
            active.home()
            return active

        def request(operation: Callable[[VintedClient], T]) -> T:
            nonlocal client
            if client is None:
                client = new_batch()
            while True:
                try:
                    return operation(client)
                except BudgetExhausted:
                    client = new_batch()

        try:
            retry_at = store.setting("retry_at")
            if retry_at and datetime.now(UTC) < datetime.fromisoformat(retry_at):
                raise HttpFailure(f"Circuito en espera hasta {retry_at}")
            result = request(
                lambda c: VintedCatalog(c).search(
                    {
                        "catalog[]": str(category),
                        "brand_ids[]": [str(value) for value in brand_ids],
                        "order": "newest_first",
                    }
                )
            )
            refs = root / (profile.refs_dir or Path("refs") / profile.id)
            cache = root / "data" / "images"
            for listing in result.listings:
                if len(report["samples"]) == limit:
                    break
                started = time.monotonic()
                try:
                    detail = request(partial(get_item, listing=listing, now=datetime.now(UTC)))
                    images = request(
                        partial(
                            image_bytes,
                            listing=detail,
                            cache=cache,
                            settings=settings,
                            require_budget=True,
                        )
                    )
                    expected = len(detail.photos[: settings.max_photos])
                    vision_start = time.monotonic()
                    evidence = inspect_photos(
                        images,
                        refs,
                        root / "refs" / "stock",
                        config.scoring.thresholds,
                        True,
                    )
                    if len(evidence.hashes) != expected:
                        raise ParseError(f"{len(evidence.hashes)}/{expected} fotos analizables")
                except CircuitOpen:
                    raise
                except (RequestsError, HttpFailure, ParseError) as error:
                    report["errors"].append(f"{listing.id}: {error}")
                    progress(f"{listing.id} · omitido · {error}")
                    continue
                elapsed = round(time.monotonic() - started, 2)
                qr = (
                    "legible"
                    if evidence.qr_decoded
                    else ("ninguno" if evidence.qr == "none" else "detectado_sin_leer")
                )
                report["samples"].append(
                    {
                        "id": listing.id,
                        "url": str(listing.url),
                        "size": detail.size,
                        "price": str(detail.price),
                        "photos": len(images),
                        "qr": qr,
                        "classification": evidence.qr,
                        "phashes": evidence.hashes,
                        "orb_parts": evidence.parts_present,
                        "seconds": elapsed,
                        "vision_seconds": round(time.monotonic() - vision_start, 2),
                    }
                )
                progress(
                    f"{len(report['samples'])}/{limit} · {listing.id} · {len(images)} fotos · "
                    f"{qr} · {elapsed:.2f} s",
                )
        except CircuitOpen as error:
            failures = int(store.setting("failures", "0")) + 1
            wait = min(
                settings.max_backoff_seconds, settings.backoff_seconds * 2 ** min(failures - 1, 20)
            )
            store.set_setting("failures", str(failures))
            store.set_setting("retry_at", (datetime.now(UTC) + timedelta(seconds=wait)).isoformat())
            report["errors"].append(str(error))
        except (RequestsError, HttpFailure, ParseError, KeyboardInterrupt) as error:
            report["errors"].append(str(error) or "Interrumpido")

    counts = Counter(sample["qr"] for sample in report["samples"])
    report["qr"] = {key: counts[key] for key in ("legible", "detectado_sin_leer", "ninguno")}
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return output, report
