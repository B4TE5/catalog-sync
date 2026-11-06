"""Tablero local con datos embebidos y escritura atómica."""

import json
from base64 import b64encode
from decimal import Decimal
from hashlib import sha256
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

from vinted_hunter.config import load_config
from vinted_hunter.pipeline.run import health, market_for
from vinted_hunter.storage.sqlite_store import SQLiteStore


def build(root: Path, database: str = "vh.sqlite", folder: str = "board") -> Path:
    config = load_config(root)
    with SQLiteStore(root / "data" / database) as store:
        payload: dict[str, Any] = {
            "listings": store.records(),
            "run": next(iter(store.runs(1)), None),
            "health": health(store, config),
            "brands": {profile.id: profile.brand for profile in config.profiles},
        }
        markets = {profile.id: market_for(store, profile, config) for profile in config.profiles}
    cache = root / "data" / "images"
    for row in payload["listings"]:
        if row["tier"] is None or row["tier"] == "rejected":
            continue
        market = markets.get(row["profile"])
        row["market_samples"] = market.count if market else 0
        minimum = max(30, config.scoring.pricing["minimum_samples"])
        median = market.median if market and market.count >= minimum else None
        row["display_under_median"] = (
            round(float(1 - Decimal(row["body"]["price"]) / median) * 100, 1) if median else None
        )
        display_photos = []
        for url in row["body"]["photos"]:
            image = cache / sha256(url.encode()).hexdigest()
            if image.is_file():
                body = image.read_bytes()
                format_name = (
                    "webp"
                    if body.startswith(b"RIFF") and body[8:12] == b"WEBP"
                    else "jpeg"
                    if body.startswith(b"\xff\xd8")
                    else "png"
                    if body.startswith(b"\x89PNG")
                    else None
                )
                if format_name:
                    url = f"data:image/{format_name};base64,{b64encode(body).decode('ascii')}"
            display_photos.append(url)
        row["display_photos"] = display_photos
    embedded = json.dumps(payload, ensure_ascii=False).replace("<", "\\u003c")
    html = Path(__file__).with_name("template.html").read_text(encoding="utf-8")
    target = root / "out" / folder / "index.html"
    target.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", dir=target.parent, encoding="utf-8", delete=False) as file:
        temporary = Path(file.name)
        file.write(html.replace("__VH_DATA__", embedded))
    try:
        temporary.replace(target)
    finally:
        temporary.unlink(missing_ok=True)
    return target
