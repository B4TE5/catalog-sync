"""Captura la portada y una página del catálogo de Vinted en una sola sesión."""

import argparse
import json
import random
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin

from curl_cffi import requests

SCRATCH = Path(__file__).resolve().parent
HOME = "https://www.vinted.es/"
CATALOG = f"{HOME}catalog?search_text=stone%20island&order=newest_first"
FLIGHT_SCRIPT = re.compile(
    r"<script\b[^>]*>self\.__next_f\.push\((\[.*?\])\)</script>", re.DOTALL
)
ITEMS_ARRAY = re.compile(r'"items"\s*:\s*\{\s*"items"\s*:\s*(\[)')
TARGET_COUNT = 10


def capture(session: requests.Session, url: str, name: str) -> requests.Response:
    response = session.get(url, timeout=30)
    path = SCRATCH / f"{name}.html"
    path.write_bytes(response.content)
    print(f"{name}: HTTP {response.status_code}, {len(response.content):,} bytes → {path}")
    print(f"  URL final: {response.url}")
    print(f"  Content-Type: {response.headers.get('Content-Type', '')}")
    title = re.search(r"<title[^>]*>([^<]*)</title>", response.text, re.IGNORECASE)
    if title:
        print(f"  Título: {title[1]}")
    return response


def extract_listings(html: str) -> list[dict[str, int | str]]:
    chunks = (json.loads(match[1]) for match in FLIGHT_SCRIPT.finditer(html))
    flight = "".join(chunk[1] for chunk in chunks if chunk[0] == 1)
    match = ITEMS_ARRAY.search(flight)
    if match is None:
        return []

    rows, _ = json.JSONDecoder().raw_decode(flight, match.start(1))
    listings: dict[int, dict[str, int | str]] = {}
    for row in rows:
        try:
            item = row["productItem"]
            listing_id = item["id"]
            title = item["title"]
            url = item["url"]
            amount = item["price"]["amount"]
            currency = item["price"]["currencyCode"]
        except (KeyError, TypeError):
            continue

        if (
            type(listing_id) is int
            and all(isinstance(value, str) and value.strip() for value in (title, amount, currency))
            and isinstance(url, str)
            and url.startswith(f"/items/{listing_id}-")
        ):
            listings[listing_id] = {
                "id": listing_id,
                "title": title,
                "price": amount,
                "currency": currency,
                "url": urljoin(HOME, url),
            }
    return list(listings.values())


def report_listings() -> int:
    html = (SCRATCH / "catalog.html").read_text(encoding="utf-8")
    listings = extract_listings(html)
    print(f"Anuncios únicos con ID, título, precio y URL extraídos del RSC: {len(listings)}")
    for listing in listings[:TARGET_COUNT]:
        print(json.dumps(listing, ensure_ascii=False))
    return 0 if len(listings) >= TARGET_COUNT else 1


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Analiza la captura local sin red.")
    if parser.parse_args().offline:
        return report_listings()

    try:
        with requests.Session(impersonate="chrome") as session:
            home = capture(session, HOME, "home")
            if home.status_code in {403, 429}:
                print("Portada bloqueada. Se interrumpe la prueba.")
                return 1
            time.sleep(random.uniform(3, 8))
            catalog = capture(session, CATALOG, "catalog")
    except requests.RequestsError as error:
        print(f"Error de transporte: {error}", file=sys.stderr)
        return 1
    return report_listings() if catalog.ok else 1


if __name__ == "__main__":
    sys.exit(main())
